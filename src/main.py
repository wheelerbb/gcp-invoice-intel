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

class InvoiceProcessor:
    def __init__(self, use_gemini: bool = False):
        self.gcs_client = GCSClient()
        if use_gemini:
            self.processor = GeminiInvoiceProcessor()
        else:
            self.processor = SimpleInvoiceProcessor()
        self.bigquery_client = BigQueryClient()

    def process_invoice(self, file_path: str, destination_blob_name: Optional[str] = None) -> dict:
        """
        Process an invoice through the complete pipeline.
        
        Args:
            file_path: Path to the invoice file
            destination_blob_name: Optional name for the file in GCS
            
        Returns:
            dict: Processed invoice data
        """
        try:
            # Generate a unique blob name if not provided
            if not destination_blob_name:
                file_extension = os.path.splitext(file_path)[1]
                destination_blob_name = f"invoices/{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4()}{file_extension}"

            # 1. Upload to Cloud Storage
            gcs_url = self.gcs_client.upload_file(file_path, destination_blob_name)
            print(f"Uploaded file to GCS: {gcs_url}")

            # 2. Process with Document AI
            processed_data = self.processor.process_document(file_path)
            print("Document AI processing completed")

            # Add storage path to the processed data
            processed_data["storage_path"] = gcs_url

            # 3. Refine with Gemini if enabled
            if isinstance(self.processor, GeminiInvoiceProcessor):
                processed_data = self.processor.refine_invoice_data(processed_data)
                print("Gemini processing completed")

            # 4. Store in BigQuery
            self.bigquery_client.insert_invoice_data(processed_data)
            print("Data stored in BigQuery")

            return processed_data

        except Exception as e:
            print(f"Error processing invoice: {str(e)}")
            raise

def process_invoice_cloud_function(event, context):
    """
    Cloud Function entry point for processing invoices.
    
    Args:
        event: Event payload from Cloud Storage trigger
        context: Cloud Function context
        
    Returns:
        dict: Processing result
    """
    try:
        # Extract file information from the event
        bucket_name = event["bucket"]
        file_name = event["name"]
        
        # Download the file to a temporary location
        temp_file = f"/tmp/{os.path.basename(file_name)}"
        gcs_client = GCSClient()
        gcs_client.download_file(file_name, temp_file)
        
        # Process the invoice
        processor = InvoiceProcessor()
        result = processor.process_invoice(temp_file, file_name)
        
        # Clean up temporary file
        os.remove(temp_file)
        
        return {
            "status": "success",
            "file": file_name,
            "result": result
        }
        
    except Exception as e:
        return {
            "status": "error",
            "file": file_name,
            "error": str(e)
        }

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process an invoice using Document AI')
    parser.add_argument('file_path', help='Path to the invoice file')
    parser.add_argument('--processor', choices=['simple', 'gemini'], default='simple',
                      help='Processor type to use (simple or gemini)')
    
    args = parser.parse_args()
    
    # Create processor with specified type
    processor = InvoiceProcessor(use_gemini=(args.processor == 'gemini'))
    result = processor.process_invoice(args.file_path)
    print("Processing result:", result) 