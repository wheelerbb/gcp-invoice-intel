from google.cloud import documentai_v1 as documentai
from .base_processor import BaseInvoiceProcessor
from datetime import datetime
import uuid
import json
import google.generativeai as genai
from src.config import (
    DOCUMENT_AI_PROCESSOR_ID,
    DOCUMENT_AI_LOCATION,
    GCP_PROJECT_ID,
    GEMINI_API_KEY,
)

class GeminiInvoiceProcessor(BaseInvoiceProcessor):
    def __init__(self):
        self.client = documentai.DocumentProcessorServiceClient()
        self.processor_name = self.client.processor_path(
            GCP_PROJECT_ID,
            DOCUMENT_AI_LOCATION,
            DOCUMENT_AI_PROCESSOR_ID,
        )
        # Initialize Gemini client
        genai.configure(api_key=GEMINI_API_KEY)
        self.gemini_client = genai.GenerativeModel('gemini-1.5-pro')

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

        # Extract entities and format the data
        entities = self._extract_entities(document)
        
        # Convert to the same format as SimpleInvoiceProcessor
        invoice_data = {
            "invoice_id": invoice_id,
            "invoice_number": entities.get("invoice_id", ""),
            "invoice_date": self._convert_date_format(entities.get("invoice_date", "")),
            "due_date": self._convert_date_format(entities.get("due_date", "")),
            "total_amount": self._convert_amount(entities.get("total_amount", "")),
            "vendor_name": entities.get("supplier_name", ""),
            "vendor_address": entities.get("supplier_address", ""),
            "line_items": self._extract_line_items(document),
            "payment_terms": entities.get("payment_terms", ""),
            "notes": "",
            "raw_data": document.text
        }

        # Refine the data using Gemini
        return self.refine_invoice_data(invoice_data)

    def _extract_entities(self, document) -> dict:
        """
        Extract entities from the document.
        
        Args:
            document: Document AI document object
            
        Returns:
            dict: Extracted entities
        """
        entities = {}
        for entity in document.entities:
            entities[entity.type_] = entity.mention_text
        return entities

    def _extract_line_items(self, document: documentai.Document) -> list:
        """Extract line items from the document"""
        line_items = []
        
        # Find all line item groups in the document
        for entity in document.entities:
            if entity.type_ == "line_item":
                item = {
                    "description": self._get_nested_entity(entity, "item_description"),
                    "quantity": float(self._get_nested_entity(entity, "quantity") or 0),
                    "unit_price": float(self._get_nested_entity(entity, "unit_price") or 0),
                    "amount": float(self._get_nested_entity(entity, "amount") or 0)
                }
                line_items.append(item)
                
        return line_items

    def _get_nested_entity(self, parent_entity, property_type: str) -> str:
        """Get nested entity value from a parent entity"""
        for prop in parent_entity.properties:
            if prop.type_ == property_type:
                return prop.mention_text
        return ""

    def refine_invoice_data(self, invoice_data: dict) -> dict:
        """
        Refine the invoice data using Gemini's capabilities.
        
        Args:
            invoice_data: Initial invoice data from Document AI
            
        Returns:
            dict: Refined invoice data
        """
        # Use Gemini to enhance the line items extraction
        prompt = f"""
        Analyze the following invoice text and extract line items:
        
        {invoice_data['raw_data']}
        
        Extract line items with the following structure:
        - description: Item description
        - quantity: Number of units
        - unit_price: Price per unit
        - amount: Total amount for the line
        
        Return ONLY a valid JSON array of line items, with no additional text or explanation.
        Example format:
        [
            {{
                "description": "Item 1",
                "quantity": 1,
                "unit_price": 100.00,
                "amount": 100.00
            }},
            {{
                "description": "Item 2",
                "quantity": 2,
                "unit_price": 50.00,
                "amount": 100.00
            }}
        ]
        """
        
        try:
            # Call Gemini API to refine the data
            response = self.gemini_client.generate_content(prompt)
            # Extract JSON from the response
            response_text = response.text.strip()
            # Remove any markdown code block markers if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            refined_line_items = json.loads(response_text)
            
            # Update the invoice data with refined line items
            invoice_data["line_items"] = refined_line_items
            
            return invoice_data
        except Exception as e:
            print(f"Error refining invoice data: {str(e)}")
            return invoice_data 