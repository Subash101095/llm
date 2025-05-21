import os
import requests
from flask import Flask, request, jsonify
from urllib.parse import urlparse
from typing import Optional
from bs4 import BeautifulSoup

app = Flask(__name__)

# Configuration
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')

def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def get_page_content(url: str) -> Optional[str]:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style tags
        for script_or_style in soup.body(['script', 'style', 'img', 'input', 'button']):
            script_or_style.decompose()
        text = soup.body.get_text(separator='\n', strip=True)  # Get text, separated by newlines

        return text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL content: {e}")
        return None
    except Exception as e:
        print(f"Error processing page content: {e}")
        return None


def summarize_text(text: str) -> Optional[str]:
    prompt = (f"Summarize the following text: {text}. "
              f"Provide a concise summary of the key information, and nothing else.  "
              f"Do not include any preamble or extra text.  "
              f"Keep the summary under 200 words."
              f"Do not give false information.  "
              f"Generate in bullet points.  ")

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,  # Get the full response at once
    }

    try:
        response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Ollama: {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"Error parsing Ollama response: {e}")
        return None


# Flask route to handle incoming requests which will be used to summarize the content of a URL
@app.route('/summarize', methods=['POST'])
def summarize():
    # Check if the request has JSON data
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "Missing 'url' in request body"}), 400

    url = data['url']
    if not is_valid_url(url):
        return jsonify({"error": "Invalid URL"}), 400

    # Fetch the page content
    page_content = get_page_content(url)
    if page_content is None:
        return jsonify({"error": "Failed to retrieve content from the URL"}), 500

    # Summarize the page content
    summary = summarize_text(page_content)
    if summary is None:
        return jsonify({"error": "Failed to summarize content. Check Ollama is running and the model is available."}), 500

    # Return the summary as a JSON response
    return jsonify({"summary": summary}), 200


if __name__ == '__main__':
    # Set the port to the value from the environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
