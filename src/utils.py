# modular_balancing/src/utils.py

import pandas as pd
from google.cloud import bigquery, storage
from google.api_core import exceptions
import os
import sys

from src.config import PROJECT_ID_SHRNK, PROJECT_ID_AP, GCP_LOCATION, GCS_BUCKET_NAME

# --- GCP Client Initialization ---
# This client will be shared across modules
bigquery_client = None
storage_client = None

def initialize_gcp_clients():
    global bigquery_client, storage_client
    if bigquery_client is None:
        try:
            bigquery_client = bigquery.Client(project=PROJECT_ID_SHRNK) # Main project for BigQuery data
            print("✅ BigQuery Client Initialized Successfully.")
        except Exception as e:
            print(f"🚨 Error initializing BigQuery client: {e}")
            sys.exit(1) # Exit if critical client fails
    if storage_client is None:
        try:
            storage_client = storage.Client(project=PROJECT_ID_SHRNK) # Assuming storage is in this project context
            print("✅ GCS Client Initialized Successfully.")
        except Exception as e:
            print(f"🚨 Error initializing GCS client: {e}")
            sys.exit(1) # Exit if critical client fails

def get_bigquery_data(query: str, project_id: str = None) -> pd.DataFrame:
    """Fetches data from BigQuery using the provided SQL query."""
    if bigquery_client is None:
        initialize_gcp_clients() # Ensure clients are initialized

    try:
        print(f"Executing query (project={project_id or PROJECT_ID_SHRNK}):\n{query[:200]}...\n")
        df = bigquery_client.query(query, project=project_id or PROJECT_ID_SHRNK).to_dataframe()
        print(f"Successfully fetched {len(df)} rows from BigQuery (Project: {project_id or PROJECT_ID_SHRNK}).")
        return df
    except Exception as e:
        print(f"🚨 Error fetching data from BigQuery: {e}")
        return pd.DataFrame() # Return empty DataFrame on failure


def save_to_gcs_pickle(df: pd.DataFrame, gcs_path: str):
    """Saves a Pandas DataFrame to GCS as a pickle file."""
    if storage_client is None:
        initialize_gcp_clients()
    try:
        # Use pandas' built-in GCS support
        df.to_pickle(gcs_path)
        print(f"✅ Saved DataFrame to GCS: {gcs_path}")
    except Exception as e:
        print(f"🚨 Error saving DataFrame to GCS '{gcs_path}': {e}")

def load_from_gcs_pickle(gcs_path: str) -> pd.DataFrame:
    """Loads a Pandas DataFrame from GCS pickle file."""
    if storage_client is None:
        initialize_gcp_clients()
    try:
        df = pd.read_pickle(gcs_path)
        print(f"✅ Loaded DataFrame from GCS: {gcs_path}")
        return df
    except Exception as e:
        print(f"🚨 Error loading DataFrame from GCS '{gcs_path}': {e}")
        return pd.DataFrame()

def ensure_gcs_bucket_exists(bucket_name: str, location: str):
    """Creates a GCS bucket if it doesn't exist, or confirms its existence."""
    if storage_client is None:
        initialize_gcp_clients()
    print(f"Attempting to create or get GCS Bucket: gs://{bucket_name}")
    try:
        bucket = storage_client.create_bucket(bucket_name, location=location)
        print(f"✅ Bucket '{bucket_name}' created successfully in '{location}'.")
        return bucket
    except exceptions.Conflict:
        bucket = storage_client.get_bucket(bucket_name) # Ensure we get the bucket object
        print(f"ℹ️ Bucket '{bucket_name}' already exists.")
        return bucket
    except exceptions.Forbidden:
        print(f"🚨 Permission denied: Ensure the service account or user has 'Storage Admin' or 'Storage Object Creator' roles in project '{PROJECT_ID_SHRNK}'.")
        return None
    except Exception as e:
        print(f"🚨 An unexpected error occurred while accessing GCS bucket: {e}")
        return None
