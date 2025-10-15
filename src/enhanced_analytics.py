# Enhanced analytics for modular relay balancing

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def calculate_move_costs(df_master):
    """Calculate comprehensive cost impact of relay moves"""
    print("📊 Calculating comprehensive move costs...")
    
    # Direct labor costs (associate hours * hourly rate)
    df_master['Direct_Labor_Cost'] = df_master['Associate_Hours_Impact'] * 15  # $15/hour
    
    # Productivity loss during transition (15% loss during relay execution)
    df_master['Productivity_Loss_Cost'] = df_master['Relay_Hours'] * 0.15 * 25  # 15% loss at $25/hour
    
    # Customer experience impact (estimated sales loss during reset)
    df_master['Customer_Impact_Cost'] = df_master['Relay_Change_Perc'] * df_master['Sales_Impact_Score'] * 10
    
    # Complexity multiplier (more complex relays cost more)
    complexity_multiplier = df_master['Complexity_Score'] / 3  # Scale 1-5 to multiplier
    
    # Total cost of move
    df_master['Total_Move_Cost'] = (
        df_master['Direct_Labor_Cost'] + 
        df_master['Productivity_Loss_Cost'] + 
        df_master['Customer_Impact_Cost']
    ) * complexity_multiplier
    
    # ROI calculation
    potential_sales_gain = df_master['Expected_Sales_Impact'] * df_master['Relay_Change_Perc']
    df_master['Move_ROI'] = (potential_sales_gain - df_master['Total_Move_Cost']) / df_master['Total_Move_Cost']
    
    return df_master

def analyze_merchant_behavior_patterns(df_bra_mra, df_master):
    """Analyze patterns in merchant requests to predict future behavior"""
    print("🔍 Analyzing merchant behavior patterns...")
    
    # Merchant request frequency and success rate
    merchant_freq = df_bra_mra.groupby('Requested_By').agg({
        'Request_ID': 'count',
        'Status': lambda x: (x == 'Approved').sum(),
        'Expected_Sales_Impact': 'mean',
        'Cost_Estimate': 'mean',
        'Priority_Level': lambda x: (x == 'High').sum()
    }).reset_index()
    
    merchant_freq['Approval_Rate'] = merchant_freq['Status'] / merchant_freq['Request_ID']
    merchant_freq['High_Priority_Rate'] = merchant_freq['Priority_Level'] / merchant_freq['Request_ID']
    merchant_freq.rename(columns={'Request_ID': 'Total_Requests', 'Status': 'Approved_Requests'}, inplace=True)
    
    # Seasonal patterns in requests
    df_bra_mra['Request_Month'] = df_bra_mra['Timestamp'].dt.month
    df_bra_mra['Request_Quarter'] = df_bra_mra['Timestamp'].dt.quarter
    
    seasonal_pattern = df_bra_mra.groupby(['Request_Month', 'Request_Type']).agg({
        'Request_ID': 'count',
        'Expected_Sales_Impact': 'mean',
        'Priority_Level': lambda x: (x.isin(['High', 'Urgent'])).sum()
    }).reset_index()
    
    # Department-specific request patterns
    if 'DeptCat' in df_master.columns:
        dept_requests = df_master.merge(
            df_bra_mra[['Relay_ID', 'Request_Type', 'Status', 'Expected_Sales_Impact', 'Cost_Estimate']], 
            on='Relay_ID', how='inner'
        )
        
        dept_patterns = dept_requests.groupby('DeptCat').agg({
            'Total_Move_Cost': 'mean',
            'Request_Type': lambda x: x.value_counts().to_dict(),
            'Status': lambda x: (x == 'Approved').mean(),
            'Expected_Sales_Impact': 'mean',
            'Move_ROI': 'mean'
        }).reset_index()
    else:
        dept_patterns = pd.DataFrame()
    
    # Request clustering based on characteristics
    request_features = df_bra_mra[['Expected_Sales_Impact', 'Cost_Estimate']].fillna(0)
    if len(request_features) > 5:
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(request_features)
        
        kmeans = KMeans(n_clusters=min(4, len(request_features)), random_state=42)
        df_bra_mra['Request_Cluster'] = kmeans.fit_predict(scaled_features)
        
        cluster_analysis = df_bra_mra.groupby('Request_Cluster').agg({
            'Expected_Sales_Impact': 'mean',
            'Cost_Estimate': 'mean',
            'Status': lambda x: (x == 'Approved').mean(),
            'Priority_Level': lambda x: x.mode().iloc[0] if len(x) > 0 else 'Medium'
        }).reset_index()
    else:
        cluster_analysis = pd.DataFrame()
    
    # Time-based patterns (day of week, time trends)
    df_bra_mra['Request_DayOfWeek'] = df_bra_mra['Timestamp'].dt.dayofweek
    df_bra_mra['Days_Since_Request'] = (datetime.now() - df_bra_mra['Timestamp']).dt.days
    
    temporal_patterns = df_bra_mra.groupby('Request_DayOfWeek').agg({
        'Request_ID': 'count',
        'Status': lambda x: (x == 'Approved').mean(),
        'Days_Since_Request': 'mean'
    }).reset_index()
    
    return {
        'merchant_frequency': merchant_freq,
        'seasonal_patterns': seasonal_pattern,
        'department_patterns': dept_patterns,
        'cluster_analysis': cluster_analysis,
        'temporal_patterns': temporal_patterns
    }

def create_predictive_model_inputs(df_master):
    """Create features for predicting relay move requests"""
    print("🤖 Creating predictive model features...")
    
    # Historical move patterns
    df_master['Move_Frequency_Score'] = df_master['Historical_Moves_Count'] / df_master['Days_Since_Last_Move'].clip(1)
    
    # Seasonality score based on month
    current_month = datetime.now().month
    seasonality_map = {
        1: 4, 2: 3, 3: 4, 4: 3, 5: 2, 6: 2,  # Q1-Q2
        7: 3, 8: 4, 9: 3, 10: 4, 11: 5, 12: 5  # Q3-Q4 (holiday heavy)
    }
    df_master['Seasonality_Score'] = df_master['WK_End_Date'].dt.month.map(seasonality_map)
    
    # Store performance indicators
    df_master['Performance_Risk_Score'] = (
        (100 - df_master['Store_Performance_Score']) / 20 +  # Lower performance = higher risk
        df_master['Customer_Traffic_Index'] / 50 +  # Higher traffic = higher risk
        (1 / df_master['Inventory_Turnover_Rate']) * 2  # Lower turnover = higher risk
    )
    
    # Business priority score
    priority_map = {'Low': 1, 'Medium': 2, 'High': 3, 'Critical': 4}
    df_master['Business_Priority_Score'] = df_master['Merchant_Priority'].map(priority_map)
    
    # Complexity and effort score
    df_master['Effort_Score'] = (
        df_master['Complexity_Score'] * 0.4 +
        df_master['Associate_Hours_Impact'] / 5 * 0.3 +
        df_master['Relay_Change_Perc'] * 5 * 0.3
    )
    
    # Overall risk score (likelihood of future move requests)
    df_master['Move_Risk_Score'] = (
        df_master['Move_Frequency_Score'] * 0.25 +
        df_master['Seasonality_Score'] * 0.20 +
        df_master['Performance_Risk_Score'] * 0.25 +
        df_master['Business_Priority_Score'] * 0.15 +
        df_master['Effort_Score'] * 0.15
    ).clip(0, 10)  # Scale 0-10
    
    # Categorize risk levels
    df_master['Risk_Category'] = pd.cut(
        df_master['Move_Risk_Score'], 
        bins=[0, 3, 6, 8, 10], 
        labels=['Low', 'Medium', 'High', 'Critical']
    )
    
    return df_master

def analyze_cost_benefit_optimization(df_master, df_suggested):
    """Analyze cost-benefit of optimization decisions"""
    print("💰 Analyzing cost-benefit of optimization...")
    
    # Calculate baseline costs (current state)
    baseline_total_cost = df_master['Total_Move_Cost'].sum()
    baseline_productivity_loss = df_master['Productivity_Loss_Cost'].sum()
    baseline_customer_impact = df_master['Customer_Impact_Cost'].sum()
    
    # Calculate optimized costs (suggested state)
    if 'Total_Move_Cost' in df_suggested.columns:
        optimized_total_cost = df_suggested['Total_Move_Cost'].sum()
        optimized_productivity_loss = df_suggested['Productivity_Loss_Cost'].sum()
        optimized_customer_impact = df_suggested['Customer_Impact_Cost'].sum()
    else:
        # Estimate 30% cost reduction through optimization
        optimized_total_cost = baseline_total_cost * 0.7
        optimized_productivity_loss = baseline_productivity_loss * 0.7
        optimized_customer_impact = baseline_customer_impact * 0.7
    
    # Calculate savings
    total_savings = baseline_total_cost - optimized_total_cost
    productivity_savings = baseline_productivity_loss - optimized_productivity_loss
    customer_experience_savings = baseline_customer_impact - optimized_customer_impact
    
    # ROI calculation
    optimization_investment = 50000  # Estimated cost of optimization system
    annual_roi = (total_savings * 52 - optimization_investment) / optimization_investment * 100
    
    # Payback period (weeks)
    payback_weeks = optimization_investment / total_savings if total_savings > 0 else float('inf')
    
    cost_benefit_summary = {
        'baseline_total_cost': baseline_total_cost,
        'optimized_total_cost': optimized_total_cost,
        'total_savings_weekly': total_savings,
        'total_savings_annual': total_savings * 52,
        'productivity_savings_weekly': productivity_savings,
        'customer_experience_savings_weekly': customer_experience_savings,
        'roi_percentage': annual_roi,
        'payback_period_weeks': payback_weeks,
        'cost_reduction_percentage': (total_savings / baseline_total_cost * 100) if baseline_total_cost > 0 else 0
    }
    
    return cost_benefit_summary

def generate_executive_summary(df_master, merchant_patterns, cost_benefit):
    """Generate executive summary metrics"""
    print("📋 Generating executive summary...")
    
    # Key metrics
    total_relays = len(df_master)
    high_risk_relays = len(df_master[df_master['Risk_Category'] == 'High'])
    avg_move_cost = df_master['Total_Move_Cost'].mean()
    
    # Merchant request insights
    if 'merchant_frequency' in merchant_patterns:
        top_requesters = merchant_patterns['merchant_frequency'].nlargest(3, 'Total_Requests')
        avg_approval_rate = merchant_patterns['merchant_frequency']['Approval_Rate'].mean()
    else:
        top_requesters = pd.DataFrame()
        avg_approval_rate = 0.75  # Default assumption
    
    # Seasonal insights
    if 'seasonal_patterns' in merchant_patterns and not merchant_patterns['seasonal_patterns'].empty:
        peak_month = merchant_patterns['seasonal_patterns'].groupby('Request_Month')['Request_ID'].sum().idxmax()
    else:
        peak_month = 11  # November (holiday season)
    
    # Cost savings potential
    weekly_savings = cost_benefit.get('total_savings_weekly', 0)
    annual_savings = cost_benefit.get('total_savings_annual', 0)
    
    executive_summary = {
        'total_relays_analyzed': total_relays,
        'high_risk_relays': high_risk_relays,
        'high_risk_percentage': (high_risk_relays / total_relays * 100) if total_relays > 0 else 0,
        'average_move_cost': avg_move_cost,
        'peak_request_month': peak_month,
        'average_approval_rate': avg_approval_rate * 100,
        'weekly_cost_savings': weekly_savings,
        'annual_cost_savings': annual_savings,
        'roi_percentage': cost_benefit.get('roi_percentage', 0),
        'payback_weeks': cost_benefit.get('payback_period_weeks', 0),
        'cost_reduction_percentage': cost_benefit.get('cost_reduction_percentage', 0)
    }
    
    return executive_summary

def identify_optimization_opportunities(df_master, merchant_patterns):
    """Identify specific optimization opportunities"""
    print("🎯 Identifying optimization opportunities...")
    
    opportunities = []
    
    # High-cost, low-ROI relays
    high_cost_low_roi = df_master[
        (df_master['Total_Move_Cost'] > df_master['Total_Move_Cost'].quantile(0.75)) &
        (df_master['Move_ROI'] < df_master['Move_ROI'].quantile(0.25))
    ]
    
    if not high_cost_low_roi.empty:
        opportunities.append({
            'type': 'High Cost, Low ROI Relays',
            'count': len(high_cost_low_roi),
            'potential_savings': high_cost_low_roi['Total_Move_Cost'].sum() * 0.3,
            'description': 'Relays with high execution cost but low business value'
        })
    
    # Frequent movers
    frequent_movers = df_master[df_master['Historical_Moves_Count'] > df_master['Historical_Moves_Count'].quantile(0.9)]
    
    if not frequent_movers.empty:
        opportunities.append({
            'type': 'Frequent Movers',
            'count': len(frequent_movers),
            'potential_savings': frequent_movers['Total_Move_Cost'].sum() * 0.5,
            'description': 'Relays moved frequently - consider schedule optimization'
        })
    
    # Low approval rate merchants
    if 'merchant_frequency' in merchant_patterns and not merchant_patterns['merchant_frequency'].empty:
        low_approval_merchants = merchant_patterns['merchant_frequency'][
            merchant_patterns['merchant_frequency']['Approval_Rate'] < 0.5
        ]
        
        if not low_approval_merchants.empty:
            opportunities.append({
                'type': 'Low Approval Rate Merchants',
                'count': len(low_approval_merchants),
                'potential_savings': 25000,  # Estimated savings from better request guidance
                'description': 'Merchants with low approval rates need better guidance'
            })
    
    # Seasonal misalignment
    off_season_requests = df_master[
        (df_master['Seasonality_Score'] <= 2) & 
        (df_master['Merchant_Priority'].isin(['High', 'Critical']))
    ]
    
    if not off_season_requests.empty:
        opportunities.append({
            'type': 'Seasonal Misalignment',
            'count': len(off_season_requests),
            'potential_savings': off_season_requests['Total_Move_Cost'].sum() * 0.2,
            'description': 'High-priority requests during low-season periods'
        })
    
    return opportunities