#!/bin/bash
# Setup script for development environment

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

echo "Please update .env with your GCP credentials" 