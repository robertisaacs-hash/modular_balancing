# modular_balancing/src/feature_engineering.py

import pandas as pd
import numpy as np

from src.utils import save_to_gcs_pickle
from src.config import (
    GCS_DATA_PATH, RELAY_HOURS_COL, SEASONAL_DESC_VALUE, DC_REALIGN_DESC_VALUE
)


def calculate_dax_measures(df: pd.DataFrame):
    """
    Calculates OveractiveCategories, OveractiveRelays, and OveractivityOccurrences
    based on the provided DAX logic.
    Assumes df contains 'DeptCat', 'RelayYear', 'Relay_ID', and 'Relay_Change_Perc'.
    For a granular master schedule (Relay_ID x Store_ID), this will likely provide
    an *overall* summary across all stores rather than per-store DAX metrics typically.
    """
    if df.empty:
        return {'OveractiveCategories': 0, 'OveractiveRelays': 0, 'OveractivityOccurrences': 0}

    # Filter for Relay_Change_Perc >= 0.5
    filtered_relays = df[df['Relay_Change_Perc'] >= 0.5]

    if filtered_relays.empty:
         return {'OveractiveCategories': 0, 'OveractiveRelays': 0, 'OveractivityOccurrences': 0}

    # Summarized data for DISTINCT COUNT (Relay_ID)
    # Grouping by DeptCat and RelayYear as in original DAX
    summarized_data_distinct = filtered_relays.groupby(['DeptCat', 'RelayYear']).agg(
        CountRelayID=('Relay_ID', 'nunique')
    ).reset_index()

    # Summarized data for COUNT (Relay_ID) - used for OveractivityOccurrences
    summarized_data_count = filtered_relays.groupby(['DeptCat', 'RelayYear']).agg(
        CountRelayID_Occurrences=('Relay_ID', 'count')
    ).reset_index()

    # OveractiveCategories
    overactive_dept_year_groups = summarized_data_distinct[summarized_data_distinct['CountRelayID'] > 2]
    overactive_categories = overactive_dept_year_groups['DeptCat'].nunique()

    # OveractiveRelays
    overactive_relays = overactive_dept_year_groups['CountRelayID'].sum()

    # OveractivityOccurrences
    overactive_occurrences_groups = summarized_data_count[summarized_data_count['CountRelayID_Occurrences'] > 2]
    sum_of_occurrences = overactive_occurrences_groups['CountRelayID_Occurrences'].sum()
    overactivity_occurrences = 1 if sum_of_occurrences > 2 else 0

    return {
        'OveractiveCategories': overactive_categories,
        'OveractiveRelays': overactive_relays,
        'OveractivityOccurrences': overactivity_occurrences
    }


def run_feature_engineering(raw_data: dict):
    """
    Performs feature engineering to create the master schedule dataframe.
    """
    print("--- Starting Feature Engineering ---")

    df_relays = raw_data['df_relays']
    df_msa = raw_data['df_msa']
    df_overactive_bridge = raw_data['df_overactive_bridge']
    df_bra_mra = raw_data['df_bra_mra']
    df_adj = raw_data['df_adj']
    df_holidays = raw_data['df_holidays']
    
    # Ensure date columns are datetime objects
    df_relays['WK_End_Date'] = pd.to_datetime(df_relays['WK_End_Date'])
    df_msa['Mod_Eff_Date'] = pd.to_datetime(df_msa['Mod_Eff_Date'])
    df_holidays['WK_End_Date'] = pd.to_datetime(df_holidays['WK_End_Date'])
    df_bra_mra['Original_WK_End_Date'] = pd.to_datetime(df_bra_mra['Original_WK_End_Date'])
    df_bra_mra['Requested_Move_WK'] = pd.to_datetime(df_bra_mra['Requested_Move_WK'])
    df_overactive_bridge['WK_End_Date'] = pd.to_datetime(df_overactive_bridge['WK_End_Date'])


    # --- 1. Map provided definitions to DataFrame columns for df_relays ---
    # Relay_Hours
    if RELAY_HOURS_COL in df_relays.columns:
        df_relays['Relay_Hours'] = df_relays[RELAY_HOURS_COL].astype(float)
    else:
        print(f"Warning: '{RELAY_HOURS_COL}' not found in df_relays. Generating mock 'Relay_Hours'.")
        df_relays['Relay_Hours'] = np.random.randint(50, 500, len(df_relays)).astype(float)

    # Is_Seasonal / Is_DC_Realign
    if 'Short_Desc' in df_relays.columns:
        df_relays['Is_Seasonal'] = (df_relays['Short_Desc'] == SEASONAL_DESC_VALUE)
        df_relays['Is_DC_Realign'] = (df_relays['Short_Desc'] == DC_REALIGN_DESC_VALUE)
    else:
        print(f"Warning: 'Short_Desc' not found in df_relays. Generating mock 'Is_Seasonal'/'Is_DC_Realign'.")
        df_relays['Is_Seasonal'] = np.random.choice([True, False], len(df_relays), p=[0.1, 0.9])
        df_relays['Is_DC_Realign'] = np.random.choice([True, False], len(df_relays), p=[0.05, 0.95])

    # Ensure RelayYear is present (already handled in mock generation, but good to check)
    if 'RelayYear' not in df_relays.columns and 'WK_End_Date' in df_relays.columns:
        df_relays['RelayYear'] = df_relays['WK_End_Date'].dt.year
    elif 'RelayYear' not in df_relays.columns:
        print("🚨 Error: 'RelayYear' column is missing and cannot be derived. DAX measures will not work.")


    # --- 2. Create Master Schedule (Relay_ID x Store_ID Granularity) ---
    # df_overactive_bridge is the link between Relay_ID and Store_ID/Store_Type.
    # Rename 'Store' in bridge table to 'Store_ID' for consistency
    if 'Store' in df_overactive_bridge.columns:
        df_overactive_bridge.rename(columns={'Store': 'Store_ID'}, inplace=True)
    if 'Store_ID' not in df_overactive_bridge.columns:
        print("🚨 Error: 'Store_ID' column missing in df_overactive_bridge. Cannot create master schedule.")
        return None

    df_overactive_bridge['Store_ID'] = df_overactive_bridge['Store_ID'].astype(str)
    df_relays['Relay_ID'] = df_relays['Relay_ID'].astype(str)
    
    # Merge df_relays with the bridge table to get Store_ID and Store_Type per relay instance
    # This creates rows for each (Relay_ID, Store_ID) combination for a given WK_End_Date
    df_master_schedule = df_relays.merge(
        df_overactive_bridge[['Relay_ID', 'Store_ID', 'Store_Type', 'WK_End_Date']],
        on=['Relay_ID', 'WK_End_Date'], # Merge on both to ensure specific instances
        how='inner' # Only include relay-store instances found in the bridge
    )
    df_master_schedule['Store_Type'] = df_master_schedule['Store_Type'].fillna('Unknown')
    print(f"Master schedule created with {len(df_master_schedule)} relay-store instances.")

    # Store original week for later comparison and as a key feature
    df_master_schedule['Original_WK_End_Date'] = df_master_schedule['WK_End_Date']

    # --- 3. Add Holiday Flags ---
    df_master_schedule = df_master_schedule.merge(
        df_holidays[['WK_End_Date', 'Is_Holiday']],
        on='WK_End_Date',
        how='left'
    )
    df_master_schedule['Is_Holiday'] = df_master_schedule['Is_Holiday'].fillna(False)


    # --- 4. Add Adjacency Group ID ---
    df_master_schedule = df_master_schedule.merge(
        df_adj,
        on='Relay_ID',
        how='left'
    )
    df_master_schedule['Adjustment_Group_ID'] = df_master_schedule['Adjustment_Group_ID'].fillna('NO_GROUP')


    # --- 5. Identify Hard Constraints ---
    df_master_schedule['Cannot_Move'] = False
    df_master_schedule.loc[df_master_schedule['Is_Seasonal'] == True, 'Cannot_Move'] = True
    df_master_schedule.loc[df_master_schedule['Is_DC_Realign'] == True, 'Cannot_Move'] = True


    # --- 6. Integrate BRA/MRA information ---
    # Merge on Relay_ID for pending requests. Status will be 'None' if no request
    df_master_schedule = df_master_schedule.merge(
        df_bra_mra[['Relay_ID', 'Request_Type', 'Requested_Move_WK', 'Status']],
        on='Relay_ID',
        how='left',
        suffixes=('', '_Requested')
    )
    df_master_schedule['Request_Type'] = df_master_schedule['Request_Type'].fillna('None')
    df_master_schedule['Requested_Move_WK'] = df_master_schedule['Requested_Move_WK'].fillna(pd.NaT)
    df_master_schedule['Status'] = df_master_schedule['Status'].fillna('None')

    # --- 7. Calculate DAX Measures (as overall context) ---
    # These are calculated on the full, granular master schedule
    dax_metrics = calculate_dax_measures(df_master_schedule)
    print("\n--- Current DAX Metrics (Overall) ---")
    print(dax_metrics)


    print("\n--- Processed Master Schedule Sample ---")
    print(df_master_schedule.head())
    print(df_master_schedule.info())

    # Save processed data
    save_to_gcs_pickle(df_master_schedule, f"{GCS_DATA_PATH}processed_master_schedule.pkl")
    print("--- Feature Engineering Complete ---")
    
    return df_master_schedule, dax_metrics

def create_master_schedule(raw_data):
    """Create comprehensive master schedule"""
    df_relays = raw_data.get('df_relays', pd.DataFrame())
    
    if df_relays.empty:
        # Create mock data structure
        df_relays = pd.DataFrame({
            'Relay_ID': [f'REL_{i:04d}' for i in range(100)],
            'Store': np.random.choice(['Store_' + str(i) for i in range(1, 21)], 100),
            'DeptCat': np.random.choice(['Grocery', 'Electronics', 'Clothing', 'Home', 'Pharmacy'], 100),
            'Associate_Hours_Impact': np.random.uniform(4, 16, 100),
            'Relay_Hours': np.random.uniform(8, 32, 100)
        })
    
    # Apply cost and risk calculations
    from src.enhanced_analytics import calculate_cost_impact_analysis
    df_master = calculate_cost_impact_analysis(df_relays)
    
    return df_master
from src.enhanced_analytics import calculate_cost_impact_analysis

def create_master_schedule(raw_data):
    """Create comprehensive master schedule from raw data"""
    df_relays = raw_data.get('df_relays', pd.DataFrame())
    
    # If no relay data, create mock structure for development
    if df_relays.empty:
        print("⚠️ No relay data found, generating mock data for development")
        df_relays = pd.DataFrame({
            'Relay_ID': [f'REL_{i:04d}' for i in range(100)],
            'Store': [f'Store_{i%20 + 1:03d}' for i in range(100)],
            'DeptCat': np.random.choice(['Grocery', 'Electronics', 'Clothing', 'Home', 'Pharmacy'], 100),
            'Associate_Hours_Impact': np.random.uniform(4, 16, 100),
            'Relay_Hours': np.random.uniform(8, 32, 100),
            'WK_End_Date': pd.date_range(start='2024-01-01', periods=100, freq='W').strftime('%Y-%m-%d')
        })
    
    # Apply cost and risk calculations
    df_master = calculate_cost_impact_analysis(df_relays)
    
    print(f"✅ Created master schedule with {len(df_master)} relays")
    return df_master