import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# GCP Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_REGION = os.getenv("GCP_REGION")
GCP_LOCATION = os.getenv("GCP_LOCATION")

# Cloud Storage
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

# Document AI
DOCUMENT_AI_PROCESSOR_ID = os.getenv("DOCUMENT_AI_PROCESSOR_ID")
DOCUMENT_AI_LOCATION = os.getenv("DOCUMENT_AI_LOCATION")

# BigQuery
BIGQUERY_DATASET_ID = os.getenv("BIGQUERY_DATASET_ID")
BIGQUERY_TABLE_ID = os.getenv("BIGQUERY_TABLE_ID")

# Vertex AI
VERTEX_AI_MODEL_ID = os.getenv("VERTEX_AI_MODEL_ID")
VERTEX_AI_ENDPOINT = os.getenv("VERTEX_AI_ENDPOINT")

# Service Account
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Validate required environment variables
required_vars = [
    GCP_PROJECT_ID,
    GCP_REGION,
    GCP_LOCATION,
    GCS_BUCKET_NAME,
    DOCUMENT_AI_PROCESSOR_ID,
    DOCUMENT_AI_LOCATION,
    BIGQUERY_DATASET_ID,
    BIGQUERY_TABLE_ID,
    VERTEX_AI_MODEL_ID,
    GOOGLE_APPLICATION_CREDENTIALS,
]

if not all(required_vars):
    missing_vars = [var for var in required_vars if not var]
    raise ValueError(f"Missing required environment variables: {missing_vars}") 