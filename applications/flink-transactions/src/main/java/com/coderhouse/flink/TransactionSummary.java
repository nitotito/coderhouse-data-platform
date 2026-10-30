package com.coderhouse.flink;

public class TransactionSummary {

    public String paymentMethod;
    public long windowStart;
    public long windowEnd;
    public long count;
    public double totalAmount;
    public double averageAmount;

    public TransactionSummary() {
    }

    public TransactionSummary(
            String paymentMethod,
            long windowStart,
            long windowEnd,
            long count,
            double totalAmount) {

        this.paymentMethod = paymentMethod;
        this.windowStart = windowStart;
        this.windowEnd = windowEnd;
        this.count = count;
        this.totalAmount = totalAmount;
        this.averageAmount = count == 0 ? 0 : totalAmount / count;
    }
}