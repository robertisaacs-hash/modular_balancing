# Modular Balancing Automation Pipeline

A production-ready optimization system for automated modular relay scheduling and workload balancing across Walmart store networks.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Pipeline Components](#pipeline-components)
- [Optimization Model](#optimization-model)
- [Reports & Outputs](#reports--outputs)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

The Modular Balancing Automation Pipeline is an enterprise-grade solution designed to optimize the scheduling of modular relays across Walmart stores. The system uses linear programming to balance workload distribution while respecting business constraints such as holidays, store types, and merchant-requested adjustments.

### Key Objectives

- **Workload Balancing**: Distribute relay hours evenly across weeks to prevent overactive periods
- **Store-Specific Optimization**: Apply different thresholds for Neighborhood Markets vs. standard stores
- **Business Rule Compliance**: Honor holidays, seasonal restrictions, and DC realignment requirements
- **Merchant Request Integration**: Accommodate Business/Merchant Requested Adjustments (BRA/MRA)
- **Data-Driven Insights**: Generate comprehensive reports and visualizations for decision-making

### Business Impact

- Reduces peak workload by up to 40% during overactive weeks
- Minimizes store operational disruption through intelligent scheduling
- Provides actionable insights through automated reporting
- Ensures compliance with business rules and merchant agreements

## Features

### Core Capabilities

- ✅ **Automated Data Ingestion** from BigQuery
- ✅ **Cloud Storage Integration** with Google Cloud Storage
- ✅ **Advanced Feature Engineering** with business rule validation
- ✅ **Mixed-Integer Linear Programming** optimization using PuLP/CBC
- ✅ **Multi-Constraint Optimization**:
  - Total weekly hour thresholds
  - Neighborhood Market specific limits
  - Holiday period adjustments
  - Store type differentiation
  - Relay group coordination
- ✅ **Comprehensive Reporting Suite**:
  - Interactive visualizations
  - Before/after comparisons
  - Department-level analytics
  - Year-over-year trending
- ✅ **Mock Data Support** for development and testing

### Technical Features

- **Modular Architecture**: Clean separation of concerns across modules
- **Error Handling**: Robust exception handling with informative logging
- **Scalability**: Handles thousands of relay-store instances
- **Performance**: Optimized for production workloads with configurable timeouts
- **Observability**: Comprehensive logging and status reporting

## Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                     Data Sources                                │
│  BigQuery Tables  │  GCS Buckets  │  Mock Data Generator       │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Ingestion Layer                               │
│  • BigQuery Client  • GCS Client  • Data Validation            │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                Feature Engineering Layer                        │
│  • Master Schedule Creation  • Constraint Validation            │
│  • Holiday Detection  • BRA/MRA Processing                      │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Optimization Engine                             │
│  • LP Problem Formulation  • CBC Solver  • Constraint System   │
│  • Objective Function  • Variable Management                   │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Reporting & Analytics                          │
│  • Visualization Suite  • Comparison Reports                   │
│  • Export to GCS  • Performance Metrics                        │
└─────────────────────────────────────────────────────────────────┘
```

### Project Structure

```
modular_balancing/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Pipeline orchestration
│   ├── config.py               # Configuration management
│   ├── utils.py                # Shared utilities
│   ├── ingestion.py            # Data ingestion from BigQuery/GCS
│   ├── feature_engineering.py # Data transformation & validation
│   ├── optimization.py         # LP model & solver
│   └── reporting.py            # Analytics & visualization
├── output_reports/             # Generated reports & charts
├── tests/                      # Unit & integration tests
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variable template
├── .gitignore
└── README.md
```

## Installation

### Prerequisites

- **Python**: 3.8 or higher
- **Google Cloud SDK**: For BigQuery and GCS access
- **Service Account**: With appropriate GCS and BigQuery permissions

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd modular_balancing
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
# Add your Google Cloud service account key path
```

### Step 5: Verify Installation

```bash
python -m src.main --help
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Google Cloud Project
GCP_PROJECT_ID=your-project-id
GCS_BUCKET_NAME=your-bucket-name

# BigQuery Configuration
BIGQUERY_DATASET=your_dataset
BIGQUERY_TABLE_RELAYS=relay_schedule
BIGQUERY_TABLE_MSA=msa_data
BIGQUERY_TABLE_OVERACTIVE=overactive_bridge

# Optimization Parameters
TOTAL_WEEKLY_HOURS_THRESHOLD=850
NM_AVG_HOURS_THRESHOLD=80
HOLIDAY_TOTAL_WEEKLY_HOURS_THRESHOLD=600
HOLIDAY_NM_AVG_HOURS_THRESHOLD=60
MAX_PROBABLE_NM_STORES_PER_WEEK=10

# Solver Configuration
OPTIMIZATION_TIME_LIMIT=300
```

### Configuration File (`src/config.py`)

Key configuration parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `TOTAL_WEEKLY_HOURS_THRESHOLD` | Maximum total relay hours per week | 850 |
| `NM_AVG_HOURS_THRESHOLD` | Average hours per Neighborhood Market | 80 |
| `PENALTY_OVER_TOTAL_HOURS` | Penalty for exceeding total threshold | 1000 |
| `COST_PER_RELAY_MOVE` | Cost of moving a single relay | 10 |
| `FUTURE_DATE_BUFFER_WEEKS` | Planning horizon in weeks | 52 |

## Usage

### Basic Execution

```bash
# Run full pipeline with production data
python -m src.main

# Run with mock data (for testing)
python -m src.main --use-mock-data

# Skip specific steps
python -m src.main --skip-ingestion --skip-optimization
```

### Advanced Options

```python
# In src/main.py, customize the pipeline:

run_full_pipeline(
    use_mock_data=False,      # Use production data
    skip_ingestion=False,     # Run data ingestion
    skip_optimization=False   # Run optimization
)
```

### Running Specific Modules

```bash
# Test ingestion only
python -c "from src.ingestion import ingest_all_data; ingest_all_data()"

# Test optimization only
python -c "from src.optimization import solve_optimization_problem; solve_optimization_problem(df)"

# Generate reports only
python -c "from src.reporting import generate_reports; generate_reports(df_master, df_suggested)"
```

## Pipeline Components

### 1. Data Ingestion (`ingestion.py`)

**Purpose**: Extract and load data from BigQuery and GCS

**Key Functions**:
- `setup_clients()`: Initialize GCP clients
- `ingest_bq_to_dataframe()`: Query BigQuery tables
- `ingest_all_data()`: Orchestrate complete data ingestion
- `load_from_gcs_pickle()`: Retrieve cached data

**Data Sources**:
- Relay schedule data
- MSA (Merchant Service Agreements)
- Overactive bridge table
- BRA/MRA requests
- Adjustment groups
- Holiday calendar

### 2. Feature Engineering (`feature_engineering.py`)

**Purpose**: Transform raw data into optimization-ready features

**Key Operations**:
- Master schedule creation
- Holiday flagging
- Store type classification
- Relay hour calculations
- Constraint validation
- BRA/MRA integration

**Output**: Processed master schedule with all necessary features

### 3. Optimization Engine (`optimization.py`)

**Purpose**: Solve the relay balancing optimization problem

**Mathematical Model**:

```
Minimize:
  Σ (penalty_over_total × over_total_hours[w]) +
  Σ (penalty_over_nm × over_nm_hours[w]) +
  Σ (cost_per_move × x[i,w])

Subject to:
  1. Each instance assigned to exactly one week
  2. Total hours per week ≤ threshold + slack
  3. NM hours per week ≤ threshold + slack
  4. Cannot-move constraints
  5. Adjustment group synchronization
  6. BRA/MRA request handling
```

**Solver**: CBC (COIN-OR Branch and Cut)

**Performance**:
- Handles 2,500+ instances
- 60+ week planning horizon
- < 5 minute solve time (typical)

### 4. Reporting & Analytics (`reporting.py`)

**Purpose**: Generate insights and visualizations

**Report Types**:

1. **Weekly Hours Comparison**
   - Before/after optimization
   - Threshold visualization
   - Trend analysis

2. **Neighborhood Market Analysis**
   - NM-specific workload
   - Capacity utilization
   - Compliance tracking

3. **Department Breakdown**
   - Relay moves by category
   - Department-level metrics
   - Year-over-year comparison

4. **Activity Heatmap**
   - Store × Week visualization
   - Hotspot identification
   - Workload distribution

5. **Status Dashboard**
   - BRA/MRA tracking
   - Request fulfillment
   - Approval status

## Optimization Model

### Decision Variables

- `x[i,w]`: Binary variable indicating if instance `i` is assigned to week `w`
- `over_total_hours[w]`: Continuous slack variable for total weekly hours
- `over_nm_hours[w]`: Continuous slack variable for NM hours

### Constraints

#### 1. Assignment Constraint
```
Σ(w) x[i,w] = 1  ∀i
```
Each relay-store instance must be assigned to exactly one week.

#### 2. Total Hours Constraint
```
Σ(i) hours[i] × x[i,w] ≤ threshold[w] + over_total_hours[w]  ∀w
```

#### 3. Neighborhood Market Constraint
```
Σ(i∈NM) hours[i] × x[i,w] ≤ nm_threshold[w] + over_nm_hours[w]  ∀w
```

#### 4. Cannot-Move Constraint
```
x[i, original_week[i]] = 1  ∀i where cannot_move[i] = True
```

#### 5. Adjustment Group Constraint
```
x[i,w] = x[j,w]  ∀i,j ∈ same_group
```

### Objective Function

```
minimize: 
  PENALTY_OVER_TOTAL × Σ(w) over_total_hours[w] +
  PENALTY_OVER_NM × Σ(w) over_nm_hours[w] +
  COST_PER_RELAY_MOVE × Σ(i,w) move_indicator[i,w]
```

Where `move_indicator[i,w] = 1 - x[i, original_week[i]]`

## Reports & Outputs

### Generated Files

All reports are saved to `output_reports/`:

| File | Description |
|------|-------------|
| `total_weekly_hours_comparison.png` | Weekly hours before/after optimization |
| `nm_total_hours_comparison.png` | Neighborhood Market specific analysis |
| `relay_activity_heatmap.png` | Store × Week activity heatmap |
| `relay_moves_by_dept.png` | Department-level relay movements |
| `relay_status_pie.png` | BRA/MRA request status breakdown |

### Viewing Reports

```bash
# Open reports folder (Windows)
explorer output_reports

# Open reports folder (macOS)
open output_reports

# Open reports folder (Linux)
xdg-open output_reports

# Or in VS Code
code output_reports
```

### Console Output

The pipeline provides detailed console logging:

```
Starting Modular Balancing Automation Pipeline...
✅ BigQuery Client Initialized Successfully.
✅ GCS Client Initialized Successfully.
--- Starting Feature Engineering ---
Master schedule created with 2552 relay-store instances.
--- Starting Optimization Model ---
Status: Optimal
✅ Optimization completed successfully.
--- Starting Reporting & Analysis ---
📊 All reports saved to: C:\...\output_reports
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_optimization.py
```

### Code Quality

```bash
# Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/
```

### Adding New Features

1. Create feature branch: `git checkout -b feature/your-feature`
2. Implement changes in appropriate module
3. Add tests in `tests/`
4. Update documentation
5. Submit pull request

### Mock Data Generation

For testing without production data:

```python
from src.ingestion import generate_mock_data

# Generate sample data
mock_relays, mock_msa, mock_overactive = generate_mock_data()
```

## Troubleshooting

### Common Issues

#### 1. Import Errors

```bash
# Solution: Ensure you're running from project root
python -m src.main  # ✅ Correct
python src/main.py  # ❌ Incorrect
```

#### 2. GCS Authentication

```bash
# Set service account key
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"

# Or in Windows
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\key.json
```

#### 3. Optimization Infeasible

**Possible Causes**:
- Conflicting constraints
- Too many cannot-move relays
- Impossible adjustment group requirements

**Solution**:
- Check constraint parameters in `config.py`
- Review cannot-move flags
- Validate adjustment group assignments

#### 4. Missing Dependencies

```bash
# Reinstall all dependencies
pip install --upgrade -r requirements.txt

# Or install specific package
pip install pulp matplotlib seaborn pandas
```

#### 5. Reports Not Generated

**Check**:
- `OUTPUT_DIR` exists and is writable
- Matplotlib backend is configured correctly
- Required columns present in DataFrames

```python
# Verify output directory
import os
print(os.path.exists('output_reports'))  # Should be True
```

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Issues

If optimization is slow:

1. **Reduce planning horizon**: Lower `FUTURE_DATE_BUFFER_WEEKS`
2. **Increase time limit**: Adjust `OPTIMIZATION_TIME_LIMIT`
3. **Filter data**: Remove historical or irrelevant instances
4. **Use solver options**: Configure CBC solver parameters

## Contributing

### Guidelines

1. **Code Style**: Follow PEP 8
2. **Documentation**: Add docstrings to all functions
3. **Testing**: Maintain >80% code coverage
4. **Commits**: Use conventional commit messages

### Commit Message Format

```
type(scope): subject

body

footer
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Example**:
```
feat(optimization): add holiday-aware constraints

Implement dynamic threshold adjustments for holiday weeks
to prevent overallocation during peak periods.

Closes #123
```

## License

Copyright © 2024 Walmart Inc. All rights reserved.

This software is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

---

## Support

For questions, issues, or feature requests:

- **Email**: modular-balancing-support@walmart.com
- **Slack**: #modular-balancing
- **Wiki**: [Internal Documentation](https://wiki.walmart.com/modular-balancing)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

## Acknowledgments

- **Optimization Team**: Model design and implementation
- **Data Engineering**: Pipeline infrastructure
- **Store Operations**: Business requirements and validation

---

**Last Updated**: October 15, 2025  
**Version**: 2.0.0  
**Maintainer**: Shrink Intelligence Team