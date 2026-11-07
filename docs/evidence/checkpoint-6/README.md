# Evidencias checkpoint 6

Estado: **PREPARADO, NO DESPLEGADO**. No hay resultados Redshift exitosos todavía.

Los JSON del preflight son respuestas reales de APIs (o errores de acceso).
`terraform-plan.txt` corresponde al plan real: 8 altas, sin cambios ni bajas.
`local-validation.json` registra solo validaciones locales, no consultas al motor.

## Capturas pendientes después del despliegue autorizado

1. `01-workgroup.png`: consola Redshift Serverless, workgroup y namespace
   coderhouse-dev-analytics, 4 RPU, estado disponible y acceso privado.
2. `02-streaming-mv.png`: Query Editor v2, definición/esquema de
   streaming.transactions_raw y su origen kinesis_source.dev-transactions-stream.
3. `03-events.png`: SELECT de transaction_id, amount, status, payment_method,
   event_time en analytics.transactions_typed con los IDs del ensayo.
4. `04-metrics.png`: SELECT analytics.transactions_per_minute, resultado del lote.
5. `05-iceberg-join.png`: SELECT analytics.recent_vs_iceberg, fila de conciliación.
6. `06-monitoring.png`: SYS_MV_REFRESH_HISTORY y SYS_STREAM_SCAN_STATES del ensayo.
7. `07-security.png`: grants y consulta del analista, más un acceso raw denegado.
8. Glue: captura existente [PE5](../glue-transaction-aggregates.png), fecha original;
   opcional captura nueva del mismo esquema sin modificar la tabla.

Mantener SQL y resultados legibles en cada captura. No incluir claves, tokens o
contraseñas. Los JSON de Data API complementan, no reemplazan capturas reales.
No se fabrican capturas ni se presenta el plan como evidencia de recursos creados.

## Permisos que faltan

ListWorkgroups (Serverless), DescribeClusters (provisionado) y KMS DescribeKey
fueron AccessDenied con terraform-dev. Preparar un acceso acotado antes de desplegar.
Data API también requiere ExecuteStatement/DescribeStatement/GetStatementResult/
CancelStatement y GetCredentials del workgroup, además de privilegios SQL reales.
Crear permisos no está incluido en una autorización de lectura del inventario.
