# modular_balancing/src/main.py

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize GCP clients early
from src.utils import initialize_gcp_clients, ensure_gcs_bucket_exists, load_from_gcs_pickle
from src.config import (
    GCS_BUCKET_NAME,
    GCP_LOCATION,
    GCS_DATA_PATH,
    GCS_MODELS_PATH
)


initialize_gcp_clients()

from src.data_ingestion import load_all_raw_data
from src.feature_engineering import run_feature_engineering
from src.optimization import solve_optimization_problem
from src.reporting import generate_reports


def run_full_pipeline(use_mock_data=False, skip_ingestion=False, skip_optimization=False):
    """
    Runs the entire modular balancing pipeline.
    
    Args:
        use_mock_data (bool): If True, generates mock data if BQ queries fail or when forced.
        skip_ingestion (bool): If True, attempts to load raw data from GCS instead of BQ.
        skip_optimization (bool): If True, skips running the optimization model,
                                   using a previously saved optimized schedule.
    """
    print("\nStarting Modular Balancing Automation Pipeline...")

    # --- 1. Ensure GCS Bucket Exists ---
    bucket = ensure_gcs_bucket_exists(GCS_BUCKET_NAME, GCP_LOCATION)
    if bucket is None:
        print("🚨 Critical: Failed to create or access GCS bucket. Exiting.")
        return

    # --- 2. Data Ingestion ---
    raw_data = None
    if skip_ingestion:
        print("Skipping BigQuery ingestion, attempting to load raw data from GCS...")
        try:
            # Load individual dataframes. This can be refined if needed.
            raw_data = {
                'df_relays': load_from_gcs_pickle(f"{GCS_DATA_PATH}raw_relays.pkl"),
                'df_msa': load_from_gcs_pickle(f"{GCS_DATA_PATH}raw_msa.pkl"),
                'df_overactive_bridge': load_from_gcs_pickle(f"{GCS_DATA_PATH}raw_overactive_bridge.pkl"),
                'df_bra_mra': load_from_gcs_pickle(f"{GCS_DATA_PATH}mock_bra_mra.pkl"), # Using mock for now
                'df_adj': load_from_gcs_pickle(f"{GCS_DATA_PATH}mock_adj.pkl"),         # Using mock for now
                'df_holidays': load_from_gcs_pickle(f"{GCS_DATA_PATH}mock_holidays.pkl") # Using mock for now
            }
            # Check if any loaded dataframe is empty (indicating failure)
            if any(df.empty for df in raw_data.values()):
                print("🚨 Failed to load all raw data from GCS. Setting skip_ingestion=False for next run.")
                raw_data = load_all_raw_data(use_mock_data=use_mock_data)
        except Exception as e:
            print(f"🚨 Error loading raw data from GCS: {e}. Falling back to full ingestion.")
            raw_data = load_all_raw_data(use_mock_data=use_mock_data)
    else:
        raw_data = load_all_raw_data(use_mock_data=use_mock_data)

    if raw_data is None or any(df.empty for df in raw_data.values()):
        print("🚨 Pipeline stopped due to missing raw data.")
        return

    # --- 3. Feature Engineering ---
    df_master_schedule, dax_metrics = run_feature_engineering(raw_data)
    if df_master_schedule is None or df_master_schedule.empty:
        print("🚨 Pipeline stopped due to empty master schedule after feature engineering.")
        return

    # --- 4. Optimization ---
    
    df_suggested_schedule = None
    if skip_optimization:
        print("Skipping optimization solver, attempting to load last optimized schedule from GCS...")
        try:
            df_suggested_schedule = load_from_gcs_pickle(f"{GCS_MODELS_PATH}optimized_schedule.pkl")
            if df_suggested_schedule.empty:
                print("⚠️ No optimized schedule found. Using master schedule as a stand-in for reporting.")
                df_suggested_schedule = df_master_schedule.copy()
        except Exception as e:
            print(f"⚠️ Error loading optimized schedule from GCS: {e}. Using master schedule as a stand-in for reporting.")
            df_suggested_schedule = df_master_schedule.copy()
    else:
        df_suggested_schedule = solve_optimization_problem(df_master_schedule)
        if df_suggested_schedule is None or df_suggested_schedule.empty:
            print("⚠️ Optimization failed or returned an empty schedule. Using master schedule as a stand-in for reporting.")
            df_suggested_schedule = df_master_schedule.copy()

    # --- 5. Reporting ---
    
    if df_suggested_schedule is None or df_suggested_schedule.empty:
        print("⚠️ Optimization failed or returned an empty schedule. Using master schedule as a stand-in for reporting.")
        df_suggested_schedule = df_master_schedule.copy()
        # Ensure required columns exist
        if 'Suggested_WK_End_Date' not in df_suggested_schedule.columns:
            # Use Original_WK_End_Date if available, else WK_End_Date
            if 'Original_WK_End_Date' in df_suggested_schedule.columns:
                df_suggested_schedule['Suggested_WK_End_Date'] = df_suggested_schedule['Original_WK_End_Date']
            else:
                df_suggested_schedule['Suggested_WK_End_Date'] = df_suggested_schedule['WK_End_Date']

    generate_reports(df_master_schedule, df_suggested_schedule)

    print("\nModular Balancing Automation Pipeline Finished Successfully!")


if __name__ == "__main__":
    # Example usage:
    # run_full_pipeline(use_mock_data=True) # Run with mock data (good for initial testing)
    # run_full_pipeline(use_mock_data=False) # Attempt to fetch real BQ data
    
    # To speed up development after initial ingestion,
    # and use previously saved raw/processed data from GCS:
    run_full_pipeline(use_mock_data=True, skip_ingestion=True, skip_optimization=False)
    # run_full_pipeline(use_mock_data=True, skip_ingestion=True, skip_optimization=True) # Load everything from GCS