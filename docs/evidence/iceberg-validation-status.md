# Evidencias Pre-entrega 5

Actualización 04/11/2026: el preflight confirmó que los permisos Glue y Athena
adjuntados ya funcionan (base ausente, Athena engine 3 disponible). Se publicó el
JAR 1.1.0 en S3; versión y SHA256 en iceberg-deployed-artifact.json. El plan
revisado siguió siendo 2 altas, 2 cambios, 0 bajas. Apply actualizó la política
de lectura del JAR y se detuvo al crear la base: glue:TagResource requiere también
el ARN del catálogo padre. La propuesta iceberg-operator-access.json ya incluye
esa corrección, pendiente de actualizar en IAM por un administrador. El operador
no tiene iam:GetPolicy. No existe aún lakehouse_db y no se inició Flink.
La salida real está en iceberg-apply-attempt.txt. No reutilizar el plan aplicado
parcialmente: regenerarlo después de corregir los permisos.

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
| iceberg-aws-preflight.json | Reintento autorizado: identidad válida, Glue/Athena bloqueados, Flink READY |

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

El 03/11/2026 el usuario autorizó desplegar y probar con costos, deteniendo Flink
al finalizar. El preflight posterior volvió a encontrar AccessDenied para
glue:GetDatabase y athena:GetWorkGroup. IAM también denegó listar políticas del
usuario y simular sus permisos. Solo se encontró el perfil local coderhouse-dev.
Computer Use no recibió aprobación para acceder a Google Chrome; no se modificó
IAM ni se inició Flink. La propuesta de acceso adicional está en
../iceberg-operator-access.json y aún requiere que la adjunte un administrador.

Pendientes: permisos Glue/Athena del operador,
comprobar/importar la base si ya existe, crear tabla al arrancar el job, comprobar
commits/metadata_location en Glue, archivos Iceberg en S3, resultados Athena y
logs de concurrencia durante el ensayo. No hay capturas AWS de estos pendientes.
El runbook está en ../iceberg-deployment.md y las consultas en ../iceberg-validation.sql.
