package com.coderhouse.flink;

import java.math.BigDecimal;
import java.nio.file.Path;
import java.util.Map;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.table.data.RowData;
import org.apache.flink.table.runtime.typeutils.InternalTypeInfo;
import org.apache.hadoop.conf.Configuration;
import org.apache.iceberg.Table;
import org.apache.iceberg.flink.FlinkSchemaUtil;
import org.apache.iceberg.flink.TableLoader;
import org.apache.iceberg.flink.sink.FlinkSink;
import org.apache.iceberg.hadoop.HadoopTables;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class IcebergCheckpointTest {
    @TempDir Path temp;

    // Java NIO-backed permission handling avoids requiring winutils.exe for a
    // temporary test directory. Production S3FileIO does not use this filesystem.
    public static class TestLocalFileSystem extends org.apache.hadoop.fs.RawLocalFileSystem {
        @Override public void setPermission(org.apache.hadoop.fs.Path path,
                org.apache.hadoop.fs.permission.FsPermission permission) {}
    }

    @Test @org.junit.jupiter.api.Timeout(60)
    void localFlinkWritesParquetAndCommitsSnapshots() throws Exception {
        String location = temp.resolve("aggregates").toUri().toString();
        Configuration hadoop = new Configuration();
        hadoop.setClass("fs.file.impl", TestLocalFileSystem.class, org.apache.hadoop.fs.FileSystem.class);
        hadoop.setBoolean("fs.file.impl.disable.cache", true);
        Table table = new HadoopTables(hadoop).create(IcebergLakehouse.SCHEMA,
                IcebergLakehouse.SPEC, Map.of("format-version", "2"), location);
        StreamExecutionEnvironment env = StreamExecutionEnvironment.createLocalEnvironment(1);
        org.apache.flink.configuration.Configuration flink = new org.apache.flink.configuration.Configuration();
        flink.set(org.apache.flink.configuration.RestartStrategyOptions.RESTART_STRATEGY, "none");
        env.configure(flink);
        env.enableCheckpointing(200);
        env.getCheckpointConfig().setMaxConcurrentCheckpoints(1);
        var rows = env.fromSequence(1, 12).map(value -> {
            Thread.sleep(200);
            return IcebergLakehouse.toRow(new TransactionSummary("card", 0, 60000,
                    value, new BigDecimal("0.30")));
        }).returns(InternalTypeInfo.<RowData>of(FlinkSchemaUtil.convert(IcebergLakehouse.SCHEMA)));
        FlinkSink.forRowData(rows).table(table)
                .tableLoader(TableLoader.fromHadoopTable(location, hadoop))
                .uidPrefix("local-iceberg-test").writeParallelism(1).append();
        env.execute("Local Iceberg checkpoint validation");
        table.refresh();
        assertNotNull(table.currentSnapshot());
        assertEquals("12", table.currentSnapshot().summary().get("total-records"));
        // At least one periodic checkpoint must commit, in addition to end-of-input.
        long snapshots = 0;
        for (var snapshot : table.snapshots()) {
            snapshots++;
            assertTrue(Long.parseLong(snapshot.summary().get("flink.max-committed-checkpoint-id")) > 0);
        }
        assertTrue(snapshots >= 2, "Expected periodic checkpoint commits before final input");
        try (var tasks = table.newScan().planFiles()) {
            for (var task : tasks) assertTrue(task.file().location().endsWith(".parquet"));
        }
    }
}
