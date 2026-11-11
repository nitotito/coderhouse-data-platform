-- Manual sequence: publish test records, refresh once, query; no one-second loop.
REFRESH MATERIALIZED VIEW streaming.transactions_raw;
SELECT transaction_id,event_time,amount,payment_method,status,validation_error
FROM analytics.transactions_typed ORDER BY approximate_arrival_timestamp DESC LIMIT 20;
SELECT * FROM analytics.transactions_per_minute ORDER BY window_start DESC LIMIT 20;
SELECT * FROM lakehouse.transaction_aggregates
WHERE window_start >= TIMESTAMP '2026-11-04 00:00:00'
  AND window_start < TIMESTAMP '2026-11-05 00:00:00';
-- A comparison, not a UNION of overlapping histories; do not add the two totals.
SELECT * FROM analytics.recent_vs_iceberg ORDER BY window_start DESC LIMIT 20;
SELECT * FROM svv_role_grants WHERE role_name='checkpoint6_analyst';
SELECT * FROM svv_relation_privileges WHERE identity_name='checkpoint6_analyst';
