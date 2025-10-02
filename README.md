modular_balancing/
├── src/
│   ├── __init__.py           # Makes 'src' a Python package
│   ├── config.py             # All global configurations and parameters
│   ├── utils.py              # Helper functions (like GCS read/write)
│   ├── data_ingestion.py     # Handles fetching/mocking all raw data
│   ├── feature_engineering.py# Processes raw data, creates master schedule & features
│   ├── optimization.py       # Defines and solves the PuLP model
│   ├── reporting.py          # Generates reports and visualizations
│   └── main.py               # Orchestrates the entire workflow
├── data/                     # Optional: local cache during development/testing
├── models/                   # Optional: local storage for optimization results
├── output_reports/           # Directory for generated plots/summaries
├── requirements.txt
├── .env                      # For environment-specific variables (e.g., GCP credentials path)
└── .gitignore                # To exclude unwanted files from version control# modular_balancing
