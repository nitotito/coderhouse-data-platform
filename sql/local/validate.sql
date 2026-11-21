SELECT * FROM analytics.recent_events ORDER BY arrival_timestamp,transaction_id;
SELECT * FROM analytics.approved_per_minute ORDER BY window_start,payment_method;
SELECT * FROM analytics.ingest_health;
SELECT current_user, pg_has_role(current_user,'capstone_analyst','member') AS analyst_member;
-- Must fail when connected as analyst_app:
-- SELECT * FROM ingestion.offsets;
