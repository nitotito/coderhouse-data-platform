# Despliegue y prueba AWS — Pre-entrega 5

Estado: **desplegado y validado en AWS el 04/11/2026**. El ensayo
`pe5_20261104_113142` obtuvo en Athena cantidad 2, total 30.30 y promedio
15.150000; checkpoint 2 y snapshot 8171898520026477263. Flink fue detenido y
confirmado READY a las 08:36 de Argentina. Terraform terminó sin diferencias.
El despliegue y los costos habían sido autorizados por el propietario.

Evidencia: [evidence/iceberg-validation-status.md](evidence/iceberg-validation-status.md).
Para repetir con costos autorizados, después de las verificaciones de este
procedimiento, usar `powershell -NoProfile -File scripts/iceberg-aws-smoke.ps1 -Run`.
El script valida los resultados y detiene Flink mediante finally.

### Desbloqueo del operador

La propuesta adicional está en [iceberg-operator-access.json](iceberg-operator-access.json).
Concede acceso a la base `lakehouse_db`, lectura de su única tabla de agregados,
consultas en el workgroup Athena `primary`, lectura de los datos y escritura del
JAR 1.1.0/resultados de Athena en prefijos específicos, publicación de eventos
controlados y lectura de logs. No concede administración IAM ni permisos globales
de Glue/Athena/S3. Complementa los permisos Terraform/Flink existentes.
Fue adjuntada por el propietario como política administrada y sus accesos fueron
comprobados con el despliegue y las consultas. No se ejecutó AWS Access Analyzer.

Crear una política administrada por el cliente, no una política insertada: el
JSON ocupa 3129 caracteres sin espacios y supera el límite agregado de 2048
para políticas insertadas de un usuario. Cabe en el límite de 6144 por política
administrada. Dividirlo en varias insertadas no evita el límite agregado.

Un administrador de la cuenta puede crearla en IAM > Políticas y adjuntarla al usuario `terraform-dev`,
o ejecutar desde la raíz del repositorio con **su perfil administrativo real**:

```powershell
# Reemplazar PERFIL_ADMIN por un perfil administrativo ya autorizado.
aws iam create-policy --policy-name CoderhouseLakehouseDelivery --policy-document file://docs/iceberg-operator-access.json --profile PERFIL_ADMIN
aws iam attach-user-policy --user-name terraform-dev --policy-arn arn:aws:iam::672049777597:policy/CoderhouseLakehouseDelivery --profile PERFIL_ADMIN
powershell -NoProfile -File scripts/iceberg-preflight.ps1
```

No configurar credenciales de administrador dentro del repositorio ni compartirlas
por chat. La política no elimina posibles restricciones de boundaries, SCP o Lake
Formation; si existen, también requieren revisión administrativa. El preflight
guarda las respuestas reales en `docs/evidence/iceberg-aws-preflight.json`.
`ABSENT` para la base permite su creación posterior por Terraform; `BLOCKED`
requiere corregir permisos antes de iniciar servicios o subir el JAR.

La sesión IAM abierta en Chrome se identificó en el inventario de ventanas,
pero el acceso a esa aplicación mediante Computer Use no fue aprobado. No se
interactuó con la consola ni se guardaron cambios de permisos desde el navegador.

Referencias: [permisos Glue y sus ancestros](https://docs.aws.amazon.com/athena/latest/ug/fine-grained-access-to-glue-resources.html)
y [acciones Athena por workgroup](https://docs.aws.amazon.com/service-authorization/latest/reference/list_athena.html).

## Permisos del operador

Además de los permisos ya utilizados por Terraform, el operador necesita acceso
a Glue para consultar/crear/actualizar `lakehouse_db`, sus etiquetas y tablas;
a IAM para adjuntar la política al rol existente; y a Managed Flink para actualizar,
iniciar, describir y detener la aplicación. Para las pruebas necesita publicar en
el stream existente, leer logs, ejecutar/consultar/cancelar consultas Athena y
leer datos y escribir resultados bajo `athena-results/` del bucket existente.
Si Lake Formation administra la ubicación o el catálogo, revisar también sus
grants antes del despliegue. La política del **job** está en
`modules/managed-flink/lakehouse.tf`; no concede administración de bases de datos
porque esa función pertenece a Terraform. No agregar `glue:*` ni `s3:*`.

Antes de aplicar, un operador autorizado debe comprobar si la base ya existe.
Si existe fuera del estado, importarla en lugar de recrearla:

```powershell
aws glue get-database --name lakehouse_db --profile coderhouse-dev --region us-east-1
# Solo si existe y no está administrada por este estado:
terraform -chdir=environments/dev import module.lakehouse.aws_glue_catalog_database.lakehouse 672049777597:lakehouse_db
```

La importación cambia el estado. En esta entrega no fue necesaria: se comprobó
EntityNotFound antes de crear la base con Terraform.

## Validaciones locales

Desde la raíz, en PowerShell:

```powershell
terraform fmt -check -recursive
terraform -chdir=environments/dev init
terraform -chdir=environments/dev validate
mvn -B -ntp -f applications/flink-transactions/pom.xml clean package
python scripts/verify-iceberg-jar.py
powershell -NoProfile -File scripts/iceberg-test-events.ps1
```

`environments/dev/flink.auto.tfvars` local contiene `enable_ingestion = true`.
Está excluido de Git. Al clonar, pasar **siempre** `-var='enable_ingestion=true'`
en el plan de esta entrega para conservar Kinesis y Flink. No reutilizar planes
antiguos de limpieza. Nunca ejecutar destroy para esta entrega.

## Después de aprobación: publicar JAR y aplicar

Se utiliza una clave nueva para conservar el JAR 1.0.0 de la Pre-entrega 4.
No sobrescribir esa clave anterior. Registrar la versión y el checksum del nuevo
objeto; no volver a subir builds distintos bajo la misma versión de entrega.

```powershell
aws s3 cp applications/flink-transactions/target/flink-transactions-1.1.0.jar s3://coderhouse-data-lake-672049777597/artifacts/flink/flink-transactions-1.1.0.jar --profile coderhouse-dev --region us-east-1
aws s3api head-object --bucket coderhouse-data-lake-672049777597 --key artifacts/flink/flink-transactions-1.1.0.jar --profile coderhouse-dev --region us-east-1
terraform -chdir=environments/dev plan -var='enable_ingestion=true' -out='iceberg.tfplan'
terraform -chdir=environments/dev show -no-color iceberg.tfplan
# Continuar únicamente con plan revisado, sin eliminaciones ni reemplazos.
terraform -chdir=environments/dev apply iceberg.tfplan
```

El plan de revisión guardado localmente se generó con `-lock=false` para evitar
escribir locks durante la inspección. En el despliegue regenerar con locking
normal y revisar nuevamente. El despliegue se completó sin eliminaciones;
el plan final es No changes. Consultar las evidencias de plan/apply antes de
intentar repetir cambios ya aplicados.

## Arrancar y enviar el lote controlado

El acumulador cambia de double a BigDecimal: los snapshots de la versión 1.0.0
no se consideran compatibles. Esta prueba de laboratorio arranca sin restaurar
esos snapshots. Para producción se necesita una migración de estado o un punto
de inicio explícito con estrategia de deduplicación. TRIM_HORIZON relee eventos
retenidos; no ejecutar dos escritores del mismo pipeline para este ensayo.

```powershell
$runConfig = @{ ApplicationRestoreConfiguration = @{ ApplicationRestoreType = 'SKIP_RESTORE_FROM_SNAPSHOT' } }
$runConfig | ConvertTo-Json -Depth 5 | Set-Content -Encoding ascii applications/flink-transactions/target/iceberg-run.json
aws kinesisanalyticsv2 start-application --application-name coderhouse-dev-transactions-flink --run-configuration file://applications/flink-transactions/target/iceberg-run.json --profile coderhouse-dev --region us-east-1
aws kinesisanalyticsv2 describe-application --application-name coderhouse-dev-transactions-flink --profile coderhouse-dev --region us-east-1 --query 'ApplicationDetail.ApplicationStatus'
# Esperar RUNNING antes de enviar. Ejecutar en un laboratorio sin otros productores.
powershell -NoProfile -File scripts/iceberg-test-events.ps1 -Send
```

El script imprime un RunId y su resultado esperado: una fila con el método
`card_<RunId>`, cantidad 2, total 30.30 y promedio 15.150000. El marcador
rechazado avanza el watermark 75 segundos respecto del inicio de ventana;
puede hacer tardíos otros eventos del laboratorio. Todos los registros de la
prueba usan una misma partition key para preservar su orden en Kinesis.
La ejecución sin `-Send` solo muestra eventos, no llama a AWS.

Esperar al menos dos checkpoints de 60 segundos **después** del cierre de la
ventana. Si no aparecen resultados, revisar watermarks, logs y checkpoints;
el silencio de un stream por sí solo no garantiza cerrar su última ventana.

## Glue, S3, Athena y evidencia

```powershell
aws glue get-table --database-name lakehouse_db --name transaction_aggregates --profile coderhouse-dev --region us-east-1 --query 'Table.{Name:Name,Parameters:Parameters,Location:StorageDescriptor.Location}' > docs/evidence/iceberg-glue-table.json
aws s3 ls s3://coderhouse-data-lake-672049777597/lakehouse/lakehouse_db/transaction_aggregates/ --recursive --profile coderhouse-dev > docs/evidence/iceberg-s3-objects.txt
aws athena get-work-group --work-group primary --profile coderhouse-dev --region us-east-1 --query 'WorkGroup.Configuration'
```

Verificar `table_type=ICEBERG`, `metadata_location` apuntando a un JSON existente
y objetos `data/*.parquet` y `metadata/`. Descargar el JSON indicado por
`metadata_location` mediante `aws s3 cp <URI> docs/evidence/iceberg-metadata.json
--profile coderhouse-dev`. No inventar el nombre del objeto.

Usar Athena **engine 3**, catálogo `AwsDataCatalog`. Si el workgroup `primary`
no permite engine 3 o impone otro bucket de resultados, elegir un workgroup
aprobado y su ubicación real. Consultas preparadas en `docs/iceberg-validation.sql`.
Ejemplo de ejecución, reemplazando RunId:

```powershell
$sql = "SELECT * FROM lakehouse_db.transaction_aggregates WHERE payment_method = 'card_REPLACE_RUN_ID'"
$queryId = aws athena start-query-execution --query-string $sql --query-execution-context Database=lakehouse_db,Catalog=AwsDataCatalog --result-configuration OutputLocation=s3://coderhouse-data-lake-672049777597/athena-results/pre-entrega-5/ --work-group primary --profile coderhouse-dev --region us-east-1 --query QueryExecutionId --output text
aws athena get-query-execution --query-execution-id $queryId --profile coderhouse-dev --region us-east-1
# Esperar SUCCEEDED; FAILED/CANCELLED no constituyen una validación exitosa.
aws athena get-query-results --query-execution-id $queryId --profile coderhouse-dev --region us-east-1 > docs/evidence/iceberg-athena-results.json
aws logs filter-log-events --log-group-name /aws/kinesis-analytics/coderhouse-dev-transactions-flink --filter-pattern ERROR --profile coderhouse-dev --region us-east-1 > docs/evidence/iceberg-errors.json
```

Repetir la ejecución con las consultas `$snapshots` y `$files`. Guardar IDs,
estado final y resultados reales. Verificar en snapshot summary
`flink.max-committed-checkpoint-id`; comparar metadata_location antes/después
de un commit y corroborar checkpoints completados en el dashboard de Flink.
Delimitar temporalmente la revisión de errores al ensayo; confirmar ausencia
de `CommitFailedException`/conflictos en ese intervalo. Una ejecución sin
errores no prueba ausencia de conflictos bajo cualquier concurrencia futura.
Las capturas de Glue, S3 y Athena se agregan solo después de observarlas.

## Detener al finalizar, incluso si falla la prueba

```powershell
aws kinesisanalyticsv2 stop-application --application-name coderhouse-dev-transactions-flink --profile coderhouse-dev --region us-east-1
aws kinesisanalyticsv2 describe-application --application-name coderhouse-dev-transactions-flink --profile coderhouse-dev --region us-east-1 --query 'ApplicationDetail.ApplicationStatus'
# Esperar READY y guardar la salida. No destruir los recursos compartidos.
```

Detener Flink no elimina el costo provisionado de los dos shards de Kinesis,
ni almacenamiento/versiones S3, Glue, consultas Athena y logs. El intervalo de
checkpoint limita latencia de visibilidad, pero cada commit puede crear archivos
pequeños aun con target de 128 MiB. Planificar compactación y expiración de
snapshots por separado; no ejecutar limpiezas durante la prueba.
