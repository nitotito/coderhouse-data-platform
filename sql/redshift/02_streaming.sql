-- Exactly one base MV consumes the existing stream. Refresh is explicitly manual.
-- Keep invalid JSON bytes for diagnostics; CASE guards JSON_PARSE.
-- Business conversions are downstream, so a bad amount cannot block ingestion.
CREATE MATERIALIZED VIEW streaming.transactions_raw
AUTO REFRESH NO AS
SELECT approximate_arrival_timestamp, refresh_time, partition_key,
       shard_id, sequence_number, kinesis_data,
       CAN_JSON_PARSE(kinesis_data) AS valid_json,
       CASE WHEN CAN_JSON_PARSE(kinesis_data)
            THEN JSON_PARSE(kinesis_data) ELSE NULL END AS payload
FROM kinesis_source."dev-transactions-stream";
