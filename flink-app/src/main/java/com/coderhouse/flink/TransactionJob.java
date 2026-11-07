
package com.coderhouse.flink;


import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.connector.kinesis.source.KinesisStreamsSource;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.api.common.typeinfo.Types;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.connector.kinesis.source.config.KinesisSourceConfigOptions;




import java.time.Duration;
import java.util.Properties;


public class TransactionJob {

    public static void main(String[] args) throws Exception {

        // 1. Crear el entorno de ejecuciÃ³n de Flink
        StreamExecutionEnvironment env =
                StreamExecutionEnvironment.getExecutionEnvironment();

        // 2. Habilitar checkpoints cada 60 segundos
        env.enableCheckpointing(60000, org.apache.flink.core.execution.CheckpointingMode.EXACTLY_ONCE);

        Properties properties = JobSettings.load();
        String streamArn = JobSettings.require(properties, "KINESIS_STREAM_ARN");
        env.getCheckpointConfig().setMinPauseBetweenCheckpoints(5000);
        env.getCheckpointConfig().setMaxConcurrentCheckpoints(1);

        // 4. Configurar Kinesis como fuente de datos
       Configuration kinesisConfig = new Configuration();

                    kinesisConfig.set(
                            KinesisSourceConfigOptions.STREAM_INITIAL_POSITION,
                            KinesisSourceConfigOptions.InitialPosition.TRIM_HORIZON
                    );

                    KinesisStreamsSource<String> source =
                            KinesisStreamsSource.<String>builder()
                                    .setStreamArn(streamArn)
                                    .setSourceConfig(kinesisConfig)
                                    .setDeserializationSchema(new SimpleStringSchema())
                                    .build();

        // 5. Consumir los registros JSON de Kinesis
        DataStream<String> rawTransactions = env.fromSource(
                source,
                WatermarkStrategy.noWatermarks(),
                "Kinesis Transactions Source",
                Types.STRING
        ).uid("kinesis-transactions-source");

        var transactions = rawTransactions.flatMap(new TransactionPipeline.Validate())
                .returns(TransactionEvent.class).uid("validate-json");
        var eventTimeTransactions = transactions.assignTimestampsAndWatermarks(
                WatermarkStrategy.<TransactionEvent>forBoundedOutOfOrderness(Duration.ofSeconds(10))
                        .withTimestampAssigner((event, previous) -> event.getEventTimeMillis())
                        .withIdleness(Duration.ofSeconds(30))).uid("event-time-watermarks");
        // Assignment subtasks see records already merged by the source; this is
        // not per-shard watermark/idleness tracking.
        var summaries = TransactionPipeline.aggregate(eventTimeTransactions);

        IcebergLakehouse.attach(summaries, properties);

        summaries.getSideOutput(TransactionPipeline.LATE_EVENTS)
                .map(new TransactionPipeline.AuditLate()).returns(Types.STRING)
                .uid("audit-late-records").print("late").uid("late-audit-console");

        // 9. Mostrar los resultados
        summaries
                .map(summary ->
                        "Window [" +
                                summary.windowStart +
                                " - " +
                                summary.windowEnd +
                                "]" +
                                " | Method: " +
                                summary.paymentMethod +
                                " | Count: " +
                                summary.count +
                                " | Total: " +
                                summary.totalAmount +
                                " | Average: " +
                                summary.averageAmount
                )
                .print().uid("aggregate-console");

        // 10. Ejecutar el job
        env.execute("Transactions Streaming Job");
    }
}
