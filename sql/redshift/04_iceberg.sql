-- Iceberg contains approved aggregates, NOT individual transactions.
-- Both sides are collapsed to exactly one row per UTC minute/payment method.
-- Historical duplicates are summed, not hidden: drift should expose replay.
-- Late data and Flink watermark/checkpoint timing can temporarily cause drift.
CREATE OR REPLACE VIEW analytics.recent_vs_iceberg AS
WITH recent AS (
  SELECT DATE_TRUNC('minute',event_time) AS window_start, payment_method,
         COUNT(*) AS approved_count, SUM(amount) AS approved_amount
  FROM analytics.transactions_typed
  WHERE validation_error IS NULL AND status='approved'
  GROUP BY 1,2
), historical AS (
  SELECT window_start, payment_method,
         SUM(transaction_count) AS approved_count, SUM(total_amount) AS approved_amount
  FROM lakehouse.transaction_aggregates
  GROUP BY 1,2
)
SELECT r.window_start, r.payment_method,
       r.approved_count AS recent_approved_count,
       h.approved_count AS iceberg_approved_count,
       r.approved_amount AS recent_approved_amount,
       h.approved_amount AS iceberg_approved_amount,
       r.approved_count-h.approved_count AS count_difference,
       r.approved_amount-h.approved_amount AS amount_difference
FROM recent r JOIN historical h
ON r.window_start=h.window_start AND r.payment_method=h.payment_method
WITH NO SCHEMA BINDING;
