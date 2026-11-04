package com.coderhouse.flink;

import java.math.BigDecimal;
import org.apache.flink.table.data.RowData;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class TransactionPipelineTest {
    private String event(String amount, String timestamp) {
        return "{\"transaction_id\":\"t1\",\"amount\":" + amount
                + ",\"payment_method\":\"card\",\"status\":\"approved\",\"timestamp\":\""
                + timestamp + "\"}";
    }

    @Test void exactMoneyAndAverageSurviveRowConversion() {
        TransactionAggregate aggregate = new TransactionAggregate();
        TransactionAccumulator acc = aggregate.createAccumulator();
        aggregate.add(TransactionParser.parse(event("0.10", "2026-11-02T12:00:01Z")), acc);
        aggregate.add(TransactionParser.parse(event("0.20", "2026-11-02T12:00:02Z")), acc);
        assertEquals(new BigDecimal("0.30"), acc.totalAmount);
        TransactionSummary summary = new TransactionSummary("card", 0, 60000, acc.count, acc.totalAmount);
        assertEquals(new BigDecimal("0.150000"), summary.averageAmount);
        RowData row = IcebergLakehouse.toRow(summary);
        assertEquals(2, row.getLong(3));
        assertEquals(new BigDecimal("0.30"), row.getDecimal(4, 38, 2).toBigDecimal());
        assertEquals(60000, row.getTimestamp(1, 6).getMillisecond());
    }

    @Test void invalidRecordsAreRejected() {
        assertNull(TransactionParser.parse("not json"));
        assertNull(TransactionParser.parse("{}"));
        assertNull(TransactionParser.parse(event("-1", "2026-11-02T12:00:00Z")));
        assertNull(TransactionParser.parse(event("0.001", "2026-11-02T12:00:00Z")));
        assertNull(TransactionParser.parse(event("1", "invalid")));
        assertNull(TransactionParser.parse(event("10000000000000000", "2026-11-02T12:00:00Z")));
    }

    @Test void epochAndOffsetTimestampsAreEquivalent() {
        TransactionEvent epoch = TransactionParser.parse(event("1", "1793620800000"));
        TransactionEvent iso = TransactionParser.parse(event("1", "2026-11-02T09:00:00-03:00"));
        assertEquals(iso.getEventTimeMillis(), epoch.getEventTimeMillis());
    }

    @Test void mergeAndDailyPartitionAreDefined() {
        TransactionAggregate aggregate = new TransactionAggregate();
        TransactionAccumulator a = aggregate.createAccumulator();
        TransactionAccumulator b = aggregate.createAccumulator();
        aggregate.add(TransactionParser.parse(event("1.00", "2026-11-02T12:00:01Z")), a);
        aggregate.add(TransactionParser.parse(event("2.00", "2026-11-02T12:00:01Z")), b);
        assertEquals(new BigDecimal("3.00"), aggregate.merge(a, b).totalAmount);
        assertEquals("day", IcebergLakehouse.SPEC.fields().get(0).transform().toString());
    }

    @Test void decimalOverflowFailsInsteadOfWritingNull() {
        TransactionSummary summary = new TransactionSummary("card", 0, 60000, 1,
                new BigDecimal("1E40"));
        assertThrows(ArithmeticException.class, () -> IcebergLakehouse.toRow(summary));
    }

    @Test void glueCatalogAndSdkClientsLoadWithoutAwsRequests() throws Exception {
        // Client construction only: no credentials lookup or AWS API calls.
        var credentials = software.amazon.awssdk.auth.credentials.AnonymousCredentialsProvider.create();
        var region = software.amazon.awssdk.regions.Region.US_EAST_1;
        try (var glue = software.amazon.awssdk.services.glue.GlueClient.builder()
                     .region(region).credentialsProvider(credentials).build();
             var s3 = software.amazon.awssdk.services.s3.S3Client.builder()
                     .region(region).credentialsProvider(credentials).build();
             var kinesis = software.amazon.awssdk.services.kinesis.KinesisClient.builder()
                     .region(region).credentialsProvider(credentials).build();
             var catalog = new org.apache.iceberg.aws.glue.GlueCatalog()) {
            catalog.initialize("glue-test", java.util.Map.of(
                    "warehouse", "s3://not-contacted/lakehouse", "client.region", "us-east-1"));
            assertEquals("glue-test", catalog.name());
            assertNotNull(glue); assertNotNull(s3); assertNotNull(kinesis);
        }
    }
}
