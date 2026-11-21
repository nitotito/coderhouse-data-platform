"""Capture live Flink metrics and independent S3 bronze delivery."""
import importlib.util
import json
import os
from pathlib import Path
import urllib.parse
import boto3
from botocore.config import Config
spec=importlib.util.spec_from_file_location("audit",Path(__file__).with_name("local-e2e.py"))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

def main():
    job=a.flink("jobs/overview")["jobs"][0]
    details=a.flink("jobs/"+job["jid"])
    observations=[]
    for vertex in details["vertices"]:
        prefix="jobs/"+job["jid"]+"/vertices/"+vertex["id"]
        available=a.flink(prefix+"/metrics")
        ids=[m["id"] for m in available if any(s in m["id"].lower() for s in ("valid_records","invalid_records","duplicate_records","late_records","millisbehind","watermark","numrecords","backpressured"))]
        values=a.flink(prefix+"/metrics?get="+urllib.parse.quote(",".join(ids))) if ids else []
        observations.append(dict(name=vertex["name"],metrics=values,backpressure=a.flink(prefix+"/backpressure")))
    a.save("flink-metrics.json",observations)
    session=boto3.session.Session()
    s3=session.client("s3",endpoint_url=os.environ["AWS_ENDPOINT_URL"],config=Config(retries={"mode":"standard","total_max_attempts":4}))
    objects=[]
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=os.environ["LAKEHOUSE_BUCKET"],Prefix="ingesta/"):
        objects.extend(dict(key=o["Key"],bytes=o["Size"],modified=o["LastModified"]) for o in page.get("Contents",[]))
    assert objects,"No bronze object delivered by Firehose"
    a.save("firehose-bronze.json",objects)
    a.save("flink-current-job.json",details)
    a.save("flink-current-checkpoints.json",a.flink("jobs/"+job["jid"]+"/checkpoints"))
    print("Observed real Flink metrics and Firehose bronze objects:",len(objects))

if __name__=="__main__":
    main()
