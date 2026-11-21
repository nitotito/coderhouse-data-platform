"""Run inside audit container before/after a host-initiated TaskManager restart."""
import json
import os
import sys
import time
from pathlib import Path
import importlib.util
import boto3
import psycopg
from botocore.config import Config
spec=importlib.util.spec_from_file_location("audit",Path(__file__).with_name("local-e2e.py"))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

def main():
    phase=sys.argv[1]
    result=json.loads((a.OUT/"result.json").read_text())
    assert result["status"]=="PASSED", result
    run=result["run_id"]
    job=a.flink("jobs/overview")["jobs"][0]["jid"]
    if phase=="before":
        cp=a.flink("jobs/"+job+"/checkpoints")
        assert cp["counts"]["completed"]>0
        a.save("recovery-before.json",dict(job_id=job,checkpoints=cp))
        return
    previous=json.loads((a.OUT/"recovery-before.json").read_text())
    deadline=time.monotonic()+180
    while True:
        cp=a.flink("jobs/"+job+"/checkpoints")
        state=a.flink("jobs/"+job)["state"]
        if state=="RUNNING" and cp.get("latest",{}).get("restored"):
            break
        if time.monotonic()>deadline:
            raise TimeoutError("No restored checkpoint after TaskManager restart")
        time.sleep(2)
    fixture=json.loads((a.OUT/"fixture.json").read_text())
    duplicate=fixture["initial"][0]
    barrier=dict(fixture["after_commit"][-1])
    barrier["transaction_id"]=run+"_recovery_barrier"
    import datetime as dt
    barrier["timestamp"]=(dt.datetime.fromisoformat(fixture["base"])+dt.timedelta(minutes=5)).isoformat()
    k=boto3.session.Session().client("kinesis",endpoint_url=os.environ["AWS_ENDPOINT_URL"],config=Config(retries={"mode":"standard","total_max_attempts":5}))
    for event in [duplicate,barrier]:
        k.put_record(StreamName=os.environ["STREAM_NAME"],PartitionKey=run,Data=json.dumps(event).encode())
    time.sleep(15)
    db=a.duckdb_connection()
    with psycopg.connect(autocommit=True) as pg:
        metrics=pg.execute("SELECT * FROM analytics.approved_per_minute WHERE payment_method=%s",(run,)).fetchall()
    s3=boto3.session.Session().client("s3",endpoint_url=os.environ["AWS_ENDPOINT_URL"])
    rows,pointer=a.iceberg(db,s3,os.environ["LAKEHOUSE_BUCKET"])
    wanted=[r for r in rows if r[2]==run]
    assert len(wanted)==len(metrics)==1,(wanted,metrics)
    assert wanted[0][3:]==metrics[0][2:]==(3,a.Decimal("33.06"),a.Decimal("11.020000"))
    a.save("recovery-after.json",dict(status="PASSED",job_id=job,restored=cp["latest"]["restored"],metrics=metrics,iceberg=wanted,duplicate_replayed=True))
    print("Recovery PASSED: checkpoint restored; duplicate replay did not change aggregates")

if __name__=="__main__":
    main()
