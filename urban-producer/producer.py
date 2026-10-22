
import json
import os
import random
import time
from datetime import datetime, timezone

from kafka import KafkaProducer

BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka:9092"
)

TOPIC = os.getenv("KAFKA_TOPIC", "urban_sensors")

SENSORS = [
    "sensor-001",
    "sensor-002",
    "sensor-003",
    "sensor-004",
    "sensor-005"
]

producer = KafkaProducer(
    bootstrap_servers=BOOTSTRAP_SERVERS,
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    key_serializer=lambda key: key.encode("utf-8"),
    acks="all",
    retries=5
)

print(f"Producer conectado a {BOOTSTRAP_SERVERS}", flush=True)

try:
    while True:
        sensor_id = random.choice(SENSORS)

        event = {
            "sensor_id": sensor_id,
            "temperature": round(random.uniform(15, 38), 2),
            "humidity": round(random.uniform(30, 90), 2),
            "air_quality_index": random.randint(20, 180),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        future = producer.send(
            TOPIC,
            key=sensor_id,
            value=event
        )

        metadata = future.get(timeout=10)

        print(
            f"Sensor={sensor_id} "
            f"Partition={metadata.partition} "
            f"Temperature={event['temperature']} "
            f"AQI={event['air_quality_index']}",
            flush=True
        )

        time.sleep(2)

except KeyboardInterrupt:
    print("Producer detenido.")

finally:
    producer.flush()
    producer.close()
