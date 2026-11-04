# Evidencias Pre-entrega 5 — validación final

**Resultado: PASSED en AWS el 04/11/2026. Flink terminó detenido en READY.**

## Ajuste a la estructura literal de la consigna

La configuración ahora está en `infra/main.tf` y `infra/modules/`; la aplicación,
el pom.xml y las pruebas están en `app/flink-transactions/`. La clave del backend
sigue siendo `environments/dev/terraform.tfstate`. No se migró el estado ni se
modificaron recursos AWS. Las listas de direcciones antes/después coinciden y el
plan desde infra/ devolvió No changes (exit code 0). Las siete pruebas volvieron
a pasar desde app/.

Evidencias adicionales: [plan tras el traslado](iceberg-layout-plan.txt),
[tests tras el traslado](iceberg-layout-tests.txt),
[direcciones anteriores](iceberg-state-addresses-before-layout.txt) y
[direcciones posteriores](iceberg-state-addresses-after-layout.txt).

La consigna original exige una captura de consola Glue. **Esa imagen está
pendiente**; las evidencias API prueban el pipeline pero no sustituyen el requisito
visual. Ver [la guía de captura](../glue-screenshots.md). El PR debe permanecer en
borrador hasta incorporar la captura real.

## Resultado de negocio observado

RunId: `pe5_20261104_113142`.

| Campo | Resultado Athena |
|---|---|
| window_start | 2026-11-04 11:33:00 UTC |
| window_end | 2026-11-04 11:34:00 UTC |
| payment_method | card_pe5_20261104_113142 |
| transaction_count | 2 |
| total_amount | 30.30 |
| average_amount | 15.150000 |

Se publicaron cuatro eventos Kinesis con la misma partition key: dos aprobados,
uno rechazado por 999.00 y un marcador rechazado de importe cero que avanzó el
watermark. La fila única devuelta por Athena refleja exclusivamente los dos
aprobados. Ventana local de Argentina: 08:33–08:34 del 04/11/2026.

## Infraestructura y transacción observadas

- Base Glue: `lakehouse_db`; tabla `transaction_aggregates`, `table_type=ICEBERG`.
- Iceberg format-version: 2; archivos Parquet, manifests y JSON de metadatos en S3.
- Partición real: `window_start_day=2026-11-04`, transformación `day(window_start)`.
- Archivo de datos: 1 fila agregada, 2101 bytes, formato PARQUET.
- Checkpoints 1 y 2 completados en CloudWatch. El primero no tenía datos;
  el segundo confirmó el snapshot `8171898520026477263`.
- Snapshot summary: `flink.max-committed-checkpoint-id=2`, engine Flink 2.2.1,
  Iceberg 1.12.0, total-records=1, total-data-files=1.
- Glue metadata_location cambió de `00000-270ceb65-5454-460a-9fa4-175dd5d9040e.metadata.json`
  a `00001-a6ac508c-2e43-4de5-9437-57f0bb426279.metadata.json`.
- Consultas Athena de datos, snapshots y archivos: SUCCEEDED, engine 3.
- Logs entre inicio del ensayo y consulta final: 0 eventos ERROR; ningún
  conflicto de commit observado. No es una prueba de carga ni de múltiples writers.
- Flink se detuvo al finalizar; READY confirmado el 04/11/2026 11:36:14 UTC
  (08:36:14 Argentina). Plan final Terraform: No changes, exit code 0.

## Evidencias reales

| Archivo | Evidencia |
|---|---|
| [iceberg-aws-test-summary.json](iceberg-aws-test-summary.json) | Resumen automatizado PASSED, fila esperada, snapshot/checkpoint y READY final |
| [iceberg-kinesis-test-events.txt](iceberg-kinesis-test-events.txt) | Eventos enviados y cuatro respuestas Kinesis con sequence numbers |
| [iceberg-glue-before-events.json](iceberg-glue-before-events.json) | Tabla y metadata_location antes del lote |
| [iceberg-glue-table.json](iceberg-glue-table.json) | Tabla y metadata_location después del commit |
| [iceberg-metadata.json](iceberg-metadata.json) | JSON Iceberg real descargado desde S3 |
| [iceberg-checkpoint-logs.json](iceberg-checkpoint-logs.json) | CloudWatch: checkpoints completados y estado del committer |
| [iceberg-s3-objects.json](iceberg-s3-objects.json) | Inventario S3 de Parquet, manifests y metadatos |
| [iceberg-athena-validation-execution.json](iceberg-athena-validation-execution.json) | Consulta 578d831f-7595-43c3-8c20-e7716ebd1307: SUCCEEDED |
| [iceberg-athena-validation-results.json](iceberg-athena-validation-results.json) | Fila real con cantidad 2, total 30.30 y promedio 15.150000 |
| [iceberg-athena-snapshots-execution.json](iceberg-athena-snapshots-execution.json) | Consulta 22697474-f58a-4600-803d-ed36bf490f0e: SUCCEEDED |
| [iceberg-athena-snapshots-results.json](iceberg-athena-snapshots-results.json) | Snapshot y summary consultados por Athena |
| [iceberg-athena-files-execution.json](iceberg-athena-files-execution.json) | Consulta 206f0429-3e36-4aed-9a6a-4eb61a15c843: SUCCEEDED |
| [iceberg-athena-files-results.json](iceberg-athena-files-results.json) | Ruta y tamaño reales del archivo Parquet |
| [iceberg-errors.json](iceberg-errors.json) | Revisión CloudWatch del intervalo: events vacío |
| [iceberg-aws-flink-running.json](iceberg-aws-flink-running.json) | RUNNING, runtime y configuración desplegada |
| [iceberg-aws-flink-after.json](iceberg-aws-flink-after.json) | READY al finalizar |
| [iceberg-deployed-artifact.json](iceberg-deployed-artifact.json) | Versión del JAR en S3, tamaño y SHA256 registrado |
| [iceberg-deployment-plan.txt](iceberg-deployment-plan.txt) | Plan regenerado antes del apply final: 2 altas, 1 cambio, 0 bajas |
| [iceberg-apply-success.txt](iceberg-apply-success.txt) | Apply final completado: 2 added, 1 changed, 0 destroyed |
| [iceberg-final-plan.txt](iceberg-final-plan.txt) | Plan posterior: No changes |
| [iceberg-tests.txt](iceberg-tests.txt) | 7 pruebas locales, 0 fallos, 0 errores |
| [iceberg-build.txt](iceberg-build.txt) | Maven clean package: BUILD SUCCESS |
| [iceberg-jar-inspection.txt](iceberg-jar-inspection.txt) | Clases requeridas y SDK verificados |

Los archivos de descripción de Flink omiten el ConditionalToken de concurrencia,
que no es necesario para la entrega. No contienen credenciales ni enlaces firmados.
Las evidencias son respuestas reales de APIs/consultas, no capturas simuladas.
No se pudieron obtener capturas de consola: Computer Use no pudo determinar la
URL de Chrome con suficiente confianza para aplicar sus controles.

## Validación local y antecedentes

Las siete pruebas incluyen precisión monetaria, validación JSON, timestamps,
merge, partición diaria, desbordamiento decimal, carga de clientes SDK sin llamadas
AWS y un MiniCluster que escribe doce filas Parquet con snapshots de checkpoints.
La prueba local utiliza un filesystem temporal adaptado a Windows. Hadoop puede
registrar warnings de winutils/HADOOP_HOME; los tests terminan exitosamente.

Los primeros intentos estaban bloqueados por Glue/Athena y por el permiso de tags
sobre el catálogo padre. El propietario habilitó una política administrada acotada;
no se quitaron permisos existentes. El primer apply solo actualizó la lectura del
JAR; el apply final creó la base y la política lakehouse y actualizó Flink. El total
incluye esos dos cambios en sitio y dos recursos nuevos, sin bajas ni reemplazos.
Los archivos iceberg-glue-access.txt, iceberg-apply-attempt.txt e iceberg-plan.txt
conservan esos antecedentes. No representan el estado final.

El despliegue/costos fueron autorizados antes de ejecutarse. El script
`../../scripts/iceberg-aws-smoke.ps1` usa finally para detener Flink incluso ante
fallos. Los dos shards Kinesis y el almacenamiento S3 permanecen desplegados y
pueden seguir generando cargos. No se ejecutó destroy ni se realizó merge a main.

No quedan verificaciones técnicas de esta prueba pendientes. El merge del
[PR #1](https://github.com/nitotito/coderhouse-data-platform/pull/1) requiere la
aprobación del propietario. No se afirma deduplicación de replays ni exactamente
una vez de extremo a extremo para nuevas ejecuciones sin restauración de estado.
