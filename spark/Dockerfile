
FROM apache/spark:3.5.5-python3

USER root

WORKDIR /opt/spark/app

COPY streaming_job.py .

# Directorio para dependencias de Maven/Ivy
RUN mkdir -p /opt/spark/.ivy2/cache \
    /opt/spark/.ivy2/jars \
    /tmp/spark-checkpoints && \
    chown -R spark:spark /opt/spark/.ivy2 \
    /tmp/spark-checkpoints \
    /opt/spark/app

USER spark

CMD ["/opt/spark/bin/spark-submit", \
     "--master", "local[2]", \
     "--conf", "spark.jars.ivy=/opt/spark/.ivy2", \
     "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5", \
     "/opt/spark/app/streaming_job.py"]
