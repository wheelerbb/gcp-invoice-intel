from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from google.cloud import documentai_v1 as documentai
from src.config import settings, logger

class BaseInvoiceProcessor(ABC):
    """Base class for all invoice processors."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def _process_document(self, file_path: str) -> Dict[str, Any]:
        """Process the document and extract information.
        
        Args:
            file_path: Path to the invoice file
            
        Returns:
            Dict containing extracted information
        """
        pass
    
    def process(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process an invoice file with error handling and logging.
        
        Args:
            file_path: Path to the invoice file
            metadata: Optional metadata to include in the result
            
        Returns:
            Dict containing processing results and metadata
        """
        try:
            self.logger.info(f"Starting processing of {file_path}")
            start_time = datetime.now()
            
            # Process the document
            result = self._process_document(file_path)
            
            # Add metadata
            if metadata:
                result.update(metadata)
            
            # Add processing metadata
            processing_time = (datetime.now() - start_time).total_seconds()
            result.update({
                "processing_timestamp": datetime.now().isoformat(),
                "processing_time_seconds": processing_time,
                "processor_type": self.__class__.__name__
            })
            
            self.logger.info(f"Successfully processed {file_path} in {processing_time:.2f} seconds")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {str(e)}", exc_info=True)
            raise
    
    def validate_result(self, result: Dict[str, Any]) -> bool:
        """Validate the processing result.
        
        Args:
            result: Processing result to validate
            
        Returns:
            bool: True if result is valid
        """
        required_fields = ["invoice_number", "total_amount", "date"]
        return all(field in result for field in required_fields)
    
    def format_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format the processing result.
        
        Args:
            result: Raw processing result
            
        Returns:
            Formatted result
        """
        # Convert numeric strings to floats
        if "total_amount" in result:
            try:
                result["total_amount"] = float(result["total_amount"])
            except (ValueError, TypeError):
                self.logger.warning(f"Could not convert total_amount to float: {result['total_amount']}")
        
        # Format date if present
        if "date" in result:
            try:
                result["date"] = datetime.strptime(result["date"], "%Y-%m-%d").isoformat()
            except (ValueError, TypeError):
                self.logger.warning(f"Could not format date: {result['date']}")
        
        return result

    def _convert_date_format(self, date_str: str) -> str:
        """Convert date from MM/DD/YYYY to YYYY-MM-DD format"""
        if not date_str:
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

    def _get_nested_entity(self, parent_entity, property_type: str) -> str:
        """Get nested entity value from a parent entity"""
        for prop in parent_entity.properties:
            if prop.type_ == property_type:
                return prop.mention_text
        return ""

    def _extract_line_items(self, document: documentai.Document) -> List[Dict[str, Any]]:
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

    def _get_entity_value(self, document: documentai.Document, entity_type: str) -> str:
        """Get the first value of an entity type"""
        for entity in document.entities:
            if entity.type_ == entity_type:
                return entity.mention_text
        return ""

    @abstractmethod
    def _extract_entities(self, document) -> dict:
        """Extract entities from the document"""
        pass 