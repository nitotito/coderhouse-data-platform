package com.coderhouse.flink;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Map;
import java.util.Properties;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.table.data.DecimalData;
import org.apache.flink.table.data.GenericRowData;
import org.apache.flink.table.data.RowData;
import org.apache.flink.table.data.StringData;
import org.apache.flink.table.data.TimestampData;
import org.apache.hadoop.conf.Configuration;
import org.apache.iceberg.PartitionSpec;
import org.apache.iceberg.Schema;
import org.apache.iceberg.Table;
import org.apache.iceberg.catalog.Catalog;
import org.apache.iceberg.catalog.TableIdentifier;
import org.apache.iceberg.exceptions.AlreadyExistsException;
import org.apache.iceberg.flink.CatalogLoader;
import org.apache.iceberg.flink.TableLoader;
import org.apache.iceberg.flink.sink.FlinkSink;
import org.apache.iceberg.types.Types;

final class IcebergLakehouse {
    static final Schema SCHEMA = new Schema(
            Types.NestedField.required(1, "window_start", Types.TimestampType.withoutZone()),
            Types.NestedField.required(2, "window_end", Types.TimestampType.withoutZone()),
            Types.NestedField.required(3, "payment_method", Types.StringType.get()),
            Types.NestedField.required(4, "transaction_count", Types.LongType.get()),
            Types.NestedField.required(5, "total_amount", Types.DecimalType.of(38, 2)),
            Types.NestedField.required(6, "average_amount", Types.DecimalType.of(38, 6)));
    static final PartitionSpec SPEC = PartitionSpec.builderFor(SCHEMA).day("window_start").build();

    private IcebergLakehouse() {}

    static void attach(DataStream<TransactionSummary> summaries, Properties settings) throws Exception {
        String warehouse = JobSettings.require(settings, "ICEBERG_WAREHOUSE");
        String database = settings.getProperty("ICEBERG_DATABASE", "lakehouse_db");
        String name = settings.getProperty("ICEBERG_TABLE", "transaction_aggregates");
        TableIdentifier id = TableIdentifier.of(database, name);
        Map<String, String> options = Map.of(
                "warehouse", warehouse,
                "io-impl", "org.apache.iceberg.aws.s3.S3FileIO",
                "client.region", settings.getProperty("AWS_REGION", "us-east-1"));
        CatalogLoader loader = CatalogLoader.custom("glue", options, new Configuration(),
                "org.apache.iceberg.aws.glue.GlueCatalog");
        Catalog catalog = loader.loadCatalog();
        try {
            // Namespace belongs to Terraform. Do not create a second, competing owner.
            try {
                catalog.buildTable(id, SCHEMA).withPartitionSpec(SPEC)
                        .withLocation(warehouse + "/" + database + "/" + name)
                        .withProperties(Map.of("format-version", "2", "write.format.default", "parquet",
                                "write.target-file-size-bytes", "134217728",
                                "write.parquet.compression-codec", "snappy"))
                        .create();
            } catch (AlreadyExistsException existing) {
                // Another submitter may have created the table concurrently.
            }
            Table table = catalog.loadTable(id);
            if (!table.schema().sameSchema(SCHEMA) || !table.spec().compatibleWith(SPEC)) {
                throw new IllegalStateException("Esquema o particionado Iceberg incompatible: " + id);
            }
            DataStream<RowData> rows = summaries.map(IcebergLakehouse::toRow)
                    .returns(org.apache.flink.table.runtime.typeutils.InternalTypeInfo.of(
                            org.apache.iceberg.flink.FlinkSchemaUtil.convert(SCHEMA)));
            FlinkSink.forRowData(rows).table(table)
                    .tableLoader(TableLoader.fromCatalog(loader, id))
                    .uidPrefix("transaction-aggregates").writeParallelism(1).append();
        } finally {
            if (catalog instanceof AutoCloseable) ((AutoCloseable) catalog).close();
        }
    }

    static RowData toRow(TransactionSummary summary) {
        return GenericRowData.of(
                TimestampData.fromLocalDateTime(Instant.ofEpochMilli(summary.windowStart)
                        .atOffset(ZoneOffset.UTC).toLocalDateTime()),
                TimestampData.fromLocalDateTime(Instant.ofEpochMilli(summary.windowEnd)
                        .atOffset(ZoneOffset.UTC).toLocalDateTime()),
                StringData.fromString(summary.paymentMethod), summary.count,
                decimal(summary.totalAmount, 2), decimal(summary.averageAmount, 6));
    }

    private static DecimalData decimal(BigDecimal value, int scale) {
        DecimalData result = DecimalData.fromBigDecimal(value.setScale(scale), 38, scale);
        if (result == null) throw new ArithmeticException("Desbordamiento decimal(38," + scale + ")");
        return result;
    }
}
