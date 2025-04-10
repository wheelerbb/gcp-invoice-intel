from google.cloud import documentai_v1 as documentai
from .base_processor import BaseInvoiceProcessor
from src.config import (
    DOCUMENT_AI_PROCESSOR_ID,
    DOCUMENT_AI_LOCATION,
    GCP_PROJECT_ID,
)

class GeminiInvoiceProcessor(BaseInvoiceProcessor):
    # ... existing DocumentAIProcessor code ... 