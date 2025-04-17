import json
import google.generativeai as genai
from .document_ai_processor import DocumentAIProcessor
from src.config import settings, logger

class GeminiInvoiceProcessor(DocumentAIProcessor):
    """Processor that uses Document AI with Gemini enhancement."""
    
    def __init__(self):
        super().__init__()
        # Initialize Gemini client
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.gemini_client = genai.GenerativeModel(settings.GEMINI_MODEL)
        logger.info(f"Initialized GeminiInvoiceProcessor with model: {settings.GEMINI_MODEL}")

    def _process_document(self, file_path: str) -> dict:
        """Process a document using Document AI with Gemini enhancement.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            dict: Structured invoice data
        """
        # First get the base Document AI result
        invoice_data = super()._process_document(file_path)
        
        # Refine the data using Gemini
        return self.refine_invoice_data(invoice_data)

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
            self.logger.error(f"Error refining invoice data: {str(e)}", exc_info=True)
            return invoice_data 