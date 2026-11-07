-- SUPER paths correspond to real transaction JSON, not Java POJO field names.
-- Empty strings are normalized before TRY_CAST. Objects/arrays become NULL.
CREATE OR REPLACE VIEW analytics.transactions_typed AS
WITH fields AS (
  SELECT approximate_arrival_timestamp, refresh_time, shard_id, sequence_number,
         valid_json,
         NULLIF(TRIM(payload.transaction_id::varchar), '') AS transaction_id,
         NULLIF(TRIM(payload.payment_method::varchar), '') AS payment_method,
         LOWER(NULLIF(TRIM(payload.status::varchar), '')) AS status,
         NULLIF(TRIM(payload.amount::varchar), '') AS amount_text,
         NULLIF(TRIM(payload."timestamp"::varchar), '') AS timestamp_text
  FROM streaming.transactions_raw
), converted AS (
  SELECT *, TRY_CAST(amount_text AS decimal(20,4)) AS precise_amount,
         CASE WHEN timestamp_text ~ '^[0-9]{13}$'
              THEN DATEADD(millisecond, MOD(TRY_CAST(timestamp_text AS bigint),86400000)::integer,
                   DATEADD(day, (TRY_CAST(timestamp_text AS bigint)/86400000)::integer,
                           TIMESTAMP '1970-01-01 00:00:00'))
              ELSE TRY_CAST(timestamp_text AS timestamptz) AT TIME ZONE 'UTC'
         END AS event_time
  FROM fields
)
SELECT approximate_arrival_timestamp, refresh_time, shard_id, sequence_number,
       transaction_id, payment_method, status, event_time,
       TRY_CAST(precise_amount AS decimal(18,2)) AS amount,
       CASE WHEN NOT valid_json THEN 'invalid_json'
            WHEN transaction_id IS NULL OR payment_method IS NULL OR status IS NULL
              THEN 'missing_required_field'
            WHEN amount_text !~ '^[0-9]+([.][0-9]{1,2})?$'
              OR precise_amount IS NULL OR precise_amount < 0
              OR precise_amount <> ROUND(precise_amount,2)
              OR TRY_CAST(precise_amount AS decimal(18,2)) IS NULL THEN 'invalid_amount'
            WHEN event_time IS NULL THEN 'invalid_timestamp'
            ELSE NULL END AS validation_error,
       approximate_arrival_timestamp AS arrival_timestamp
FROM converted;

-- Ordinary aggregate view avoids assumptions about incremental eligibility of
-- SUPER extraction/timestamp conversions in a nested MV. Always reads base state.
CREATE OR REPLACE VIEW analytics.transactions_per_minute AS
SELECT DATE_TRUNC('minute',event_time) AS window_start, payment_method,
       COUNT(*) AS transaction_count,
       SUM(amount) AS total_amount,
       -- AVG preserves input scale: widen BEFORE aggregating, not afterwards.
       AVG(amount::decimal(24,6))::decimal(38,6) AS average_amount,
       SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved_count,
       SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS rejected_count,
       SUM(CASE WHEN status='approved' THEN amount ELSE 0 END) AS approved_amount
FROM analytics.transactions_typed
WHERE validation_error IS NULL
GROUP BY 1,2;
