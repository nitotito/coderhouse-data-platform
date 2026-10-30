package com.coderhouse.flink;

import org.apache.flink.streaming.api.functions.windowing.ProcessWindowFunction;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.util.Collector;

public class TransactionWindowResult extends
        ProcessWindowFunction<TransactionAccumulator, TransactionSummary, String, TimeWindow> {

    @Override
    public void process(
            String paymentMethod,
            Context context,
            Iterable<TransactionAccumulator> elements,
            Collector<TransactionSummary> out) {

        TransactionAccumulator accumulator = elements.iterator().next();

        out.collect(new TransactionSummary(
                paymentMethod,
                context.window().getStart(),
                context.window().getEnd(),
                accumulator.count,
                accumulator.totalAmount
        ));
    }
}