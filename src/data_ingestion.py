# modular_balancing/src/data_ingestion.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.utils import get_bigquery_data, save_to_gcs_pickle
from src.config import (
    PROJECT_ID_SHRNK, PROJECT_ID_AP,ONE_YEAR_AGO, FUTURE_DATE_BUFFER_WEEKS,
    BQ_RELAYS_TABLE_ID, BQ_MSA_TABLE_ID, BQ_OVERACTIVE_BRIDGE_TABLE_ID,
    GCS_DATA_PATH, RELAY_HOURS_COL, SEASONAL_DESC_VALUE, DC_REALIGN_DESC_VALUE
)


def _generate_mock_relays(num_relays=1000):
    print("Generating mock df_relays data...")
    two_years_ago_dt = datetime.now() - timedelta(days=2 * 365)
    current_date_dt = datetime.now()
    future_date_dt = current_date_dt + timedelta(weeks=FUTURE_DATE_BUFFER_WEEKS)
    
    wk_end_dates_full = pd.to_datetime(pd.date_range(start=two_years_ago_dt, end=future_date_dt, freq='W'))
    wk_end_dates_recent = wk_end_dates_full[wk_end_dates_full >= (current_date_dt - timedelta(days=TIME_WINDOW_DAYS))]


    dept_cats = ['Grocery', 'Electronics', 'Apparel', 'Home', 'Health', 'General Merchandise']

    mock_relay_ids = np.arange(1, num_relays + 1).astype(str)

    data = {
        'Relay_ID': mock_relay_ids,
        'WK_End_Date': np.random.choice(wk_end_dates_recent, num_relays),
        'DeptCat': np.random.choice(dept_cats, num_relays),
        'Relay_Change_Perc': np.random.rand(num_relays) * 0.7 + 0.3, # 0.3 to 1.0
        RELAY_HOURS_COL: np.random.randint(50, 500, num_relays), # Total_Store_Hours
        'Short_Desc': np.random.choice(
            ['Regular Relay', SEASONAL_DESC_VALUE, DC_REALIGN_DESC_VALUE, 'Special Event'],
            num_relays,
            p=[0.8, 0.1, 0.05, 0.05]
        ),
    }
    df = pd.DataFrame(data)
    df['WK_End_Date'] = pd.to_datetime(df['WK_End_Date'])
    df['Relay_ID'] = df['Relay_ID'].astype(str)
    df['DeptCat'] = df['DeptCat'].astype(str)
    
    # Derive RelayYear as it's used in DAX measures
    df['RelayYear'] = df['WK_End_Date'].dt.year

    return df


def _generate_mock_msa(num_msa_records=500, relay_ids_for_linking=None):
    print("Generating mock df_msa data...")
    current_date_dt = datetime.now()
    future_date_dt = current_date_dt + timedelta(weeks=FUTURE_DATE_BUFFER_WEEKS)
    wk_end_dates = pd.to_datetime(pd.date_range(start=ONE_YEAR_AGO, end=future_date_dt, freq='W'))

    mod_types = ['Standard', 'Small Format', 'Large Format']
    
    # Generate Store_IDs ensuring some overlap with actual/mock relays
    if relay_ids_for_linking is not None and not relay_ids_for_linking.empty:
         # Assuming relay_ids_for_linking has 'Store_ID'
         stores_used_in_relays = relay_ids_for_linking['Store_ID'].unique()
         mock_store_ids = np.concatenate((
             stores_used_in_relays,
             np.arange(max(map(int, stores_used_in_relays)) + 1, max(map(int, stores_used_in_relays)) + 51).astype(str)
         ))
         mock_store_ids = np.unique(mock_store_ids) # Remove duplicates
    else:
        mock_store_ids = np.arange(1001, 1051).astype(str) # 50 stores

    data = {
        'Mod_ID': np.arange(10001, 10001 + num_msa_records).astype(str),
        'Store': np.random.choice(mock_store_ids, num_msa_records, replace=True), # 'Store' column for Store_ID
        'Mod_Eff_Date': np.random.choice(wk_end_dates, num_msa_records),
        'Mod_Type': np.random.choice(mod_types, num_msa_records),
        'Store_Type': np.random.choice(['Neighborhood Market', 'Supercenter', 'Division 1'], num_msa_records, p=[0.2, 0.7, 0.1]),
    }
    df = pd.DataFrame(data)
    df['Mod_Eff_Date'] = pd.to_datetime(df['Mod_Eff_Date'])
    df['Store'] = df['Store'].astype(str)
    return df

def _generate_mock_overactive_bridge(df_relays_raw, df_msa_raw):
    print("Generating mock df_overactive_bridge data...")
    current_date_dt = datetime.now()
    future_date_dt = current_date_dt + timedelta(weeks=FUTURE_DATE_BUFFER_WEEKS)
    wk_end_dates = pd.to_datetime(pd.date_range(start=ONE_YEAR_AGO, end=future_date_dt, freq='W'))

    bridge_data = []
    
    # Ensure relays have associated stores in the bridge
    relays_to_use = df_relays_raw[df_relays_raw['WK_End_Date'] >= pd.to_datetime(ONE_YEAR_AGO)]
    if relays_to_use.empty:
      relays_to_use = df_relays_raw # Fallback if filtering makes it empty

    store_ids_from_msa = df_msa_raw['Store'].unique()
    
    for _, relay_row in relays_to_use.iterrows():
        relay_id = relay_row['Relay_ID']
        # Each relay impacts a random number of stores
        num_stores_for_relay = np.random.randint(1, 5) 
        stores_affected = np.random.choice(store_ids_from_msa, num_stores_for_relay, replace=False)
        
        for store_id in stores_affected:
            # For mock, use a random store type, in real data this comes from MSA
            store_type = np.random.choice(['Neighborhood Market', 'Supercenter', 'Division 1'])
            
            bridge_data.append({
                'Relay_ID': relay_id,
                'Store': store_id, # This is the Store_ID in the bridge table
                'Store_Type': store_type, # This is the Store_Type for the Store_ID
                'WK_End_Date': relay_row['WK_End_Date'] # Link by WK_End_Date too
            })
            
    df = pd.DataFrame(bridge_data)
    df['Store'] = df['Store'].astype(str)
    df['Relay_ID'] = df['Relay_ID'].astype(str)
    df['WK_End_Date'] = pd.to_datetime(df['WK_End_Date'])
    return df

def _generate_mock_bra_mra(df_relays_raw):
    print("Generating mock df_bra_mra data...")
    wk_end_dates = pd.to_datetime(pd.date_range(start=ONE_YEAR_AGO, end=datetime.now() + timedelta(weeks=FUTURE_DATE_BUFFER_WEEKS), freq='W'))

    num_requests = 50
    bra_mra_data = []

    # Get relays that are in the future from current_date to allow for requests
    future_relays = df_relays_raw[df_relays_raw['WK_End_Date'] >= datetime.now()].copy()
    if future_relays.empty:
        # Fallback if no future relays, just use all relays.
        # In real scenario, requests are for future moves.
        future_relays = df_relays_raw.sample(n=min(len(df_relays_raw), num_requests), random_state=42)

    if len(future_relays) < num_requests:
         num_requests = len(future_relays)

    for i in range(num_requests):
        relay_idx = np.random.randint(0, len(future_relays))
        relay_id = future_relays.iloc[relay_idx]['Relay_ID']
        original_wk = future_relays.iloc[relay_idx]['WK_End_Date']

        # Ensure requested_move_wk is different from original for some
        possible_move_weeks = wk_end_dates[wk_end_dates != original_wk]
        if not possible_move_weeks.empty:
            requested_move_wk = np.random.choice(possible_move_weeks)
        else:
            requested_move_wk = original_wk # Should not happen if wk_end_dates is large enough

        bra_mra_data.append({
            'Request_ID': i + 1,
            'Relay_ID': relay_id,
            'Original_WK_End_Date': original_wk,
            'Requested_Move_WK': requested_move_wk,
            'Request_Type': np.random.choice(['BRA', 'MRA'], p=[0.6, 0.4]),
            'Status': np.random.choice(['Pending', 'Approved', 'Rejected'], p=[0.7, 0.2, 0.1]),
            'Requested_By': 'User_' + str(np.random.randint(1, 10)),
            'Timestamp': pd.to_datetime(datetime.now() - timedelta(days=np.random.randint(1, 30)))
        })
    df = pd.DataFrame(bra_mra_data)
    df['Original_WK_End_Date'] = pd.to_datetime(df['Original_WK_End_Date'])
    df['Requested_Move_WK'] = pd.to_datetime(df['Requested_Move_WK'])
    df['Relay_ID'] = df['Relay_ID'].astype(str)
    return df

def _generate_mock_adjacencies(df_relays_raw):
    print("Generating mock df_adj data...")
    num_adj_groups = 10
    adj_data = []
    
    all_relay_ids_in_scope = df_relays_raw['Relay_ID'].unique()
    
    if len(all_relay_ids_in_scope) < 2 * num_adj_groups: # Ensure enough relays for groups
        print("Not enough relays to create adjacency groups.")
        return pd.DataFrame(columns=['Relay_ID', 'Adjustment_Group_ID'])

    # Ensure relays in groups exist in df_relays
    for i in range(num_adj_groups):
        group_size = np.random.randint(2, 5) # Groups of 2-4 relays
        group_members = np.random.choice(all_relay_ids_in_scope, group_size, replace=False)
        for relay_id in group_members:
            adj_data.append({'Relay_ID': relay_id, 'Adjustment_Group_ID': f'GROUP_{i+1}'})
    df = pd.DataFrame(adj_data)
    df['Relay_ID'] = df['Relay_ID'].astype(str)
    return df

def _generate_mock_holidays():
    print("Generating mock df_holidays data...")
    current_date_dt = datetime.now()
    future_date_dt = current_date_dt + timedelta(weeks=FUTURE_DATE_BUFFER_WEEKS)
    dates_in_scope = pd.to_datetime(pd.date_range(start=ONE_YEAR_AGO, end=future_date_dt, freq='W'))
    
    holiday_data = {
        'WK_End_Date': dates_in_scope,
        'Is_Holiday': np.random.choice([True, False], len(dates_in_scope), p=[0.05, 0.95]) # Lower overall probability
    }
    df = pd.DataFrame(holiday_data)
    # Force some holidays around year-end
    df.loc[
        df['WK_End_Date'].dt.month.isin([11, 12]) &
        (df['WK_End_Date'].dt.day.isin([25, 31]) | (df['WK_End_Date'].dt.weekday == 4)) # Friday before Christmas/NYE
        , 'Is_Holiday'
    ] = True
    df['WK_End_Date'] = pd.to_datetime(df['WK_End_Date'])
    return df


def load_all_raw_data(use_mock_data=False):
    """
    Loads all raw data from BigQuery or generates mock data.
    Saves raw dataframes to GCS.
    """
    print("--- Starting Data Ingestion ---")
    raw_data = {}
    
    # 1. MTRAK_ADHOC.RELAYS
    relays_query = f"""
    SELECT
        Relay_ID, WK_End_Date, DeptCat, Relay_Change_Perc,
        {RELAY_HOURS_COL}, Short_Desc
    FROM {BQ_RELAYS_TABLE_ID}
    WHERE DATE(WK_End_Date) >= DATE('{ONE_YEAR_AGO}')
    """
    df_relays = get_bigquery_data(relays_query, project_id=PROJECT_ID_SHRNK)
    if df_relays.empty and use_mock_data:
        df_relays = _generate_mock_relays()
    if df_relays.empty:
        print("🚨 Error: df_relays is empty. Cannot continue without relay data.")
        return None
    save_to_gcs_pickle(df_relays, f"{GCS_DATA_PATH}raw_relays.pkl")
    raw_data['df_relays'] = df_relays

    # 2. MODSPACE_ADHOC.MSA
    msa_query = f"""
    SELECT
        Mod_ID, Store, Mod_Eff_Date, Mod_Type, Store_Type
    FROM {BQ_MSA_TABLE_ID}
    WHERE DATE(Mod_Eff_Date) >= DATE('{ONE_YEAR_AGO}')
    """
    df_msa = get_bigquery_data(msa_query, project_id=PROJECT_ID_SHRNK)
    if df_msa.empty and use_mock_data:
        df_msa = _generate_mock_msa(relay_ids_for_linking=df_relays) # Pass relays for better linking
    if df_msa.empty:
        print("🚨 Error: df_msa is empty. Cannot continue without MSA data.")
        return None
    save_to_gcs_pickle(df_msa, f"{GCS_DATA_PATH}raw_msa.pkl")
    raw_data['df_msa'] = df_msa
    
    # 3. storeleveloveractivemodulars (The Bridge)
    # Assuming this table contains Relay_ID, Store (as Store_ID), Store_Type, and WK_End_Date
    overactive_bridge_query = f"""
    SELECT *
    FROM {BQ_OVERACTIVE_BRIDGE_TABLE_ID}
    WHERE DATE(WK_End_Date) >= DATE('{ONE_YEAR_AGO}')
    """
    df_overactive_bridge = get_bigquery_data(overactive_bridge_query, project_id=PROJECT_ID_AP)
    if df_overactive_bridge.empty and use_mock_data:
        df_overactive_bridge = _generate_mock_overactive_bridge(df_relays, df_msa)
    if df_overactive_bridge.empty:
        print("🚨 Error: df_overactive_bridge is empty. Cannot continue without bridge data.")
        return None
    save_to_gcs_pickle(df_overactive_bridge, f"{GCS_DATA_PATH}raw_overactive_bridge.pkl")
    raw_data['df_overactive_bridge'] = df_overactive_bridge

    # 4. Mock BRA/MRA Requests (Requires a real table name from Ben Baker)
    # Using mock until the real table is identified
    df_bra_mra = pd.DataFrame() # Placeholder for real BQ query
    if use_mock_data or df_bra_mra.empty: # Only generate mock if no real data or forced
        df_bra_mra = _generate_mock_bra_mra(df_relays)
    save_to_gcs_pickle(df_bra_mra, f"{GCS_DATA_PATH}mock_bra_mra.pkl")
    raw_data['df_bra_mra'] = df_bra_mra

    # 5. Mock Relay Adjacencies (Requires a real table name/source)
    # Using mock until the real table is identified
    df_adj = pd.DataFrame() # Placeholder for real BQ query
    if use_mock_data or df_adj.empty: # Only generate mock if no real data or forced
        df_adj = _generate_mock_adjacencies(df_relays)
    save_to_gcs_pickle(df_adj, f"{GCS_DATA_PATH}mock_adj.pkl")
    raw_data['df_adj'] = df_adj

    # 6. Mock Holiday Calendar (Requires a real table name/source or explicit definition)
    # Using mock until the real table is identified
    df_holidays = pd.DataFrame() # Placeholder for real BQ query
    if use_mock_data or df_holidays.empty: # Only generate mock if no real data or forced
        df_holidays = _generate_mock_holidays()
    save_to_gcs_pickle(df_holidays, f"{GCS_DATA_PATH}mock_holidays.pkl")
    raw_data['df_holidays'] = df_holidays
    
    print("--- Data Ingestion Complete ---")
    return raw_data