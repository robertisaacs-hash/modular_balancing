# modular_balancing/src/data_ingestion.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.utils import get_bigquery_data, save_to_gcs_pickle
from src.config import (
    PROJECT_ID_SHRNK, PROJECT_ID_AP, ONE_YEAR_AGO, FUTURE_DATE_BUFFER_WEEKS,
    BQ_RELAYS_TABLE_ID, BQ_MSA_TABLE_ID, BQ_OVERACTIVE_BRIDGE_TABLE_ID,
    GCS_DATA_PATH, RELAY_HOURS_COL, SEASONAL_DESC_VALUE, DC_REALIGN_DESC_VALUE,
    TIME_WINDOW_DAYS
)

def _generate_mock_relays(num_relays=1000):
    """Enhanced mock relay data with merchant request analytics"""
    print("Generating enhanced mock df_relays data...")
    two_years_ago_dt = datetime.now() - timedelta(days=2 * 365)
    current_date_dt = datetime.now()
    future_date_dt = current_date_dt + timedelta(weeks=FUTURE_DATE_BUFFER_WEEKS)
    
    wk_end_dates_full = pd.to_datetime(pd.date_range(start=two_years_ago_dt, end=future_date_dt, freq='W'))
    wk_end_dates_recent = wk_end_dates_full[wk_end_dates_full >= (current_date_dt - timedelta(days=TIME_WINDOW_DAYS))]

    dept_cats = ['Grocery', 'Electronics', 'Apparel', 'Home', 'Health', 'General Merchandise']
    mock_relay_ids = np.arange(1, num_relays + 1).astype(str)

    # Enhanced data with merchant request analytics
    data = {
        'Relay_ID': mock_relay_ids,
        'WK_End_Date': np.random.choice(wk_end_dates_recent, num_relays),
        'DeptCat': np.random.choice(dept_cats, num_relays),
        'Relay_Change_Perc': np.random.uniform(0.1, 1.0, num_relays),
        'Total_Store_Hours': np.random.randint(100, 500, num_relays),
        'Short_Desc': np.random.choice([
            'Regular Relay', SEASONAL_DESC_VALUE, DC_REALIGN_DESC_VALUE, 
            'Promotional Relay', 'Emergency Relay'
        ], num_relays),
        'RelayYear': np.random.choice([2024, 2025, 2026], num_relays),
        RELAY_HOURS_COL: np.random.uniform(10, 50, num_relays),
        
        # Enhanced merchant analytics fields
        'Request_Reason': np.random.choice([
            'Seasonal Demand', 'Inventory Constraints', 'Store Traffic Patterns',
            'Competitive Response', 'Promotional Calendar', 'Supply Chain Issues',
            'Customer Feedback', 'Store Renovation', 'Product Launch'
        ], num_relays, p=[0.25, 0.15, 0.15, 0.1, 0.15, 0.1, 0.05, 0.03, 0.02]),
        
        'Historical_Moves_Count': np.random.poisson(2, num_relays),  # Average 2 moves per relay
        'Days_Since_Last_Move': np.random.exponential(45, num_relays).astype(int),
        'Associate_Hours_Impact': np.random.normal(8, 2, num_relays).clip(2, 20),  # Hours per move
        'Merchant_Priority': np.random.choice(['Low', 'Medium', 'High', 'Critical'], num_relays, p=[0.4, 0.3, 0.25, 0.05]),
        'Store_Performance_Score': np.random.normal(75, 15, num_relays).clip(0, 100),
        'Customer_Traffic_Index': np.random.normal(100, 25, num_relays).clip(20, 200),
        'Inventory_Turnover_Rate': np.random.exponential(4, num_relays).clip(0.5, 20),
        'Sales_Impact_Score': np.random.normal(50, 20, num_relays).clip(0, 100),
        'Complexity_Score': np.random.choice([1, 2, 3, 4, 5], num_relays, p=[0.1, 0.2, 0.4, 0.2, 0.1]),
        'Last_Modified_By': np.random.choice([
            'merchant_a', 'merchant_b', 'merchant_c', 'system_auto', 'store_mgr_1'
        ], num_relays),
        'Approval_Level_Required': np.random.choice(['Store', 'Regional', 'Corporate'], num_relays, p=[0.6, 0.3, 0.1])
    }

    return pd.DataFrame(data)

def _generate_mock_msa(relay_ids_for_linking=None, n_rows=500):
    """Enhanced MSA data with store analytics"""
    print("Generating enhanced mock df_msa data...")
    
    if relay_ids_for_linking is None:
        relay_ids_for_linking = [str(i) for i in range(1, 201)]
    
    store_types = ['Supercenter', 'Neighborhood Market', 'Sam\'s Club', 'Express']
    regions = ['Northeast', 'Southeast', 'Midwest', 'Southwest', 'West']
    
    data = {
        'Store': np.random.randint(1000, 1200, n_rows),
        'Store_Type': np.random.choice(store_types, n_rows, p=[0.6, 0.25, 0.1, 0.05]),
        'Region': np.random.choice(regions, n_rows),
        'Store_Size_SqFt': np.random.normal(150000, 30000, n_rows).clip(50000, 300000).astype(int),
        'Annual_Sales_M': np.random.normal(80, 20, n_rows).clip(20, 200),
        'Employee_Count': np.random.normal(300, 75, n_rows).clip(50, 800).astype(int),
        'Customer_Count_Daily': np.random.normal(2500, 600, n_rows).clip(500, 8000).astype(int),
        'Parking_Spaces': np.random.normal(400, 100, n_rows).clip(100, 1000).astype(int),
        'Years_Operating': np.random.randint(1, 30, n_rows),
        'Renovation_Score': np.random.choice([1, 2, 3, 4, 5], n_rows, p=[0.1, 0.2, 0.4, 0.2, 0.1]),
        'Digital_Adoption_Score': np.random.normal(70, 15, n_rows).clip(0, 100),
        'Seasonal_Variation_Index': np.random.normal(1.2, 0.3, n_rows).clip(0.5, 3.0)
    }
    
    return pd.DataFrame(data)

def _generate_mock_overactive_bridge(df_relays_raw, df_msa_raw):
    """Enhanced overactive bridge data"""
    print("Generating enhanced mock df_overactive_bridge data...")
    
    # Sample relays that might be overactive
    overactive_sample = df_relays_raw.sample(n=min(100, len(df_relays_raw)))
    
    data = {
        'Relay_ID': overactive_sample['Relay_ID'].values,
        'DeptCat': overactive_sample['DeptCat'].values,
        'WK_End_Date': overactive_sample['WK_End_Date'].values,
        'Overactive_Reason': np.random.choice([
            'High Traffic Week', 'Holiday Period', 'Promotional Event',
            'Inventory Surge', 'Competitive Response', 'Supply Chain Delay'
        ], len(overactive_sample)),
        'Severity_Level': np.random.choice(['Medium', 'High', 'Critical'], len(overactive_sample), p=[0.5, 0.4, 0.1]),
        'Expected_Duration_Days': np.random.randint(3, 21, len(overactive_sample)),
        'Mitigation_Strategy': np.random.choice([
            'Defer Non-Critical', 'Add Temp Staff', 'Extend Hours', 'Postpone'
        ], len(overactive_sample))
    }
    
    return pd.DataFrame(data)

def _generate_mock_bra_mra(df_relays_raw):
    """Enhanced Business/Merchant Requested Adjustments data"""
    print("Generating enhanced mock BRA/MRA data...")
    
    # Sample subset of relays for requests
    request_sample = df_relays_raw.sample(n=min(250, len(df_relays_raw)))
    current_date = datetime.now()
    
    data = {
        'Request_ID': [f"REQ_{i:06d}" for i in range(1, len(request_sample) + 1)],
        'Relay_ID': request_sample['Relay_ID'].values,
        'Store_ID': np.random.randint(1000, 1200, len(request_sample)),
        'Request_Type': np.random.choice(['BRA', 'MRA'], len(request_sample), p=[0.6, 0.4]),
        'Status': np.random.choice(['Pending', 'Approved', 'Rejected', 'In Progress'], 
                                 len(request_sample), p=[0.4, 0.3, 0.2, 0.1]),
        'Requested_Move_WK': pd.to_datetime([
            current_date + timedelta(weeks=np.random.randint(-4, 12)) 
            for _ in range(len(request_sample))
        ]),
        'Original_WK_End_Date': request_sample['WK_End_Date'].values,
        'Requested_By': np.random.choice([
            'merchant_team_1', 'merchant_team_2', 'regional_mgr_1', 
            'category_mgr_1', 'store_operations'
        ], len(request_sample)),
        'Business_Justification': np.random.choice([
            'Seasonal alignment', 'Promotional support', 'Inventory management',
            'Customer experience', 'Competitive response', 'Operational efficiency'
        ], len(request_sample)),
        'Priority_Level': np.random.choice(['Low', 'Medium', 'High', 'Urgent'], 
                                         len(request_sample), p=[0.3, 0.4, 0.25, 0.05]),
        'Expected_Sales_Impact': np.random.normal(5000, 2000, len(request_sample)).clip(0, 50000),
        'Cost_Estimate': np.random.normal(1500, 500, len(request_sample)).clip(200, 10000),
        'Approval_Chain': np.random.choice([
            'Store->Regional', 'Regional->Corporate', 'Auto-Approved', 'Corporate Review'
        ], len(request_sample), p=[0.4, 0.3, 0.2, 0.1]),
        'Timestamp': pd.to_datetime([
            current_date - timedelta(days=np.random.randint(1, 90)) 
            for _ in range(len(request_sample))
        ])
    }
    
    return pd.DataFrame(data)

def _generate_mock_adjacencies(df_relays_raw):
    """Generate mock adjacency/grouping data"""
    print("Generating mock df_adj data...")
    
    num_groups = min(50, len(df_relays_raw) // 10)
    relay_sample = df_relays_raw.sample(n=min(200, len(df_relays_raw)))
    
    # Create adjustment groups
    group_data = []
    for i in range(num_groups):
        group_size = np.random.randint(2, 8)  # Groups of 2-7 relays
        group_relays = relay_sample.sample(n=min(group_size, len(relay_sample)))
        
        for _, relay in group_relays.iterrows():
            group_data.append({
                'Adjustment_Group_ID': f'GROUP_{i+1}',
                'Relay_ID': relay['Relay_ID'],
                'Group_Type': np.random.choice(['Seasonal', 'Promotional', 'Operational']),
                'Sync_Required': np.random.choice([True, False], p=[0.7, 0.3]),
                'Lead_Relay': i == 0,  # First relay in group is lead
                'Dependency_Level': np.random.choice(['High', 'Medium', 'Low'], p=[0.3, 0.5, 0.2])
            })
    
    return pd.DataFrame(group_data)

def _generate_mock_holidays():
    """Generate mock holiday data"""
    print("Generating mock df_holidays data...")
    
    current_year = datetime.now().year
    holidays = []
    
    # Define major retail holidays
    holiday_dates = [
        (f'{current_year}-01-01', 'New Year'),
        (f'{current_year}-07-04', 'Independence Day'),
        (f'{current_year}-11-28', 'Thanksgiving'),
        (f'{current_year}-12-25', 'Christmas'),
        (f'{current_year}-11-29', 'Black Friday'),
        (f'{current_year}-12-26', 'Post-Christmas'),
        (f'{current_year+1}-01-01', 'New Year'),
        (f'{current_year+1}-07-04', 'Independence Day'),
        (f'{current_year+1}-11-27', 'Thanksgiving'),
        (f'{current_year+1}-12-25', 'Christmas')
    ]
    
    for date_str, name in holiday_dates:
        # Add the holiday and surrounding weeks
        base_date = pd.to_datetime(date_str)
        for offset in [-7, 0, 7]:  # Week before, during, and after
            holiday_week = base_date + timedelta(days=offset)
            holidays.append({
                'WK_End_Date': holiday_week,
                'Holiday_Name': name,
                'Holiday_Type': 'Major' if name in ['Christmas', 'Thanksgiving'] else 'Standard',
                'Traffic_Multiplier': np.random.uniform(1.2, 2.5) if offset == 0 else np.random.uniform(0.8, 1.4),
                'Staffing_Adjustment': np.random.uniform(1.1, 1.8)
            })
    
    return pd.DataFrame(holidays)

def load_all_raw_data(use_mock_data=False):
    """Load all raw data with enhanced mock data generation"""
    if use_mock_data:
        print("🔄 Loading enhanced mock data...")
        
        # Generate enhanced mock data
        df_relays = _generate_mock_relays(1000)
        df_msa = _generate_mock_msa(df_relays['Relay_ID'].unique(), 500)
        df_overactive_bridge = _generate_mock_overactive_bridge(df_relays, df_msa)
        df_bra_mra = _generate_mock_bra_mra(df_relays)
        df_adj = _generate_mock_adjacencies(df_relays)
        df_holidays = _generate_mock_holidays()
        
        print(f"✅ Generated enhanced mock data:")
        print(f"   - Relays: {len(df_relays)} records")
        print(f"   - MSA: {len(df_msa)} records")
        print(f"   - Overactive Bridge: {len(df_overactive_bridge)} records")
        print(f"   - BRA/MRA Requests: {len(df_bra_mra)} records")
        print(f"   - Adjustment Groups: {len(df_adj)} records")
        print(f"   - Holidays: {len(df_holidays)} records")
        
        return {
            'df_relays': df_relays,
            'df_msa': df_msa,
            'df_overactive_bridge': df_overactive_bridge,
            'df_bra_mra': df_bra_mra,
            'df_adj': df_adj,
            'df_holidays': df_holidays
        }
    else:
        # Use existing production data loading logic
        print("🔄 Loading production data from BigQuery/GCS...")
        # ... existing production data loading code ...
        pass