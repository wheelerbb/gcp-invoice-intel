# GCP Invoice Processing with Gemini

This project implements an automated invoice processing system using Google Cloud Platform (GCP) services including Gemini AI. The system extracts structured data from invoices using Document AI and optionally refines the results using Gemini, storing the processed data in BigQuery.

## Features

- Automated invoice processing pipeline
- OCR and data extraction using Document AI
- Contextual understanding and refinement using Gemini
- Flexible processing modes (with/without Gemini)
- Data storage and analysis in BigQuery
- File tracking and inventory management
- Robust error handling and logging
- Support for both production and ad-hoc processing

## Processing Flows

### Document AI Only Flow (--no-gemini switch)
1. PDF invoice is uploaded to Cloud Storage
2. Document AI processes the document:
   - Extracts raw text
   - Identifies entities (invoice number, dates, amounts, etc.)
   - Extracts line items with quantities and prices
3. Results are parsed and structured
4. Data is stored in BigQuery with file tracking

### Document AI + Gemini Flow (default)
1. PDF invoice is uploaded to Cloud Storage
2. Document AI processes the document (same as above)
3. Gemini refines the extracted data:
   - Analyzes the raw text and Document AI output
   - Provides enhanced understanding of complex cases
   - Improves accuracy of extracted information
4. Results are parsed and structured
5. Data is stored in BigQuery with file tracking

Both flows include robust error handling and fallback mechanisms to ensure data consistency.

## To-Dos

- [ ] Prove test functionality
- [ ] Prove CI/CD functionality
- [ ] Prove cloud function config
- [ ] Prove cloud function execution
- [x] Add file operations and tracking
- [x] Solution multiple BQ entries per file
- [x] Capture whether Gemini was used in BQ
- [ ] Add performance metrics for both processing flows
- [x] Fix GCS file path handling
- [x] Add proper schema for GCS URI in BigQuery
- [ ] Improve line item extraction
- [ ] Add error handling for streaming buffer updates
- [ ] Add retry mechanism for BigQuery operations
- [ ] Add logging for processing metrics

## Prerequisites

- Python 3.9+
- Google Cloud Platform account
- GCP Service account with appropriate permissions:
  - BigQuery Data Editor
  - BigQuery Job User
  - BigQuery User
  - Storage Object Viewer
  - Document AI API User

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
     - Vertex AI (for Gemini)
     - BigQuery
   - Create a Cloud Storage bucket for invoice storage
   - Set up Document AI processor
   - Set up BigQuery dataset and tables

5. Set up environment variables:
```bash
cp .env.example .env
```
Edit `.env` with your GCP credentials and configuration:
- `GCS_BUCKET_NAME`: Your Cloud Storage bucket name
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to your service account key
- `DOCUMENT_AI_PROCESSOR_ID`: Your Document AI processor ID
- `BIGQUERY_DATASET`: Your BigQuery dataset name (default: invoice_processing)

## Project Structure

```
gcp-invoice-processing/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── document_ai/
│   │   ├── __init__.py
│   │   └── document_ai_processor.py
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

Process a single invoice:
```bash
python src/main.py path/to/invoice.pdf [--adhoc] [--no-gemini]
```

Options:
- `--adhoc`: Process in ad-hoc mode (non-production)
- `--no-gemini`: Skip Gemini refinement step

## Development

- Run tests: `pytest`
- Format code: `black src tests`
- Sort imports: `isort src tests`

## License

MIT License 
