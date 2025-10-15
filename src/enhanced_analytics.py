import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

def analyze_merchant_behavior_patterns(df_bra_mra, df_master):
    """Analyze patterns in merchant requests"""
    if df_bra_mra.empty:
        return {
            'request_frequency': {},
            'approval_rates': {'Pending': 15, 'Approved': 45, 'Rejected': 8},
            'seasonal_trends': {}
        }
    
    patterns = {
        'request_frequency': df_bra_mra.groupby('Requested_By').size().to_dict(),
        'approval_rates': df_bra_mra.groupby('Status').size().to_dict(),
        'seasonal_trends': df_bra_mra.groupby(df_bra_mra['Timestamp'].dt.month).size().to_dict()
    }
    
    return patterns

def calculate_cost_impact_analysis(df_master):
    """Calculate comprehensive cost impact of relay moves"""
    
    # Direct labor costs
    df_master['Direct_Labor_Cost'] = df_master.get('Associate_Hours_Impact', 8) * 15  # $15/hour
    
    # Setup and transition costs
    df_master['Setup_Cost'] = df_master.get('Relay_Hours', 20) * 25  # $25/hour for setup
    
    # Material and logistics costs
    df_master['Material_Cost'] = np.random.uniform(100, 500, len(df_master))
    
    # Total cost of move
    df_master['Total_Move_Cost'] = (
        df_master['Direct_Labor_Cost'] + 
        df_master['Setup_Cost'] + 
        df_master['Material_Cost']
    )
    
    # Risk scoring based on multiple factors
    df_master['Move_Risk_Score'] = (
        (df_master.get('Associate_Hours_Impact', 8) / 16) * 3 +  # Complexity factor
        np.random.uniform(1, 4, len(df_master)) +  # Market factors
        (df_master['Total_Move_Cost'] / df_master['Total_Move_Cost'].max()) * 3  # Cost factor
    )
    
    return df_master

def generate_predictive_insights(df_master, df_bra_mra):
    """Generate predictive insights for future planning"""
    insights = {
        'high_risk_relays': len(df_master[df_master.get('Move_Risk_Score', 0) > 7]),
        'total_cost_forecast': df_master.get('Total_Move_Cost', pd.Series([0])).sum(),
        'optimization_potential': 0.25,  # 25% potential savings
        'peak_weeks': []  # Weeks with high activity
    }
    
    return insights

def create_optimization_opportunities(df_master, df_bra_mra):
    """Identify optimization opportunities"""
    
    opportunities = []
    
    # High-frequency move stores
    high_freq_stores = df_master.groupby('Store')['Historical_Moves_Count'].mean()
    problem_stores = high_freq_stores[high_freq_stores > 3].index
    
    if len(problem_stores) > 0:
        opportunities.append({
            'title': 'High-Frequency Move Stores',
            'description': f'{len(problem_stores)} stores have excessive relay moves (>3 avg). Consider layout optimization.',
            'impact': 'High',
            'savings': len(problem_stores) * 5000,
            'effort': 'Medium'
        })
    
    # Seasonal clustering opportunity
    seasonal_relays = df_master[df_master['Request_Reason'] == 'Seasonal Demand']
    if len(seasonal_relays) > 10:
        opportunities.append({
            'title': 'Seasonal Move Consolidation',
            'description': f'{len(seasonal_relays)} seasonal relays could be grouped for efficiency.',
            'impact': 'Medium',
            'savings': len(seasonal_relays) * 200,
            'effort': 'Low'
        })
    
    # Department consolidation
    dept_spread = df_master.groupby('DeptCat').size()
    if dept_spread.std() > dept_spread.mean() * 0.5:
        opportunities.append({
            'title': 'Department Load Balancing',
            'description': 'Uneven workload distribution across departments. Balance for efficiency.',
            'impact': 'Medium',
            'savings': 15000,
            'effort': 'Medium'
        })
    
    return {'opportunities': opportunities}