"""Inspect the actual deployment artifact; no AWS access required."""
from pathlib import Path
from zipfile import ZipFile
import argparse

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--jar',type=Path,default=Path(__file__).resolve().parents[1] / "flink-app/target/flink-transactions-1.2.0.jar")
jar=parser.parse_args().jar
required = [
    "com/coderhouse/flink/TransactionJob.class",
    "org/apache/iceberg/flink/sink/FlinkSink.class",
    "org/apache/iceberg/aws/glue/GlueCatalog.class",
    "org/apache/iceberg/aws/s3/S3FileIO.class",
    "org/apache/flink/connector/kinesis/source/KinesisStreamsSource.class",
    "software/amazon/awssdk/services/glue/GlueClient.class",
    "software/amazon/awssdk/services/s3/S3Client.class",
    "software/amazon/awssdk/services/kinesis/KinesisClient.class",
    "software/amazon/awssdk/http/apache5/Apache5HttpClient.class",
    "org/apache/hadoop/conf/Configuration.class",
]
with ZipFile(jar) as archive:
    names = archive.namelist()
    for name in required:
        assert names.count(name) == 1, f"Missing or repeated: {name}"
        print(f"OK {name}")
    assert "org/apache/flink/streaming/api/environment/StreamExecutionEnvironment.class" not in names
    assert "org/apache/flink/table/data/RowData.class" not in names
    manifest = archive.read("META-INF/MANIFEST.MF").decode()
    assert "Main-Class: com.coderhouse.flink.TransactionJob" in manifest
    sdk = archive.read("META-INF/maven/software.amazon.awssdk/sdk-core/pom.properties").decode()
    assert "version=2.54.17" in sdk, sdk
    print("OK AWS SDK 2.54.17 with Apache5 transport")
print(f"OK provided Flink classes excluded; main class set; JAR {jar.stat().st_size:,} bytes")
