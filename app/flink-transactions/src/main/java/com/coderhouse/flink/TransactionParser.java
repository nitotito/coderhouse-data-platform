package com.coderhouse.flink;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

final class TransactionParser {
    private static final Logger LOG = LoggerFactory.getLogger(TransactionParser.class);
    private static final ObjectMapper MAPPER = new ObjectMapper()
            .setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);

    private TransactionParser() {}

    static TransactionEvent parse(String json) {
        try {
            TransactionEvent event = MAPPER.readValue(json.trim(), TransactionEvent.class);
            event.getEventTimeMillis();
            if (event.getTransactionId() == null || event.getTransactionId().isBlank()
                    || event.getPaymentMethod() == null || event.getPaymentMethod().isBlank()
                    || event.getStatus() == null || event.getStatus().isBlank()
                    || event.getAmount() == null || event.getAmount().signum() < 0) {
                throw new IllegalArgumentException("Campos obligatorios ausentes o importe negativo");
            }
            // Reject fractional cents instead of silently rounding input money.
            event.setAmount(event.getAmount().setScale(2, java.math.RoundingMode.UNNECESSARY));
            if (event.getAmount().precision() > 18) throw new IllegalArgumentException("Importe fuera de rango");
            return event;
        } catch (Exception e) {
            LOG.warn("Transacción descartada: {}", e.getClass().getSimpleName());
            return null;
        }
    }
}
