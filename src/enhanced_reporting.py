# Enhanced reporting with interactive visualizations

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime

# Get the project root directory (parent of src)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output_reports')
INTERACTIVE_DIR = os.path.join(OUTPUT_DIR, 'interactive')

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(INTERACTIVE_DIR, exist_ok=True)

def create_merchant_request_dashboard(df_master, df_bra_mra):
    """Create comprehensive dashboard for merchant request analysis"""
    print("📊 Creating merchant request dashboard...")
    
    figs = {}
    
    # 1. Request Reason Analysis (Treemap)
    if 'Request_Reason' in df_master.columns:
        reason_summary = df_master.groupby('Request_Reason').agg({
            'Total_Move_Cost': 'sum',
            'Relay_ID': 'count',
            'Associate_Hours_Impact': 'sum'
        }).reset_index()
        reason_summary.columns = ['Request_Reason', 'Total_Cost', 'Request_Count', 'Total_Hours']
        
        figs['reason_treemap'] = px.treemap(
            reason_summary, 
            path=['Request_Reason'], 
            values='Total_Cost',
            color='Total_Hours',
            color_continuous_scale='Reds',
            title="Cost Impact by Request Reason",
            hover_data=['Request_Count', 'Total_Hours']
        )
        figs['reason_treemap'].update_layout(height=500)
    
    # 2. Historical Move Patterns by Department
    if 'DeptCat' in df_master.columns and 'WK_End_Date' in df_master.columns:
        move_patterns = df_master.groupby([df_master['WK_End_Date'].dt.to_period('M'), 'DeptCat']).agg({
            'Historical_Moves_Count': 'mean',
            'Total_Move_Cost': 'sum'
        }).reset_index()
        move_patterns['Month'] = move_patterns['WK_End_Date'].astype(str)
        
        figs['move_patterns'] = px.line(
            move_patterns, 
            x='Month', 
            y='Historical_Moves_Count',
            color='DeptCat',
            title="Historical Move Frequency by Department",
            hover_data=['Total_Move_Cost']
        )
        figs['move_patterns'].update_layout(height=500, xaxis_tickangle=45)
    
    # 3. Store-Level Impact Heatmap
    if 'Store_ID' in df_master.columns and 'WK_End_Date' in df_master.columns:
        # Sample stores for better visualization
        top_stores = df_master.groupby('Store_ID')['Total_Move_Cost'].sum().nlargest(20).index
        store_sample = df_master[df_master['Store_ID'].isin(top_stores)]
        
        store_impact = store_sample.groupby(['Store_ID', df_master['WK_End_Date'].dt.to_period('M')]).agg({
            'Total_Move_Cost': 'sum',
            'Associate_Hours_Impact': 'sum'
        }).reset_index()
        store_impact['Month'] = store_impact['WK_End_Date'].astype(str)
        
        pivot_data = store_impact.pivot(index='Store_ID', columns='Month', values='Total_Move_Cost').fillna(0)
        
        figs['cost_heatmap'] = px.imshow(
            pivot_data,
            title="Store-Level Cost Impact Over Time",
            color_continuous_scale='RdYlBu_r',
            aspect='auto'
        )
        figs['cost_heatmap'].update_layout(height=600)
    
    # 4. Request Status Breakdown
    if not df_bra_mra.empty and 'Status' in df_bra_mra.columns:
        status_counts = df_bra_mra['Status'].value_counts()
        
        figs['status_pie'] = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="BRA/MRA Request Status Distribution"
        )
    
    # 5. Cost vs ROI Scatter
    if 'Move_ROI' in df_master.columns and 'Total_Move_Cost' in df_master.columns:
        figs['cost_roi_scatter'] = px.scatter(
            df_master,
            x='Total_Move_Cost',
            y='Move_ROI',
            color='DeptCat' if 'DeptCat' in df_master.columns else None,
            size='Associate_Hours_Impact' if 'Associate_Hours_Impact' in df_master.columns else None,
            title="Cost vs ROI Analysis",
            hover_data=['Relay_ID', 'Request_Reason'] if 'Request_Reason' in df_master.columns else ['Relay_ID']
        )
        # Add quadrant lines
        figs['cost_roi_scatter'].add_hline(y=0, line_dash="dash", line_color="gray")
        figs['cost_roi_scatter'].add_vline(x=df_master['Total_Move_Cost'].median(), line_dash="dash", line_color="gray")
    
    return figs

def create_data_quality_dashboard(raw_data):
    """Create data quality and input validation dashboard"""
    print("🔍 Creating data quality dashboard...")
    
    figs = {}
    
    for table_name, df in raw_data.items():
        if df.empty:
            continue
            
        # Data completeness
        completeness = (1 - df.isnull().sum() / len(df)) * 100
        
        figs[f'{table_name}_completeness'] = px.bar(
            x=completeness.index,
            y=completeness.values,
            title=f"Data Completeness - {table_name}",
            labels={'x': 'Columns', 'y': 'Completeness %'},
            color=completeness.values,
            color_continuous_scale='RdYlGn'
        )
        figs[f'{table_name}_completeness'].add_hline(
            y=95, line_dash="dash", line_color="red", 
            annotation_text="95% Threshold"
        )
        figs[f'{table_name}_completeness'].update_layout(height=400)
        
        # Record counts over time (if date column exists)
        date_cols = [col for col in df.columns if 'date' in col.lower() or 'timestamp' in col.lower()]
        if date_cols:
            date_col = date_cols[0]
            if pd.api.types.is_datetime64_any_dtype(df[date_col]) or df[date_col].dtype == 'object':
                try:
                    df_temp = df.copy()
                    df_temp[date_col] = pd.to_datetime(df_temp[date_col])
                    record_counts = df_temp.groupby(df_temp[date_col].dt.to_period('M')).size().reset_index()
                    record_counts[date_col] = record_counts[date_col].astype(str)
                    
                    figs[f'{table_name}_volume'] = px.line(
                        record_counts,
                        x=date_col,
                        y=0,
                        title=f"Record Volume Over Time - {table_name}",
                        labels={'y': 'Record Count'}
                    )
                    figs[f'{table_name}_volume'].update_layout(height=300)
                except:
                    pass  # Skip if date parsing fails
        
        # Data distribution for key numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns[:4]  # Limit to 4 columns
        if len(numeric_cols) > 0:
            fig_dist = make_subplots(
                rows=len(numeric_cols), cols=1,
                subplot_titles=numeric_cols,
                vertical_spacing=0.08
            )
            
            for i, col in enumerate(numeric_cols, 1):
                fig_dist.add_trace(
                    go.Histogram(x=df[col], name=col, showlegend=False),
                    row=i, col=1
                )
            
            fig_dist.update_layout(
                title=f"Data Distributions - {table_name}",
                height=200*len(numeric_cols)
            )
            figs[f'{table_name}_distributions'] = fig_dist
    
    return figs

def create_optimization_impact_dashboard(df_baseline, df_optimized, cost_benefit):
    """Create optimization impact visualization"""
    print("⚡ Creating optimization impact dashboard...")
    
    figs = {}
    
    # 1. Cost Reduction Waterfall Chart
    categories = ['Baseline Cost', 'Direct Labor Savings', 'Productivity Savings', 'Customer Impact Savings', 'Optimized Cost']
    values = [
        cost_benefit.get('baseline_total_cost', 0),
        -cost_benefit.get('productivity_savings_weekly', 0) * 0.4,  # Portion of total savings
        -cost_benefit.get('productivity_savings_weekly', 0) * 0.4,
        -cost_benefit.get('customer_experience_savings_weekly', 0) * 0.2,
        cost_benefit.get('optimized_total_cost', 0)
    ]
    
    figs['cost_waterfall'] = go.Figure(go.Waterfall(
        name="Cost Analysis",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=categories,
        y=values,
        text=[f"${v:,.0f}" for v in values],
        textposition="outside",
        connector={"line":{"color":"rgb(63, 63, 63)"}},
    ))
    figs['cost_waterfall'].update_layout(
        title="Weekly Cost Impact of Optimization",
        showlegend=False,
        height=500
    )
    
    # 2. ROI Timeline
    weeks = list(range(1, 53))  # 52 weeks
    weekly_savings = cost_benefit.get('total_savings_weekly', 0)
    cumulative_savings = [weekly_savings * w for w in weeks]
    investment = 50000  # Optimization system cost
    net_benefit = [savings - investment for savings in cumulative_savings]
    
    figs['roi_timeline'] = go.Figure()
    figs['roi_timeline'].add_trace(go.Scatter(
        x=weeks, y=cumulative_savings,
        mode='lines', name='Cumulative Savings',
        line=dict(color='green', width=3)
    ))
    figs['roi_timeline'].add_trace(go.Scatter(
        x=weeks, y=net_benefit,
        mode='lines', name='Net Benefit',
        line=dict(color='blue', width=3)
    ))
    figs['roi_timeline'].add_hline(
        y=0, line_dash="dash", line_color="red",
        annotation_text="Break-even"
    )
    figs['roi_timeline'].update_layout(
        title="ROI Timeline - First Year",
        xaxis_title="Weeks",
        yaxis_title="Dollars ($)",
        height=400
    )
    
    # 3. Before/After Comparison
    if 'Total_Move_Cost' in df_baseline.columns and 'Total_Move_Cost' in df_optimized.columns:
        comparison_data = pd.DataFrame({
            'Scenario': ['Baseline', 'Optimized'],
            'Total_Cost': [df_baseline['Total_Move_Cost'].sum(), df_optimized['Total_Move_Cost'].sum()],
            'Avg_Cost_Per_Relay': [df_baseline['Total_Move_Cost'].mean(), df_optimized['Total_Move_Cost'].mean()],
            'High_Cost_Relays': [
                len(df_baseline[df_baseline['Total_Move_Cost'] > df_baseline['Total_Move_Cost'].quantile(0.8)]),
                len(df_optimized[df_optimized['Total_Move_Cost'] > df_optimized['Total_Move_Cost'].quantile(0.8)])
            ]
        })
        
        figs['before_after'] = px.bar(
            comparison_data.melt(id_vars='Scenario'),
            x='variable', y='value', color='Scenario',
            barmode='group',
            title="Before vs After Optimization Metrics"
        )
        figs['before_after'].update_layout(height=400)
    
    return figs

def create_predictive_insights_dashboard(df_master, merchant_patterns):
    """Create predictive insights and forecasting dashboard"""
    print("🔮 Creating predictive insights dashboard...")
    
    figs = {}
    
    # 1. Risk Score Distribution
    if 'Move_Risk_Score' in df_master.columns:
        figs['risk_distribution'] = px.histogram(
            df_master,
            x='Move_Risk_Score',
            color='Risk_Category' if 'Risk_Category' in df_master.columns else None,
            title="Relay Move Risk Score Distribution",
            nbins=20
        )
        figs['risk_distribution'].update_layout(height=400)
    
    # 2. Seasonal Request Patterns
    if 'seasonal_patterns' in merchant_patterns and not merchant_patterns['seasonal_patterns'].empty:
        seasonal_data = merchant_patterns['seasonal_patterns']
        
        figs['seasonal_forecast'] = px.line(
            seasonal_data,
            x='Request_Month',
            y='Request_ID',
            color='Request_Type' if 'Request_Type' in seasonal_data.columns else None,
            title="Seasonal Request Patterns",
            markers=True
        )
        figs['seasonal_forecast'].update_layout(height=400)
    
    # 3. Department Risk Matrix
    if 'DeptCat' in df_master.columns and 'Move_Risk_Score' in df_master.columns:
        dept_risk = df_master.groupby('DeptCat').agg({
            'Move_Risk_Score': 'mean',
            'Total_Move_Cost': 'mean',
            'Relay_ID': 'count'
        }).reset_index()
        
        figs['dept_risk_matrix'] = px.scatter(
            dept_risk,
            x='Move_Risk_Score',
            y='Total_Move_Cost',
            size='Relay_ID',
            color='DeptCat',
            title="Department Risk vs Cost Matrix",
            hover_data=['Relay_ID']
        )
        figs['dept_risk_matrix'].update_layout(height=500)
    
    # 4. Merchant Performance Scorecard
    if 'merchant_frequency' in merchant_patterns and not merchant_patterns['merchant_frequency'].empty:
        merchant_data = merchant_patterns['merchant_frequency']
        
        figs['merchant_scorecard'] = px.scatter(
            merchant_data,
            x='Approval_Rate',
            y='Total_Requests',
            size='Expected_Sales_Impact' if 'Expected_Sales_Impact' in merchant_data.columns else 'Total_Requests',
            color='High_Priority_Rate' if 'High_Priority_Rate' in merchant_data.columns else None,
            title="Merchant Performance Scorecard",
            hover_data=['Requested_By'] if 'Requested_By' in merchant_data.columns else None
        )
        figs['merchant_scorecard'].update_layout(height=500)
    
    return figs

def save_interactive_reports(all_figs):
    """Save all interactive reports as HTML files"""
    print("💾 Saving interactive reports...")
    
    report_files = []
    
    for category, figs in all_figs.items():
        if isinstance(figs, dict):
            for fig_name, fig in figs.items():
                filename = f"{category}_{fig_name}.html"
                filepath = os.path.join(INTERACTIVE_DIR, filename)
                fig.write_html(filepath)
                report_files.append(filepath)
                print(f"✅ Saved {filename}")
        else:
            filename = f"{category}.html"
            filepath = os.path.join(INTERACTIVE_DIR, filename)
            figs.write_html(filepath)
            report_files.append(filepath)
            print(f"✅ Saved {filename}")
    
    return report_files

def generate_dashboard_data_json(df_master, merchant_patterns, cost_benefit, executive_summary):
    """Generate JSON data for web dashboard"""
    print("📄 Generating dashboard data JSON...")
    
    # Summary metrics for dashboard
    dashboard_data = {
        'executive_summary': executive_summary,
        'cost_benefit': cost_benefit,
        'data_timestamp': datetime.now().isoformat(),
        
        # Key metrics
        'kpi_metrics': {
            'total_relays': int(len(df_master)),
            'total_weekly_cost': float(df_master['Total_Move_Cost'].sum()) if 'Total_Move_Cost' in df_master.columns else 0,
            'average_move_cost': float(df_master['Total_Move_Cost'].mean()) if 'Total_Move_Cost' in df_master.columns else 0,
            'high_risk_count': int(len(df_master[df_master['Risk_Category'] == 'High'])) if 'Risk_Category' in df_master.columns else 0,
            'potential_annual_savings': cost_benefit.get('total_savings_annual', 0),
            'roi_percentage': cost_benefit.get('roi_percentage', 0),
            'payback_weeks': cost_benefit.get('payback_period_weeks', 0)
        },
        
        # Department breakdown
        'department_summary': {},
        
        # Top risk relays
        'top_risk_relays': [],
        
        # Recent trends
        'trends': {}
    }
    
    # Department breakdown
    if 'DeptCat' in df_master.columns:
        dept_summary = df_master.groupby('DeptCat').agg({
            'Total_Move_Cost': 'sum',
            'Relay_ID': 'count',
            'Move_Risk_Score': 'mean'
        }).round(2).to_dict('index')
        dashboard_data['department_summary'] = dept_summary
    
    # Top risk relays
    if 'Move_Risk_Score' in df_master.columns:
        top_risk = df_master.nlargest(10, 'Move_Risk_Score')[
            ['Relay_ID', 'Move_Risk_Score', 'Total_Move_Cost', 'DeptCat']
        ].round(2).to_dict('records')
        dashboard_data['top_risk_relays'] = top_risk
    
    # Save JSON file
    json_path = os.path.join(OUTPUT_DIR, 'dashboard_data.json')
    with open(json_path, 'w') as f:
        json.dump(dashboard_data, f, indent=2, default=str)
    
    print(f"✅ Saved dashboard data to {json_path}")
    return json_path

def create_all_enhanced_reports(df_master, df_suggested, df_bra_mra, raw_data, merchant_patterns, cost_benefit, executive_summary):
    """Generate all enhanced reports and visualizations"""
    print("🚀 Creating all enhanced reports...")
    
    all_figs = {}
    
    # Create all dashboard categories
    all_figs['merchant_analysis'] = create_merchant_request_dashboard(df_master, df_bra_mra)
    all_figs['data_quality'] = create_data_quality_dashboard(raw_data)
    all_figs['optimization_impact'] = create_optimization_impact_dashboard(df_master, df_suggested, cost_benefit)
    all_figs['predictive_insights'] = create_predictive_insights_dashboard(df_master, merchant_patterns)
    
    # Save interactive reports
    report_files = save_interactive_reports(all_figs)
    
    # Generate dashboard JSON data
    json_path = generate_dashboard_data_json(df_master, merchant_patterns, cost_benefit, executive_summary)
    
    return {
        'interactive_reports': report_files,
        'dashboard_data': json_path,
        'figures': all_figs
    }