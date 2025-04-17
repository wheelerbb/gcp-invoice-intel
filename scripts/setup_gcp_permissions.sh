#!/bin/bash

# Exit on error
set -e

# Check if project ID is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <GCP_PROJECT_ID> <SERVICE_ACCOUNT_EMAIL>"
    exit 1
fi

GCP_PROJECT_ID=$1
SERVICE_ACCOUNT_EMAIL=$2

# Required roles for the service account
ROLES=(
    "roles/storage.admin"
    "roles/documentai.admin"
    "roles/aiplatform.admin"
    "roles/bigquery.admin"
    "roles/cloudfunctions.admin"
    "roles/iam.serviceAccountUser"
)

echo "Setting up permissions for service account: $SERVICE_ACCOUNT_EMAIL in project: $GCP_PROJECT_ID"

# Grant each role to the service account
for ROLE in "${ROLES[@]}"; do
    echo "Granting $ROLE..."
    gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
        --role="$ROLE"
done

echo "All permissions have been granted successfully!" 