from setuptools import setup, find_packages

setup(
    name="gcp-invoice-processing",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "google-cloud-storage>=2.10.0",
        "google-cloud-documentai>=2.15.0",
        "google-cloud-aiplatform>=1.36.0",
        "google-cloud-bigquery>=3.11.0",
        "google-cloud-functions>=1.12.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.5.0",
    ],
    python_requires=">=3.9",
) 