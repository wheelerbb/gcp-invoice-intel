from typing import Dict, Any, List
import uuid
from google.cloud import documentai
from .base_processor import BaseProcessor
from src.config import settings, logger
import json
from datetime import datetime

class DocumentAIProcessor(BaseProcessor):
    """Processor that uses Google Cloud Document AI for invoice processing."""
    
    def __init__(self):
        super().__init__()
        # Initialize Document AI client
        self.client = documentai.DocumentProcessorServiceClient()
        self.processor_name = f"projects/{settings.GCP_PROJECT_ID}/locations/us/processors/{settings.DOCUMENT_AI_PROCESSOR_ID}"
        logger.info(f"Initialized DocumentAIProcessor with processor: {self.processor_name}")

    def _process_document(self, file_path: str) -> Dict[str, Any]:
        """Process a document using Document AI.
        
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

        # Extract entities and convert to invoice data structure
        invoice_data = self._extract_entities(document)
        
        return invoice_data

    def _convert_date_format(self, date_str: str) -> str:
        """Convert date from MM/DD/YY to YYYY-MM-DD format"""
        if not date_str:
            return "1900-01-01"  # Default date for missing values
        try:
            # Try MM/DD/YY format first
            parsed_date = datetime.strptime(date_str, "%m/%d/%y")
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            try:
                # Try MM/DD/YYYY format as fallback
                parsed_date = datetime.strptime(date_str, "%m/%d/%Y")
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                return "1900-01-01"  # Default date for invalid values

    def process(self, file_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process a document file.
        
        Args:
            file_path: Path to the document file
            metadata: Additional metadata about the file
            
        Returns:
            dict: Processed document data
        """
        # Process the document
        document_data = self._process_document(file_path)
        
        # Add metadata and ensure processing_timestamp is set
        document_data.update(metadata)
        if "processing_timestamp" not in document_data:
            document_data["processing_timestamp"] = datetime.utcnow().isoformat()
        
        return document_data

    def _extract_entities(self, document: documentai.Document) -> Dict[str, Any]:
        """Extract entities from the document.
        
        Args:
            document: Document AI document object
            
        Returns:
            dict: Extracted invoice data
        """
        # Extract entities and convert to invoice data structure
        invoice_data = {
            "invoice_number": self._get_entity_value(document, "invoice_id"),
            "invoice_date": self._convert_date_format(self._get_entity_value(document, "invoice_date")),
            "due_date": self._convert_date_format(self._get_entity_value(document, "due_date")),
            "total_amount": self._convert_amount(self._get_entity_value(document, "total_amount")),
            "vendor_name": self._get_entity_value(document, "supplier_name"),
            "vendor_address": self._get_entity_value(document, "supplier_address"),
            "line_items": self._extract_line_items(document),  # Using base class implementation
            "payment_terms": self._get_entity_value(document, "payment_terms"),
            "notes": "",
            "raw_data": document.text,
            "processor_type": self.__class__.__name__,
            "processing_timestamp": datetime.utcnow().isoformat()
        }

        return invoice_data

    def _extract_line_items(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """Extract line items from the document."""
        line_items = []
        
        # Find all line item groups in the document
        for entity in document.entities:
            if entity.type_ == "line_item":
                # Get all properties for this line item
                properties = {prop.type_: prop.mention_text for prop in entity.properties}
                logger.info(f"Processing line item with properties: {properties}")
                
                # Extract description (may have multiple descriptions, use the first one)
                descriptions = [v for k, v in properties.items() if k == "line_item/description"]
                description = descriptions[0] if descriptions else ""
                logger.info(f"Found descriptions: {descriptions}, using: {description}")
                
                # Extract other fields
                quantity = self._convert_amount(properties.get("line_item/quantity", "0"))
                unit_price = self._convert_amount(properties.get("line_item/unit_price", "0"))
                amount = self._convert_amount(properties.get("line_item/amount", "0"))
                logger.info(f"Extracted fields - quantity: {quantity}, unit_price: {unit_price}, amount: {amount}")
                
                if description or quantity > 0 or unit_price > 0 or amount > 0:
                    item = {
                        "description": description,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "amount": amount
                    }
                    line_items.append(item)
                    logger.info(f"Added line item: {item}")
                else:
                    logger.info("Skipping line item due to no valid data")
                
        logger.info(f"Total line items extracted: {len(line_items)}")
        return line_items 