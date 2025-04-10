# GCP Invoice Processing with Gemini

This project implements an automated invoice processing system using Google Cloud Platform (GCP) services including Gemini AI. The system extracts structured data from invoices using Document AI and Gemini and stores the results in BigQuery.

## To-Dos

- [ ] Prove test functionality
- [ ] Prove CI/CD functionality
- [ ] Prove cloud function config
- [ ] Prove cloud function execution

## Features

- Automated invoice processing pipeline
- OCR and data extraction using Document AI
- Contextual understanding and refinement using Gemini
- Data storage and analysis in BigQuery
- Serverless processing with Cloud Functions

## Prerequisites

- Python 3.9+
- Google Cloud Platform account
- GCP Service account with appropriate permissions

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd gcp-invoice-processing
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure GCP:
   - Enable required APIs in your GCP project:
     - Cloud Storage
     - Document AI
     - Vertex AI
     - Cloud Functions
   - Create a Cloud Storage bucket for invoice storage
   - Set up Document AI processor
   - Set up GCP permissions:
     ```bash
     # Make the script executable
     chmod +x scripts/setup_gcp_permissions.sh

     # Run the script with your project ID and service account email
     ./scripts/setup_gcp_permissions.sh <GCP_PROJECT_ID> <SERVICE_ACCOUNT_EMAIL>
     ```

5. Set up environment variables:
```bash
cp .env.example .env
```
  Edit `.env` with your GCP credentials and configuration.

6. Deploy Cloud Functions

## Project Structure

```
gcp-invoice-processing/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── storage/
│   │   ├── __init__.py
│   │   └── gcs_client.py
│   ├── document_ai/
│   │   ├── __init__.py
│   │   └── processor.py
│   ├── gemini/
│   │   ├── __init__.py
│   │   └── processor.py
│   └── bigquery/
│       ├── __init__.py
│       └── client.py
├── tests/
│   ├── __init__.py
│   └── test_main.py
├── requirements.txt
├── .env.example
└── README.md
```

## Usage

1. Upload invoices to the configured Cloud Storage bucket
2. The Cloud Function will automatically trigger the processing pipeline
3. Monitor processing status in the GCP Console
4. Query processed data in BigQuery

## Development

- Run tests: `pytest`
- Format code: `black src tests`
- Sort imports: `isort src tests`

## License

MIT License 
