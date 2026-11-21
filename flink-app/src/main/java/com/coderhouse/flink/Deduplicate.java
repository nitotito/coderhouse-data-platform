package com.coderhouse.flink;

import org.apache.flink.api.common.functions.OpenContext;
import org.apache.flink.api.common.functions.RichFilterFunction;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;

/** First business ID wins. No TTL: replay safety lasts for the retained checkpoint state. */
public final class Deduplicate extends RichFilterFunction<TransactionEvent> {
    private transient ValueState<Boolean> seen;
    private transient org.apache.flink.metrics.Counter duplicates;
    @Override public void open(OpenContext context) {
        duplicates = getRuntimeContext().getMetricGroup().counter("duplicate_records");
        seen = getRuntimeContext().getState(new ValueStateDescriptor<>("seen-business-id", Boolean.class));
    }
    @Override public boolean filter(TransactionEvent event) throws Exception {
        if (Boolean.TRUE.equals(seen.value())) {
            duplicates.inc();
            return false;
        }
        seen.update(true);
        return true;
    }
}
