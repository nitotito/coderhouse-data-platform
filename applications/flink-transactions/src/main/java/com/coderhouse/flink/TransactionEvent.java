package com.coderhouse.flink;

import java.time.OffsetDateTime;

public class TransactionEvent {

    private String transactionId;
    private double amount;
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

    public double getAmount() {
        return amount;
    }

    public void setAmount(double amount) {
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
        return OffsetDateTime.parse(timestamp)
                .toInstant()
                .toEpochMilli();
    }
}