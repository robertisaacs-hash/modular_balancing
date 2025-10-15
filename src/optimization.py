# modular_balancing/src/optimization.py

from datetime import datetime, timedelta
from pulp import LpProblem, LpMinimize, LpVariable, LpBinary, lpSum, PULP_CBC_CMD, LpStatus
import pandas as pd

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

    # Normalize important date columns
    df_optim_scope['Original_WK_End_Date'] = pd.to_datetime(df_optim_scope['Original_WK_End_Date'], errors='coerce')
    df_optim_scope['WK_End_Date'] = pd.to_datetime(df_optim_scope['WK_End_Date'], errors='coerce')

    # Get a list of all potential target weeks (original weeks + future buffer)
    current_date_dt = datetime.now()
    all_possible_weeks_dt = pd.to_datetime(pd.date_range(
        start=df_optim_scope['Original_WK_End_Date'].min(),
        end=current_date_dt + timedelta(weeks=FUTURE_DATE_BUFFER_WEEKS),
        freq='W'
    ))

    # Use only weeks from the current period or in the future for moving.
    valid_target_weeks_dt = all_possible_weeks_dt[all_possible_weeks_dt >= pd.to_datetime(ONE_YEAR_AGO)]
    if valid_target_weeks_dt.empty:
        print("No valid target weeks for optimization found.")
        return pd.DataFrame()

    # --- build a truly unique instance key and ensure uniqueness ---
    df_optim_scope['Relay_Store_Instance_ID'] = (
        df_optim_scope['Relay_ID'].astype(str).str.strip() + '_' +
        df_optim_scope['Store_ID'].astype(str).str.strip() + '_' +
        df_optim_scope['Original_WK_End_Date'].dt.strftime('%Y-%m-%d').fillna('NA')
    )

    # Prefer rows with explicit moves / higher impact, then drop exact dup keys
    sort_cols = [c for c in ['Requested_Move_WK', 'WK_End_Date', 'Relay_Change_Perc', 'Total_Store_Hours']
                 if c in df_optim_scope.columns]
    if sort_cols:
        df_optim_scope = df_optim_scope.sort_values(sort_cols, ascending=False)

    # Drop exact duplicates of the ID, keep the “best” row
    df_optim_scope = df_optim_scope.drop_duplicates(
        subset='Relay_Store_Instance_ID', keep='first'
    )

    # If duplicates still exist, suffix a counter deterministically
    if not df_optim_scope['Relay_Store_Instance_ID'].is_unique:
        order = df_optim_scope.groupby('Relay_Store_Instance_ID').cumcount()
        dup_mask2 = order > 0
        df_optim_scope.loc[dup_mask2, 'Relay_Store_Instance_ID'] = (
            df_optim_scope.loc[dup_mask2, 'Relay_Store_Instance_ID'] + '_' + order[dup_mask2].astype(str)
        )

    if not df_optim_scope['Relay_Store_Instance_ID'].is_unique:
        counts = df_optim_scope['Relay_Store_Instance_ID'].value_counts()
        raise ValueError(
            "Non-unique Relay_Store_Instance_ID after normalization. Examples:\n"
            + counts[counts > 1].head(10).to_string()
        )

    # Define sets and lookup dict from the deduped view
    RELAY_INSTANCES = df_optim_scope['Relay_Store_Instance_ID'].unique().tolist()
    WEEKS = sorted(list(set(valid_target_weeks_dt.tolist())))  # datetime objects
    WEEKS_STR = [w.strftime('%Y-%m-%d') for w in WEEKS]        # string keys for PuLP

    # properties dict built from unique view
    relay_instance_properties = df_optim_scope.set_index('Relay_Store_Instance_ID').to_dict('index')

    # Get all unique Relay_IDs from these instances for adjacency handling
    all_relay_ids_in_scope = df_optim_scope['Relay_ID'].unique().tolist()

    # --- Define the Optimization Problem ---
    prob = LpProblem("Modular_Balancing_Problem", LpMinimize)

    # --- Decision Variables ---
    x = LpVariable.dicts("x", (RELAY_INSTANCES, WEEKS_STR), lowBound=0, upBound=1, cat=LpBinary)

    # Auxiliary variables for penalizing threshold breaches
    y_total_over = LpVariable.dicts("y_total_over", WEEKS_STR, lowBound=0, cat='Continuous')
    y_nm_total_over = LpVariable.dicts("y_nm_total_over", WEEKS_STR, lowBound=0, cat='Continuous')

    # --- Objective Function ---
    move_cost_terms = []
    for s in RELAY_INSTANCES:
        orig_raw = relay_instance_properties[s].get('Original_WK_End_Date')
        orig_dt = pd.to_datetime(orig_raw, errors='coerce') if orig_raw is not None else pd.NaT
        orig_str = orig_dt.strftime('%Y-%m-%d') if not pd.isna(orig_dt) else None
        for w_str in WEEKS_STR:
            if orig_str is None or w_str != orig_str:
                move_cost_terms.append(COST_PER_RELAY_MOVE * x[s][w_str])

    prob += lpSum(move_cost_terms) + lpSum(PENALTY_OVER_TOTAL_HOURS * y_total_over[w] for w in WEEKS_STR) + \
            lpSum(PENALTY_OVER_NM_HOURS_PROXY * y_nm_total_over[w] for w in WEEKS_STR)

    # --- Constraints ---

    # 1. Each relay-store instance must be assigned to exactly one week
    for s in RELAY_INSTANCES:
        prob += lpSum(x[s][w_str] for w_str in WEEKS_STR) == 1, f"Instance_{s}_Assigned_Once"

    # 2. Hard Constraint: Seasonal/DC Realignments do not move
    for s in RELAY_INSTANCES:
        cannot_move = relay_instance_properties[s].get('Cannot_Move', False)
        if cannot_move:
            orig_raw = relay_instance_properties[s].get('Original_WK_End_Date')
            orig_dt = pd.to_datetime(orig_raw, errors='coerce') if orig_raw is not None else pd.NaT
            if pd.isna(orig_dt):
                # If original week is missing, force the instance to stay in its current WK_End_Date if available
                current_week_raw = relay_instance_properties[s].get('WK_End_Date')
                current_week_dt = pd.to_datetime(current_week_raw, errors='coerce') if current_week_raw is not None else pd.NaT
                if pd.isna(current_week_dt):
                    # As a last resort, keep the assignment variable sum==1 (already enforced) and skip forcing a week
                    continue
                orig_str = current_week_dt.strftime('%Y-%m-%d')
            else:
                orig_str = orig_dt.strftime('%Y-%m-%d')

            if orig_str in WEEKS_STR:
                prob += x[s][orig_str] == 1, f"CannotMove_{s}_Force_OrigWeek"
            else:
                # If original week not in our target weeks, add constraint to prefer original by preventing other assignments
                prob += lpSum(x[s][w_str] for w_str in WEEKS_STR) == 1, f"CannotMove_{s}_Fallback"

    # 3. Adjacency Constraint: Relays in the same group must move together (Relay_ID level)
    if 'Adjustment_Group_ID' in df_optim_scope.columns and 'Relay_ID' in df_optim_scope.columns:
        adjusted_groups = df_optim_scope[df_optim_scope['Adjustment_Group_ID'] != 'NO_GROUP']['Adjustment_Group_ID'].unique()
        for group_id in adjusted_groups:
            group_relays = df_optim_scope[df_optim_scope['Adjustment_Group_ID'] == group_id]['Relay_ID'].unique().tolist()
            if len(group_relays) <= 1:
                continue
            # Build instance lists per relay_id
            instances_by_relay = {
                rid: df_optim_scope[df_optim_scope['Relay_ID'] == rid]['Relay_Store_Instance_ID'].unique().tolist()
                for rid in group_relays
            }
            reference = group_relays[0]
            ref_instances = instances_by_relay[reference]
            for other in group_relays[1:]:
                other_instances = instances_by_relay[other]
                for w_str in WEEKS_STR:
                    prob += lpSum(x[i][w_str] for i in ref_instances) == lpSum(x[j][w_str] for j in other_instances), \
                            f"Adjacency_Group_{group_id}_{reference}_{other}_{w_str}"

    # 4. Total Weekly Hours Threshold
    for w_dt in WEEKS:
        w_str = w_dt.strftime('%Y-%m-%d')
        current_week_total_hours = lpSum(
            float(relay_instance_properties[s].get('Relay_Hours', 0)) * x[s][w_str]
            for s in RELAY_INSTANCES
        )

        # Determine the threshold for this week (holiday or regular)
        is_holiday_week_bool = False
        rows = df_processed[df_processed['WK_End_Date'] == w_dt]
        if not rows.empty and 'Is_Holiday' in rows.columns:
            is_holiday_week_bool = bool(rows['Is_Holiday'].iloc[0])
        threshold = HOLIDAY_TOTAL_WEEKLY_HOURS_THRESHOLD if is_holiday_week_bool else TOTAL_WEEKLY_HOURS_THRESHOLD

        # current_week_total_hours <= threshold + y_total_over
        prob += current_week_total_hours <= threshold + y_total_over[w_str], f"TotalHours_Upper_{w_str}"
        # y_total_over represents the overage amount
        prob += y_total_over[w_str] >= current_week_total_hours - threshold, f"TotalHours_OverDef_{w_str}"

    # 5. Neighborhood Market Hours Average Threshold (Proxy: Total NM Hours)
    nm_store_types = ['Neighborhood Market']
    nm_relay_instances = df_optim_scope[df_optim_scope['Store_Type'].isin(nm_store_types)]['Relay_Store_Instance_ID'].unique().tolist()

    for w_dt in WEEKS:
        w_str = w_dt.strftime('%Y-%m-%d')
        current_week_nm_total_hours = lpSum(
            float(relay_instance_properties[s].get('Relay_Hours', 0)) * x[s][w_str]
            for s in nm_relay_instances
        )

        is_holiday_week_bool = False
        rows = df_processed[df_processed['WK_End_Date'] == w_dt]
        if not rows.empty and 'Is_Holiday' in rows.columns:
            is_holiday_week_bool = bool(rows['Is_Holiday'].iloc[0])

        nm_threshold_proxy = (HOLIDAY_NM_AVG_HOURS_THRESHOLD if is_holiday_week_bool else NM_AVG_HOURS_THRESHOLD) * MAX_PROBABLE_NM_STORES_PER_WEEK

        prob += current_week_nm_total_hours <= nm_threshold_proxy + y_nm_total_over[w_str], f"NMHours_Upper_{w_str}"
        prob += y_nm_total_over[w_str] >= current_week_nm_total_hours - nm_threshold_proxy, f"NMHours_OverDef_{w_str}"

    # --- Solve the Problem ---
    print("\n--- Solving the Optimization Problem (this may take a moment)... ---")
    prob.solve(PULP_CBC_CMD(msg=0))

    print(f"Status: {LpStatus[prob.status]}")

    # --- Extract Results ---
    if LpStatus[prob.status] == 'Optimal':
        suggested_schedule_data = []
        for s in RELAY_INSTANCES:
            for w_str in WEEKS_STR:
                val = x[s][w_str].value()
                if val is None:
                    continue
                if round(val) == 1:
                    props = relay_instance_properties.get(s, {})
                    orig_raw = props.get('Original_WK_End_Date')
                    orig_dt = pd.to_datetime(orig_raw, errors='coerce') if orig_raw is not None else pd.NaT
                    suggested_schedule_data.append({
                        'Relay_Store_Instance_ID': s,
                        'Relay_ID': props.get('Relay_ID'),
                        'Store_ID': props.get('Store_ID'),
                        'Original_WK_End_Date': orig_dt,
                        'Suggested_WK_End_Date': pd.to_datetime(w_str),
                        'Relay_Hours': props.get('Relay_Hours'),
                        'Store_Type': props.get('Store_Type'),
                        'Cannot_Move': props.get('Cannot_Move', False)
                    })

        df_suggested_schedule = pd.DataFrame(suggested_schedule_data)

        # If you really want to drop the ID, do so; otherwise keep for traceability
        if 'Relay_Store_Instance_ID' in df_suggested_schedule.columns:
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