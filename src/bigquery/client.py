from google.cloud import bigquery
from src.config import (
    GCP_PROJECT_ID,
    BIGQUERY_DATASET_ID,
    BIGQUERY_TABLE_ID,
)
import os
import hashlib
import uuid
from datetime import datetime
import json

class BigQueryClient:
    def __init__(self):
        self.client = bigquery.Client()
        self.dataset_id = f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET_ID}"
        self.invoices_table_id = f"{self.dataset_id}.{BIGQUERY_TABLE_ID}"
        self.file_inventory_table_id = f"{self.dataset_id}.file_inventory"
        
        # Ensure dataset and tables exist
        self._create_dataset_if_not_exists()
        self._create_invoices_table_if_not_exists()
        self._create_file_inventory_table_if_not_exists()
        
        # Verify tables exist
        try:
            self.client.get_table(self.invoices_table_id)
            self.client.get_table(self.file_inventory_table_id)
        except Exception as e:
            print(f"Error verifying tables: {str(e)}")
            raise

    def _create_dataset_if_not_exists(self):
        """Create the BigQuery dataset if it doesn't exist."""
        try:
            self.client.get_dataset(self.dataset_id)
        except Exception:
            dataset = bigquery.Dataset(self.dataset_id)
            dataset.location = "US"  # Set the location
            self.client.create_dataset(dataset, exists_ok=True)

    def _create_invoices_table_if_not_exists(self):
        """Create the processed_invoices table if it doesn't exist."""
        schema = [
            bigquery.SchemaField("invoice_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("invoice_number", "STRING"),
            bigquery.SchemaField("invoice_date", "DATE"),
            bigquery.SchemaField("due_date", "DATE"),
            bigquery.SchemaField("total_amount", "FLOAT64"),
            bigquery.SchemaField("vendor_name", "STRING"),
            bigquery.SchemaField("vendor_address", "STRING"),
            bigquery.SchemaField("storage_path", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("is_production", "BOOLEAN", mode="REQUIRED"),
            bigquery.SchemaField("original_filename", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("project_name", "STRING"),
            bigquery.SchemaField("line_items", "RECORD", mode="REPEATED", fields=[
                bigquery.SchemaField("description", "STRING"),
                bigquery.SchemaField("quantity", "FLOAT64"),
                bigquery.SchemaField("unit_price", "FLOAT64"),
                bigquery.SchemaField("amount", "FLOAT64"),
            ]),
            bigquery.SchemaField("payment_terms", "STRING"),
            bigquery.SchemaField("notes", "STRING"),
            bigquery.SchemaField("processing_timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("raw_data", "STRING"),
        ]

        try:
            self.client.get_table(self.invoices_table_id)
        except Exception:
            table = bigquery.Table(self.invoices_table_id, schema=schema)
            self.client.create_table(table, exists_ok=True)

    def _create_file_inventory_table_if_not_exists(self):
        """Create the file_inventory table if it doesn't exist."""
        schema = [
            bigquery.SchemaField("file_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("original_filename", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("storage_path", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("project_name", "STRING"),
            bigquery.SchemaField("file_size", "INTEGER"),
            bigquery.SchemaField("file_type", "STRING"),
            bigquery.SchemaField("upload_timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("processing_count", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("last_processing_timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("best_processing_id", "STRING"),
            bigquery.SchemaField("is_production", "BOOLEAN", mode="REQUIRED"),
            bigquery.SchemaField("metadata", "STRING"),
        ]

        try:
            self.client.get_table(self.file_inventory_table_id)
        except Exception:
            table = bigquery.Table(self.file_inventory_table_id, schema=schema)
            self.client.create_table(table, exists_ok=True)

    def get_or_create_file_id(self, file_path: str, is_production: bool = False, project_name: str = None) -> str:
        """
        Get or create a file ID for the given file path.
        
        Args:
            file_path: Path to the file
            is_production: Whether this is a production file
            project_name: Project name for production files
            
        Returns:
            str: File ID
        """
        # Generate deterministic UUID based on file path
        file_id = self._generate_file_id(file_path)
        
        # Check if file exists in inventory
        query = f"""
        SELECT file_id, processing_count
        FROM `{self.file_inventory_table_id}`
        WHERE file_id = @file_id
        ORDER BY upload_timestamp DESC
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("file_id", "STRING", file_id)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            results = list(query_job)
            
            if results:
                # File exists, update processing count
                try:
                    self._update_file_processing(file_id)
                except Exception as e:
                    print(f"Warning: Could not update processing count: {str(e)}")
                return file_id
            else:
                # File doesn't exist, insert new record
                original_filename = os.path.basename(file_path)
                storage_path = file_path if is_production else f"invoices/{file_id}_{original_filename}"
                
                row = {
                    "file_id": file_id,
                    "storage_path": storage_path,
                    "original_filename": original_filename,
                    "project_name": project_name,
                    "upload_timestamp": datetime.utcnow().isoformat(),
                    "processing_count": 1,
                    "last_processing_timestamp": datetime.utcnow().isoformat(),
                    "is_production": is_production,
                    "metadata": json.dumps({
                        "created_at": datetime.utcnow().isoformat(),
                        "is_production": is_production
                    })
                }
                
                errors = self.client.insert_rows_json(
                    self.file_inventory_table_id,
                    [row]
                )
                
                if errors:
                    print(f"Errors inserting file inventory record: {errors}")
                
                return file_id
                
        except Exception as e:
            print(f"Error checking file inventory: {str(e)}")
            return file_id

    def _generate_file_id(self, file_path: str) -> str:
        """
        Generate a deterministic UUID based on the file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: Deterministic UUID
        """
        # Get absolute path and normalize it
        abs_path = os.path.abspath(file_path)
        normalized_path = os.path.normpath(abs_path)
        
        # Create MD5 hash of the path
        file_hash = hashlib.md5(normalized_path.encode()).hexdigest()
        
        # Convert to UUID format
        return str(uuid.UUID(file_hash))

    def _update_file_processing(self, file_id: str):
        """Update processing count and timestamp for a file."""
        from datetime import datetime
        
        query = f"""
        UPDATE `{self.file_inventory_table_id}`
        SET processing_count = processing_count + 1,
            last_processing_timestamp = @timestamp
        WHERE file_id = @file_id
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("file_id", "STRING", file_id),
                bigquery.ScalarQueryParameter("timestamp", "TIMESTAMP", datetime.utcnow().isoformat())
            ]
        )
        
        self.client.query(query, job_config=job_config).result()

    def store_invoice_data(self, invoice_data: dict):
        """
        Store processed invoice data in BigQuery.
        
        Args:
            invoice_data: Dictionary containing the invoice data
        """
        from datetime import datetime
        
        # Add processing timestamp
        invoice_data["processing_timestamp"] = datetime.utcnow().isoformat()
        
        # Convert the data to the expected format
        rows_to_insert = [{
            "invoice_id": invoice_data.get("invoice_id"),
            "invoice_number": invoice_data.get("invoice_number"),
            "invoice_date": invoice_data.get("invoice_date"),
            "due_date": invoice_data.get("due_date"),
            "total_amount": float(invoice_data.get("total_amount", 0)),
            "vendor_name": invoice_data.get("vendor_name"),
            "vendor_address": invoice_data.get("vendor_address"),
            "storage_path": invoice_data.get("storage_path"),
            "is_production": invoice_data.get("is_production", False),
            "original_filename": invoice_data.get("original_filename", ""),
            "project_name": invoice_data.get("project_name"),
            "line_items": invoice_data.get("line_items", []),
            "payment_terms": invoice_data.get("payment_terms"),
            "notes": invoice_data.get("notes"),
            "processing_timestamp": invoice_data["processing_timestamp"],
            "raw_data": str(invoice_data),
        }]

        errors = self.client.insert_rows_json(self.invoices_table_id, rows_to_insert)
        
        if errors:
            raise Exception(f"Error inserting rows into BigQuery: {errors}")

    def query_invoice_data(self, query: str):
        """
        Execute a query on the invoice data.
        
        Args:
            query: SQL query string
            
        Returns:
            list: Query results
        """
        query_job = self.client.query(query)
        return list(query_job) 