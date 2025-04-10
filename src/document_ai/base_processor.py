from abc import ABC, abstractmethod

class BaseInvoiceProcessor:
    """Base class for invoice processors"""
    
    @abstractmethod
    def process_document(self, file_path: str) -> dict:
        """Process a document and extract invoice data"""
        pass

    @abstractmethod
    def _extract_entities(self, document) -> dict:
        """Extract entities from the document"""
        pass 