-- Athena engine 3, catalog AwsDataCatalog. Replace the run ID from the producer.
SELECT window_start, window_end, payment_method, transaction_count, total_amount, average_amount
FROM lakehouse_db.transaction_aggregates
WHERE window_start >= TIMESTAMP '2026-11-02 00:00:00'
  AND window_start < TIMESTAMP '2026-11-03 00:00:00'
ORDER BY window_start, payment_method;

SELECT * FROM lakehouse_db.transaction_aggregates
WHERE payment_method = 'card_REPLACE_RUN_ID';
-- Expected for a fresh run: exactly one row, count=2, total=30.30, average=15.150000.

SELECT committed_at, snapshot_id, operation, summary
FROM "lakehouse_db"."transaction_aggregates$snapshots"
ORDER BY committed_at DESC;

SELECT file_path, file_format, record_count, file_size_in_bytes
FROM "lakehouse_db"."transaction_aggregates$files";

-- Replay detection: append mode can produce repeated aggregates.
SELECT window_start, payment_method, COUNT(*) AS copies
FROM lakehouse_db.transaction_aggregates
GROUP BY window_start, payment_method HAVING COUNT(*) > 1;
