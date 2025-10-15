from flask import Flask, render_template, jsonify, request, send_from_directory
import plotly
import json
import pandas as pd
import os
import numpy as np
from datetime import datetime
import traceback

from src.data_ingestion import load_all_raw_data
from src.feature_engineering import create_master_schedule
from src.enhanced_analytics import (
    calculate_move_costs, analyze_merchant_behavior_patterns,
    create_predictive_model_inputs, analyze_cost_benefit_optimization,
    generate_executive_summary, identify_optimization_opportunities
)
from src.enhanced_reporting import create_all_enhanced_reports
from src.optimization import solve_optimization_problem

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Global data cache
_data_cache = {}
_cache_timestamp = None
CACHE_DURATION = 3600  # 1 hour in seconds

def load_and_process_data(use_mock_data=True, force_refresh=False):
    """Load and process all data with caching"""
    global _data_cache, _cache_timestamp
    
    # Use cache if recent (within 1 hour) and not forcing refresh
    if not force_refresh and _cache_timestamp and (datetime.now() - _cache_timestamp).seconds < CACHE_DURATION:
        print("📱 Using cached data...")
        return _data_cache
    
    print("🔄 Loading and processing data...")
    
    try:
        # Load raw data
        raw_data = load_all_raw_data(use_mock_data=use_mock_data)
        
        # Create master schedule
        df_master = create_master_schedule(
            raw_data['df_relays'],
            raw_data['df_msa'],
            raw_data['df_overactive_bridge'],
            raw_data['df_bra_mra'],
            raw_data['df_adj'],
            raw_data['df_holidays']
        )
        
        # Enhanced analytics
        df_master = calculate_move_costs(df_master)
        df_master = create_predictive_model_inputs(df_master)
        
        # Run optimization (simplified for demo - in production, run full optimization)
        df_suggested = df_master.copy()
        df_suggested['Suggested_WK_End_Date'] = df_suggested['Original_WK_End_Date']
        # Simulate some moves for demonstration
        sample_indices = np.random.choice(len(df_suggested), size=min(50, len(df_suggested)), replace=False)
        for idx in sample_indices:
            df_suggested.iloc[idx, df_suggested.columns.get_loc('Suggested_WK_End_Date')] = \
                df_suggested.iloc[idx]['Original_WK_End_Date'] + pd.Timedelta(weeks=np.random.choice([-2, -1, 1, 2]))
        
        # Analyze patterns
        merchant_patterns = analyze_merchant_behavior_patterns(raw_data['df_bra_mra'], df_master)
        cost_benefit = analyze_cost_benefit_optimization(df_master, df_suggested)
        executive_summary = generate_executive_summary(df_master, merchant_patterns, cost_benefit)
        opportunities = identify_optimization_opportunities(df_master, merchant_patterns)
        
        # Cache results
        _data_cache = {
            'raw_data': raw_data,
            'df_master': df_master,
            'df_suggested': df_suggested,
            'merchant_patterns': merchant_patterns,
            'cost_benefit': cost_benefit,
            'executive_summary': executive_summary,
            'opportunities': opportunities
        }
        _cache_timestamp = datetime.now()
        
        print("✅ Data processing completed successfully")
        return _data_cache
        
    except Exception as e:
        print(f"❌ Error loading data: {str(e)}")
        traceback.print_exc()
        # Return empty cache or fallback data
        return {
            'raw_data': {},
            'df_master': pd.DataFrame(),
            'df_suggested': pd.DataFrame(),
            'merchant_patterns': {},
            'cost_benefit': {},
            'executive_summary': {},
            'opportunities': {}
        }

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'cache_status': 'active' if _cache_timestamp else 'empty'
    })

@app.route('/api/refresh-data', methods=['POST'])
def refresh_data():
    """Force refresh of cached data"""
    try:
        load_and_process_data(force_refresh=True)
        return jsonify({'status': 'success', 'message': 'Data refreshed successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/executive-summary')
def executive_summary():
    """Executive summary metrics"""
    try:
        data = load_and_process_data()
        return jsonify(data['executive_summary'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cost-analysis')
def cost_analysis():
    """Cost analysis and ROI metrics"""
    try:
        data = load_and_process_data()
        return jsonify(data['cost_benefit'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/merchant-analysis')
def merchant_analysis():
    """Merchant request analysis charts"""
    try:
        data = load_and_process_data()
        
        # Create merchant analysis charts
        from src.enhanced_reporting import create_merchant_request_dashboard
        figs = create_merchant_request_dashboard(data['df_master'], data['raw_data']['df_bra_mra'])
        
        graphs = {}
        for fig_name, fig in figs.items():
            graphs[fig_name] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        return jsonify(graphs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data-quality')
def data_quality():
    """Data quality assessment charts"""
    try:
        data = load_and_process_data()
        
        from src.enhanced_reporting import create_data_quality_dashboard
        figs = create_data_quality_dashboard(data['raw_data'])
        
        graphs = {}
        for fig_name, fig in figs.items():
            graphs[fig_name] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        return jsonify(graphs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/optimization-impact')
def optimization_impact():
    """Optimization impact visualization"""
    try:
        data = load_and_process_data()
        
        from src.enhanced_reporting import create_optimization_impact_dashboard
        figs = create_optimization_impact_dashboard(
            data['df_master'], data['df_suggested'], data['cost_benefit']
        )
        
        graphs = {}
        for fig_name, fig in figs.items():
            graphs[fig_name] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        return jsonify(graphs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/predictive-insights')
def predictive_insights():
    """Predictive analytics and forecasting"""
    try:
        data = load_and_process_data()
        
        from src.enhanced_reporting import create_predictive_insights_dashboard
        figs = create_predictive_insights_dashboard(data['df_master'], data['merchant_patterns'])
        
        graphs = {}
        for fig_name, fig in figs.items():
            graphs[fig_name] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        return jsonify(graphs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/optimization-opportunities')
def optimization_opportunities():
    """Optimization opportunities and recommendations"""
    try:
        data = load_and_process_data()
        return jsonify(data['opportunities'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/department-breakdown')
def department_breakdown():
    """Department-level metrics breakdown"""
    try:
        data = load_and_process_data()
        df_master = data['df_master']
        
        if 'DeptCat' in df_master.columns and not df_master.empty:
            breakdown = df_master.groupby('DeptCat').agg({
                'Total_Move_Cost': ['sum', 'mean', 'count'],
                'Move_Risk_Score': 'mean',
                'Associate_Hours_Impact': 'sum'
            }).round(2)
            
            # Flatten column names
            breakdown.columns = ['_'.join(col).strip() for col in breakdown.columns]
            breakdown = breakdown.reset_index().to_dict('records')
        else:
            breakdown = []
        
        return jsonify(breakdown)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/top-risk-relays')
def top_risk_relays():
    """Top risk relays for proactive management"""
    try:
        data = load_and_process_data()
        df_master = data['df_master']
        
        if 'Move_Risk_Score' in df_master.columns and not df_master.empty:
            # Select relevant columns for display
            display_columns = ['Relay_ID', 'DeptCat', 'Move_Risk_Score', 'Total_Move_Cost', 
                             'Historical_Moves_Count', 'Days_Since_Last_Move']
            available_columns = [col for col in display_columns if col in df_master.columns]
            
            top_risk = df_master.nlargest(20, 'Move_Risk_Score')[available_columns]
            top_risk = top_risk.round(2).to_dict('records')
        else:
            top_risk = []
        
        return jsonify(top_risk)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/store-performance')
def store_performance():
    """Store-level performance metrics"""
    try:
        data = load_and_process_data()
        df_master = data['df_master']
        
        if 'Store_ID' in df_master.columns and not df_master.empty:
            store_metrics = df_master.groupby('Store_ID').agg({
                'Total_Move_Cost': 'sum',
                'Move_Risk_Score': 'mean',
                'Associate_Hours_Impact': 'sum',
                'Relay_ID': 'count'
            }).round(2)
            
            store_metrics.columns = ['Total_Cost', 'Avg_Risk_Score', 'Total_Hours_Impact', 'Relay_Count']
            store_metrics = store_metrics.reset_index().to_dict('records')
        else:
            store_metrics = []
        
        return jsonify(store_metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weekly-forecast')
def weekly_forecast():
    """Weekly workload forecast"""
    try:
        data = load_and_process_data()
        df_master = data['df_master']
        
        if 'WK_End_Date' in df_master.columns and not df_master.empty:
            weekly_forecast = df_master.groupby('WK_End_Date').agg({
                'Total_Move_Cost': 'sum',
                'Associate_Hours_Impact': 'sum',
                'Relay_ID': 'count'
            }).round(2)
            
            weekly_forecast.columns = ['Projected_Cost', 'Hours_Required', 'Relay_Count']
            weekly_forecast = weekly_forecast.reset_index()
            weekly_forecast['WK_End_Date'] = weekly_forecast['WK_End_Date'].dt.strftime('%Y-%m-%d')
            weekly_forecast = weekly_forecast.to_dict('records')
        else:
            weekly_forecast = []
        
        return jsonify(weekly_forecast)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/merchant-requests')
def merchant_requests():
    """Current merchant requests status"""
    try:
        data = load_and_process_data()
        df_bra_mra = data['raw_data'].get('df_bra_mra', pd.DataFrame())
        
        if not df_bra_mra.empty:
            # Get recent requests
            requests_summary = df_bra_mra.groupby(['Status', 'Request_Type']).size().reset_index()
            requests_summary.columns = ['Status', 'Request_Type', 'Count']
            requests_summary = requests_summary.to_dict('records')
        else:
            requests_summary = []
        
        return jsonify(requests_summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # For development
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # For production deployment (Posit Connect)
    application = app