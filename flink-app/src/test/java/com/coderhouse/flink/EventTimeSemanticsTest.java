package com.coderhouse.flink;

import java.util.ArrayList;
import java.util.List;
import org.apache.flink.api.common.eventtime.Watermark;
import org.apache.flink.api.common.eventtime.WatermarkGenerator;
import org.apache.flink.api.common.eventtime.WatermarkOutput;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class EventTimeSemanticsTest {
    private static class BarrierWatermarks implements WatermarkGenerator<TransactionEvent> {
        public void onEvent(TransactionEvent e,long timestamp,WatermarkOutput out) {
            if(e.getTransactionId().startsWith("barrier"))out.emitWatermark(new Watermark(timestamp-10001));
        }
        public void onPeriodicEmit(WatermarkOutput out) {}
    }
    private static String event(String id,int seconds,String amount,String status) {
        return "{\"transaction_id\":\""+id+"\",\"amount\":"+amount
                +",\"payment_method\":\"card\",\"status\":\""+status
                +"\",\"timestamp\":\"1970-01-01T00:"
                +String.format("%02d:%02d",seconds/60,seconds%60)+"Z\"}";
    }
    @Test @org.junit.jupiter.api.Timeout(60)
    void duplicateAndOutOfOrderAreCountedButClosedWindowLateIsSeparated() throws Exception {
        List<String> input=List.of(event("b",12,"10.01","approved"),
                event("a",1,"10.00","approved"),event("a",1,"10.00","approved"),
                "not-json",event("rejected",13,"999","rejected"),
                event("barrier-1",75,"0","rejected"),event("late",3,"1000","approved"),
                event("barrier-2",135,"0","rejected"));
        var env=StreamExecutionEnvironment.createLocalEnvironment(1);
        var valid=env.fromSequence(0,input.size()-1).map(i->input.get(i.intValue()))
                .flatMap(new TransactionPipeline.Validate()).returns(TransactionEvent.class);
        var timed=valid.assignTimestampsAndWatermarks(WatermarkStrategy
                .<TransactionEvent>forGenerator(context->new BarrierWatermarks())
                .withTimestampAssigner((e,previous)->e.getEventTimeMillis()));
        var result=TransactionPipeline.aggregate(timed);
        var late=result.getSideOutput(TransactionPipeline.LATE_EVENTS)
                .map(e->new TransactionSummary("LATE",0,60000,1,e.getAmount()));
        List<TransactionSummary> observed=new ArrayList<>();
        try(var iterator=result.union(late).executeAndCollect()) {
            while(iterator.hasNext())observed.add(iterator.next());
        }
        assertEquals(2,observed.size());
        var aggregate=observed.stream().filter(s->s.paymentMethod.equals("card")).findFirst().orElseThrow();
        assertEquals(3,aggregate.count);
        assertEquals("30.01",aggregate.totalAmount.toPlainString());
        assertEquals("10.003333",aggregate.averageAmount.toPlainString());
        var dropped=observed.stream().filter(s->s.paymentMethod.equals("LATE")).findFirst().orElseThrow();
        assertEquals("1000.00",dropped.totalAmount.toPlainString());
    }
}
