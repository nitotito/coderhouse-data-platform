package com.coderhouse.flink;

import java.time.Duration;
import org.apache.flink.api.common.functions.OpenContext;
import org.apache.flink.api.common.functions.RichFlatMapFunction;
import org.apache.flink.api.common.functions.RichMapFunction;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.metrics.Counter;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.util.Collector;
import org.apache.flink.util.OutputTag;

/** Shared production/test window logic. Business duplicates are counted. */
final class TransactionPipeline {
    static final OutputTag<TransactionEvent> LATE_EVENTS = new OutputTag<>(
            "late-transactions", TypeInformation.of(TransactionEvent.class));

    static SingleOutputStreamOperator<TransactionSummary> aggregate(DataStream<TransactionEvent> input) {
        return input.filter(e -> "approved".equalsIgnoreCase(e.getStatus()))
                .name("Approved transactions").uid("approved-transactions")
                .keyBy(TransactionEvent::getPaymentMethod)
                .window(TumblingEventTimeWindows.of(Duration.ofMinutes(1)))
                .sideOutputLateData(LATE_EVENTS)
                .aggregate(new TransactionAggregate(), new TransactionWindowResult())
                .name("Approved minute aggregates").uid("approved-minute-aggregates");
    }

    public static final class Validate extends RichFlatMapFunction<String, TransactionEvent> {
        private transient Counter valid;
        private transient Counter invalid;
        @Override public void open(OpenContext context) {
            valid = getRuntimeContext().getMetricGroup().counter("valid_records");
            invalid = getRuntimeContext().getMetricGroup().counter("invalid_records");
        }
        @Override public void flatMap(String json, Collector<TransactionEvent> out) {
            TransactionEvent event = TransactionParser.parse(json);
            if (event == null) invalid.inc();
            else { valid.inc(); out.collect(event); }
        }
    }

    public static final class AuditLate extends RichMapFunction<TransactionEvent, String> {
        private transient Counter late;
        @Override public void open(OpenContext context) {
            late = getRuntimeContext().getMetricGroup().counter("late_records");
        }
        @Override public String map(TransactionEvent event) throws Exception {
            late.inc();
            byte[] hash = java.security.MessageDigest.getInstance("SHA-256")
                    .digest(event.getTransactionId().getBytes(java.nio.charset.StandardCharsets.UTF_8));
            return "LATE_DROPPED|id_sha256=" + java.util.HexFormat.of().formatHex(hash);
        }
    }
}
