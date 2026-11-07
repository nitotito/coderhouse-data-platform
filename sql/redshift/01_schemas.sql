-- Execute as deployment owner, database analytics, region us-east-1.
-- No CREATE EXTERNAL DATABASE: Glue already exists and remains Terraform-owned.
SET timezone TO 'UTC';
CREATE SCHEMA IF NOT EXISTS streaming;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE EXTERNAL SCHEMA IF NOT EXISTS kinesis_source
FROM KINESIS IAM_ROLE default REGION 'us-east-1';
CREATE EXTERNAL SCHEMA IF NOT EXISTS lakehouse
FROM DATA CATALOG DATABASE 'lakehouse_db'
IAM_ROLE default REGION 'us-east-1';
