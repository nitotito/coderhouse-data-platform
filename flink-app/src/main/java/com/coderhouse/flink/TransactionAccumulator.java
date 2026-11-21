package com.coderhouse.flink;

import java.math.BigDecimal;

public class TransactionAccumulator {
    public long count = 0;
    public BigDecimal totalAmount = BigDecimal.ZERO;
}