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

```mermaid
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