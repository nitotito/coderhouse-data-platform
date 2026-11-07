-- Run once as owner. AWS IAM role grants service access; this DB role grants SQL.
CREATE ROLE checkpoint6_analyst;
REVOKE ALL ON SCHEMA streaming FROM PUBLIC;
REVOKE ALL ON SCHEMA analytics FROM PUBLIC;
REVOKE ALL ON SCHEMA kinesis_source FROM PUBLIC;
REVOKE ALL ON SCHEMA lakehouse FROM PUBLIC;
GRANT USAGE ON SCHEMA analytics TO ROLE checkpoint6_analyst;
GRANT SELECT ON analytics.transactions_typed TO ROLE checkpoint6_analyst;
GRANT SELECT ON analytics.transactions_per_minute TO ROLE checkpoint6_analyst;
GRANT SELECT ON analytics.recent_vs_iceberg TO ROLE checkpoint6_analyst;
-- Analyst cannot refresh MVs, create schemas, read raw bytes, or assume IAM role.
-- Explicitly bind a real authenticated DB identity after approving membership:
-- GRANT ROLE checkpoint6_analyst TO "IAM:analyst-name";
