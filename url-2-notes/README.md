# URL to Short Notes
This folder contains a simple project that takes a URL as input and generates short notes from the content of the page.

## About this project :

1. Generally when using LLMs, we need to use the API key and other credentials to access the model.
2. But this project uses the LLMs locally, so no need to use the API key.
3. Generally when using LLMs locally, it could not read the content from the URL.
4. So this project fetches the content from the URL and generates short notes from it.
5. This Project uses BeautifulSoup to scrape the content from the URL.
6. With the extracted content, it uses the LLMs to generate short notes.

## How to use this project :
1. Clone the repository.
2. Install the required packages using the command:
```pip install -r requirements.txt```
3. Run the script using the command:
```python app.py```
4. In postman, use the following URL:
```[POST] : http://localhost:5000/summarize```
5. In the body, use the following JSON format:
```json
{
    "url": "https://www.example.com"
}
```
6. The response will be in the following format:
```json
{
    "summary": "This is a summary of the content from the URL."
}
```

## Note :
1. The project uses llama3.2 locally.

