-- Serverless-compatible SYS views. Owner sees their own refreshes; superuser all.
SELECT * FROM sys_stream_scan_states
WHERE external_schema_name='kinesis_source' ORDER BY record_time DESC LIMIT 20;
SELECT * FROM sys_stream_scan_errors
WHERE external_schema_name='kinesis_source' ORDER BY record_time DESC LIMIT 20;
SELECT mv_name,refresh_type,status,start_time,end_time,duration
FROM sys_mv_refresh_history
WHERE schema_name='streaming' ORDER BY start_time DESC LIMIT 20;
SELECT * FROM sys_mv_state ORDER BY start_time DESC LIMIT 20;
SELECT COUNT(*) AS stored_records, MAX(approximate_arrival_timestamp) AS last_arrival,
       MAX(refresh_time) AS last_ingest_refresh
FROM streaming.transactions_raw;
SELECT validation_error,COUNT(*) AS records
FROM analytics.transactions_typed GROUP BY 1;
-- refresh_time is refresh start, not record visibility time. Negative values are
-- possible for records arriving during a refresh. Data API observation separately
-- measures upper-bound end-to-end latency; never present this as an SLA.
SELECT shard_id,sequence_number,approximate_arrival_timestamp,refresh_time,
       DATEDIFF(millisecond,approximate_arrival_timestamp,GETDATE()) AS arrival_age_ms
FROM streaming.transactions_raw ORDER BY approximate_arrival_timestamp DESC LIMIT 20;
