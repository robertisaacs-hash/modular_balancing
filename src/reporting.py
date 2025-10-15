# modular_balancing/src/reporting.py
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

from src.utils import load_from_gcs_pickle
from src.config import (
    GCS_DATA_PATH, GCS_MODELS_PATH, GCS_REPORTS_PATH, LOCAL_REPORTS_DIR,
    TOTAL_WEEKLY_HOURS_THRESHOLD, NM_AVG_HOURS_THRESHOLD,
    HOLIDAY_TOTAL_WEEKLY_HOURS_THRESHOLD, HOLIDAY_NM_AVG_HOURS_THRESHOLD,
    MAX_PROBABLE_NM_STORES_PER_WEEK, ONE_YEAR_AGO, FUTURE_DATE_BUFFER_WEEKS
)

# Get the project root directory (parent of src)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output_reports')

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"📁 Reports will be saved to: {OUTPUT_DIR}")

def _get_thresholds_df(df_processed, start_date, end_date):
    """Helper to create a DataFrame with weekly thresholds."""
    all_weeks = pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq='W'))
    threshold_info = df_processed[['WK_End_Date', 'Is_Holiday']].drop_duplicates().set_index('WK_End_Date')
    thresholds_data = []
    for week in all_weeks:
        is_holiday = threshold_info.loc[week, 'Is_Holiday'] if week in threshold_info.index else False
        total_thresh = HOLIDAY_TOTAL_WEEKLY_HOURS_THRESHOLD if is_holiday else TOTAL_WEEKLY_HOURS_THRESHOLD
        nm_total_thresh = (HOLIDAY_NM_AVG_HOURS_THRESHOLD * MAX_PROBABLE_NM_STORES_PER_WEEK) if is_holiday else \
                          (NM_AVG_HOURS_THRESHOLD * MAX_PROBABLE_NM_STORES_PER_WEEK)
        thresholds_data.append({
            'Week': week,
            'Is_Holiday': is_holiday,
            'Total_Hours_Threshold': total_thresh,
            'NM_Total_Hours_Threshold_Proxy': nm_total_thresh
        })
    return pd.DataFrame(thresholds_data)

# --- VISUALIZATION FUNCTIONS ---

def plot_relay_activity_heatmap(df_master_schedule):
    """Heatmap of relay activity by Store and Week."""
    pivot = df_master_schedule.pivot_table(
        index='Store_ID',
        columns='WK_End_Date',
        values='Relay_Hours',
        aggfunc='sum',
        fill_value=0
    )
    plt.figure(figsize=(20, 8))
    sns.heatmap(pivot, cmap='YlGnBu')
    plt.title('Relay Activity Heatmap (Store vs. Week)')
    plt.xlabel('Week Ending Date')
    plt.ylabel('Store ID')
    plt.tight_layout()
    
    filename = 'relay_activity_heatmap.png'
    save_path = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Saved '{filename}' to {save_path}")

def plot_relay_moves_by_dept(df_moved_relays: pd.DataFrame):
    """Bar chart of relay moves by department category."""
    if df_moved_relays.empty or 'DeptCat' not in df_moved_relays.columns:
        print("⚠️ No relay moves or DeptCat column missing, skipping dept chart.")
        return
    
    dept_counts = df_moved_relays['DeptCat'].value_counts().reset_index()
    dept_counts.columns = ['DeptCat', 'Moves']
    
    plt.figure(figsize=(10, 6))
    sns.barplot(data=dept_counts, x='DeptCat', y='Moves', palette='viridis')
    plt.title('Relay Moves by Department')
    plt.xlabel('Department')
    plt.ylabel('Number of Moves')
    plt.tight_layout()
    
    filename = 'relay_moves_by_dept.png'
    save_path = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Saved '{filename}' to {save_path}")

def plot_relay_status_pie(df_master_schedule: pd.DataFrame):
    """Pie chart of relay request statuses (BRA/MRA)."""
    if 'Status' not in df_master_schedule.columns:
        print("⚠️ Status column missing, skipping pie chart.")
        return
    
    status_counts = df_master_schedule['Status'].value_counts()
    
    plt.figure(figsize=(6, 6))
    plt.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', startangle=140)
    plt.title('Relay Status Breakdown')
    plt.tight_layout()
    
    filename = 'relay_status_pie.png'
    save_path = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Saved '{filename}' to {save_path}")

def plot_total_weekly_hours_comparison(df_processed: pd.DataFrame, df_suggested_schedule: pd.DataFrame, df_thresholds: pd.DataFrame):
    """Plots total weekly hours before and after optimization."""
    df_current_total_hours = df_processed.groupby('WK_End_Date')['Relay_Hours'].sum().reset_index()
    df_current_total_hours.rename(columns={'WK_End_Date': 'Week', 'Relay_Hours': 'Value'}, inplace=True)
    df_current_total_hours['Type'] = 'Current'

    df_suggested_total_hours = df_suggested_schedule.groupby('Suggested_WK_End_Date')['Relay_Hours'].sum().reset_index()
    df_suggested_total_hours.rename(columns={'Suggested_WK_End_Date': 'Week', 'Relay_Hours': 'Value'}, inplace=True)
    df_suggested_total_hours['Type'] = 'Suggested'

    df_combined_total_hours = pd.concat([df_current_total_hours, df_suggested_total_hours], ignore_index=True)
    df_combined_total_hours = df_combined_total_hours.merge(df_thresholds, on='Week', how='left')

    plt.figure(figsize=(18, 8))
    sns.lineplot(data=df_combined_total_hours, x='Week', y='Value', hue='Type', marker='o')
    plt.plot(df_combined_total_hours['Week'], df_combined_total_hours['Total_Hours_Threshold'],
             color='red', linestyle='--', label='Threshold')
    plt.title('Total Weekly Relay Hours: Current vs. Suggested')
    plt.xlabel('Week Ending Date')
    plt.ylabel('Total Relay Hours')
    plt.xticks(rotation=45)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    
    filename = 'total_weekly_hours_comparison.png'
    save_path = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Saved '{filename}' to {save_path}")

def plot_nm_total_hours_comparison(df_processed: pd.DataFrame, df_suggested_schedule: pd.DataFrame, df_thresholds: pd.DataFrame):
    """Plots NM total hours before and after optimization."""
    nm_store_types = ['Neighborhood Market']
    df_current_nm_scope = df_processed[df_processed['Store_Type'].isin(nm_store_types)]
    df_suggested_nm_scope = df_suggested_schedule[df_suggested_schedule['Store_Type'].isin(nm_store_types)]

    df_current_nm_total_hours = df_current_nm_scope.groupby('WK_End_Date')['Relay_Hours'].sum().reset_index()
    df_current_nm_total_hours.rename(columns={'WK_End_Date': 'Week', 'Relay_Hours': 'Value'}, inplace=True)
    df_current_nm_total_hours['Type'] = 'Current'

    df_suggested_nm_total_hours = df_suggested_nm_scope.groupby('Suggested_WK_End_Date')['Relay_Hours'].sum().reset_index()
    df_suggested_nm_total_hours.rename(columns={'Suggested_WK_End_Date': 'Week', 'Relay_Hours': 'Value'}, inplace=True)
    df_suggested_nm_total_hours['Type'] = 'Suggested'

    df_combined_nm_total_hours = pd.concat([df_current_nm_total_hours, df_suggested_nm_total_hours], ignore_index=True)
    df_combined_nm_total_hours = df_combined_nm_total_hours.merge(df_thresholds, on='Week', how='left')

    plt.figure(figsize=(18, 8))
    sns.lineplot(data=df_combined_nm_total_hours, x='Week', y='Value', hue='Type', marker='o')
    plt.plot(df_combined_nm_total_hours['Week'], df_combined_nm_total_hours['NM_Total_Hours_Threshold_Proxy'],
             color='red', linestyle='--', label='Threshold')
    plt.title(f'Neighborhood Market Total Relay Hours (Proxy for Avg - {MAX_PROBABLE_NM_STORES_PER_WEEK} Stores): Current vs. Suggested')
    plt.xlabel('Week Ending Date')
    plt.ylabel('Total Relay Hours (NM Only)')
    plt.xticks(rotation=45)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    
    filename = 'nm_total_hours_comparison.png'
    save_path = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Saved '{filename}' to {save_path}")

# --- MAIN REPORTING FUNCTION ---

def generate_reports(df_processed: pd.DataFrame, df_suggested_schedule: pd.DataFrame):
    """
    Generates comparison reports between current and suggested schedules.
    """
    print("--- Starting Reporting & Analysis ---")
    print(f"📁 Output directory: {OUTPUT_DIR}")

    # Ensure Suggested_WK_End_Date exists
    if 'Suggested_WK_End_Date' not in df_suggested_schedule.columns:
        print("⚠️ 'Suggested_WK_End_Date' not found, using 'WK_End_Date' as fallback")
        if 'WK_End_Date' in df_suggested_schedule.columns:
            df_suggested_schedule['Suggested_WK_End_Date'] = df_suggested_schedule['WK_End_Date']
        elif 'Original_WK_End_Date' in df_suggested_schedule.columns:
            df_suggested_schedule['Suggested_WK_End_Date'] = df_suggested_schedule['Original_WK_End_Date']
        else:
            print("🚨 Cannot generate reports: No valid date columns found")
            return

    if df_processed.empty or df_suggested_schedule.empty:
        print("Cannot generate reports: input DataFrames are empty.")
        return

    # Ensure date columns are datetime objects
    df_processed['WK_End_Date'] = pd.to_datetime(df_processed['WK_End_Date'])
    df_suggested_schedule['Suggested_WK_End_Date'] = pd.to_datetime(df_suggested_schedule['Suggested_WK_End_Date'])
    
    if 'Original_WK_End_Date' in df_suggested_schedule.columns:
        df_suggested_schedule['Original_WK_End_Date'] = pd.to_datetime(df_suggested_schedule['Original_WK_End_Date'])

    # Determine reporting date range
    min_date = min(df_processed['WK_End_Date'].min(), df_suggested_schedule['Suggested_WK_End_Date'].min())
    max_date = max(df_processed['WK_End_Date'].max(), df_suggested_schedule['Suggested_WK_End_Date'].max()) + pd.Timedelta(weeks=FUTURE_DATE_BUFFER_WEEKS)
    df_thresholds = _get_thresholds_df(df_processed, min_date, max_date)

    # --- Generate Comparison Charts ---
    plot_total_weekly_hours_comparison(df_processed, df_suggested_schedule, df_thresholds)
    plot_nm_total_hours_comparison(df_processed, df_suggested_schedule, df_thresholds)

    # --- 3. Display Moved Relays ---
    if 'Original_WK_End_Date' in df_suggested_schedule.columns:
        df_moved_relays = df_suggested_schedule[
            df_suggested_schedule['Suggested_WK_End_Date'] != df_suggested_schedule['Original_WK_End_Date']
        ].copy()
    else:
        df_moved_relays = pd.DataFrame()
    
    if not df_moved_relays.empty:
        print("\n--- Relays Suggested to Move ---")
        columns_to_show = ['Relay_ID', 'Store_ID']
        optional_cols = ['DeptCat', 'Original_WK_End_Date', 'Suggested_WK_End_Date', 'Relay_Hours', 
                        'Cannot_Move', 'Adjustment_Group_ID']
        for col in optional_cols:
            if col in df_moved_relays.columns:
                columns_to_show.append(col)
        
        moved_summary = df_moved_relays[columns_to_show]
        print(moved_summary.sort_values(['Original_WK_End_Date', 'Relay_ID', 'Store_ID'] 
                                       if 'Original_WK_End_Date' in columns_to_show 
                                       else ['Relay_ID', 'Store_ID']).to_string())
        print(f"\nTotal Number of Relay-Store Instances Moved: {len(df_moved_relays)}")
    else:
        print("\nNo relay-store instances were suggested to move (or all thresholds were already met).")

    # --- 4. Pending Adjustments (BRA/MRA) vs. Suggested Moves ---
    if 'Request_Type' in df_processed.columns:
        df_pending_requests = df_processed[df_processed['Request_Type'] != 'None'].copy()
    else:
        df_pending_requests = pd.DataFrame()
    
    print("\n--- Pending Business/Merchant Requested Adjustments (BRA/MRA) ---")
    if not df_pending_requests.empty and not df_moved_relays.empty:
        merge_cols = ['Relay_ID', 'Store_ID']
        request_cols = [col for col in ['Request_Type', 'Requested_Move_WK', 'Status'] 
                       if col in df_pending_requests.columns]
        
        merged_moves_with_requests = df_moved_relays.merge(
            df_pending_requests[merge_cols + request_cols],
            on=merge_cols,
            how='left'
        )
        
        if 'Requested_Move_WK' in merged_moves_with_requests.columns and 'Status' in merged_moves_with_requests.columns:
            merged_moves_with_requests['Suggested_Matches_Request'] = (
                (merged_moves_with_requests['Suggested_WK_End_Date'] == merged_moves_with_requests['Requested_Move_WK']) &
                (merged_moves_with_requests['Status'] == 'Pending')
            )
            print("\nMatches between Suggested Moves and Pending BRA/MRA Requests (per Relay-Store Instance):")
            display_cols = [col for col in ['Relay_ID', 'Store_ID', 'Request_Type', 'Original_WK_End_Date',
                                            'Requested_Move_WK', 'Suggested_WK_End_Date', 
                                            'Suggested_Matches_Request', 'Status'] 
                           if col in merged_moves_with_requests.columns]
            print(merged_moves_with_requests[display_cols].sort_values(
                ['Original_WK_End_Date', 'Relay_ID', 'Store_ID'] 
                if 'Original_WK_End_Date' in display_cols 
                else ['Relay_ID', 'Store_ID']
            ).to_string())
    elif not df_pending_requests.empty:
        print("\nPending BRA/MRA requests found, but no relays were suggested to move.")
        display_cols = [col for col in ['Relay_ID', 'Store_ID', 'Request_Type', 
                                        'Original_WK_End_Date', 'Requested_Move_WK', 'Status'] 
                       if col in df_pending_requests.columns]
        print(df_pending_requests[display_cols].to_string())
    else:
        print("No pending BRA/MRA requests found in the data.")

    # --- 5. Previous Years Relays by Dept/Category Numbers & New Relays ---
    if 'DeptCat' in df_processed.columns and 'WK_End_Date' in df_processed.columns:
        current_max_year = df_processed['WK_End_Date'].dt.year.max()
        previous_year = current_max_year - 1
        current_year_relays = df_processed[df_processed['WK_End_Date'].dt.year == current_max_year]
        previous_year_relays = df_processed[df_processed['WK_End_Date'].dt.year == previous_year]
        current_year_dept_counts = current_year_relays.groupby('DeptCat')['Relay_ID'].nunique().reset_index()
        previous_year_dept_counts = previous_year_relays.groupby('DeptCat')['Relay_ID'].nunique().reset_index()
        comparison_df = current_year_dept_counts.merge(
            previous_year_dept_counts, on='DeptCat', how='outer', suffixes=('_CurrentYear', '_PreviousYear')
        ).fillna(0)
        comparison_df['Change'] = comparison_df['Relay_ID_CurrentYear'] - comparison_df['Relay_ID_PreviousYear']
        print(f"\n--- Relay Counts by Department: {current_max_year} vs. {previous_year} ---")
        print(comparison_df.sort_values('Relay_ID_CurrentYear', ascending=False).to_string())
        
        current_year_unique_relays = current_year_relays['Relay_ID'].unique()
        previous_year_unique_relays = previous_year_relays['Relay_ID'].unique()
        new_relays_this_year = current_year_relays[
            ~current_year_relays['Relay_ID'].isin(previous_year_unique_relays)
        ][['Relay_ID', 'DeptCat', 'WK_End_Date']].drop_duplicates()
        
        if not new_relays_this_year.empty:
            print(f"\n--- New Relays: Present in {current_max_year} but NOT in {previous_year} ---")
            print(new_relays_this_year.to_string())
        else:
            print(f"\nNo new unique relays identified in {current_max_year} not present in {previous_year}.")

    print("\n--- Reporting & Analysis Complete ---")

    # --- CALL VISUALIZATION FUNCTIONS ---
    plot_relay_activity_heatmap(df_processed)
    plot_relay_moves_by_dept(df_moved_relays)
    plot_relay_status_pie(df_processed)
    
    # Final confirmation
    print(f"\n📊 All reports saved to: {OUTPUT_DIR}")
    print(f"📂 To view reports, run: explorer \"{OUTPUT_DIR}\"")