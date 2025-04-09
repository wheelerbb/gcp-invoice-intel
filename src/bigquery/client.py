from google.cloud import bigquery
from src.config import (
    GCP_PROJECT_ID,
    BIGQUERY_DATASET_ID,
    BIGQUERY_TABLE_ID,
)

class BigQueryClient:
    def __init__(self):
        self.client = bigquery.Client()
        self.dataset_id = f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET_ID}"
        self.table_id = f"{self.dataset_id}.{BIGQUERY_TABLE_ID}"
        
        # Ensure dataset and table exist
        self._create_dataset_if_not_exists()
        self._create_table_if_not_exists()

    def _create_dataset_if_not_exists(self):
        """Create the BigQuery dataset if it doesn't exist."""
        try:
            self.client.get_dataset(self.dataset_id)
        except Exception:
            dataset = bigquery.Dataset(self.dataset_id)
            self.client.create_dataset(dataset, exists_ok=True)

    def _create_table_if_not_exists(self):
        """Create the BigQuery table if it doesn't exist."""
        schema = [
            bigquery.SchemaField("invoice_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("invoice_number", "STRING"),
            bigquery.SchemaField("invoice_date", "DATE"),
            bigquery.SchemaField("due_date", "DATE"),
            bigquery.SchemaField("total_amount", "FLOAT64"),
            bigquery.SchemaField("vendor_name", "STRING"),
            bigquery.SchemaField("vendor_address", "STRING"),
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
            self.client.get_table(self.table_id)
        except Exception:
            table = bigquery.Table(self.table_id, schema=schema)
            self.client.create_table(table, exists_ok=True)

    def insert_invoice_data(self, invoice_data: dict):
        """
        Insert processed invoice data into BigQuery.
        
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
            "line_items": invoice_data.get("line_items", []),
            "payment_terms": invoice_data.get("payment_terms"),
            "notes": invoice_data.get("notes"),
            "processing_timestamp": invoice_data["processing_timestamp"],
            "raw_data": str(invoice_data),
        }]

        errors = self.client.insert_rows_json(self.table_id, rows_to_insert)
        
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