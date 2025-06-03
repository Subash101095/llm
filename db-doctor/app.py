import json
import os
from typing import Optional

import requests
import sqlparse
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434/api/generate')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')

# Load schema.json once on startup
with open("schema.json", "r") as f:
    schema = json.load(f)


def generate_query(user_prompt: str) -> Optional[str]:
    prompt = f"""
    You are an SQL query generator. Your sole purpose is to output highly optimized SQL queries and their performance analysis.

    Given this database schema: {json.dumps(schema, indent=2)}
    Given the user's request: {user_prompt}

    **YOUR ENTIRE RESPONSE MUST STRICTLY FOLLOW ONE OF THE FORMATS BELOW. DO NOT INCLUDE ANY ADDITIONAL TEXT, INTRODUCTORY PHRASES, CONCLUDING REMARKS, OR CONVERSATIONAL ELEMENTS.**

    **Format 1: For Valid SQL Query Requests**
        a. SQL Query:
        [Generated SQL Query based on user request]

        b. Explanation of the Query:
        [Short explanation of the query's components and how it fulfills the user’s request]

        c. Performance Schema Report:
        ----------------------------------------------------------------------------------------------------------------
        | Metric                       | Value                                                                          
        |------------------------------|--------------------------------------------------------------------------------
        | Total Execution Time         | [Estimated for 1000 rows per table]                                            
        | Cost of Query                | [Estimated for 1000 rows per table]                                            
        | Number of Loops              | [Estimated for 1000 rows per table]                                            
        | Index Usage                  | [Yes/No]                                                                       
        | Potential Indexes            | [List of columns ONLY from the provided schema]                                
        | Temporary Table Usage        | [Yes/No]                                                                       
        | Recommendations Summary      | [Text]                                                                          
        -----------------------------------------------------------------------------------------------------------------
        Generate the report by calculating/estimating all relevant metrics based on a conceptual dataset where *each table* involved in the query contains **1000 rows**.
        **Crucially, all suggested indexes and optimization comments MUST strictly refer ONLY to tables and columns that are explicitly defined in the provided database schema.**

    **Format 2: For Irrelevant Requests**
    The request is irrelevant.

    **Format 3: For Uncertain Requests**
    I don't know.

    Remember, your output must be *only* one of the above formats, with no deviations.
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = requests.post(f"{OLLAMA_URL}", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Ollama: {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"Error parsing Ollama response: {e}")
        return None

def optimize_query(user_prompt: str) -> Optional[str]:
    prompt = f"""
    You are an SQL query optimizer. Your sole purpose is to output highly optimized SQL queries and their performance analysis.

    Given this database schema: {json.dumps(schema, indent=2)}
    Given the user's SQL query: {user_prompt}

    **YOUR ENTIRE RESPONSE MUST STRICTLY FOLLOW ONE OF THE FORMATS BELOW. DO NOT INCLUDE ANY ADDITIONAL TEXT, INTRODUCTORY PHRASES, CONCLUDING REMARKS, OR CONVERSATIONAL ELEMENTS.**

    **Format 1: For Valid SQL Query Optimization Requests**
        a. Optimized SQL Query:
        [The most highly optimized version of the user's provided SQL query
        CRITICAL: The optimized query MUST produce the exact same result set (including order, if specified by ORDER BY) as the original query for any given data.
        DO NOT add, remove, or modify WHERE, HAVING, or JOIN conditions in a way that changes the logical outcome or filtering criteria. Only rewrite them for equivalent logical and performance gains (e.g., rewriting `A OR B` with `UNION ALL` if semantically equivalent and beneficial, or simplifying `X = X` conditions).
        DO NOT introduce new columns, tables, or operations (like `c.Email LIKE ''`) unless they are strictly necessary for the original query's logic and were somehow implicit.]

        b. Explanation of the Optimization:
        [A concise explanation detailing the specific optimizations applied to the user's query, how these changes improve performance, and how the optimized query achieves the original query's intent.]

        c. Performance Schema Report (for the Optimized Query):
        ----------------------------------------------------------------------------------------------------------------
        | Metric                       | Value                                                                          
        |------------------------------|--------------------------------------------------------------------------------
        | Total Execution Time         | [Estimated for 1000 rows per table]                                            
        | Cost of Query                | [Estimated for 1000 rows per table]                                            
        | Number of Loops              | [Estimated for 1000 rows per table]                                            
        | Index Usage                  | [Yes/No]                                                                       
        | Potential Indexes            | [List of columns ONLY from the provided schema]                                
        | Temporary Table Usage        | [Yes/No]                                                                       
        | Recommendations Summary      | [Text]                                                                         
        ----------------------------------------------------------------------------------------------------------------
        Generate this report by calculating/estimating all relevant metrics for the *Optimized SQL Query* (from section 'a') based on a conceptual dataset where *each table* involved in the query contains **1000 rows**.
        **Crucially, all suggested indexes and optimization comments MUST strictly refer ONLY to tables and columns that are explicitly defined in the provided database schema.**

    **Format 2: For Irrelevant Requests (e.g., if the user provides non-SQL text, incomplete SQL, or a query that cannot be optimized against the schema)**
    The request is irrelevant.

    **Format 3: For Uncertain Requests (e.g., if the query is too complex, ambiguous, or if optimization is not clear-cut)**
    I don't know.

    Remember, your output must be *only* one of the above formats, with no deviations.
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = requests.post(f"{OLLAMA_URL}", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
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
    performance_report_start = -1

    # Find the starting line index for each major section
    for i, line in enumerate(lines):
        if line.startswith('a. SQL Query:') or line.startswith('a. Optimized SQL Query:'):
            sql_query_start = i
        elif line.startswith('b. Explanation of the Query:') or line.startswith('b. Explanation of the Optimization:'):
            explanation_start = i
        elif line.startswith('c. Performance Schema Report:') or line.startswith('c. Performance Schema Report (for the Optimized Query):'):
            performance_report_start = i

    if not (sql_query_start != -1 and explanation_start != -1 and performance_report_start != -1):
        print(lines)
        return "Error: Could not parse the expected response format. Section markers missing."

    sql_query_raw_lines = []
    for i in range(sql_query_start + 1, explanation_start):
        sql_query_raw_lines.append(lines[i])
    sql_query = "\n".join(sql_query_raw_lines).strip()
    formatted_sql = sqlparse.format(sql_query, reindent=True, keyword_case='upper')

    explanation_lines = []
    for i in range(explanation_start + 1, performance_report_start):
        explanation_lines.append(lines[i])
    explanation = "\n".join(explanation_lines).strip()

    performance_report_content_lines = lines[performance_report_start + 1:]

    performance_report = "\n".join(performance_report_content_lines).strip()

    output_parts = [
        f"## SQL Query\n{formatted_sql}",
        f"## Explanation of the Query\n{explanation}",
        f"## Performance Schema Report\n{performance_report}"
    ]

    return "\n\n".join(output_parts)


@app.post("/generate-sql")
def generate_sql():
    # Check if the request has JSON data
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    user_prompt = data['query']

    # Generate SQL Query
    response = generate_query(user_prompt)
    if response is None:
        return jsonify({"error": "Failed to Generate Query. Check Ollama is running and the model is available."}), 500

    # Return the summary as a JSON response
    return parse_and_format_sql_response(response), 200


@app.post("/optimize-sql")
def optimize_sql():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    user_prompt = data['query']

    # Generate SQL Query
    response = optimize_query(user_prompt)
    if response is None:
        return jsonify({"error": "Failed to Generate Query. Check Ollama is running and the model is available."}), 500

    # Return the summary as a JSON response
    return parse_and_format_sql_response(response), 200


if __name__ == '__main__':
    # Set the port to the value from the environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
