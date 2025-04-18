from google.cloud import storage
from src.config import settings, logger
import os

class GCSClient:
    def __init__(self, use_production_bucket: bool = True):
        self.client = storage.Client.from_service_account_json(settings.GOOGLE_APPLICATION_CREDENTIALS)
        self.bucket_name = settings.GCS_PRODUCTION_BUCKET_NAME if use_production_bucket else settings.GCS_ADHOC_BUCKET_NAME
        self.bucket = self.client.bucket(self.bucket_name)
        logger.info(f"Initialized GCS client with bucket: {self.bucket_name}")

    def upload_file(self, source_file_path: str, destination_blob_name: str) -> str:
        """
        Upload a file to Google Cloud Storage.
        
        Args:
            source_file_path: Path to the local file to upload
            destination_blob_name: Name of the blob in the bucket
            
        Returns:
            str: GCS URI of the uploaded file
        """
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_path)
        logger.info(f"Uploaded {source_file_path} to {destination_blob_name}")
        return f"gs://{self.bucket_name}/{destination_blob_name}"

    def download_file(self, source_blob_name: str, destination_file_path: str) -> None:
        """
        Download a file from Google Cloud Storage.
        
        Args:
            source_blob_name: Name of the blob in the bucket
            destination_file_path: Path where to save the downloaded file
        """
        blob = self.bucket.blob(source_blob_name)
        blob.download_to_filename(destination_file_path)
        logger.info(f"Downloaded {source_blob_name} to {destination_file_path}")

    def list_files(self, prefix: str = None) -> list:
        """
        List files in the bucket.
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            list: List of blob names
        """
        blobs = self.bucket.list_blobs(prefix=prefix)
        files = [blob.name for blob in blobs]
        logger.debug(f"Listed {len(files)} files with prefix: {prefix}")
        return files

    def delete_file(self, blob_name: str) -> None:
        """
        Delete a file from the bucket.
        
        Args:
            blob_name: Name of the blob to delete
        """
        blob = self.bucket.blob(blob_name)
        blob.delete()
        logger.info(f"Deleted {blob_name} from bucket") 