# Modular Relay Balancing Automation

## Table of Contents
1.  [About the Project](#1-about-the-project)
2.  [Features](#2-features)
3.  [Architecture](#3-architecture)
4.  [Prerequisites](#4-prerequisites)
5.  [Installation](#5-installation)
6.  [Setup & Configuration](#6-setup--configuration)
    *   [GCP Service Account Credentials](#gcp-service-account-credentials)
    *   [GCS Bucket Creation](#gcs-bucket-creation)
    *   [Configuration File (`src/config.py`)](#configuration-file-srccomfigpy)
7.  [Usage](#7-usage)
    *   [Running the Pipeline](#running-the-pipeline)
    *   [Pipeline Execution Flags](#pipeline-execution-flags)
8.  [Data Sources](#8-data-sources)
9.  [Output & Reporting](#9-output--reporting)
10. [Future Enhancements](#10-future-enhancements)
11. [Contact](#11-contact)

---

## 1. About the Project

The Modular Relay Balancing Automation project aims to streamline and optimize the weekly scheduling of modular relays across Walmart stores. Historically, this complex decision-making process, involving various constraints, thresholds, and interdependencies, has been performed manually by senior managers. This application automates the balancing act by ingesting critical data, applying business rules, and leveraging an optimization model to suggest the most efficient relay schedules.

The core objective is to ensure that modular relay activity within any given week adheres to defined operational thresholds (e.e., total weekly hours, neighborhood market average hours) while respecting hard constraints (e.g., seasonal relays, DC realignments, adjacency requirements) and integrating business/merchant requested adjustments.

## 2. Features

*   **Automated Data Ingestion:** Fetches real-time and historical data from various BigQuery datasets.
*   **Comprehensive Feature Engineering:** Transforms raw data into actionable features, including:
    *   Relay-level attributes (hours, seasonal flags, change percentages).
    *   Store-level attributes (store ID, type, holiday indicators).
    *   Business-specific flags (overactive categories/relays, adjacency groups).
    *   Integration of Business/Merchant Requested Adjustments (BRA/MRA).
*   **Rule-Based Constraints:** Enforces hard business rules that prevent certain relays from moving (e.g., Seasonal, DC Realignments).
*   **Optimization-Driven Balancing:** Utilizes a Linear Programming (LP) model to:
    *   Minimize operational overload by adhering to weekly hour thresholds.
    *   Respect adjacency requirements for simultaneous relay deployments.
    *   Generate an optimized schedule suggesting which relays (and their associated stores) should move to which week.
*   **Performance Comparison:** Compares the optimized schedule against the current schedule to highlight improvements in key metrics.
*   **Reporting & Visualization:** Generates charts and tabular summaries for easy interpretation of current state, suggested adjustments, and threshold compliance.
*   **Cloud-Native Design:** Leverages Google Cloud Platform (GCP) services (BigQuery, Cloud Storage) for scalable data processing and storage.

## 3. Architecture

The application follows a modular, pipeline-based architecture implemented in Python.

```
graph TD
    A[GCP BigQuery Data Sources] --> B{Data Ingestion Layer};
    B -- Raw Data (GCS) --> C{Feature Engineering Layer};
    C -- Processed Data (GCS) --> D{Optimization Layer (PuLP)};
    D -- Optimized Schedule (GCS) --> E{Reporting Layer};
    E -- Reports (Local / GCS) --> F[End User / Power BI Dashboard];

    subgraph Orchestration (main.py)
        direction LR
        B -- df_relays, df_msa, df_overactive_bridge, etc. --> C;
        C -- df_master_schedule --> D;
        D -- df_suggested_schedule --> E;
    end
```

*   **Key Components:**
   *   src/config.py: Centralized configuration for GCP project IDs, BigQuery tables, GCS buckets, thresholds, and optimization parameters.
   *   src/utils.py: Houses reusable utilities, particularly for GCP client initialization and GCS read/write operations.
   *   src/data_ingestion.py: Responsible for querying BigQuery data and generating mock data when needed. It also performs initial mapping of generic column names to business-defined terms (Relay_Hours, Is_Seasonal, Is_DC_Realign).   
   *   src/feature_engineering.py: Handles data cleaning, transformation, creation of the granular master schedule (Relay_ID per Store_ID), application of initial business rules (e.g., Cannot_Move), and calculation of DAX-like contextual metrics. Critically, it uses the wmt-assetprotection-prod.Store_Support_Dev.storeleveloveractivemodulars dataset as a bridge to link Relay_ID to specific Store_IDs and Store_Types.
   *   src/optimization.py: Formulates the balancing problem as a Linear Programming model using PuLP, defining decision variables, objective function (minimizing moves and threshold breaches), and all associated constraints.
   *   src/reporting.py: Visualizes key metrics (total hours, NM hours) comparing current and optimized schedules, highlights moved relays, and summarizes unaddressed requests.

## 4. Prerequisites
Before you begin, ensure you have the following:

Python 3.9+ installed.
Git installed.
Google Cloud Project: Access to a Google Cloud Project with Billing enabled.
Service Account: A GCP Service Account with the following roles (at minimum) in your respective projects:
BigQuery Data Viewer for wmt-us-gg-shrnk-prod (for RELAYS and MSA) and wmt-assetprotection-prod (for storeleveloveractivemodulars).
Storage Object Admin (Storage Object Creator + Storage Object Viewer) for the GCS bucket (wmt-us-gg-shrnk-prod-modrelaybalancing-data).
Storage Bucket Creator for the project where the GCS bucket resides (likely wmt-us-gg-shrnk-prod). (This is for the initial bucket creation.)
Service Account Key JSON File: Download the JSON key file for your service account.
Network Access: Ensure your corporate network allows outbound connections to Google Cloud services and Python Package Index (PyPI) through any required proxies. You may need to configure proxy settings for pip.

## 5. Installation
Clone the Repository:
```
git clone <repository_url> modular_balancing
cd modular_balancing
```

Create and Activate a Python Virtual Environment (Recommended):

```
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

Install Dependencies:

```
pip install -r requirements.txt
```

## 6. Setup & Configuration

* ## GCP Service Account Credentials
Place your JSON key file: Move your downloaded service account JSON key file to a secure location on your machine.

Configure .env: Create a file named .env in the root of your modular_balancing project directory and add the following line, replacing /path/to/your/service_account_key.json with the absolute path to your file:

```odular_balancing/.env
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service_account_key.json
```
SECURITY WARNING: granularize roles. Do NOT commit gcp_key.json or your .env file to version control. Add *.json and .env to your .gitignore.

* ## GCS Bucket Creation
Before running the pipeline, ensure your dedicated GCS bucket is created. The pipeline's utility functions will attempt to create it if it doesn't exist.

Verify Bucket Name: In src/config.py, ensure GCS_BUCKET_NAME is set to a globally unique name (e.g., wmt-us-gg-shrnk-prod-modrelaybalancing-data).
Initial Run: The first time you run src/main.py, it will check for/create the bucket.
* ## Configuration File (src/config.py)
Review and adjust the parameters in src/config.py to match your exact environment and business requirements:

*   PROJECT_ID_SHRNK, PROJECT_ID_AP, GCP_LOCATION: Confirm these are correct for your Google Cloud setup.
*   BQ_RELAYS_TABLE_ID, BQ_MSA_TABLE_ID, BQ_OVERACTIVE_BRIDGE_TABLE_ID: Update these with the specific, fully qualified BigQuery table IDs for your datasets.
*   TIME_WINDOW_DAYS: Adjust how much historical data (e.g., 365 for one year, 730 for two years) to fetch and process.
*   TOTAL_WEEKLY_HOURS_THRESHOLD, NM_AVG_HOURS_THRESHOLD: Set the target operational thresholds provided by the senior manager.
*   HOLIDAY_TOTAL_WEEKLY_HOURS_THRESHOLD, HOLIDAY_NM_AVG_HOURS_THRESHOLD: Adjust these if holiday weeks require different balancing targets.
*   PENALTY_OVER_TOTAL_HOURS, PENALTY_OVER_NM_HOURS_PROXY, COST_PER_RELAY_MOVE: These are crucial for tuning the optimization model's behavior. Adjust these weights based on which factors are most critical to prioritize (e.g., how much to penalize exceeding hours vs. how disruptive a relay move is).
*   MAX_PROBABLE_NM_STORES_PER_WEEK: This is a key heuristic for the Neighborhood Market (NM) average hours proxy. Validate this value based on actual data to ensure the proxy constraint is meaningful.
*   RELAY_HOURS_COL: Confirmed as "Total_Store_Hours".
*   SEASONAL_DESC_VALUE, DC_REALIGN_DESC_VALUE: Confirmed values from Short_Desc column.
## 7. Usage 
* ## Running the Pipeline
From the root of your project directory (modular_balancing), execute the main.py script:

```
python src/main.py
```
* ## Pipeline Execution Flags
The run_full_pipeline function in src/main.py accepts several flags to control its execution, useful for development and debugging:

*   use_mock_data (default: False):
   *   Set to True to generate mock data for all BigQuery sources if the real query fails or if no data is returned. This is useful for initial testing without live BigQuery access.
*   skip_ingestion (default: False):
   *   Set to True to skip fetching data from BigQuery and instead attempt to load previously saved raw dataframes from GCS. Useful for iterating on feature engineering or optimization without re-querying large datasets.
*   skip_optimization (default: False):
   *   Set to True to skip running the PuLP optimization solver and instead attempt to load a previously saved optimized schedule from GCS. Useful for re-running reporting without re-solving a potentially long-running optimization model.
Example Usage in src/main.py (within if __name__ == "__main__":)

```
# Run with mock data for quick testing
# run_full_pipeline(use_mock_data=True)

# Run with real BQ data (if mock data is False)
# run_full_pipeline(use_mock_data=False)

# Load data from GCS and run optimization (good for iterating after first full run)
run_full_pipeline(use_mock_data=False, skip_ingestion=True)

# Load everything from GCS (for quick reporting/testing of downstream steps)
# run_full_pipeline(use_mock_data=False, skip_ingestion=True, skip_optimization=True)
```
## 8. Data Sources
The application leverages several BigQuery tables:

*   wmt-assort-bridge-tools.MTRAK_ADHOC.RELAYS: Provides core relay information (Relay_ID, WK_End_Date, DeptCat, Relay_Change_Perc, Total_Store_Hours, Short_Desc).
*   wmt-assort-bridge-tools.MODSPACE_ADHOC.MSA: Contains modular space details by store (Mod_ID, Store, Mod_Eff_Date, Mod_Type, Store_Type).
*   wmt-assetprotection-prod.Store_Support_Dev.storeleveloveractivemodulars: Critical Bridge Table. This dataset links Relay_ID to specific Store_IDs (column Store) and their Store_Type for a given week (WK_End_Date), allowing the pipeline to associate individual relays with the stores they impact.
*   BRA/MRA Requests Table (currently mocked): Expected to contain Relay_ID, Requested_Move_WK, Request_Type, Status for business/merchant requested adjustments. This needs to be updated with the actual BigQuery table name and schema once identified.
*   Adjacency Mapping Table (currently mocked): Expected to define Relay_IDs that must move together due to spatial adjacencies. This needs to be updated with the actual BigQuery table name and schema once identified.
*   Holiday Calendar Table (currently mocked): Expected to indicate WK_End_Dates that are holidays and may require unique thresholds. This needs to be updated once identified.
## 9. Output & Reporting
The src/reporting.py module generates the following:

*   **Visualizations:**
   *   total_weekly_hours_comparison.png: Line plot comparing total weekly relay hours (current vs. suggested) against defined thresholds.
   *   nm_total_hours_comparison.png: Line plot comparing Neighborhood Market total weekly relay hours (current vs. suggested) against a proxy threshold.
*   **Console Summaries (also suitable for export):**
   *   A detailed list of Relay_ID and Store_ID instances that have been suggested to move, showing their original and new WK_End_Date.
   *   A comparison of suggested moves against any pending BRA/MRA requests, highlighting matches or discrepancies.
   *   Analysis of relay counts by department comparing the current year to the previous year, identifying new relays.
These outputs are saved locally to the output_reports/ directory and can be configured to be uploaded to GCS for Power BI integration.

## 10. Future Enhancements
   *   Real Data for Mocked Sources: Integrate actual BigQuery tables for BRA/MRA, Adjacency Groups, and Holiday Calendar.
   *   Refined MAX_PROBABLE_NM_STORES_PER_WEEK: Implement a dynamic calculation or more robust modeling for the Neighborhood Market average hours.
   *   Advanced Optimization Objectives: Incorporate additional business objectives into the LP model, such as minimizing disruption to specific high-priority store types or departments, or considering forecast sales impact.
   *   User Interface/API: Develop a front-end interface or an API endpoint to trigger the pipeline, view results, and integrate with ModSpace communication workflows.
   *   Automated GCS Reporting: Automatically upload generated reports (plots and detailed CSVs/Parquets) to a dedicated GCS bucket for Power BI consumption.
   *   Logging: Implement more comprehensive logging using Python's logging module.
   *   Unit/Integration Tests: Add tests to ensure data transformations and optimization logic are working as expected.
## 11. Contact
For questions or support, please contact your project lead or the development team.