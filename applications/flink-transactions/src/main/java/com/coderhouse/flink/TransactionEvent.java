package com.coderhouse.flink;

import java.time.OffsetDateTime;
import java.math.BigDecimal;

public class TransactionEvent {

    private String transactionId;
    private BigDecimal amount;
    private String paymentMethod;
    private String status;
    private String timestamp;

    public TransactionEvent() {
    }

    public String getTransactionId() {
        return transactionId;
    }

    public void setTransactionId(String transactionId) {
        this.transactionId = transactionId;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public void setAmount(BigDecimal amount) {
        this.amount = amount;
    }

    public String getPaymentMethod() {
        return paymentMethod;
    }

    public void setPaymentMethod(String paymentMethod) {
        this.paymentMethod = paymentMethod;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(String timestamp) {
        this.timestamp = timestamp;
    }

    public long getEventTimeMillis() {
    if (timestamp == null || timestamp.isBlank()) {
        throw new IllegalArgumentException("Timestamp vacío o nulo");
    }

    String value = timestamp.trim();

    // Timestamp Unix en milisegundos
    if (value.matches("\\d{13}")) {
        return Long.parseLong(value);
    }

    // Timestamp ISO 8601
    return OffsetDateTime.parse(value)
            .toInstant()
            .toEpochMilli();
}
}