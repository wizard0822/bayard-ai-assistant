import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.auth import credentials, default
from google.auth.transport import requests
from google.oauth2 import service_account
from vertexai import init
from vertex_ai_utils import initialize_vertex_ai, generate_model_output
from elasticsearch_utils import search_elasticsearch
import json

app = Flask(__name__)
CORS(app)

PROJECT_ID = os.environ.get('PROJECT_ID')
SECRET_URI = os.environ.get('SECRET_URI')

def get_secret(secret_uri):
    """Retrieve the secret value from Google Secret Manager."""
    try:
        _, project = default()
        if not project:
            raise ValueError("Project ID not found.")

        service = requests.SecretManagerServiceClient()
        response = service.access_secret_version(name=secret_uri)
        secret_value = response.payload.data.decode("UTF-8")

        return secret_value
    except Exception as e:
        print(f"Error retrieving secret: {e}")
        return None

# Retrieve the service account key from Google Secret Manager
key_path = get_secret(SECRET_URI)

# Load the credentials from the secret value
if key_path:
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(key_path)
    )
else:
    print("Could not load credentials from Google Secret Manager.")

initialize_vertex_ai()

@app.route("/health-check", methods=["GET"])
def health_check():
    return "OK", 200

@app.route("/api/bayard", methods=["POST"])
def handle_bayard_request():
    input_text = request.json.get("input_text")
    print(f"Received input_text: {input_text}")

    if not input_text:
        return jsonify({"error": "User input is required."}), 400

    filtered_docs = search_elasticsearch(input_text)
    print(f"Filtered documents: {filtered_docs}")

    if filtered_docs is None:
        return jsonify({"error": "Error occurred while searching Elasticsearch."}), 500

    model_output = generate_model_output(input_text, filtered_docs)
    print(f"Generated model output: {model_output}")

    return jsonify({"modelOutput": model_output}), 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)