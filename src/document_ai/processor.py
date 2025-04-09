from google.cloud import documentai_v1 as documentai
from src.config import (
    DOCUMENT_AI_PROCESSOR_ID,
    DOCUMENT_AI_LOCATION,
    GCP_PROJECT_ID,
)

class DocumentAIProcessor:
    def __init__(self):
        self.client = documentai.DocumentProcessorServiceClient()
        self.processor_name = self.client.processor_path(
            GCP_PROJECT_ID,
            DOCUMENT_AI_LOCATION,
            DOCUMENT_AI_PROCESSOR_ID,
        )

    def process_document(self, file_path: str) -> dict:
        """
        Process a document using Document AI.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            dict: Extracted data from the document
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

        # Extract relevant information
        extracted_data = {
            "text": document.text,
            "pages": len(document.pages),
            "entities": self._extract_entities(document),
        }

        return extracted_data

    def _extract_entities(self, document: documentai.Document) -> dict:
        """
        Extract entities from the processed document.
        
        Args:
            document: Processed Document AI document
            
        Returns:
            dict: Extracted entities
        """
        entities = {}
        
        for entity in document.entities:
            entity_type = entity.type_
            entity_text = entity.mention_text
            confidence = entity.confidence
            
            if entity_type not in entities:
                entities[entity_type] = []
                
            entities[entity_type].append({
                "text": entity_text,
                "confidence": confidence,
            })
            
        return entities 