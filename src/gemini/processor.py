from google.cloud import aiplatform
from src.config import (
    GCP_PROJECT_ID,
    GCP_LOCATION,
    VERTEX_AI_MODEL_ID,
)

class GeminiProcessor:
    def __init__(self):
        aiplatform.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
        self.model = aiplatform.preview.get_model(VERTEX_AI_MODEL_ID)

    def refine_invoice_data(self, document_ai_output: dict) -> dict:
        """
        Refine and enhance the extracted invoice data using Gemini.
        
        Args:
            document_ai_output: Output from Document AI processing
            
        Returns:
            dict: Refined invoice data
        """
        prompt = self._create_prompt(document_ai_output)
        
        try:
            response = self.model.predict(prompt=prompt)
            refined_data = self._parse_response(response.text)
            return refined_data
        except Exception as e:
            print(f"Error refining data with Gemini: {str(e)}")
            return document_ai_output

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
        
        prompt = f"""
        Analyze the following invoice text and extracted entities to provide a structured response:
        
        Invoice Text:
        {text}
        
        Extracted Entities:
        {entities}
        
        Please provide a structured response with the following information:
        1. Invoice number
        2. Invoice date
        3. Due date
        4. Total amount
        5. Vendor information
        6. Line items (if any)
        7. Payment terms
        8. Any special notes or conditions
        
        Format the response as a JSON object with these fields.
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
        # This is a placeholder implementation
        # In a real implementation, you would need to properly parse the JSON response
        # and handle any potential errors in the response format
        
        try:
            # Assuming the response is valid JSON
            import json
            return json.loads(response_text)
        except json.JSONDecodeError:
            # If the response is not valid JSON, return a structured error
            return {
                "error": "Failed to parse Gemini response",
                "raw_response": response_text
            } 