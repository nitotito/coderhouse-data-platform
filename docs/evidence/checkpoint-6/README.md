# Evidencias checkpoint 6

Estado: **PRUEBA FUNCIONAL Y SEGURIDAD PASSED en AWS el 07/11/2026**.
RunId `pe6_20261107_033721`. El usuario autorizó un único ensayo y el retiro
posterior de todos los recursos del módulo temporal.

Los JSON del preflight son respuestas reales de APIs (o errores de acceso).
`terraform-plan.txt` corresponde al plan real: 8 altas, sin cambios ni bajas.
`terraform-apply-second.txt` acredita las ocho altas exitosas. El primer apply
falló por permisos antes de crear recursos y queda como antecedente.
`local-validation.json` separa comprobaciones locales y estado del ensayo AWS.

## Resultados reales

| Evidencia | Resultado |
|---|---|
| [test-summary.json](test-summary.json) | PASSED: métricas, errores de entrada y JOIN |
| [Lote y recibos Kinesis](pe6_20261107_033721-events.json) | Un solo envío de nueve registros |
| [Filas tipadas](004-typed-results.json) | Ocho JSON con ID del ensayo; cinco campos extraídos |
| [Métricas](005-metrics-results.json) | Count 3, aprobadas 2, rechazada 1, total 1029.30, aprobado 30.30 |
| [JOIN Iceberg](006-iceberg-join-results.json) | Una fila: 2/2 aprobadas, 30.30/30.30, diferencias cero |
| [Estado streaming](008-monitor-1-results.json) | Progreso real de escaneo del stream |
| [Errores de escaneo](009-monitor-2-results.json) | Cero filas del origen en la observación |
| [Refresco](010-monitor-3-results.json) | Manual, incremental, exitoso; 9.735348 s |
| [Conteo raw](012-monitor-5-results.json) | Nueve registros almacenados |
| [Calidad](013-monitor-6-results.json) | Seis válidos, tres inválidos clasificados |
| [security-summary.json](security-summary.json) | Identidad analista comprobada, métricas/JOIN permitidos, raw/REFRESH denegados |
| [Workgroup desplegado](deployed-workgroup.json) | AVAILABLE, base y máximo 4 RPU, acceso privado |
| [Uso observado](001-serverless-usage-results.json) | Muestra SYS_SERVERLESS_USAGE; no factura definitiva |
| [Plan de retiro inicial](initial-terraform-cleanup-plan.txt) | Solo ocho bajas de module.redshift[0] |
| [Retiro](cleanup-summary.json) | Alcance auditado y estado de ejecución |
| [Verificación final AWS](cleanup-verification.json) | PASSED: no quedan recursos temporales y las fuentes anteriores siguen intactas |

El primer retiro eliminó siete recursos y falló al listar perfiles del rol IAM.
ListRolePolicies/ListAttachedRolePolicies devolvieron listas vacías; DeleteRole
del rol exacto fue exitoso y GetRole devolvió NoSuchEntity. Se sincronizó Terraform
con un segundo plan/apply sin cambios de recursos. Los logs iniciales se conservan
con prefijo initial-. La política propuesta incorpora el permiso de listado para
reproducir el retiro con Terraform sin ese ajuste manual. No hace falta ampliar
el acceso ahora: el ensayo ya fue retirado.

La ingesta nueva incluyó event time actual y una muestra con event time histórico
para conciliar con el snapshot PE5 de solo lectura. Flink no se inició. No es una
nueva validación de escritura Flink ni una medida de refresco automático.
Los archivos de ejecución incluyen SQL, ID, estado y usuario de Data API. Los
errores de desarrollo y las denegaciones esperadas se conservan; sus FAILED no
invalidan el PASSED del ensayo final. El JSON original last-failure documenta
el primer intento de asumir el rol, anterior a la corrección por ExternalId.

## Capturas reales de consola incorporadas

El propietario autorizó una segunda sesión breve y guardó tres capturas reales,
revisadas visualmente e incorporadas al PDF. Incluyen el SQL, la base analytics y
las grillas de resultados:

- [Eventos](redshift-eventos.png): cinco campos JSON y seis filas válidas.
- [Métricas](redshift-metricas.png): dos ventanas, cantidades e importes esperados.
- [JOIN](redshift-join.png): una fila conciliada, 2/2 aprobadas y diferencias cero.

El usuario SQL de consola fue IAM:RootIdentity, con checkpoint6_analyst. Los nueve
registros se recuperaron de la retención Kinesis; no se reenviaron. Los originales
PNG no se editaron. Las vistas ampliadas del PDF son recortes de visualización
del original, no imágenes sintéticas. Plan, apply, consultas y retiro de esta
sesión se guardan en `capture-session/`.

Las siguientes son capturas adicionales opcionales; las tres exigidas de resultados
ya están guardadas. No se vuelve a desplegar para obtener más sin autorización.

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

## Antecedentes de permisos

ListWorkgroups (Serverless), DescribeClusters (provisionado) y KMS DescribeKey
fueron inicialmente AccessDenied con terraform-dev y luego habilitados.
Data API también requiere ExecuteStatement/DescribeStatement/GetStatementResult/
CancelStatement y GetCredentials del workgroup, además de privilegios SQL reales.
Se comprobó su funcionamiento durante el ensayo. La confianza de ejecución SQL
usa el ExternalId Serverless documentado; los contextos globales se validan si
están presentes. USAGE en lakehouse fue necesario para el JOIN del analista.
