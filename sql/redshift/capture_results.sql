-- Segunda sesion autorizada: consultas para capturas reales de Query Editor v2.
-- Workgroup coderhouse-dev-analytics; database analytics; region us-east-1.
-- Ejecutar cada SELECT por separado y capturar SQL + grilla de resultados.

-- 0. Identidad de conexion (util para conceder el rol al usuario exacto).
SELECT current_user AS db_user;

-- 1. Eventos procedentes de Kinesis: cinco campos JSON extraidos y tipados.
SELECT transaction_id, event_time, amount, payment_method, status
FROM analytics.transactions_typed
WHERE validation_error IS NULL
ORDER BY payment_method, event_time;

-- 2. Metricas por minuto y metodo de pago.
SELECT window_start, payment_method, transaction_count,
       total_amount, average_amount, approved_count, rejected_count, approved_amount
FROM analytics.transactions_per_minute
ORDER BY window_start DESC;

-- 3. JOIN: una fila por minuto/metodo; aprobadas e importes conciliados.
SELECT window_start, payment_method,
       recent_approved_count, iceberg_approved_count,
       recent_approved_amount, iceberg_approved_amount,
       count_difference, amount_difference
FROM analytics.recent_vs_iceberg;

-- 4. Opcional: lectura historica directa de Iceberg mediante Glue.
SELECT window_start, window_end, payment_method, transaction_count,
       total_amount, average_amount
FROM lakehouse.transaction_aggregates
WHERE payment_method='card_pe5_20261104_113142';

-- 5. Opcional: visible al propietario del refresco o superusuario SQL.
-- Otra identidad puede obtener cero filas por visibilidad de las tablas SYS.
SELECT mv_name, refresh_type, status, start_time, end_time, duration
FROM sys_mv_refresh_history
WHERE schema_name='streaming'
ORDER BY start_time DESC LIMIT 5;
