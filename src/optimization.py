# modular_balancing/src/optimization.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pulp import LpProblem, LpMinimize, LpVariable, LpBinary, lpSum, PULP_CBC_CMD, LpStatus


from src.utils import save_to_gcs_pickle
from src.config import (
    GCS_MODELS_PATH, ONE_YEAR_AGO, FUTURE_DATE_BUFFER_WEEKS,
    TOTAL_WEEKLY_HOURS_THRESHOLD, NM_AVG_HOURS_THRESHOLD,
    HOLIDAY_TOTAL_WEEKLY_HOURS_THRESHOLD, HOLIDAY_NM_AVG_HOURS_THRESHOLD,
    PENALTY_OVER_TOTAL_HOURS, PENALTY_OVER_NM_HOURS_PROXY, COST_PER_RELAY_MOVE,
    MAX_PROBABLE_NM_STORES_PER_WEEK
)

def solve_optimization_problem(df_processed: pd.DataFrame):
    """
    Defines and solves the modular relay balancing optimization problem using PuLP.
    """
    print("--- Starting Optimization Model ---")

    # Filter for relays that could potentially be moved (current date onward)
    df_optim_scope = df_processed[df_processed['Original_WK_End_Date'] >= pd.to_datetime(ONE_YEAR_AGO)].copy()
    if df_optim_scope.empty:
        print("No relays in optimization scope to process.")
        return pd.DataFrame()

    # Get a list of all potential target weeks (original weeks + future buffer)
    current_date_dt = datetime.now()
    all_possible_weeks_dt = pd.to_datetime(pd.date_range(
        start=df_optim_scope['Original_WK_End_Date'].min(),
        end=current_date_dt + timedelta(weeks=FUTURE_DATE_BUFFER_WEEKS),
        freq='W'
    ))
    
    # Use only weeks from the current period or in the future for moving.
    # We allow moving into weeks for which there is current data implicitly.
    valid_target_weeks_dt = all_possible_weeks_dt[all_possible_weeks_dt >= pd.to_datetime(ONE_YEAR_AGO)]
    if valid_target_weeks_dt.empty:
        print("No valid target weeks for optimization found.")
        return pd.DataFrame()
    dupe_mask = df_optim_scope.duplicated(['Relay_ID','Store_ID','Original_WK_End_Date'], keep=False)
    print("Pre-fix duplicate rows:", dupe_mask.sum())

        # --- build a truly unique instance key and ensure uniqueness ---

    # For visibility before fixing
    dupe_mask = df_optim_scope.duplicated(
        ['Relay_ID', 'Store_ID', 'Original_WK_End_Date'], keep=False
    )
    print("Pre-fix duplicate rows:", int(dupe_mask.sum()))

    # 1) Normalize Original_WK_End_Date to datetime
    if not pd.api.types.is_datetime64_any_dtype(df_optim_scope['Original_WK_End_Date']):
        df_optim_scope['Original_WK_End_Date'] = pd.to_datetime(
            df_optim_scope['Original_WK_End_Date'], errors='coerce'
        )

    # 2) Build the composite key: Relay + Store + Original Week
    df_optim_scope['Relay_Store_Instance_ID'] = (
        df_optim_scope['Relay_ID'].astype(str).str.strip() + '_' +
        df_optim_scope['Store_ID'].astype(str).str.strip() + '_' +
        df_optim_scope['Original_WK_End_Date'].dt.strftime('%Y-%m-%d').fillna('NA')
    )

    # 3) Prefer rows with explicit moves / higher impact, then drop exact dup keys
    sort_cols = [c for c in ['Requested_Move_WK', 'WK_End_Date', 'Relay_Change_Perc', 'Total_Store_Hours']
                 if c in df_optim_scope.columns]
    if sort_cols:
        df_optim_scope = df_optim_scope.sort_values(sort_cols, ascending=False)

    # Drop exact duplicates of the ID, keep the “best” row
    df_optim_scope = df_optim_scope.drop_duplicates(
        subset='Relay_Store_Instance_ID', keep='first'
    )

    # 4) If any keys are STILL duplicated (e.g., because they were '..._NA'),
    # suffix a counter deterministically to make them unique without dropping data.
    if not df_optim_scope['Relay_Store_Instance_ID'].is_unique:
        order = df_optim_scope.groupby('Relay_Store_Instance_ID').cumcount()
        dup_mask2 = order > 0
        df_optim_scope.loc[dup_mask2, 'Relay_Store_Instance_ID'] = (
            df_optim_scope.loc[dup_mask2, 'Relay_Store_Instance_ID'] + '_' + order[dup_mask2].astype(str)
        )

    # Final guardrail (fails fast with a preview if somehow still duplicated)
    if not df_optim_scope['Relay_Store_Instance_ID'].is_unique:
        counts = df_optim_scope['Relay_Store_Instance_ID'].value_counts()
        raise ValueError(
            "Non-unique Relay_Store_Instance_ID after normalization. Examples:\n"
            + counts[counts > 1].head(10).to_string()
        )

    # 5) Define sets and lookup dict **from the deduped view**
    RELAY_INSTANCES = df_optim_scope['Relay_Store_Instance_ID'].tolist()
    WEEKS = sorted(list(set(valid_target_weeks_dt.tolist())))
    WEEKS_STR = [w.strftime('%Y-%m-%d') for w in WEEKS]

    # IMPORTANT: build the properties dict from the unique view
    relay_instance_properties = (
        df_optim_scope
        .set_index('Relay_Store_Instance_ID')   # now guaranteed unique
        .to_dict('index')
    )



    RELAY_INSTANCES = df_optim_scope['Relay_Store_Instance_ID'].unique().tolist()
    WEEKS = sorted(list(set(valid_target_weeks_dt.tolist()))) # Sorted list of unique datetime objects
    WEEKS_STR = [w.strftime('%Y-%m-%d') for w in WEEKS] # String representation for PuLP keys

    # Create a dictionary for quick lookup of relay instance properties
    dedup = df_optim_scope.drop_duplicates('Relay_Store_Instance_ID', keep='first')
    relay_instance_properties = dedup.set_index('Relay_Store_Instance_ID').to_dict('index')

    # Get all unique Relay_IDs from these instances for adjacency handling
    all_relay_ids_in_scope = df_optim_scope['Relay_ID'].unique().tolist()

    # --- Define the Optimization Problem ---
    prob = LpProblem("Modular_Balancing_Problem", LpMinimize)

    # --- Decision Variables ---
    # x[s][w] = 1 if Relay_Store_Instance s is assigned to Week w, 0 otherwise
    x = LpVariable.dicts("x", (RELAY_INSTANCES, WEEKS_STR), 0, 1, LpBinary)

    # Auxiliary variables for penalizing threshold breaches
    y_total_over = LpVariable.dicts("y_total_over", WEEKS_STR, 0)
    y_nm_total_over = LpVariable.dicts("y_nm_total_over", WEEKS_STR, 0)

    # --- Objective Function ---
    # Minimize (cost of moving relays) + (penalties for exceeding total hours) + (penalties for exceeding NM total hours proxy)
    prob += lpSum(
        COST_PER_RELAY_MOVE * x[s][w_str] # Cost if moved from original week
        for s in RELAY_INSTANCES
        for w_str in WEEKS_STR
        if pd.to_datetime(w_str) != relay_instance_properties[s]['Original_WK_End_Date']
    ) + \
    lpSum(PENALTY_OVER_TOTAL_HOURS * y_total_over[w] for w in WEEKS_STR) + \
    lpSum(PENALTY_OVER_NM_HOURS_PROXY * y_nm_total_over[w] for w in WEEKS_STR)


    # --- Constraints ---

    # 1. Each relay-store instance must be assigned to exactly one week
    for s in RELAY_INSTANCES:
        prob += lpSum(x[s][w_str] for w_str in WEEKS_STR) == 1, f"Instance_{s}_Assigned_Once"

    # 2. Hard Constraint: Seasonal/DC Realignments do not move
    for s in RELAY_INSTANCES:
        if relay_instance_properties[s]['Cannot_Move']:
            original_week = relay_instance_properties[s]['Original_WK_End_Date']
            for w_str in WEEKS_STR:
                if pd.to_datetime(w_str) != original_week:
                    prob += x[s][w_str] == 0, f"Instance_{s}_CannotMove_From_{w_str}"
            prob += x[s][original_week.strftime('%Y-%m-%d')] == 1, f"Instance_{s}_MustStayInOriginalWeek"

    # 3. Adjacency Constraint: Relays in the same group must move together (all instances of those relays)
    # This applies to the Relay_ID level, not individual Relay_Store_Instance_IDs.
    adjusted_groups = df_optim_scope[df_optim_scope['Adjustment_Group_ID'] != 'NO_GROUP']['Adjustment_Group_ID'].unique()
    for group_id in adjusted_groups:
        group_relay_ids = df_optim_scope[df_optim_scope['Adjustment_Group_ID'] == group_id]['Relay_ID'].unique().tolist()
        
        if len(group_relay_ids) > 1:
            first_relay_id = group_relay_ids[0]
            # Compare ALL instances of first_relay_id to ALL instances of other relays in the group
            first_relay_instances = df_optim_scope[df_optim_scope['Relay_ID'] == first_relay_id]['Relay_Store_Instance_ID'].tolist()
            
            for other_relay_id in group_relay_ids[1:]:
                other_relay_instances = df_optim_scope[df_optim_scope['Relay_ID'] == other_relay_id]['Relay_Store_Instance_ID'].tolist()
                
                # The constraint is that the *Relay_ID* moves together, implying all its instances move to the same week.
                # So if Relay_A moves to Week X, all its store instances go to Week X.
                # If Relay_B in the same group, it must also move to Week X for all its instances.
                
                # Simplification: we assert that all instances of a given Relay_ID must land in the same week.
                # And THEN all Relay_IDs in a group must land in the same week.
                # This implies a new set of variables: z[r][w_str] = 1 if Relay r is in week w_str
                # For simplicity, we'll enforce that the *first instance* of a relay dictates its week,
                # and then all other instances of relays in the same group follow that week.
                
                # To handle "all instances of a relay must go to the same week" first:
                # Add a constraint that for any given Relay_ID, all its instances (s1, s2, ...)
                # are assigned to the same week. Let's make an explicit variable:
                for w_str in WEEKS_STR:
                    for s1 in first_relay_instances:
                        for s2 in other_relay_instances:
                            prob += x[s1][w_str] == x[s2][w_str], f"Group_{group_id}_Link_{s1}_{s2}_Week_{w_str}"
                    

    # 4. Total Weekly Hours Threshold
    for w_dt in WEEKS: # Iterate over datetime objects
        w_str = w_dt.strftime('%Y-%m-%d')
        current_week_total_hours = lpSum(
            relay_instance_properties[s]['Relay_Hours'] * x[s][w_str]
            for s in RELAY_INSTANCES
        )
        # Determine the threshold for this week (holiday or regular)
        # Assuming df_holidays is loaded and contains Is_Holiday for all weeks in WEEKS
        is_holiday_week_bool = df_processed[df_processed['WK_End_Date'] == w_dt]['Is_Holiday'].iloc[0] if not df_processed[df_processed['WK_End_Date'] == w_dt].empty else False
        threshold = HOLIDAY_TOTAL_WEEKLY_HOURS_THRESHOLD if is_holiday_week_bool else TOTAL_WEEKLY_HOURS_THRESHOLD

        prob += current_week_total_hours <= threshold + y_total_over[w_str], f"Total_Hours_Limit_{w_str}"
        prob += y_total_over[w_str] >= 0 # Ensure y_total_over is non-negative


    # 5. Neighborhood Market Hours Average Threshold (Proxy: Total NM Hours)
    nm_store_types = ['Neighborhood Market'] # Define exact string for NM stores
    nm_relay_instances = df_optim_scope[df_optim_scope['Store_Type'].isin(nm_store_types)]['Relay_Store_Instance_ID'].unique().tolist()

    for w_dt in WEEKS: # Iterate over datetime objects
        w_str = w_dt.strftime('%Y-%m-%d')
        current_week_nm_total_hours = lpSum(
            relay_instance_properties[s]['Relay_Hours'] * x[s][w_str]
            for s in nm_relay_instances
        )
        is_holiday_week_bool = df_processed[df_processed['WK_End_Date'] == w_dt]['Is_Holiday'].iloc[0] if not df_processed[df_processed['WK_End_Date'] == w_dt].empty else False
        nm_threshold_proxy = HOLIDAY_NM_AVG_HOURS_THRESHOLD * MAX_PROBABLE_NM_STORES_PER_WEEK if is_holiday_week_bool else NM_AVG_HOURS_THRESHOLD * MAX_PROBABLE_NM_STORES_PER_WEEK

        prob += current_week_nm_total_hours <= nm_threshold_proxy + y_nm_total_over[w_str], f"NM_Total_Hours_Proxy_Limit_{w_str}"
        prob += y_nm_total_over[w_str] >= 0

    # --- Solve the Problem ---
    print("\n--- Solving the Optimization Problem (this may take a moment)... ---")
    prob.solve(PULP_CBC_CMD(msg=0)) # msg=0 suppresses solver output

    print(f"Status: {LpStatus[prob.status]}")

    # --- Extract Results ---
    if LpStatus[prob.status] == 'Optimal':
        suggested_schedule_data = []
        for s in RELAY_INSTANCES:
            assigned_week = None
            for w_str in WEEKS_STR:
                if x[s][w_str].varValue == 1:
                    assigned_week = pd.to_datetime(w_str)
                    break
            
            # Reconstruct original instance data plus new assigned week
            instance_data = relay_instance_properties[s].copy()
            instance_data['Suggested_WK_End_Date'] = assigned_week
            suggested_schedule_data.append(instance_data)

        df_suggested_schedule = pd.DataFrame(suggested_schedule_data)

        # Drop the temporary 'Relay_Store_Instance_ID' if no longer needed
        df_suggested_schedule.drop(columns=['Relay_Store_Instance_ID'], inplace=True)

        print(f"\nOptimization successful. Objective Value: {prob.objective.value()}")
        print("\n--- Suggested Schedule Sample ---")
        print(df_suggested_schedule.head())

        # Save results
        save_to_gcs_pickle(df_suggested_schedule, f"{GCS_MODELS_PATH}optimized_schedule.pkl")
        print("--- Optimization Complete ---")
        return df_suggested_schedule
    else:
        print("Optimization failed or found no feasible solution.")
        return pd.DataFrame()
