FROM python:3.12-slim
WORKDIR /workspace
COPY ingest-consumer/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY ingest-consumer /workspace/ingest-consumer
CMD ["python", "-u", "/workspace/ingest-consumer/consumer.py"]
