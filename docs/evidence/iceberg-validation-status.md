# Evidencias Pre-entrega 5

Validaciones locales y lecturas AWS realizadas el 02–03/11/2026, hora Argentina.
No se ejecutó terraform apply ni se publicaron objetos S3; Flink no se inició.

| Archivo | Evidencia real |
|---|---|
| iceberg-plan.txt | Plan remoto: 2 altas, 2 cambios en sitio, 0 eliminaciones |
| iceberg-terraform-validate.txt | Configuración Terraform válida |
| iceberg-build.txt | Salida del build final Maven: BUILD SUCCESS |
| iceberg-tests.txt | 7 tests, 0 fallos, 0 errores, 0 omitidos |
| iceberg-jar-inspection.txt | Clases del JAR y versión SDK verificadas |
| iceberg-jar-sha256.txt | SHA256 del artefacto local, excluido de Git |
| iceberg-aws-flink-before.json | READY, FLINK-2_2, checkpoints 60000 ms, paralelismo 1 |
| iceberg-aws-versioning.json | Versionado S3 Enabled |
| iceberg-glue-access.txt | AccessDenied real del operador al consultar Glue |

La prueba IcebergCheckpointTest ejecuta un MiniCluster Flink local, escribe 12
filas a Parquet y comprueba snapshots de commits periódicos además del cierre
del flujo acotado. Usa HadoopTables y un filesystem temporal de pruebas;
no usa Glue, S3, Kinesis ni Athena. El filesystem evita depender de winutils.exe
en Windows. Hadoop puede registrar advertencias de librería nativa/HADOOP_HOME;
un checkpoint disparado durante el cierre puede ser rechazado con task is closing.
Los resultados finales y las aserciones de snapshots/filas son exitosos.

TransactionPipelineTest comprueba precisión decimal, promedios, validación JSON,
timestamps, merge, particionado, desbordamiento y carga de GlueCatalog junto con
clientes SDK Glue/S3/Kinesis sin ejecutar peticiones AWS. Esta última prueba
detectó y permitió corregir la falta del transporte HTTP Apache5.

El build final no presenta clases duplicadas reportadas por Shade. Las advertencias
restantes corresponden a recursos compartidos como licencias, manifiestos y
metadatos Maven. La inspección también verifica exclusión de Flink core/Table.

IAM Policy Autopilot 0.4.0 se ejecutó contra IcebergLakehouse.java con región
us-east-1, cuenta 672049777597 y service hints glue/s3; devolvió Policies vacío
porque los accesos SDK están encapsulados por las librerías Iceberg, no escritos
directamente en ese archivo. La política de ejecución declara explícitamente las
operaciones de GlueCatalog/S3FileIO y sus recursos; no se subió ninguna política
desde esa herramienta.

Pendientes: autorización de despliegue/costos, permisos Glue del operador,
comprobar/importar la base si ya existe, crear tabla al arrancar el job, comprobar
commits/metadata_location en Glue, archivos Iceberg en S3, resultados Athena y
logs de concurrencia durante el ensayo. No hay capturas AWS de estos pendientes.
El runbook está en ../iceberg-deployment.md y las consultas en ../iceberg-validation.sql.
