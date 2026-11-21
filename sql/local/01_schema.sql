-- Local credentials are passed by Compose; this file contains no passwords.
CREATE ROLE capstone_analyst NOLOGIN;
CREATE ROLE ingest_writer NOLOGIN;
CREATE ROLE catalog_writer NOLOGIN;
CREATE SCHEMA analytics;
CREATE SCHEMA ingestion;
CREATE SCHEMA iceberg_catalog;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA analytics, ingestion, iceberg_catalog FROM PUBLIC;
CREATE TABLE ingestion.events (
  transaction_id text PRIMARY KEY, event_time timestamptz NOT NULL,
  amount numeric(18,2) NOT NULL CHECK(amount >= 0), payment_method text NOT NULL,
  status text NOT NULL, arrival_timestamp timestamptz NOT NULL,
  inserted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  eligible boolean NOT NULL
);
CREATE TABLE ingestion.offsets (shard_id text PRIMARY KEY, sequence_number text NOT NULL);
CREATE TABLE ingestion.watermark (singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), max_event_time timestamptz);
INSERT INTO ingestion.watermark VALUES (true, NULL);
CREATE MATERIALIZED VIEW analytics.approved_per_minute AS
 SELECT date_trunc('minute', event_time AT TIME ZONE 'UTC') AS window_start,
 payment_method, count(*)::bigint AS transaction_count,
 sum(amount)::numeric(38,2) AS total_amount,
 avg(amount::numeric(24,6))::numeric(38,6) AS average_amount
 FROM ingestion.events WHERE status='approved' AND eligible
 GROUP BY 1,2;
CREATE UNIQUE INDEX approved_minute_key ON analytics.approved_per_minute(window_start,payment_method);
CREATE VIEW analytics.ingest_health AS SELECT count(*) AS event_count,
 max(arrival_timestamp) AS latest_arrival,
 max(inserted_at) AS latest_insert,
 max(extract(epoch FROM inserted_at-arrival_timestamp)) AS max_ingest_lag_seconds,
 extract(epoch FROM clock_timestamp()-max(inserted_at)) AS freshness_seconds
 FROM ingestion.events;
CREATE VIEW analytics.recent_events AS SELECT transaction_id,event_time,amount,payment_method,status,arrival_timestamp,inserted_at,eligible FROM ingestion.events;
GRANT USAGE ON SCHEMA analytics TO capstone_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO capstone_analyst;
GRANT USAGE ON SCHEMA ingestion,analytics TO ingest_writer;
GRANT SELECT,INSERT,UPDATE ON ALL TABLES IN SCHEMA ingestion TO ingest_writer;
-- Refresh needs MV ownership. The login inherits this owner role.
ALTER MATERIALIZED VIEW analytics.approved_per_minute OWNER TO ingest_writer;
GRANT USAGE,CREATE ON SCHEMA iceberg_catalog TO catalog_writer;
