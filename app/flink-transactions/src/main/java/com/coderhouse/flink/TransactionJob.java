
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

        // 1. Crear el entorno de ejecución de Flink
        StreamExecutionEnvironment env =
                StreamExecutionEnvironment.getExecutionEnvironment();

        // 2. Habilitar checkpoints cada 60 segundos
        env.enableCheckpointing(60000);

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
        );

        // 6. Convertir JSON en TransactionEvent, descartando registros inválidos
DataStream<TransactionEvent> transactions =
        rawTransactions
                .map(TransactionParser::parse)
                .returns(TransactionEvent.class)
                .filter(event -> event != null);

        // 7. Configurar Event Time y Watermarks
        WatermarkStrategy<TransactionEvent> watermarkStrategy =
                WatermarkStrategy
                        .<TransactionEvent>forBoundedOutOfOrderness(
                                Duration.ofSeconds(10)
                        )
                        .withTimestampAssigner(
                                (event, previousTimestamp) ->
                                        event.getEventTimeMillis()
                        )
                        .withIdleness(
                                Duration.ofSeconds(30)
                        );

        DataStream<TransactionEvent> eventTimeTransactions =
                transactions.assignTimestampsAndWatermarks(
                        watermarkStrategy
                );

        // 8. Filtrar, agrupar y agregar por ventanas
        DataStream<TransactionSummary> summaries =
                eventTimeTransactions

                        // Solo transacciones aprobadas
                        .filter(event ->
                                "approved".equalsIgnoreCase(
                                        event.getStatus()
                                )
                        )

                        // Agrupar por método de pago
                        .keyBy(TransactionEvent::getPaymentMethod)

                        // Ventanas Tumbling de un minuto
                        .window(
                                TumblingEventTimeWindows.of(
                                        Duration.ofMinutes(1)
                                )
                        )

                        // Calcular cantidad, total y promedio
                        .aggregate(
                                new TransactionAggregate(),
                                new TransactionWindowResult()
                        );

        IcebergLakehouse.attach(summaries, properties);

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
                .print();

        // 10. Ejecutar el job
        env.execute("Transactions Streaming Job");
    }
}
