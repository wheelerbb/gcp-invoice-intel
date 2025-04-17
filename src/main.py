import os
import uuid
import hashlib
import argparse
from datetime import datetime
from typing import Optional, Dict, Any
import logging
from pathlib import Path

from src.config import settings, logger, PROJECT_ROOT
from src.storage.gcs_client import GCSClient
from src.bigquery.client import BigQueryClient
from src.document_ai.base_processor import BaseProcessor
from src.document_ai.document_ai_processor import DocumentAIProcessor

class InvoiceProcessor:
    def __init__(self, use_production_bucket: bool = False, use_gemini: bool = None):
        """Initialize the invoice processor.
        
        Args:
            use_production_bucket: Whether to use the production bucket
            use_gemini: Whether to use Gemini for processing (defaults to settings.USE_GEMINI)
        """
        self.gcs_client = GCSClient(use_production_bucket=use_production_bucket)
        self.bigquery_client = BigQueryClient()
        self.use_gemini = use_gemini if use_gemini is not None else settings.USE_GEMINI
        self.document_ai_processor = DocumentAIProcessor()
        
        # Only initialize Gemini if we're going to use it
        self.gemini_processor = None
        if self.use_gemini:
            from src.gemini.processor import GeminiProcessor
            self.gemini_processor = GeminiProcessor()
            
        logger.info(f"Initialized InvoiceProcessor with {'Gemini' if self.use_gemini else 'Document AI'} processor")

    def _generate_file_id(self, file_path: str) -> str:
        """Generate a deterministic UUID based on the file path."""
        file_hash = hashlib.md5(os.path.abspath(file_path).encode()).hexdigest()
        return str(uuid.UUID(file_hash))

    def process_invoice(self, file_path: str, is_adhoc: bool = False, project_name: str = None) -> Dict[str, Any]:
        """Process a single invoice file.
        
        Args:
            file_path: Path to the invoice file
            is_adhoc: Whether this is an ad-hoc processing request
            project_name: Project name for production files
            
        Returns:
            Dict containing processing results
        """
        try:
            # Convert relative path to absolute path
            if not os.path.isabs(file_path):
                file_path = os.path.normpath(str(PROJECT_ROOT / file_path))

            logger.info(f"Starting invoice processing for {file_path}")
            
            # Get or create file ID
            file_id = self.bigquery_client.get_or_create_file_id(
                file_path=file_path,
                is_production=not is_adhoc,
                project_name=project_name
            )
            
            # Upload to GCS
            original_filename = os.path.basename(file_path)
            storage_path = f"invoices/{file_id}_{original_filename}" if is_adhoc else file_path
            gcs_uri = self.gcs_client.upload_file(file_path, storage_path)
            
            # Prepare metadata
            metadata = {
                "invoice_id": file_id,
                "storage_path": storage_path,
                "gcs_uri": gcs_uri,
                "is_production": not is_adhoc,
                "original_filename": original_filename,
                "project_name": project_name
            }
            
            # Process with Document AI
            result = self.document_ai_processor.process(file_path, metadata)
            
            # Enhance with Gemini if enabled
            if self.use_gemini and self.gemini_processor:
                result = self.gemini_processor.refine_invoice_data(result)
            
            # Store in BigQuery
            self.bigquery_client.store_invoice_data(result)
            
            logger.info(f"Successfully processed invoice {file_id}")
            return {
                "success": True,
                "file_id": file_id,
                "storage_path": storage_path,
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Error processing invoice: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }

    def process_invoice_cloud_function(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Cloud Function to process invoice files uploaded to GCS.
        
        Args:
            event: Event payload
            context: Context object
            
        Returns:
            Dict containing processing results
        """
        try:
            bucket_name = event["bucket"]
            file_path = event["name"]
            
            is_production = bucket_name == settings.GCS_PRODUCTION_BUCKET_NAME
            processor = InvoiceProcessor(use_production_bucket=is_production)
            
            return processor.process_invoice(file_path)
            
        except Exception as e:
            logger.error(f"Error in cloud function: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

def main():
    parser = argparse.ArgumentParser(description="Process invoice files")
    parser.add_argument("file_path", help="Path to the invoice file")
    parser.add_argument("--adhoc", action="store_true", help="Process as an ad-hoc request")
    parser.add_argument("--project", help="Project name for production files")
    parser.add_argument("--no-gemini", action="store_true", help="Disable Gemini processing")
    args = parser.parse_args()

    processor = InvoiceProcessor(
        use_production_bucket=not args.adhoc,
        use_gemini=not args.no_gemini
    )
    result = processor.process_invoice(
        file_path=args.file_path,
        is_adhoc=args.adhoc,
        project_name=args.project
    )
    print(result)

if __name__ == "__main__":
    main() 