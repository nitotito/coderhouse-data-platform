CREATE TEMP TABLE pe6_raw_fixture (approximate_arrival_timestamp timestamp, refresh_time timestamp,shard_id varchar(128),sequence_number varchar(128),valid_json boolean,payload SUPER);

INSERT INTO pe6_raw_fixture VALUES (GETDATE(),GETDATE(),'fixture','iso-z',true,JSON_PARSE('{"transaction_id": "iso-z", "payment_method": "card", "status": "approved", "timestamp": "2026-11-11T15:00:00Z", "amount": "10.01"}'));

INSERT INTO pe6_raw_fixture VALUES (GETDATE(),GETDATE(),'fixture','iso-offset',true,JSON_PARSE('{"transaction_id": "iso-offset", "payment_method": "card", "status": "approved", "timestamp": "2026-11-11T12:00:00-03:00", "amount": "10.00"}'));

INSERT INTO pe6_raw_fixture VALUES (GETDATE(),GETDATE(),'fixture','epoch-ms',true,JSON_PARSE('{"transaction_id": "epoch-ms", "payment_method": "card", "status": "approved", "timestamp": "1794409200000", "amount": "10.00"}'));

INSERT INTO pe6_raw_fixture VALUES (GETDATE(),GETDATE(),'fixture','bad-date',true,JSON_PARSE('{"transaction_id": "bad-date", "payment_method": "card", "status": "approved", "timestamp": "2026-02-30T15:00:00Z", "amount": "1.00"}'));

INSERT INTO pe6_raw_fixture VALUES (GETDATE(),GETDATE(),'fixture','no-timezone',true,JSON_PARSE('{"transaction_id": "no-timezone", "payment_method": "card", "status": "approved", "timestamp": "2026-11-11T15:00:00", "amount": "1.00"}'));

INSERT INTO pe6_raw_fixture VALUES (GETDATE(),GETDATE(),'fixture','empty-time',true,JSON_PARSE('{"transaction_id": "empty-time", "payment_method": "card", "status": "approved", "timestamp": "", "amount": "1.00"}'));

INSERT INTO pe6_raw_fixture VALUES (GETDATE(),GETDATE(),'fixture','missing-time',true,JSON_PARSE('{"transaction_id": "missing-time", "payment_method": "card", "status": "approved", "amount": "1.00"}'));

INSERT INTO pe6_raw_fixture VALUES (GETDATE(),GETDATE(),'fixture','bad-money',true,JSON_PARSE('{"transaction_id": "bad-money", "payment_method": "card", "status": "approved", "timestamp": "2026-11-11T15:00:00Z", "amount": "bad"}'));

INSERT INTO pe6_raw_fixture VALUES (GETDATE(),GETDATE(),'fixture','missing-money',true,JSON_PARSE('{"transaction_id": "missing-money", "payment_method": "card", "status": "approved", "timestamp": "2026-11-11T15:00:00Z"}'));

WITH fields AS (
  SELECT approximate_arrival_timestamp, refresh_time, shard_id, sequence_number,
         valid_json,
         NULLIF(TRIM(payload.transaction_id::varchar), '') AS transaction_id,
         NULLIF(TRIM(payload.payment_method::varchar), '') AS payment_method,
         LOWER(NULLIF(TRIM(payload.status::varchar), '')) AS status,
         NULLIF(TRIM(payload.amount::varchar), '') AS amount_text,
         NULLIF(TRIM(payload."timestamp"::varchar), '') AS timestamp_text
  FROM pe6_raw_fixture
), converted AS (
  SELECT *, TRY_CAST(amount_text AS decimal(20,4)) AS precise_amount,
         CASE WHEN timestamp_text ~ '^[0-9]{13}$'
              THEN DATEADD(millisecond, MOD(TRY_CAST(timestamp_text AS bigint),86400000)::integer,
                   DATEADD(day, (TRY_CAST(timestamp_text AS bigint)/86400000)::integer,
                           TIMESTAMP '1970-01-01 00:00:00'))
              WHEN timestamp_text ~ (
                   '^[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}'
                   || '([.][0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})$')
              THEN TRY_CAST(timestamp_text AS timestamptz) AT TIME ZONE 'UTC'
              ELSE NULL
         END AS event_time
  FROM fields
)
SELECT approximate_arrival_timestamp, refresh_time, shard_id, sequence_number,
       transaction_id, payment_method, status, event_time,
       TRY_CAST(precise_amount AS decimal(18,2)) AS amount,
       CASE WHEN NOT valid_json THEN 'invalid_json'
            WHEN transaction_id IS NULL OR payment_method IS NULL OR status IS NULL
              THEN 'missing_required_field'
            WHEN amount_text IS NULL
              OR NOT (amount_text ~ '^[0-9]+([.][0-9]{1,2})?$')
              OR precise_amount IS NULL OR precise_amount < 0
              OR precise_amount <> ROUND(precise_amount,2)
              OR TRY_CAST(precise_amount AS decimal(18,2)) IS NULL THEN 'invalid_amount'
            WHEN event_time IS NULL THEN 'invalid_timestamp'
            ELSE NULL END AS validation_error,
       approximate_arrival_timestamp AS arrival_timestamp
FROM converted ORDER BY transaction_id;
