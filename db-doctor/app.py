import io
import json
import os
from typing import Optional

import google.generativeai as googleai
import requests
import sqlparse
from flask import Flask, send_file, render_template_string, request, jsonify
from graphviz import Digraph
from graphviz.backend import ExecutableNotFound

from prompts import QUERY_GENERATOR_PROMPT
from prompts import QUERY_OPTIMIZER_PROMPT

app = Flask(__name__)

# Initialize Google Generative AI
googleai.configure(api_key="AIzaSyDUXYOZPdmIbOQXf7VUAXIi9Ss5dgzTx58")
model = googleai.GenerativeModel('gemini-2.0-flash')

# Load schema.json once on startup
with open("schema.json", "r") as f:
    schema = json.load(f)


def generate_query(user_prompt: str, system_prompt: str) -> Optional[str]:
    prompt = f"""
        You are an SQL query generator and optimiser. Your sole purpose is to output highly optimized SQL queries and their performance analysis.
    
        Given this database schema: {json.dumps(schema, indent=2)}
        Given the user's request: {user_prompt}
    """

    prompt = prompt + " " + system_prompt
    prompt = prompt.strip()

    try:
        response = model.generate_content(prompt)
        data = response.text.strip()
        print(f"Generated response: {data}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Ollama: {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"Error parsing Ollama response: {e}")
        return None


def parse_and_format_sql_response(response: str) -> str:
    if response == "The request is irrelevant." or response == "I don't know.":
        return response

    lines = response.strip().split('\n')

    sql_query_start = -1
    explanation_start = -1
    relationship_impact_analysis_start = -1
    performance_report_start = -1

    # Find the starting line index for each major section
    for i, line in enumerate(lines):
        if line.startswith('a. SQL Query:') or line.startswith('a. Optimized SQL Query:'):
            sql_query_start = i
        elif line.startswith('b. Explanation of the Query:') or line.startswith('b. Explanation of the Optimization:'):
            explanation_start = i
        elif line.startswith('c. Relationship Impact Analysis:'):
            relationship_impact_analysis_start = i
        elif line.startswith('d. Performance Schema Report:') or line.startswith(
                'c. Performance Schema Report (for the Optimized Query):'):
            performance_report_start = i

    if not (
            sql_query_start != -1 and explanation_start != -1 and relationship_impact_analysis_start != -1 and performance_report_start != -1):
        print(lines)
        return "Error: Could not parse the expected response format. Section markers missing."

    sql_query_raw_lines = []
    for i in range(sql_query_start + 1, explanation_start):
        sql_query_raw_lines.append(lines[i])
    sql_query = "\n".join(sql_query_raw_lines).strip()
    formatted_sql = sqlparse.format(sql_query, reindent=True, keyword_case='upper')

    explanation_lines = []
    for i in range(explanation_start + 1, relationship_impact_analysis_start):
        explanation_lines.append(lines[i])
    explanation = "\n".join(explanation_lines).strip()

    impact_analysis_lines = []
    for i in range(relationship_impact_analysis_start + 1, performance_report_start):
        impact_analysis_lines.append(lines[i])
    impact_analysis = "\n".join(impact_analysis_lines).strip()

    performance_report_content_lines = lines[performance_report_start + 1:]

    performance_report = "\n".join(performance_report_content_lines).strip()

    output_parts = [
        f"## SQL Query\n{formatted_sql}",
        f"## Explanation of the Query\n{explanation}",
        f"## Impact of the Query\n{impact_analysis}",
        f"## Performance Schema Report\n{performance_report}"
    ]

    return "\n\n".join(output_parts)


def generate_schema_graph_bytes(schema_data, format='svg'):
    """
    Generates a graph visualization of the database schema and returns it as bytes.
    Uses HTML-like labels for richer node content.
    """
    dot = Digraph(comment='Database Schema', graph_attr={'rankdir': 'LR'})  # LR for Left-Right layout

    for table in schema_data.get('tables', []):
        table_name = table.get('name')
        if not table_name:
            continue

        # Start the HTML-like label for the table node
        html_label = f'''<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">
                          <TR><TD COLSPAN="2" BGCOLOR="lightblue"><B>{table_name}</B></TD></TR>'''

        for col in table.get('columns', []):
            col_name = col.get('name')
            col_type = col.get('type', '')
            pk_info = " (PK)" if col.get('primary_key') else ""

            # Escape parentheses in foreign_key string for HTML-like labels
            fk_text = ""
            if 'foreign_key' in col:
                # Replace ( and ) with their HTML entities to avoid syntax errors in DOT's HTML-like labels
                fk_target = col['foreign_key'].replace("(", "&#40;").replace(")", "&#41;")
                fk_text = f' <FONT COLOR="blue" POINT-SIZE="10">&#8594; {fk_target}</FONT>'

            # Add column details as a row in the HTML table
            html_label += f'''<TR><TD ALIGN="LEFT">{col_name}{pk_info}</TD><TD ALIGN="LEFT">{col_type}{fk_text}</TD></TR>'''

        html_label += '</TABLE>>'  # Close the HTML table and the entire HTML-like label

        # Add the node with the HTML-like label and 'none' shape
        dot.node(table_name, label=html_label, shape='none', fontname="Helvetica")

    # Add relationships (foreign keys) as edges
    for table in schema_data.get('tables', []):
        table_name = table.get('name')
        if not table_name:
            continue

        for col in table.get('columns', []):
            if 'foreign_key' in col:
                fk_info = col['foreign_key']
                try:
                    # Extract the target table name from "TargetTable(TargetColumn)"
                    target_table = fk_info.split('(')[0].strip()
                    # Create an edge from the foreign key table to the primary key table
                    # Label the edge with the foreign key column name
                    dot.edge(table_name, target_table, label=col.get('name'), fontname="Helvetica", color='blue')
                except IndexError:
                    print(f"Warning: Malformed foreign_key format for {table_name}.{col.get('name')}: {fk_info}")

    try:
        print(dot.source)

        # Render the graph to bytes in memory
        return dot.pipe(format=format)
    except ExecutableNotFound:
        print("ERROR: Graphviz 'dot' executable not found. Make sure Graphviz is installed and in your system's PATH.")
        return None
    except Exception as e:
        print(f"ERROR: Failed to generate graph: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Graphviz stderr: {e.stderr.decode('utf-8')}")
        return None


@app.post("/generate-sql")
def generate_sql():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    user_prompt = data['query']

    # Generate SQL Query
    response = generate_query(user_prompt, QUERY_GENERATOR_PROMPT)
    if response is None:
        return jsonify({"error": "Failed to Generate Query."}), 500

    # Return the summary as a JSON response
    return parse_and_format_sql_response(response), 200


@app.post("/optimize-sql")
def optimize_sql():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    user_prompt = data['query']

    # Generate SQL Query
    response = generate_query(user_prompt, QUERY_OPTIMIZER_PROMPT)
    if response is None:
        return jsonify({"error": "Failed to Generate Query."}), 500

    # Return the summary as a JSON response
    return parse_and_format_sql_response(response), 200


@app.route('/graph')
def index():
    """
    Renders a simple HTML page that includes the graph image.
    """
    return render_template_string("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>DB Schema Graph Viewer</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #333; }
                img { max-width: 100%; height: auto; border: 1px solid #ddd; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
            </style>
        </head>
        <body>
            <h1>Database Schema Graph</h1>
            <p>This graph visually represents the tables and their relationships defined in your `schema.json` file.</p>
            <img src="/schema-graph" alt="Database Schema Graph">
        </body>
        </html>
    """)


@app.route('/schema-graph')
def schema_graph_endpoint():
    """
    Endpoint to generate and serve the database schema graph image.
    Reads schema from 'schema.json'.
    """
    schema_file = 'schema.json'

    try:
        with open(schema_file, 'r') as f:
            schema_data = json.load(f)
    except FileNotFoundError:
        return "Schema file not found on the server.", 404
    except json.JSONDecodeError:
        return "Invalid JSON schema format. Check 'schema.json' syntax.", 500

    # Generate graph as PNG bytes
    graph_bytes = generate_schema_graph_bytes(schema_data, format='png')

    if graph_bytes is None:
        # Return a more descriptive error if graph generation failed
        return "Failed to generate graph image. Please check server logs for Graphviz errors (e.g., 'dot' executable not found or DOT syntax errors).", 500

    # Use io.BytesIO to treat bytes as a file-like object for send_file
    return send_file(io.BytesIO(graph_bytes), mimetype='image/png')


if __name__ == '__main__':
    # Set the port to the value from the environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
