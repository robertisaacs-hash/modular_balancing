# bq_dryrun.py
from google.cloud import bigquery
from google.oauth2 import service_account

KEY_PATH = r"C:\Users\hrisaac\OneDrive - Walmart Inc\Documents\VSCode\Projects\modular_balancing\gcp_key.json"
creds = service_account.Credentials.from_service_account_file(KEY_PATH)

client = bigquery.Client(project="wmt-us-gg-shrnk-prod", credentials=creds)
job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)

tests = [
    ("billing project check (jobs.create)", "SELECT 1"),
    ("dataset read: MTRAK", "SELECT COUNT(*) FROM `wmt-assort-bridge-tools.MTRAK_ADHOC.RELAYS`"),
    ("dataset read: MODSPACE", "SELECT COUNT(*) FROM `wmt-assort-bridge-tools.MODSPACE_ADHOC.MSA`"),
]

for name, sql in tests:
    print(f"\n--- Dry run: {name} ---")
    try:
        client.query(sql, job_config=job_config).result()
        print("OK ✅")
    except Exception as e:
        print("FAIL ❌", e)
