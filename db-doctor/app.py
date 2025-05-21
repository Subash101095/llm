import os
import requests
from flask import Flask, request, jsonify
from typing import Optional
import json
import sqlparse

app = Flask(__name__)

# Configuration
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434/api/generate')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')

# Load schema.json once on startup
with open("schema.json", "r") as f:
    schema = json.load(f)


def generate_query(user_prompt: str) -> Optional[str]:
    prompt = f"""
    You are a SQL expert. Given this database schema:
    {json.dumps(schema, indent=2)}

    Generate an SQL query for the following request:
    {user_prompt}
    
    Only return the SQL query, nothing else.
    
    Generate the most efficient SQL query possible.
    
    If the request contains table names or column names that are not in the schema,
    or if the request is not possible to fulfill with the given schema,
    return "I cannot generate a SQL query for this request since the request 
    does not match with the schema provided."
    """

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,  # Get the full response at once
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

    formatted_sql = sqlparse.format(response, reindent=True, keyword_case='upper')

    # Return the summary as a JSON response
    return formatted_sql, 200


if __name__ == '__main__':
    # Set the port to the value from the environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
