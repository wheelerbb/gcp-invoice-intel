from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from google.cloud import documentai_v1 as documentai
from src.config import settings, logger

class BaseProcessor(ABC):
    """Base class for document processors."""
    
    def __init__(self):
        """Initialize the processor."""
        self.logger = logger
    
    @abstractmethod
    def _process_document(self, file_path: str) -> Dict[str, Any]:
        """Process a document file. To be implemented by subclasses.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            dict: Processed document data
        """
        raise NotImplementedError("Subclasses must implement _process_document")
    
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
        
        # Add metadata
        document_data.update(metadata)
        
        return document_data
    
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
        """Convert amount string to float.
        
        Args:
            amount_str: Amount as string
            
        Returns:
            float: Amount as float
        """
        if not amount_str:
            return 0.0
        try:
            # Remove any non-numeric characters except decimal point
            cleaned = ''.join(c for c in amount_str if c.isdigit() or c == '.')
            return float(cleaned)
        except ValueError:
            return 0.0

    def _get_nested_entity(self, parent_entity, property_type: str) -> str:
        """Get nested entity value from a parent entity"""
        for prop in parent_entity.properties:
            if prop.type_ == property_type:
                return prop.mention_text
        return ""

    def _extract_line_items(self, document) -> List[Dict[str, Any]]:
        """Extract line items from the document.
        
        Args:
            document: Document object
            
        Returns:
            List[Dict[str, Any]]: List of line items
        """
        line_items = []
        
        # Find all line item groups in the document
        for entity in document.entities:
            if entity.type_ == "line_item":
                # Get all properties for this line item
                properties = {prop.type_: prop.mention_text for prop in entity.properties}
                
                # Extract description (may have multiple descriptions, use the first one)
                descriptions = [v for k, v in properties.items() if k == "line_item/description"]
                description = descriptions[0] if descriptions else ""
                
                # Extract other fields
                quantity = self._convert_amount(properties.get("line_item/quantity", "0"))
                unit_price = self._convert_amount(properties.get("line_item/unit_price", "0"))
                amount = self._convert_amount(properties.get("line_item/amount", "0"))
                
                if description or quantity > 0 or unit_price > 0 or amount > 0:
                    item = {
                        "description": description,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "amount": amount
                    }
                    line_items.append(item)
                
        return line_items

    def _get_entity_value(self, document, entity_type: str) -> str:
        """Get the value of an entity from the document.
        
        Args:
            document: Document object
            entity_type: Type of entity to extract
            
        Returns:
            str: Entity value or empty string if not found
        """
        for entity in document.entities:
            if entity.type_ == entity_type:
                return entity.mention_text
        return ""

    @abstractmethod
    def _extract_entities(self, document) -> dict:
        """Extract entities from the document"""
        pass 