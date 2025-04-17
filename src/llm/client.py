from google.cloud import documentai_v1 as documentai
import google.generativeai as genai
from datetime import datetime, timedelta
import json
import re
from src.config import (
    DOCUMENT_AI_PROCESSOR_ID,
    DOCUMENT_AI_LOCATION,
    GCP_PROJECT_ID,
    GEMINI_API_KEY,
)

class LLMClient:
    def __init__(self, use_gemini: bool = True):
        # Initialize Document AI client
        self.document_ai_client = documentai.DocumentProcessorServiceClient()
        self.processor_name = self.document_ai_client.processor_path(
            GCP_PROJECT_ID,
            DOCUMENT_AI_LOCATION,
            DOCUMENT_AI_PROCESSOR_ID,
        )
        
        # Initialize Gemini client if needed
        self.use_gemini = use_gemini
        if use_gemini:
            genai.configure(api_key=GEMINI_API_KEY)
            self.gemini_client = genai.GenerativeModel('gemini-1.5-pro')

    def process_invoice(self, file_path: str) -> dict:
        """
        Process an invoice file using Document AI and optionally Gemini.
        
        Args:
            file_path: Path to the invoice file
            
        Returns:
            dict: Structured invoice data
        """
        # Process with Document AI
        document_ai_output = self._process_with_document_ai(file_path)
        
        if self.use_gemini:
            # Refine with Gemini
            refined_data = self._refine_with_gemini(document_ai_output)
        else:
            # Use Document AI output directly
            refined_data = self._parse_document_ai_output(document_ai_output)
        
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

        try:
            # Process the document
            result = self.document_ai_client.process_document(request=request)
            document = result.document
            
            # Print document structure for debugging
            print("Document structure:", document)
            
            # Extract text and entities
            text = document.text if hasattr(document, 'text') else ""
            entities = self._extract_entities(document)
            line_items = self._extract_line_items(document)
            
            # Print extracted data for debugging
            print("Extracted text:", text)
            print("Extracted entities:", entities)
            print("Extracted line items:", line_items)
            
            return {
                "text": text,
                "entities": entities,
                "line_items": line_items
            }
        except Exception as e:
            print(f"Error processing document with Document AI: {str(e)}")
            return {
                "text": "",
                "entities": {},
                "line_items": []
            }

    def _refine_with_gemini(self, document_ai_output: dict) -> dict:
        """
        Refine Document AI output using Gemini.
        
        Args:
            document_ai_output: Output from Document AI processing
            
        Returns:
            dict: Refined invoice data
        """
        # Print document_ai_output structure for debugging
        print("Document AI output structure:", document_ai_output)
        
        # Get the raw text from document_ai_output
        raw_text = document_ai_output.get("text", "")
        entities = document_ai_output.get("entities", {})
        line_items = document_ai_output.get("line_items", [])
        
        # Create a structured data object from Document AI output
        structured_data = {
            "invoice_number": entities.get("invoice_id", ""),
            "invoice_date": entities.get("invoice_date", "1900-01-01"),
            "due_date": entities.get("due_date", "1900-01-01"),
            "total_amount": float(entities.get("total_amount", "0").replace("$", "").replace(",", "")) if entities.get("total_amount") else 0.0,
            "vendor_name": entities.get("supplier_name", ""),
            "vendor_address": entities.get("supplier_address", ""),
            "line_items": line_items,
            "payment_terms": entities.get("payment_terms", ""),
            "notes": "",
            "raw_data": raw_text
        }
        
        # If Gemini is not enabled, return the structured data
        if not self.use_gemini:
            return structured_data
        
        # Create prompt for Gemini
        prompt = self._create_prompt(document_ai_output)
        
        try:
            response = self.gemini_client.generate_content(prompt)
            # Get the text from the response parts
            response_text = response.text if hasattr(response, 'text') else response.parts[0].text
            print("Gemini response text:", response_text)  # Debug print
            refined_data = self._parse_response(response_text)
            
            # Add raw data for reference
            refined_data["raw_data"] = raw_text
            
            return refined_data
        except Exception as e:
            print(f"Error refining data with Gemini: {str(e)}")
            return structured_data

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
            
            # Clean up the response text
            response_text = response_text.strip()
            
            # Find the first and last curly braces to extract just the JSON object
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                response_text = response_text[start_idx:end_idx]
            
            # Print the cleaned response for debugging
            print("Cleaned response text:", response_text)
            
            # Parse the JSON response
            data = json.loads(response_text)
            
            # Print the parsed data for debugging
            print("Parsed data:", data)
            
            # Map vendor_information to vendor_name and vendor_address
            if "vendor_information" in data:
                vendor_info = data.pop("vendor_information")
                data["vendor_name"] = vendor_info.get("name", "")
                data["vendor_address"] = vendor_info.get("address", "")
            
            # Map special_notes_or_conditions to notes
            if "special_notes_or_conditions" in data:
                data["notes"] = data.pop("special_notes_or_conditions")
            
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
                    
            # Print the final data for debugging
            print("Final data:", data)
            
            return data
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse Gemini response: {response_text}")
            print(f"JSON decode error: {str(e)}")
            return self._fallback_data(document_ai_output)

    def _fallback_data(self, document_ai_output: dict) -> dict:
        """
        Generate fallback data when Gemini processing fails.
        
        Args:
            document_ai_output: Output from Document AI processing
            
        Returns:
            dict: Basic invoice data structure
        """
        # Get raw text from document_ai_output
        raw_text = ""
        if isinstance(document_ai_output, dict):
            raw_text = document_ai_output.get("text", document_ai_output.get("raw_data", ""))
        
        # Get entities from document_ai_output
        entities = {}
        if isinstance(document_ai_output, dict):
            entities = document_ai_output.get("entities", {})
        
        # Extract basic information from entities
        return {
            "invoice_number": entities.get("invoice_id", ""),
            "invoice_date": entities.get("invoice_date", "1900-01-01"),
            "due_date": entities.get("due_date", "1900-01-01"),
            "total_amount": float(entities.get("total_amount", "0").replace("$", "").replace(",", "")) if entities.get("total_amount") else 0.0,
            "vendor_name": entities.get("supplier_name", ""),
            "vendor_address": entities.get("supplier_address", ""),
            "line_items": document_ai_output.get("line_items", []) if isinstance(document_ai_output, dict) else [],
            "payment_terms": entities.get("payment_terms", ""),
            "notes": "",
            "raw_data": raw_text
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
        try:
            print("Document object:", document)  # Debug print
            if hasattr(document, 'entities'):
                for entity in document.entities:
                    try:
                        entities[entity.type_] = entity.mention_text
                    except AttributeError as e:
                        print(f"Error accessing entity attributes: {str(e)}")
                        continue
            else:
                print("Document has no entities attribute")
        except Exception as e:
            print(f"Error extracting entities: {str(e)}")
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
        
        try:
            # Find all line item groups in the document
            for entity in document.entities:
                if entity.type_ == "line_item":
                    try:
                        # Extract line item properties
                        description = ""
                        quantity = 0.0
                        unit_price = 0.0
                        amount = 0.0
                        
                        for prop in entity.properties:
                            if prop.type_ == "line_item/description":
                                description = prop.mention_text
                            elif prop.type_ == "line_item/quantity":
                                try:
                                    quantity = float(prop.normalized_value.text)
                                except (ValueError, AttributeError):
                                    quantity = 0.0
                            elif prop.type_ == "line_item/unit_price":
                                try:
                                    unit_price = float(prop.normalized_value.text)
                                except (ValueError, AttributeError):
                                    unit_price = 0.0
                            elif prop.type_ == "line_item/amount":
                                try:
                                    amount = float(prop.normalized_value.text)
                                except (ValueError, AttributeError):
                                    amount = 0.0
                        
                        # Only add line items that have at least one non-zero value
                        if description or quantity > 0 or unit_price > 0 or amount > 0:
                            item = {
                                "description": description,
                                "quantity": quantity,
                                "unit_price": unit_price,
                                "amount": amount
                            }
                            line_items.append(item)
                            print(f"Extracted line item: {item}")  # Debug print
                    except (ValueError, AttributeError) as e:
                        print(f"Error processing line item: {str(e)}")
                        continue
        except AttributeError as e:
            print(f"Error accessing document entities: {str(e)}")
            return []
                
        return line_items

    def _get_nested_entity(self, parent_entity, property_type: str) -> str:
        """
        Get nested entity value from a parent entity.
        
        Args:
            parent_entity: Parent entity object
            property_type: Type of property to extract
            
        Returns:
            str: Extracted value or empty string if not found
        """
        try:
            for prop in parent_entity.properties:
                if prop.type_ == property_type:
                    return prop.mention_text
        except AttributeError as e:
            print(f"Error accessing entity properties: {str(e)}")
        return ""

    def _parse_document_ai_output(self, document_ai_output: dict) -> dict:
        """Parse Document AI output into structured format."""
        def convert_currency(amount_str: str) -> float:
            """Convert currency string to float."""
            try:
                # Remove currency symbols and commas
                amount_str = amount_str.replace('$', '').replace(',', '').strip()
                return float(amount_str)
            except (ValueError, AttributeError):
                return 0.0

        def convert_date(date_str: str) -> str:
            """Convert date string to YYYY-MM-DD format."""
            try:
                # Try different date formats
                for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        return dt.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
                return "1900-01-01"
            except (ValueError, AttributeError):
                return "1900-01-01"

        def calculate_due_date(invoice_date: str, payment_terms: str) -> str:
            """Calculate due date based on payment terms."""
            try:
                # Parse invoice date
                invoice_dt = datetime.strptime(invoice_date, '%Y-%m-%d')
                
                # Check for NTO terms
                nto_match = re.search(r'NTO is issued at (\d+) days', payment_terms)
                if nto_match:
                    days = int(nto_match.group(1))
                    due_dt = invoice_dt + timedelta(days=days)
                    return due_dt.strftime('%Y-%m-%d')
                
                return "1900-01-01"
            except (ValueError, AttributeError):
                return "1900-01-01"

        # Extract text and entities from document_ai_output
        text = document_ai_output.get('text', '')
        entities = document_ai_output.get('entities', {})
        line_items = document_ai_output.get('line_items', [])
        
        # Initialize data structure
        data = {
            'invoice_number': entities.get('invoice_id', ''),
            'invoice_date': convert_date(entities.get('invoice_date', '')),
            'due_date': '1900-01-01',  # Will be calculated later if possible
            'total_amount': convert_currency(entities.get('total_amount', '')),
            'vendor_name': entities.get('supplier_name', ''),
            'vendor_address': entities.get('supplier_address', ''),
            'line_items': line_items,
            'payment_terms': entities.get('payment_terms', ''),
            'notes': '',
            'raw_data': text
        }
        
        # Calculate due date based on payment terms if available
        if data['invoice_date'] != '1900-01-01' and data['payment_terms']:
            data['due_date'] = calculate_due_date(data['invoice_date'], data['payment_terms'])
        
        return data 