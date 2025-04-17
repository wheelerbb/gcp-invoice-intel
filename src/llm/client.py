from google.cloud import documentai_v1 as documentai
import google.generativeai as genai
from datetime import datetime
import json
from src.config import (
    DOCUMENT_AI_PROCESSOR_ID,
    DOCUMENT_AI_LOCATION,
    GCP_PROJECT_ID,
    GEMINI_API_KEY,
)

class LLMClient:
    def __init__(self):
        # Initialize Document AI client
        self.document_ai_client = documentai.DocumentProcessorServiceClient()
        self.processor_name = self.document_ai_client.processor_path(
            GCP_PROJECT_ID,
            DOCUMENT_AI_LOCATION,
            DOCUMENT_AI_PROCESSOR_ID,
        )
        
        # Initialize Gemini client
        genai.configure(api_key=GEMINI_API_KEY)
        self.gemini_client = genai.GenerativeModel('gemini-1.5-pro')

    def process_invoice(self, file_path: str) -> dict:
        """
        Process an invoice file using Document AI and Gemini.
        
        Args:
            file_path: Path to the invoice file
            
        Returns:
            dict: Structured invoice data
        """
        # 1. Process with Document AI
        document_ai_output = self._process_with_document_ai(file_path)
        
        # 2. Refine with Gemini
        refined_data = self._refine_with_gemini(document_ai_output)
        
        return refined_data

    def _process_with_document_ai(self, file_path: str) -> dict:
        """
        Process document using Document AI.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            dict: Document AI output
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
        result = self.document_ai_client.process_document(request=request)
        document = result.document

        # Extract entities and format the data
        entities = self._extract_entities(document)
        
        return {
            "text": document.text,
            "entities": entities,
            "line_items": self._extract_line_items(document)
        }

    def _refine_with_gemini(self, document_ai_output: dict) -> dict:
        """
        Refine Document AI output using Gemini.
        
        Args:
            document_ai_output: Output from Document AI processing
            
        Returns:
            dict: Refined invoice data
        """
        prompt = self._create_prompt(document_ai_output)
        
        try:
            response = self.gemini_client.generate_content(prompt)
            refined_data = self._parse_response(response.text)
            
            # Add raw data for reference
            refined_data["raw_data"] = document_ai_output["text"]
            
            return refined_data
        except Exception as e:
            print(f"Error refining data with Gemini: {str(e)}")
            return self._fallback_data(document_ai_output)

    def _create_prompt(self, document_ai_output: dict) -> str:
        """
        Create a prompt for Gemini based on Document AI output.
        
        Args:
            document_ai_output: Output from Document AI processing
            
        Returns:
            str: Formatted prompt
        """
        text = document_ai_output.get("text", "")
        entities = document_ai_output.get("entities", {})
        line_items = document_ai_output.get("line_items", [])
        
        prompt = f"""
        Analyze the following invoice text and extracted entities to provide a structured response:
        
        Invoice Text:
        {text}
        
        Extracted Entities:
        {entities}
        
        Line Items:
        {line_items}
        
        Please provide a structured response with the following information:
        1. Invoice number
        2. Invoice date (in YYYY-MM-DD format)
        3. Due date (in YYYY-MM-DD format)
        4. Total amount (as a float)
        5. Vendor information (name and address)
        6. Line items (with description, quantity, unit_price, and amount)
        7. Payment terms
        8. Any special notes or conditions
        
        Format the response as a JSON object with these fields. Ensure all dates are in YYYY-MM-DD format
        and all amounts are floats. If any information is missing or unclear, use appropriate default values.
        """
        
        return prompt

    def _parse_response(self, response_text: str) -> dict:
        """
        Parse the Gemini response into a structured format.
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            dict: Parsed response data
        """
        try:
            # Remove any markdown code block markers if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
                
            # Parse the JSON response
            data = json.loads(response_text)
            
            # Ensure required fields are present
            required_fields = {
                "invoice_number": "",
                "invoice_date": "1900-01-01",
                "due_date": "1900-01-01",
                "total_amount": 0.0,
                "vendor_name": "",
                "vendor_address": "",
                "line_items": [],
                "payment_terms": "",
                "notes": ""
            }
            
            # Update with parsed data, keeping defaults for missing fields
            for field, default in required_fields.items():
                if field not in data:
                    data[field] = default
                    
            return data
            
        except json.JSONDecodeError:
            print(f"Failed to parse Gemini response: {response_text}")
            return self._fallback_data({"text": response_text})

    def _fallback_data(self, document_ai_output: dict) -> dict:
        """
        Generate fallback data when Gemini processing fails.
        
        Args:
            document_ai_output: Output from Document AI processing
            
        Returns:
            dict: Basic invoice data structure
        """
        return {
            "invoice_number": "",
            "invoice_date": "1900-01-01",
            "due_date": "1900-01-01",
            "total_amount": 0.0,
            "vendor_name": "",
            "vendor_address": "",
            "line_items": [],
            "payment_terms": "",
            "notes": "",
            "raw_data": document_ai_output.get("text", "")
        }

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

    def _extract_line_items(self, document) -> list:
        """
        Extract line items from the document.
        
        Args:
            document: Document AI document object
            
        Returns:
            list: Extracted line items
        """
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
        """
        Get nested entity value from a parent entity.
        
        Args:
            parent_entity: Parent entity object
            property_type: Type of property to extract
            
        Returns:
            str: Extracted property value
        """
        for prop in parent_entity.properties:
            if prop.type_ == property_type:
                return prop.mention_text
        return "" 