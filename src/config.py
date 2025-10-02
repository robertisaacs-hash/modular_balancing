# modular_balancing/src/config.py

import os
from datetime import datetime, timedelta

# --- GCP Configuration ---
PROJECT_ID_SHRNK = "wmt-us-gg-shrnk-prod" # Billing project for assays and MSA
PROJECT_ID_AP = "wmt-assetprotection-prod" # Project for the bridge table
GCP_LOCATION = "us-central1" # GCS bucket region

# --- BigQuery Table IDs ---
BQ_RELAYS_TABLE_ID = "`wmt-assort-bridge-tools.MTRAK_ADHOC.RELAYS`"
BQ_MSA_TABLE_ID = "`wmt-assort-bridge-tools.MODSPACE_ADHOC.MSA`"
BQ_OVERACTIVE_BRIDGE_TABLE_ID = "`wmt-assetprotection-prod.Store_Support_Dev.storeleveloveractivemodulars`"

# --- GCS Configuration ---
GCS_BUCKET_NAME = "wmt-us-gg-shrnk-prod-modrelaybalancing-data" # YOUR UNIQUE BUCKET NAME
GCS_DATA_PATH = f"gs://{GCS_BUCKET_NAME}/data/"
GCS_MODELS_PATH = f"gs://{GCS_BUCKET_NAME}/models/"
GCS_REPORTS_PATH = f"gs://{GCS_BUCKET_NAME}/reports/"

# --- Data Timeframes ---
# Adjusted for 1 year for mock data generation, change to 2*365 for full history
TIME_WINDOW_DAYS = 365
ONE_YEAR_AGO = (datetime.now() - timedelta(days=TIME_WINDOW_DAYS)).strftime('%Y-%m-%d')
FUTURE_DATE_BUFFER_WEEKS = 12 # How many weeks into the future to consider for relay moves

# --- Optimization Thresholds & Parameters ---
TOTAL_WEEKLY_HOURS_THRESHOLD = 500000
NM_AVG_HOURS_THRESHOLD = 40.0

# Holiday thresholds (example - confirm with manager)
HOLIDAY_TOTAL_WEEKLY_HOURS_THRESHOLD = 450000 # Example: 10% lower
HOLIDAY_NM_AVG_HOURS_THRESHOLD = 35.0 # Example: 10% lower

# Cost/Penalties for Optimization (Tune these based on business priorities)
PENALTY_OVER_TOTAL_HOURS = 1000 # High penalty for exceeding main threshold
PENALTY_OVER_NM_HOURS_PROXY = 500 # High penalty for exceeding NM total hours proxy
COST_PER_RELAY_MOVE = 1 # Cost for moving a single relay
# For NM avg, we need a proxy for the total hours. This assumes a max number of NM stores
# that typically have relays in a week. Needs to be validated from real data.
MAX_PROBABLE_NM_STORES_PER_WEEK = 20

# --- File Paths ---
LOCAL_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../data')
LOCAL_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../models')
LOCAL_REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../output_reports')

# Create local directories if they don't exist
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
os.makedirs(LOCAL_MODELS_DIR, exist_ok=True)
os.makedirs(LOCAL_REPORTS_DIR, exist_ok=True)

# --- Column Mappings (Based on your clarifications) ---
RELAY_HOURS_COL = "Total_Store_Hours" # From 'MTRAK Query'
SEASONAL_DESC_VALUE = "Seasonal Relay" # From 'MTRAK Query'[Short_Desc]
DC_REALIGN_DESC_VALUE = "DC Realignment" # From 'MTRAK Query'[Short_Desc]