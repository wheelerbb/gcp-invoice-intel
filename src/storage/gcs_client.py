from google.cloud import storage
from src.config import GCS_BUCKET_NAME

class GCSClient:
    def __init__(self):
        self.client = storage.Client()
        self.bucket = self.client.bucket(GCS_BUCKET_NAME)

    def upload_file(self, source_file_path: str, destination_blob_name: str) -> str:
        """
        Upload a file to Google Cloud Storage.
        
        Args:
            source_file_path: Path to the local file to upload
            destination_blob_name: Name of the blob in the bucket
            
        Returns:
            str: Public URL of the uploaded file
        """
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_path)
        return blob.public_url

    def download_file(self, source_blob_name: str, destination_file_path: str) -> None:
        """
        Download a file from Google Cloud Storage.
        
        Args:
            source_blob_name: Name of the blob in the bucket
            destination_file_path: Path where to save the downloaded file
        """
        blob = self.bucket.blob(source_blob_name)
        blob.download_to_filename(destination_file_path)

    def list_files(self, prefix: str = None) -> list:
        """
        List files in the bucket.
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            list: List of blob names
        """
        blobs = self.bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]

    def delete_file(self, blob_name: str) -> None:
        """
        Delete a file from the bucket.
        
        Args:
            blob_name: Name of the blob to delete
        """
        blob = self.bucket.blob(blob_name)
        blob.delete() 