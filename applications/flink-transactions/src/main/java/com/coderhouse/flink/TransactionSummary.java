package com.coderhouse.flink;

import java.math.BigDecimal;
import java.math.RoundingMode;

public class TransactionSummary {

    public String paymentMethod;
    public long windowStart;
    public long windowEnd;
    public long count;
    public BigDecimal totalAmount;
    public BigDecimal averageAmount;

    public TransactionSummary() {
    }

    public TransactionSummary(
            String paymentMethod,
            long windowStart,
            long windowEnd,
            long count,
            BigDecimal totalAmount) {

        this.paymentMethod = paymentMethod;
        this.windowStart = windowStart;
        this.windowEnd = windowEnd;
        this.count = count;
        this.totalAmount = totalAmount;
        this.averageAmount = count == 0 ? BigDecimal.ZERO.setScale(6) : totalAmount.divide(BigDecimal.valueOf(count), 6, RoundingMode.HALF_UP);
    }
}