import os
import uuid
import tempfile
import hashlib
import argparse
from datetime import datetime
from typing import Optional

from src.storage.gcs_client import GCSClient
from src.gemini.processor import GeminiProcessor
from src.bigquery.client import BigQueryClient
from src.document_ai.gemini_processor import GeminiInvoiceProcessor
from src.document_ai.simple_processor import SimpleInvoiceProcessor
from src.llm.client import LLMClient

class InvoiceProcessor:
    def __init__(self, use_production_bucket: bool = False, use_gemini: bool = True):
        self.gcs_client = GCSClient(use_production_bucket=use_production_bucket)
        self.bigquery_client = BigQueryClient()
        self.llm_client = LLMClient(use_gemini=use_gemini)
        self.use_production_bucket = use_production_bucket

    def _generate_file_id(self, file_path: str) -> str:
        """
        Generate a deterministic UUID based on the file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: UUID string
        """
        # Create a hash of the absolute file path
        file_hash = hashlib.md5(os.path.abspath(file_path).encode()).hexdigest()
        # Convert the hash to a UUID
        return str(uuid.UUID(file_hash))

    def process_invoice(self, file_path: str, is_adhoc: bool = False, project_name: str = None) -> dict:
        """
        Process a single invoice file.
        
        Args:
            file_path: Path to the invoice file
            is_adhoc: Whether this is an ad-hoc processing request
            project_name: Project name for production files
            
        Returns:
            dict: Processing results
        """
        try:
            # Get or create file ID
            file_id = self.bigquery_client.get_or_create_file_id(
                file_path=file_path,
                is_production=not is_adhoc,
                project_name=project_name
            )
            
            # Upload to GCS
            original_filename = os.path.basename(file_path)
            if is_adhoc:
                storage_path = f"invoices/{file_id}_{original_filename}"
            else:
                storage_path = file_path  # For production, use the original path
                
            gcs_uri = self.gcs_client.upload_file(file_path, storage_path)
            
            # Process with LLM
            llm_result = self.llm_client.process_invoice(file_path)
            
            # Add metadata
            llm_result.update({
                "invoice_id": file_id,
                "storage_path": storage_path,
                "is_production": not is_adhoc,
                "original_filename": original_filename,
                "project_name": project_name
            })
            
            # Store in BigQuery
            self.bigquery_client.store_invoice_data(llm_result)
            
            print(f"Successfully processed invoice:")
            print(f"File ID: {file_id}")
            print(f"Storage Path: {storage_path}")
            print("\nExtracted Data:")
            for key, value in llm_result.items():
                print(f"{key}: {value}")
            
            return {
                "success": True,
                "file_id": file_id,
                "storage_path": storage_path,
                "data": llm_result
            }
            
        except Exception as e:
            print(f"Error processing invoice: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def process_invoice_cloud_function(self, event, context):
        """
        Cloud Function to process invoice files uploaded to GCS.
        
        Args:
            event: Event payload
            context: Context object
            
        Returns:
            dict: Processing results
        """
        # Get file details from event
        bucket_name = event["bucket"]
        file_path = event["name"]
        
        # Determine if this is a production or ad hoc file
        is_production = bucket_name == GCS_PRODUCTION_BUCKET_NAME
        
        # Create processor with appropriate bucket
        processor = InvoiceProcessor(use_production_bucket=is_production)
        
        # Process the file
        return processor.process_invoice(file_path)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process invoice files")
    parser.add_argument("file_path", help="Path to the invoice file")
    parser.add_argument("--adhoc", action="store_true", help="Process as ad hoc file")
    parser.add_argument("--project", help="Project name for production files")
    parser.add_argument("--no-gemini", action="store_true", help="Process without Gemini")
    
    args = parser.parse_args()
    
    # Create processor with appropriate bucket and Gemini setting
    processor = InvoiceProcessor(
        use_production_bucket=not args.adhoc,
        use_gemini=not args.no_gemini
    )
    
    # Process the file
    result = processor.process_invoice(
        file_path=args.file_path,
        is_adhoc=args.adhoc,
        project_name=args.project
    )
    
    if result["success"]:
        print(f"Successfully processed invoice:")
        print(f"File ID: {result['file_id']}")
        print(f"Storage Path: {result['storage_path']}")
        print("\nExtracted Data:")
        for key, value in result["data"].items():
            if key not in ["raw_data", "processing_timestamp"]:
                print(f"{key}: {value}")
    else:
        print(f"Error processing invoice: {result.get('error')}") 