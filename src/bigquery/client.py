from google.cloud import bigquery
from src.config import settings, logger
import os
import hashlib
import uuid
from datetime import datetime
import json
import time
from pathlib import Path

class BigQueryClient:
    def __init__(self):
        self.client = bigquery.Client.from_service_account_json(settings.GOOGLE_APPLICATION_CREDENTIALS)
        self.dataset_id = f"{settings.GCP_PROJECT_ID}.{settings.BIGQUERY_DATASET}"
        self.invoices_table_id = f"{self.dataset_id}.{settings.BIGQUERY_TABLE}"
        self.file_inventory_table_id = f"{self.dataset_id}.file_inventory"
        
        # Ensure dataset and tables exist
        self._create_dataset_if_not_exists()
        self._create_invoices_table_if_not_exists()
        self._create_file_inventory_table_if_not_exists()
        
        # Verify tables exist
        try:
            self.client.get_table(self.invoices_table_id)
            self.client.get_table(self.file_inventory_table_id)
            logger.info(f"Successfully connected to BigQuery tables")
        except Exception as e:
            logger.error(f"Error verifying tables: {str(e)}", exc_info=True)
            raise

    def _create_dataset_if_not_exists(self):
        """Create the BigQuery dataset if it doesn't exist."""
        try:
            self.client.get_dataset(self.dataset_id)
            logger.debug(f"Dataset {self.dataset_id} already exists")
        except Exception:
            dataset = bigquery.Dataset(self.dataset_id)
            dataset.location = "US"  # Set the location
            self.client.create_dataset(dataset, exists_ok=True)
            logger.info(f"Created dataset {self.dataset_id}")

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
            bigquery.SchemaField("gcs_uri", "STRING", mode="REQUIRED"),
        ]

        try:
            self.client.get_table(self.invoices_table_id)
            logger.debug(f"Table {self.invoices_table_id} already exists")
        except Exception:
            table = bigquery.Table(self.invoices_table_id, schema=schema)
            self.client.create_table(table, exists_ok=True)
            logger.info(f"Created table {self.invoices_table_id}")

    def _create_file_inventory_table_if_not_exists(self):
        """Create the file_inventory table if it doesn't exist."""
        schema = [
            bigquery.SchemaField("file_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("original_filename", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("project_name", "STRING"),
            bigquery.SchemaField("file_size", "INTEGER"),
            bigquery.SchemaField("file_type", "STRING"),
            bigquery.SchemaField("upload_timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("processing_count", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("last_processing_timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("best_processing_id", "STRING"),
            bigquery.SchemaField("is_production", "BOOLEAN", mode="REQUIRED"),
            bigquery.SchemaField("gcs_uri", "STRING", mode="REQUIRED"),
        ]

        try:
            self.client.get_table(self.file_inventory_table_id)
            logger.debug(f"Table {self.file_inventory_table_id} already exists")
        except Exception:
            table = bigquery.Table(self.file_inventory_table_id, schema=schema)
            self.client.create_table(table, exists_ok=True)
            logger.info(f"Created table {self.file_inventory_table_id}")

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
                    self._update_file_processing(file_id, file_path, is_production)
                    logger.info(f"Updated processing count for file {file_id}")
                except Exception as e:
                    logger.warning(f"Could not update processing count: {str(e)}")
                return file_id
            else:
                # File doesn't exist, insert new record
                original_filename = os.path.basename(file_path)
                # If production and no project_name provided, get it from parent folder
                if is_production and not project_name:
                    project_name = Path(file_path).parent.name
                storage_path = f"invoices/{file_id}_{original_filename}" if not is_production else f"clients/{project_name}/{original_filename}"
                bucket_name = settings.GCS_PRODUCTION_BUCKET_NAME if is_production else settings.GCS_ADHOC_BUCKET_NAME
                
                # Get file info
                file_stats = os.stat(file_path)
                file_size = file_stats.st_size
                file_type = os.path.splitext(file_path)[1].lower()
                
                row = {
                    "file_id": file_id,
                    "original_filename": original_filename,
                    "project_name": project_name,
                    "file_size": file_size,
                    "file_type": file_type,
                    "upload_timestamp": datetime.utcnow().isoformat(),
                    "processing_count": 1,
                    "last_processing_timestamp": datetime.utcnow().isoformat(),
                    "is_production": is_production,
                    "gcs_uri": f"gs://{bucket_name}/{storage_path}"
                }
                
                errors = self.client.insert_rows_json(
                    self.file_inventory_table_id,
                    [row]
                )
                
                if errors:
                    logger.error(f"Errors inserting file inventory record: {errors}")
                else:
                    logger.info(f"Created new file inventory record for {file_id}")
                
                return file_id
                
        except Exception as e:
            logger.error(f"Error checking file inventory: {str(e)}", exc_info=True)
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

    def _update_file_processing(self, file_id: str, file_path: str = None, is_production: bool = None):
        """Update file inventory record.
        
        Args:
            file_id: File ID to update
            file_path: Path to the file (optional)
            is_production: Whether this is a production file (optional)
        """
        if file_path:
            # Get file info
            file_stats = os.stat(file_path)
            file_size = file_stats.st_size
            file_type = os.path.splitext(file_path)[1].lower()
            original_filename = os.path.basename(file_path)
            # If production and no project_name provided, get it from parent folder
            if is_production and not project_name:
                project_name = Path(file_path).parent.name
            storage_path = f"invoices/{file_id}_{original_filename}" if not is_production else f"clients/{project_name}/{original_filename}"
            bucket_name = settings.GCS_PRODUCTION_BUCKET_NAME if is_production else settings.GCS_ADHOC_BUCKET_NAME
            
            # Update all fields
            query = f"""
            UPDATE `{self.file_inventory_table_id}`
            SET processing_count = processing_count + 1,
                last_processing_timestamp = CURRENT_TIMESTAMP(),
                file_size = @file_size,
                file_type = @file_type,
                is_production = @is_production,
                gcs_uri = @gcs_uri
            WHERE file_id = @file_id
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("file_id", "STRING", file_id),
                    bigquery.ScalarQueryParameter("file_size", "INTEGER", file_size),
                    bigquery.ScalarQueryParameter("file_type", "STRING", file_type),
                    bigquery.ScalarQueryParameter("is_production", "BOOL", bool(is_production)),
                    bigquery.ScalarQueryParameter("gcs_uri", "STRING", f"gs://{bucket_name}/{storage_path}")
                ]
            )
        else:
            # Just update processing count and timestamp
            query = f"""
            UPDATE `{self.file_inventory_table_id}`
            SET processing_count = processing_count + 1,
                last_processing_timestamp = CURRENT_TIMESTAMP()
            WHERE file_id = @file_id
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("file_id", "STRING", file_id)
                ]
            )
        
        try:
            self.client.query(query, job_config=job_config).result()
            logger.info(f"Updated file inventory record for {file_id}")
        except Exception as e:
            logger.error(f"Error updating file inventory record: {str(e)}", exc_info=True)
            raise

    def store_invoice_data(self, invoice_data: dict):
        """Store invoice data in BigQuery."""
        try:
            errors = self.client.insert_rows_json(
                self.invoices_table_id,
                [invoice_data]
            )
            
            if errors:
                logger.error(f"Errors inserting invoice data: {errors}")
            else:
                logger.info(f"Successfully stored invoice data for {invoice_data.get('invoice_id')}")
                
        except Exception as e:
            logger.error(f"Error storing invoice data: {str(e)}", exc_info=True)
            raise

    def query_invoice_data(self, query: str):
        """Run a query against the invoice data."""
        try:
            query_job = self.client.query(query)
            results = list(query_job)
            logger.info(f"Successfully executed query with {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}", exc_info=True)
            raise 