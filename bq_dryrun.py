# bq_dryrun.py
from google.cloud import bigquery

client = bigquery.Client(project="wmt-us-gg-shrnk-prod")
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
