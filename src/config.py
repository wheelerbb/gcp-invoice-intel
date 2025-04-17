from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Get the project root directory (parent of src)
PROJECT_ROOT = Path(__file__).parent.parent

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # GCP Configuration
    GCP_PROJECT_ID: str
    GCP_LOCATION: str
    GCP_REGION: str = "us-east4"  # Default value
    
    # Storage Configuration
    GCS_BUCKET_NAME: str
    GCS_PRODUCTION_BUCKET_NAME: str
    GCS_ADHOC_BUCKET_NAME: str
    
    # Document AI Configuration
    DOCUMENT_AI_PROCESSOR_ID: str
    DOCUMENT_AI_LOCATION: str
    
    # BigQuery Configuration
    BIGQUERY_DATASET: str
    BIGQUERY_TABLE: str
    
    # LLM Configuration
    USE_GEMINI: bool = True
    GEMINI_MODEL: str = "gemini-pro"
    GEMINI_API_KEY: str
    
    # Processing Configuration
    PROCESSING_TIMEOUT: int = 300  # 5 minutes
    MAX_RETRIES: int = 3
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Service Account
    GOOGLE_APPLICATION_CREDENTIALS: str

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Convert relative paths to absolute paths
        if not os.path.isabs(self.GOOGLE_APPLICATION_CREDENTIALS):
            self.GOOGLE_APPLICATION_CREDENTIALS = str(PROJECT_ROOT / self.GOOGLE_APPLICATION_CREDENTIALS)

# Create a singleton instance
settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__) 