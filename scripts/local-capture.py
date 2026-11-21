"""Print real read-only queries for manual screenshots; never draw synthetic evidence."""
import importlib.util
import json
import os
import sys
from pathlib import Path
import psycopg
spec=importlib.util.spec_from_file_location("audit",Path(__file__).with_name("local-e2e.py"))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

def main():
    kind=sys.argv[1]
    run=json.loads((a.OUT/"result.json").read_text())["run_id"]
    print("Run:",run,flush=True)
    if kind=="postgres":
        queries=[("SELECT transaction_id, event_time, arrival_timestamp, inserted_at, eligible FROM analytics.recent_events WHERE payment_method=%s ORDER BY event_time",(run,)),("SELECT * FROM analytics.approved_per_minute WHERE payment_method=%s",(run,)),("SELECT * FROM analytics.ingest_health",())]
        with psycopg.connect(autocommit=True) as pg:
            for sql,params in queries:
                cursor=pg.execute(sql,params)
                print("\nPostgreSQL SQL:",sql,"\nColumns:",[c.name for c in cursor.description])
                for row in cursor:
                    print(" | ".join(str(v) for v in row))
    elif kind=="duckdb":
        import boto3
        db=a.duckdb_connection()
        s3=boto3.session.Session().client("s3",endpoint_url=os.environ["AWS_ENDPOINT_URL"])
        rows,pointer=a.iceberg(db,s3,os.environ["LAKEHOUSE_BUCKET"])
        print("DuckDB SQL: SELECT * FROM iceberg_scan(?) WHERE payment_method = ?")
        print("Metadata pointer:",pointer)
        print("window_start | window_end | payment_method | transaction_count | total_amount | average_amount")
        for row in db.execute("SELECT * FROM iceberg_scan(?) WHERE payment_method = ?",[pointer,run]).fetchall():
            print(" | ".join(str(v) for v in row))
    else:
        raise ValueError("Expected postgres or duckdb")

if __name__=="__main__":
    main()
