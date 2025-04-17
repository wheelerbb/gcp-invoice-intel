from typing import Dict, Any, List
import uuid
from google.cloud import documentai_v1 as documentai
from .base_processor import BaseInvoiceProcessor
from src.config import settings, logger
import json
from datetime import datetime

class DocumentAIProcessor(BaseInvoiceProcessor):
    """Base processor for Document AI functionality."""
    
    def __init__(self):
        super().__init__()
        self.client = documentai.DocumentProcessorServiceClient.from_service_account_json(settings.GOOGLE_APPLICATION_CREDENTIALS)
        self.processor_name = self.client.processor_path(
            settings.GCP_PROJECT_ID,
            settings.DOCUMENT_AI_LOCATION,
            settings.DOCUMENT_AI_PROCESSOR_ID,
        )
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

    def _extract_entities(self, document: documentai.Document) -> Dict[str, Any]:
        """Extract entities from the document.
        
        Args:
            document: Document AI document object
            
        Returns:
            dict: Extracted invoice data
        """
        # Generate a unique invoice ID
        invoice_id = str(uuid.uuid4())

        # Extract entities and convert to invoice data structure
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
            "raw_data": document.text,
            "processor_type": self.__class__.__name__
        }

        return invoice_data 

    def _extract_line_items(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """Extract line items from the document."""
        line_items = []
        
        # First try to get line items from tables
        for table in document.pages[0].tables:
            # Look for rows that have numeric values in the right columns
            for row in table.body_rows:
                cells = [cell.text for cell in row.cells]
                if len(cells) >= 4:  # Need at least description, quantity, price, amount
                    try:
                        # Try to parse numeric values
                        quantity = float(cells[1].strip()) if cells[1].strip() else None
                        unit_price = float(cells[2].strip().replace('$', '')) if cells[2].strip() else None
                        amount = float(cells[3].strip().replace('$', '')) if cells[3].strip() else None
                        
                        # Get description from first cell
                        description = cells[0].strip()
                        
                        # If description is empty but we have a product code, use that
                        if not description and len(cells) > 4:
                            description = cells[4].strip()
                        
                        if description and (quantity is not None or amount is not None):
                            line_items.append({
                                "description": description,
                                "quantity": quantity,
                                "unit_price": unit_price,
                                "amount": amount
                            })
                    except (ValueError, IndexError):
                        continue
        
        # If no line items found in tables, try to extract from raw text
        if not line_items:
            # Look for patterns like "quantity description price amount"
            text = document.text
            lines = text.split('\n')
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 4:
                    try:
                        quantity = float(parts[0])
                        unit_price = float(parts[-2].replace('$', ''))
                        amount = float(parts[-1].replace('$', ''))
                        description = ' '.join(parts[1:-2])
                        
                        line_items.append({
                            "description": description,
                            "quantity": quantity,
                            "unit_price": unit_price,
                            "amount": amount
                        })
                    except (ValueError, IndexError):
                        continue
        
        return line_items 