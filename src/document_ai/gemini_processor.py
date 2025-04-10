from google.cloud import documentai_v1 as documentai
from .base_processor import BaseInvoiceProcessor
from src.config import (
    DOCUMENT_AI_PROCESSOR_ID,
    DOCUMENT_AI_LOCATION,
    GCP_PROJECT_ID,
)

class GeminiInvoiceProcessor(BaseInvoiceProcessor):
    def __init__(self):
        self.client = documentai.DocumentProcessorServiceClient()
        self.processor_name = self.client.processor_path(
            GCP_PROJECT_ID,
            DOCUMENT_AI_LOCATION,
            DOCUMENT_AI_PROCESSOR_ID,
        )

    def process_document(self, file_path: str) -> dict:
        """
        Process a document using Document AI with Gemini enhancement.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            dict: Structured invoice data
        """
        # Read the file into memory
        with open(file_path, "rb") as file:
            file_content = file.read()

        # Configure the process request
        document = documentai.Document(
            content=file_content,
            mime_type="application/pdf",  # Adjust based on file type
        )

        request = documentai.ProcessRequest(
            name=self.processor_name,
            document=document,
        )

        # Process the document
        result = self.client.process_document(request=request)
        document = result.document

        # Extract entities
        return self._extract_entities(document)

    def _extract_entities(self, document) -> dict:
        """
        Extract entities from the document.
        
        Args:
            document: Document AI document object
            
        Returns:
            dict: Extracted entities
        """
        text = document.text
        entities = {}
        for entity in document.entities:
            entities[entity.type_] = entity.mention_text

        return {
            "text": text,
            "entities": entities,
        } 