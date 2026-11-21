"""Publish a new controlled fixture and reconcile equivalent committed aggregates."""
import datetime as dt
import json
import os
import time
import urllib.request
from urllib.parse import urlparse
from pathlib import Path
from decimal import Decimal
import boto3
from botocore.config import Config
import duckdb
import psycopg

OUT=Path("/repo/docs/evidence/capstone/local")

def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/name).write_text(json.dumps(value,indent=2,default=str)+"\n")

def flink(path):
    with urllib.request.urlopen(os.environ["FLINK_REST_URL"].rstrip("/")+"/"+path,timeout=10) as r:
        return json.load(r)

def iceberg(db, s3, bucket):
    # Resolve the current pointer through JDBC, never guess the newest S3 object.
    # This connection uses the catalog login only, passed by Compose.
    with psycopg.connect(user=os.environ["CATALOG_USER"],password=os.environ["CATALOG_PASSWORD"]) as cat:
        row=cat.execute("SELECT metadata_location FROM iceberg_catalog.iceberg_tables WHERE table_name=%s",(os.environ["ICEBERG_TABLE"],)).fetchone()
    if not row:
        return [],None
    pointer=row[0]
    rows=db.execute("SELECT * FROM iceberg_scan(?) ORDER BY window_start,payment_method",[pointer]).fetchall()
    return rows,pointer

def duckdb_connection():
    db=duckdb.connect()
    db.execute("INSTALL iceberg; LOAD iceberg; INSTALL httpfs; LOAD httpfs")
    endpoint=urlparse(os.environ["AWS_ENDPOINT_URL"])
    def quote(value):
        return "'"+value.replace("'", "''")+"'"
    options={"KEY_ID":os.environ["AWS_ACCESS_KEY_ID"], "SECRET":os.environ["AWS_SECRET_ACCESS_KEY"],
             "REGION":os.environ["AWS_REGION"], "ENDPOINT":endpoint.netloc, "URL_STYLE":"path"}
    db.execute("CREATE SECRET local_s3 (TYPE s3, "+", ".join(key+" "+quote(value) for key,value in options.items())+
               ", USE_SSL "+("true" if endpoint.scheme=="https" else "false")+")")
    return db

def main():
    save("result.json", {"status":"RUNNING"})
    endpoint=os.environ["AWS_ENDPOINT_URL"]
    if urlparse(endpoint).hostname != os.environ["LOCALSTACK_HOST"]:
        raise ValueError("Local-only audit")
    session=boto3.session.Session()
    cfg=Config(retries={"mode":"standard","total_max_attempts":5})
    k=session.client("kinesis",endpoint_url=endpoint,config=cfg)
    s3=session.client("s3",endpoint_url=endpoint,config=cfg)
    bucket=os.environ["LAKEHOUSE_BUCKET"]
    db=duckdb_connection()
    jobs=flink("jobs/overview")["jobs"]
    assert len(jobs)==1 and jobs[0]["state"]=="RUNNING",jobs
    job=jobs[0]["jid"]
    now=dt.datetime.now(dt.timezone.utc)
    base=now.replace(second=0,microsecond=0)
    run="local_"+now.strftime("%Y%m%d_%H%M%S")
    def event(suffix,seconds,amount="10.00",status="approved"):
        return dict(transaction_id=run+suffix,timestamp=(base+dt.timedelta(seconds=seconds)).isoformat(),amount=amount,payment_method=run,status=status)
    first=event("_a",1,"10.01")
    initial=[first,event("_b",3,"20.02"),first,event("_ooo",2,"3.03"),event("_reject",4,"999.00","rejected"),"{bad json",event("_advance",80,"0.00","rejected")]
    fixture=dict(run_id=run,base=base,initial=initial)
    save("fixture.json",fixture)
    receipts=[]
    for e in initial:
        response=k.put_record(StreamName=os.environ["STREAM_NAME"],PartitionKey=run,Data=json.dumps(e).encode() if isinstance(e,dict) else e.encode())
        receipts.append(dict(shard=response["ShardId"],sequence=response["SequenceNumber"]))
        time.sleep(.3)
    save("publication-receipts.json",receipts)
    with psycopg.connect(autocommit=True) as pg:
        deadline=time.monotonic()+180
        while True:
            rows,pointer=iceberg(db,s3,bucket)
            wanted=[r for r in rows if r[2]==run]
            if wanted:
                break
            if time.monotonic()>deadline:
                raise TimeoutError("No committed Iceberg window after 180 seconds")
            time.sleep(2)
        assert wanted[0][3:]==(3,Decimal("33.06"),Decimal("11.020000")),wanted
        # Send late data only after the closed window is committed in Iceberg.
        late=event("_late",5,"1000.00")
        for e in [late,first,event("_advance2",150,"0.00","rejected")]:
            r=k.put_record(StreamName=os.environ["STREAM_NAME"],PartitionKey=run,Data=json.dumps(e).encode())
            receipts.append(dict(shard=r["ShardId"],sequence=r["SequenceNumber"]))
        fixture["after_commit"]=[late,first,event("_advance2",150,"0.00","rejected")]
        save("fixture.json",fixture);save("publication-receipts.json",receipts)
        deadline=time.monotonic()+60
        while True:
            events=pg.execute("SELECT * FROM analytics.recent_events WHERE payment_method=%s ORDER BY event_time",(run,)).fetchall()
            if len(events)==7:
                break
            if time.monotonic()>deadline:
                raise TimeoutError("Consumer did not persist all unique events")
            time.sleep(1)
        time.sleep(8)
        metrics=pg.execute("SELECT * FROM analytics.approved_per_minute WHERE payment_method=%s",(run,)).fetchall()
        rows,pointer=iceberg(db,s3,bucket)
        wanted=[r for r in rows if r[2]==run]
        assert len(metrics)==len(wanted)==1,(metrics,wanted)
        assert metrics[0][2:]==wanted[0][3:],(metrics,wanted)
        assert metrics[0][2:]==(3,Decimal("33.06"),Decimal("11.020000"))
        assert [e[-1] for e in events if e[0].endswith("_late")]==[False]
        membership=pg.execute("SELECT current_user,pg_has_role(current_user,'capstone_analyst','member')").fetchone()
        assert membership[1]
        try:
            pg.execute("SELECT * FROM ingestion.offsets")
        except psycopg.errors.InsufficientPrivilege:
            denied=True
        else:
            raise AssertionError("Analyst unexpectedly read private offsets")
        health=pg.execute("SELECT * FROM analytics.ingest_health").fetchall()
        checkpoints=flink("jobs/"+job+"/checkpoints")
        assert checkpoints["counts"]["completed"]>0,checkpoints
        save("postgres-events.json",events);save("postgres-metrics.json",metrics)
        save("duckdb-iceberg.json",dict(pointer=pointer,rows=wanted))
        save("flink-checkpoints.json",checkpoints);save("flink-job.json",flink("jobs/"+job))
        save("health.json",health);save("security.json",dict(membership=membership,private_read_denied=denied))
        key=pointer.split("/",3)[3]
        with s3.get_object(Bucket=bucket,Key=key)["Body"] as body:
            save("iceberg-metadata.json",json.load(body))
        save("result.json",dict(status="PASSED",run_id=run,utc=dt.datetime.now(dt.timezone.utc),published=len(receipts),unique_valid=7,approved_count=3,approved_total="33.06",approved_average="11.020000",late_excluded=True,duplicates_ignored=True,checkpoint_completed=checkpoints["counts"]["completed"],scope="one partition key; manual recovery test separate"))
        print(json.dumps(dict(status="PASSED",run_id=run,metrics=metrics,iceberg=wanted),default=str))

if __name__=="__main__":
    main()
