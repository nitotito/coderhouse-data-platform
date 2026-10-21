
import boto3
import json
import random
import uuid
from datetime import datetime, timezone

session = boto3.Session(
    profile_name="coderhouse-dev",
    region_name="us-east-1"
)

kinesis = session.client("kinesis")

STREAM_NAME = "dev-transactions-stream"

records = []

for i in range(100):
    transaction_id = str(uuid.uuid4())

    event = {
        "transaction_id": transaction_id,
        "amount": round(random.uniform(100, 50000), 2),
        "payment_method": random.choice(
            ["QR", "CARD", "TRANSFER"]
        ),
        "status": random.choice(
            ["approved", "pending", "rejected"]
        ),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    records.append({
        "Data": (json.dumps(event) + "\n").encode("utf-8"),
        "PartitionKey": transaction_id
    })

response = kinesis.put_records(
    StreamName=STREAM_NAME,
    Records=records
)

print(f"Registros enviados: {len(records)}")
print(f"Registros fallidos: {response['FailedRecordCount']}")

for record in response["Records"]:
    if "ShardId" in record:
        print(record["ShardId"])
