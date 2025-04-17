from google.cloud import documentai_v1 as documentai
from .base_processor import BaseInvoiceProcessor
from datetime import datetime
import uuid
from src.config import (
    DOCUMENT_AI_PROCESSOR_ID,
    DOCUMENT_AI_LOCATION,
    GCP_PROJECT_ID,
)

class SimpleInvoiceProcessor(BaseInvoiceProcessor):
    def __init__(self):
        self.client = documentai.DocumentProcessorServiceClient()
        self.processor_name = self.client.processor_path(
            GCP_PROJECT_ID,
            DOCUMENT_AI_LOCATION,
            DOCUMENT_AI_PROCESSOR_ID,
        )

    def _convert_date_format(self, date_str: str) -> str:
        """Convert date from MM/DD/YYYY to YYYY-MM-DD format"""
        if not date_str:
            # Use invoice date as due date if not provided
            return "1900-01-01"  # Default date for missing values
        try:
            parsed_date = datetime.strptime(date_str, "%m/%d/%Y")
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            return "1900-01-01"  # Default date for invalid values

    def _convert_amount(self, amount_str: str) -> float:
        """Convert string amount to float, handling commas and currency symbols"""
        if not amount_str:
            return 0.0
        try:
            # Remove currency symbols and commas
            clean_amount = amount_str.replace("$", "").replace(",", "").strip()
            return float(clean_amount)
        except ValueError:
            return 0.0

    def process_document(self, file_path: str) -> dict:
        """
        Process a document using only Document AI.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            dict: Structured invoice data
        """
        # Read the file into memory
        with open(file_path, "rb") as file:
            file_content = file.read()

        # Configure the process request
        raw_document = documentai.RawDocument(
            content=file_content,
            mime_type="application/pdf",  # Adjust based on file type
        )

        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document,
        )

        # Process the document
        result = self.client.process_document(request=request)
        document = result.document

        # Generate a unique invoice ID
        invoice_id = str(uuid.uuid4())

        # Convert Document AI entities directly to invoice data structure
        invoice_data = {
            "invoice_id": invoice_id,
            "invoice_number": self._get_entity_value(document, "invoice_id"),
            "invoice_date": self._convert_date_format(self._get_entity_value(document, "invoice_date")),
            "due_date": self._convert_date_format(self._get_entity_value(document, "due_date")),
            "total_amount": self._convert_amount(self._get_entity_value(document, "total_amount")),
            "vendor_name": self._get_entity_value(document, "supplier_name"),
            "vendor_address": self._get_entity_value(document, "supplier_address"),
            "line_items": self._extract_line_items(document),
            "payment_terms": self._get_entity_value(document, "payment_terms"),
            "notes": "",
            "raw_data": document.text
        }

        return invoice_data

    def _extract_entities(self, document: documentai.Document) -> dict:
        """Extract raw entities from the document"""
        entities = {}
        for entity in document.entities:
            entity_type = entity.type_
            entity_text = entity.mention_text
            
            if entity_type not in entities:
                entities[entity_type] = []
                
            entities[entity_type].append(entity_text)
            
        return entities

    def _get_entity_value(self, document: documentai.Document, entity_type: str) -> str:
        """Get the first value of an entity type"""
        for entity in document.entities:
            if entity.type_ == entity_type:
                return entity.mention_text
        return ""

    def _extract_line_items(self, document: documentai.Document) -> list:
        """Extract line items from the document"""
        line_items = []
        
        # Find all line item groups in the document
        for entity in document.entities:
            if entity.type_ == "line_item":
                item = {
                    "description": self._get_nested_entity(entity, "item_description"),
                    "quantity": self._convert_amount(self._get_nested_entity(entity, "quantity")),
                    "unit_price": self._convert_amount(self._get_nested_entity(entity, "unit_price")),
                    "amount": self._convert_amount(self._get_nested_entity(entity, "amount"))
                }
                line_items.append(item)
                
        return line_items

    def _get_nested_entity(self, parent_entity, property_type: str) -> str:
        """Get nested entity value from a parent entity"""
        for prop in parent_entity.properties:
            if prop.type_ == property_type:
                return prop.mention_text
        return "" 