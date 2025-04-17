import os
import uuid
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
    def __init__(self, use_production_bucket: bool = False):
        self.gcs_client = GCSClient(use_production_bucket)
        self.bigquery_client = BigQueryClient()
        self.llm_client = LLMClient()
        self.use_production_bucket = use_production_bucket

    def process_invoice(self, file_path: str, project_name: str = None) -> dict:
        """
        Process an invoice file and store results in BigQuery.
        
        Args:
            file_path: Path to the invoice file
            project_name: Optional project name for production files
            
        Returns:
            dict: Processing results
        """
        # Get original filename and determine storage path
        original_filename = os.path.basename(file_path)
        
        if self.use_production_bucket:
            # For production files, use the original path
            storage_path = file_path
        else:
            # For ad hoc files, generate a UUID-based path
            file_id = str(uuid.uuid4())
            storage_path = f"invoices/{file_id}/{original_filename}"
            
            # Upload the file to GCS
            self.gcs_client.upload_file(file_path, storage_path)
        
        # Get or create file_id from inventory
        file_id = self.bigquery_client.get_or_create_file_id(
            storage_path=storage_path,
            original_filename=original_filename,
            project_name=project_name
        )
        
        # Download the file for processing
        local_path = self.gcs_client.download_file(storage_path)
        
        try:
            # Process the invoice
            invoice_data = self.llm_client.process_invoice(local_path)
            
            # Add metadata
            invoice_data.update({
                "invoice_id": file_id,  # Use the same file_id as the invoice_id
                "storage_path": storage_path,
                "is_production": self.use_production_bucket,
                "original_filename": original_filename,
                "project_name": project_name,
                "processing_timestamp": datetime.utcnow().isoformat()
            })
            
            # Store in BigQuery
            self.bigquery_client.insert_invoice_data(invoice_data)
            
            return {
                "success": True,
                "file_id": file_id,
                "storage_path": storage_path,
                "data": invoice_data
            }
            
        finally:
            # Clean up local file
            if os.path.exists(local_path):
                os.remove(local_path)

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
    
    args = parser.parse_args()
    
    # Create processor with appropriate bucket
    processor = InvoiceProcessor(use_production_bucket=not args.adhoc)
    
    # Process the file
    result = processor.process_invoice(args.file_path, args.project)
    
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