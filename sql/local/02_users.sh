#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
 -v ingest_password="$INGEST_PASSWORD" -v catalog_password="$CATALOG_PASSWORD" -v analyst_password="$ANALYST_PASSWORD" <<'SQL'
CREATE USER ingest_app PASSWORD :'ingest_password' IN ROLE ingest_writer;
CREATE USER catalog_app PASSWORD :'catalog_password' IN ROLE catalog_writer;
ALTER ROLE catalog_app SET search_path TO iceberg_catalog;
CREATE USER analyst_app PASSWORD :'analyst_password' IN ROLE capstone_analyst;
SQL
