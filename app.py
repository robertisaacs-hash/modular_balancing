from flask import Flask, render_template, jsonify, request, send_from_directory
import plotly
import json
import pandas as pd
import os
from datetime import datetime

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

# Global data cache
_data_cache = {}
_cache_timestamp = None

def load_and_process_data(use_mock_data=True):
    """Load and process all data with caching"""
    global _data_cache, _cache_timestamp
    
    # Use cache if recent (within 1 hour)
    if _cache_timestamp and (datetime.now() - _cache_timestamp).seconds < 3600:
        return _data_cache
    
    print("🔄 Loading and processing data...")
    
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
    
    # Run optimization (mock for demo)
    df_suggested = df_master.copy()
    df_suggested['Suggested_WK_End_Date'] = df_suggested['Original_WK_End_Date']
    
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
    
    return _data_cache

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/executive-summary')
def executive_summary():
    data = load_and_process_data()
    return jsonify(data['executive_summary'])

@app.route('/api/cost-analysis')
def cost_analysis():
    data = load_and_process_data()
    return jsonify(data['cost_benefit'])

@app.route('/api/merchant-analysis')
def merchant_analysis():
    data = load_and_process_data()
    
    # Create merchant analysis charts
    from src.enhanced_reporting import create_merchant_request_dashboard
    figs = create_merchant_request_dashboard(data['df_master'], data['raw_data']['df_bra_mra'])
    
    graphs = {}
    for fig_name, fig in figs.items():
        graphs[fig_name] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return jsonify(graphs)

@app.route('/api/data-quality')
def data_quality():
    data = load_and_process_data()
    
    from src.enhanced_reporting import create_data_quality_dashboard
    figs = create_data_quality_dashboard(data['raw_data'])
    
    graphs = {}
    for fig_name, fig in figs.items():
        graphs[fig_name] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return jsonify(graphs)

@app.route('/api/optimization-impact')
def optimization_impact():
    data = load_and_process_data()
    
    from src.enhanced_reporting import create_optimization_impact_dashboard
    figs = create_optimization_impact_dashboard(
        data['df_master'], data['df_suggested'], data['cost_benefit']
    )
    
    graphs = {}
    for fig_name, fig in figs.items():
        graphs[fig_name] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return jsonify(graphs)

@app.route('/api/predictive-insights')
def predictive_insights():
    data = load_and_process_data()
    
    from src.enhanced_reporting import create_predictive_insights_dashboard
    figs = create_predictive_insights_dashboard(data['df_master'], data['merchant_patterns'])
    
    graphs = {}
    for fig_name, fig in figs.items():
        graphs[fig_name] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return jsonify(graphs)

@app.route('/api/optimization-opportunities')
def optimization_opportunities():
    data = load_and_process_data()
    return jsonify(data['opportunities'])

@app.route('/api/department-breakdown')
def department_breakdown():
    data = load_and_process_data()
    df_master = data['df_master']
    
    if 'DeptCat' in df_master.columns:
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

@app.route('/api/top-risk-relays')
def top_risk_relays():
    data = load_and_process_data()
    df_master = data['df_master']
    
    if 'Move_Risk_Score' in df_master.columns:
        top_risk = df_master.nlargest(20, 'Move_Risk_Score')[
            ['Relay_ID', 'DeptCat', 'Move_Risk_Score', 'Total_Move# filepath: c:\Users\hrisaac\OneDrive - Walmart Inc\Documents\VSCode\Projects\modular_balancing\app.py
from flask import Flask, render_template, jsonify, request, send_from_directory
import plotly
import json
import pandas as pd
import os
from datetime import datetime

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

# Global data cache
_data_cache = {}
_cache_timestamp = None

def load_and_process_data(use_mock_data=True):
    """Load and process all data with caching"""
    global _data_cache, _cache_timestamp
    
    # Use cache if recent (within 1 hour)
    if _cache_timestamp and (datetime.now() - _cache_timestamp).seconds < 3600:
        return _data_cache
    
    print("🔄 Loading and processing data...")
    
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
    
    # Run optimization (mock for demo)
    df_suggested = df_master.copy()
    df_suggested['Suggested_WK_End_Date'] = df_suggested['Original_WK_End_Date']
    
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
    
    return _data_cache

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/executive-summary')
def executive_summary():
    data = load_and_process_data()
    return jsonify(data['executive_summary'])

@app.route('/api/cost-analysis')
def cost_analysis():
    data = load_and_process_data()
    return jsonify(data['cost_benefit'])

@app.route('/api/merchant-analysis')
def merchant_analysis():
    data = load_and_process_data()
    
    # Create merchant analysis charts
    from src.enhanced_reporting import create_merchant_request_dashboard
    figs = create_merchant_request_dashboard(data['df_master'], data['raw_data']['df_bra_mra'])
    
    graphs = {}
    for fig_name, fig in figs.items():
        graphs[fig_name] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return jsonify(graphs)

@app.route('/api/data-quality')
def data_quality():
    data = load_and_process_data()
    
    from src.enhanced_reporting import create_data_quality_dashboard
    figs = create_data_quality_dashboard(data['raw_data'])
    
    graphs = {}
    for fig_name, fig in figs.items():
        graphs[fig_name] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return jsonify(graphs)

@app.route('/api/optimization-impact')
def optimization_impact():
    data = load_and_process_data()
    
    from src.enhanced_reporting import create_optimization_impact_dashboard
    figs = create_optimization_impact_dashboard(
        data['df_master'], data['df_suggested'], data['cost_benefit']
    )
    
    graphs = {}
    for fig_name, fig in figs.items():
        graphs[fig_name] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return jsonify(graphs)

@app.route('/api/predictive-insights')
def predictive_insights():
    data = load_and_process_data()
    
    from src.enhanced_reporting import create_predictive_insights_dashboard
    figs = create_predictive_insights_dashboard(data['df_master'], data['merchant_patterns'])
    
    graphs = {}
    for fig_name, fig in figs.items():
        graphs[fig_name] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return jsonify(graphs)

@app.route('/api/optimization-opportunities')
def optimization_opportunities():
    data = load_and_process_data()
    return jsonify(data['opportunities'])

@app.route('/api/department-breakdown')
def department_breakdown():
    data = load_and_process_data()
    df_master = data['df_master']
    
    if 'DeptCat' in df_master.columns:
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

@app.route('/api/top-risk-relays')
def top_risk_relays():
    data = load_and_process_data()
    df_master = data['df_master']
    
    if 'Move_Risk_Score' in df_master.columns:
        top_risk = df_master.nlargest(20, 'Move_Risk_Score')[
            ['Relay_ID', 'DeptCat', 'Move_Risk_Score', 'Total_Move