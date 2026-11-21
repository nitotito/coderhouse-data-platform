"""Kinesis polling consumer. Offsets and business IDs commit atomically in PostgreSQL."""
import datetime as dt
import json
import os
import time
from urllib.parse import urlparse
from decimal import Decimal, InvalidOperation
import boto3
from botocore.config import Config
import psycopg


def parse(raw):
    try:
        e = json.loads(raw)
        for key in ("transaction_id", "payment_method", "status"):
            if not isinstance(e.get(key), str) or not e[key].strip():
                return None
        text = str(e["timestamp"])
        when = (dt.datetime.fromtimestamp(int(text)/1000, dt.timezone.utc)
                if len(text)==13 and text.isdigit() else dt.datetime.fromisoformat(text.replace("Z", "+00:00")))
        if when.tzinfo is None:
            return None
        amount = Decimal(str(e["amount"]))
        if not amount.is_finite() or amount < 0 or amount != amount.quantize(Decimal(".01")) or amount >= Decimal("1e16"):
            return None
        return (e["transaction_id"], when, amount, e["payment_method"], e["status"].lower())
    except (ValueError, TypeError, KeyError, InvalidOperation, OverflowError):
        return None


def main():
    endpoint = os.environ["AWS_ENDPOINT_URL"]
    # No fallback to real AWS or a developer profile.
    if urlparse(endpoint).hostname != os.environ["LOCALSTACK_HOST"]:
        raise ValueError("This consumer is restricted to the Compose LocalStack endpoint")
    client = boto3.session.Session().client("kinesis", endpoint_url=endpoint,
        config=Config(retries={"mode":"standard", "total_max_attempts":5}, connect_timeout=3, read_timeout=10))
    stream = os.environ["STREAM_NAME"]
    refresh = float(os.getenv("REFRESH_SECONDS", "2"))
    iterators = {}
    with psycopg.connect(autocommit=True) as conn:
        shards = client.get_paginator("list_shards").paginate(StreamName=stream)
        for page in shards:
            for shard in page["Shards"]:
                sid = shard["ShardId"]
                offset = conn.execute("SELECT sequence_number FROM ingestion.offsets WHERE shard_id=%s", (sid,)).fetchone()
                args = dict(StreamName=stream, ShardId=sid, ShardIteratorType="AFTER_SEQUENCE_NUMBER" if offset else "TRIM_HORIZON")
                if offset:
                    args["StartingSequenceNumber"] = offset[0]
                iterators[sid] = client.get_shard_iterator(**args)["ShardIterator"]
        last_refresh = 0
        while True:
            for sid, iterator in list(iterators.items()):
                response = client.get_records(ShardIterator=iterator, Limit=100)
                iterators[sid] = response["NextShardIterator"]
                for record in response["Records"]:
                    event = parse(record["Data"])
                    with conn.transaction():
                        if event:
                            previous = conn.execute("SELECT max_event_time FROM ingestion.watermark WHERE singleton FOR UPDATE").fetchone()[0]
                            # Flink bounded-out-of-orderness watermark is max timestamp minus 10s minus 1ms.
                            window_end = event[1].replace(second=0,microsecond=0)+dt.timedelta(minutes=1)
                            eligible = previous is None or window_end > previous-dt.timedelta(seconds=10,milliseconds=1)
                            inserted = conn.execute("INSERT INTO ingestion.events(transaction_id,event_time,amount,payment_method,status,arrival_timestamp,eligible) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING transaction_id", (*event,record["ApproximateArrivalTimestamp"],eligible)).fetchone()
                            if inserted:
                                conn.execute("UPDATE ingestion.watermark SET max_event_time=GREATEST(max_event_time,%s) WHERE singleton", (event[1],))
                        conn.execute("INSERT INTO ingestion.offsets VALUES (%s,%s) ON CONFLICT(shard_id) DO UPDATE SET sequence_number=excluded.sequence_number", (sid,record["SequenceNumber"]))
            if time.monotonic()-last_refresh >= refresh:
                conn.execute("REFRESH MATERIALIZED VIEW analytics.approved_per_minute")
                last_refresh=time.monotonic()
            time.sleep(.25)

if __name__ == "__main__":
    main()
