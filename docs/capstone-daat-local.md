# Arquitectura y auditoría del pipeline local de transacciones

Autor: Nicolás López. Destinatario: evaluación final de Data Engineering.
Fecha de ejecución: 20 de noviembre de 2026 en Argentina, 21 de noviembre en UTC.

## Alcance y conclusión

El laboratorio despliega infraestructura emulada con Terraform y ejecuta Flink,
PostgreSQL, un consumidor de Kinesis y consultas DuckDB sobre Iceberg. No requiere
cuenta AWS. La prueba con estado vacío creó 20 recursos de LocalStack; un segundo
plan terminó sin cambios. Un lote nuevo llegó a ambos destinos y produjo las
mismas métricas después de deduplicar, filtrar aprobados y aplicar la política
temporal. El reinicio de un TaskManager restauró un checkpoint y conservó el
resultado al repetir un identificador.

Las capturas de las preentregas AWS no se presentan como evidencia de este ensayo.
Las definiciones AWS se validaron estáticamente, sin apply ni consultas cloud.
La emulación no demuestra capacidad, aislamiento de red o enforcement IAM de AWS.

## Arquitectura y responsabilidades

El productor publica JSON en Kinesis de LocalStack. Flink valida, deduplica por
transaction_id, asigna Event Time y watermarks, filtra aprobados y agrega ventanas
de un minuto. Iceberg confirma archivos Parquet y metadatos JSON en S3 durante
los checkpoints. El catálogo JDBC mantiene el puntero de metadatos en un esquema
separado de PostgreSQL. DuckDB resuelve ese puntero y lee la tabla Iceberg real.

En una ruta independiente, ingest-consumer lee Kinesis mediante polling, valida
los eventos y guarda IDs únicos y offsets en una misma transacción PostgreSQL.
Una vista materializada agrupa aprobados temporalmente elegibles. Firehose entrega
una copia bronze sin transformar a otro prefijo S3. Terraform crea VPC, subredes,
rutas, endpoint S3, bucket protegido, stream, rol Firehose, logs y alarmas emulados.
Los contenedores se comunican por la red de Compose; la VPC emulada no transporta
ese tráfico ni prueba aislamiento equivalente al de una VPC real.

## Repositorio y estructura

[Repositorio](https://github.com/nitotito/coderhouse-data-platform).
La implementación local se desarrolla en la rama feature/capstone-local.
docker-compose.yml está en la raíz; terraform/local reutiliza los módulos de
network y kinesis; flink-app contiene el job Java; ingest-consumer contiene el
lector Python; sql/local contiene esquemas, roles, vista y validaciones.
local contiene Dockerfiles y example.env. scripts/local-e2e.py automatiza la
conciliación; local-recovery.py comprueba restauración y duplicados.

Las preentregas aprobadas se conservan como antecedentes. sql/redshift contiene
la implementación AWS anterior. El runbook AWS preliminar no es una instrucción
para ejecutar esta entrega local. La guía operativa vigente es capstone-local.md.

## Despliegue reproducible y ciclo de vida

Requisito del host: Docker con contenedores Linux, Compose v2 e Internet durante
la primera construcción. Maven y Terraform se ejecutan dentro de imágenes; el
auditor no necesita instalar sus versiones en el host para el arranque normal.

```powershell
docker compose up -d --build
docker compose ps -a
docker compose logs terraform
docker compose --profile tools run --rm audit
```

Compose espera salud de LocalStack/PostgreSQL y apply exitoso antes de iniciar
Flink y el consumidor. La imagen Flink compila el JAR desde fuentes. PostgreSQL
ejecuta su inicialización al crear un volumen vacío. El contenedor Terraform
ejecuta tflocal init y apply sin pasos manuales de creación de recursos.

El ensayo limpio eliminó únicamente el proyecto Compose y su estado local,
incluidos sus volúmenes. clean-precondition.json prueba ausencia del tfstate
local; clean-compose-up.txt y clean-terraform-apply.txt conservan los recibos.
La comprobación posterior exige No changes y código 0 de plan -detailed-exitcode.
El script local-clean-start.py reproduce ese reset deliberado. No se usa para
recuperar un job con datos existentes ni borra estados de las preentregas.

stop conserva contenedores y volúmenes; down retira contenedores/red. LocalStack
no tiene persistencia configurada en este laboratorio, por lo que recrearlo
pierde sus recursos emulados. Conservar solo PostgreSQL y checkpoints no equivale
a restaurar toda la plataforma. Un ensayo nuevo requiere estado local coherente.

## Configuración y dimensionamiento

| Parámetro | Valor local | Motivo y límite |
|---|---|---|
| Shards | 2 | Permite analizar particionado; el fixture usa una sola partition key |
| Retención | 24 horas | Ventana de recuperación limitada; medir el atraso máximo |
| Paralelismo Flink | 1 | Orden reproducible para el ensayo; no benchmark de capacidad |
| Slots TaskManager | 4 | Margen para operadores y sink del job |
| Checkpoints | 5000 ms | Commits observables en una prueba breve; AWS parte de 60 s |
| Watermark | 10 s de desorden | Máximo Event Time observado menos 10 s menos 1 ms |
| Idleness | 30 s | En el operador posterior a la fuente, no garantía por shard |
| Ventana | 60 s UTC | Agregación por método de pago y minuto |
| Refresco PostgreSQL | 2 s | Secuencial; no promesa de latencia bajo saturación |
| Iceberg | v2 y Parquet | Compresión Snappy y partición day(window_start) |

Los nombres, región, credenciales locales y puertos tienen variables de Compose;
local/example.env documenta sus valores. Las variables Terraform reciben los
mismos nombres. No se montan perfiles reales ni se usan IDs de una cuenta AWS.
La cuenta 000000000000 es la identidad del emulador con credenciales test.

En AWS, dimensionar con registros/s, bytes/s, tamaño medio y concentración por
partition key. Dos shards no eliminan una clave caliente. Retención, intervalos
de checkpoint, paralelismo y archivos pequeños afectan costo y recuperación.
El laboratorio no consume recursos AWS; tampoco demuestra costo cero de los
recursos históricos de una cuenta que no se inspeccionó en esta sesión.

## Temporalidad y política de eventos

timestamp es Event Time del productor, expresado como ISO con zona o epoch ms.
arrival_timestamp proviene de ApproximateArrivalTimestamp de Kinesis; inserted_at
se mide en PostgreSQL. Separar estas tres magnitudes evita confundir antigüedad
del evento con atraso de ingesta. Se rechazan JSON inválido, campos ausentes,
fechas inválidas, timestamps sin zona, importes negativos y fracciones de centavo.

La ventana emite cuando su fin queda detrás del watermark. Un evento fuera de
orden dentro de una ventana abierta cuenta; un evento para una ventana ya cerrada
va al side output LATE_EVENTS y al log LATE_DROPPED. El contador late_records
permite observarlo. No se configura allowed lateness ni corrección retrospectiva.
La partición diaria de Iceberg permite descartar días en consultas con filtros
temporales, sin crear una partición por método de pago y minuto.

## Idempotencia y garantías reales

El primer evento válido por transaction_id gana; el contrato exige IDs inmutables.
Flink conserva IDs en ValueState checkpointed, sin TTL. PostgreSQL tiene una clave
primaria y ON CONFLICT DO NOTHING. Repetir un ID no incrementa el agregado.
Offsets y eventos se confirman juntos en PostgreSQL: un fallo antes del commit
permite releer; un fallo después no duplica el efecto de negocio.

En Flink, EXACTLY_ONCE se refiere a estado, offsets y coordinación del sink con
checkpoints compatibles. No significa una transacción distribuida entre Iceberg
y PostgreSQL, ni visibilidad simultánea. La deduplicación de negocio es adicional.
Sin TTL, el estado de IDs crece; un despliegue productivo necesita horizonte de
replay, retención de IDs y política de correcciones explícitos. Arrancar un job
nuevo desde TRIM_HORIZON sobre una tabla existente sin restaurar estado puede
volver a insertar agregados. Ese procedimiento no es una recuperación válida.

## Prueba de consistencia entre destinos

El run local_20261121_014317 publicó diez registros con una partition key común:
tres aprobados únicos, un duplicado, un rechazo, un JSON inválido, dos avances
temporales y un aprobado tardío; también repitió el primer ID después del commit.
El conjunto válido único inicial fue de siete eventos. El tardío se publicó
después de observar el cierre y commit de la ventana Iceberg, no por una espera
arbitraria. La prueba de recuperación añadió otro duplicado y un avance rechazado.

La comparación usa la ventana UTC 2026-11-21 01:43 y el mismo payment_method.
Los importes aprobados elegibles son 10.01, 20.02 y 3.03. Rechazos, duplicados,
JSON inválido y el aprobado tardío de 1000 no deben incrementar el agregado.

| Destino | Cantidad | Suma | Promedio |
|---|---|---|---|
| PostgreSQL MV | 3 | 33.06 | 11.020000 |
| DuckDB sobre Iceberg | 3 | 33.06 | 11.020000 |
| Diferencia | 0 | 0.00 | 0.000000 |

Se conservaron fixture, secuencias de publicación, eventos PostgreSQL, métricas,
puntero JDBC, metadatos Iceberg y respuestas REST de Flink. DuckDB ejecutó
iceberg_scan sobre metadatos y Parquet en S3 de LocalStack. No se comparó un CSV
exportado ni se reutilizó un snapshot de una preentrega.

El consumidor replica el criterio temporal usando su máximo Event Time visto.
La prueba verifica equivalencia con una clave y paralelismo 1. Intercalaciones
distintas entre shards, pausas o paralelismos pueden producir decisiones temporales
distintas entre lectores. Antes de escalar, transportar decisiones o agregados
emitidos por Flink al destino analítico para tener una única autoridad temporal.
No se afirma consistencia general para esas intercalaciones no probadas.

## Observabilidad y resultados medidos

La consulta de salud inicial observó lag máximo de ingesta de 0.228648 s y freshness
de 8.919828 s al tomar la muestra. Son medidas de este lote local pequeño, no SLA,
percentiles ni tiempos garantizados de producción. Freshness crece al dejar de
publicar; el fixture usa Event Time adelantado para cerrar ventanas, por lo que
no debe medirse freshness como ahora menos timestamp del productor.

Flink tenía siete checkpoints completados al cerrar el primer audit limpio.
Se guardaron conteos, duración y checkpoint restaurado mediante REST. La muestra
de millisBehindLatest por shard fue 0 y no observó backpressure sostenido.
Las métricas de validación, duplicados, tardíos y watermark se conservan con su
contexto de operador. No se inyectó saturación de shards ni lentitud de S3.
Firehose produjo cuatro objetos bronze en la observación realizada después del
lote y la recuperación. Su archivo es independiente de la tabla Iceberg.

## Recuperación comprobada y límites

Se guardó el checkpoint antes del fallo y se reiniciaron solo TaskManager y
consumidor. El mismo job 84f02cc5f39aabd690f3543ef130f57e restauró el checkpoint 7
desde el volumen compartido. Se repitió un ID y se publicó otro avance temporal.
Ambos destinos conservaron una sola fila agregada con 3 / 33.06 / 11.020000.
recovery-before.json y recovery-after.json registran el resultado real.

El reinicio no prueba HA del JobManager, pérdida completa del disco del host,
restauración de Managed Flink, resharding ni recuperación ante pérdida del catálogo.
Para esos escenarios hacen falta almacenamiento durable, checkpoints externos,
HA, backups del catálogo y ensayos de desastre separados. Los 11 tests Java
incluyen estado temporal, deduplicación y commits Iceberg con recuperación local;
los tres tests Python cubren fechas, precisión monetaria y metadatos evolutivos.

## Backpressure y análisis de fallos

Un S3 lento puede frenar el writer Iceberg, llenar buffers y propagar backpressure
hacia los operadores y la fuente Flink. Aumentan lag y duración de checkpoints;
si vence el timeout pueden ocurrir reintentos desde el último checkpoint válido.
El productor sigue publicando hasta los límites de Kinesis. La retención desacopla
temporalmente las velocidades, pero no ofrece un buffer infinito.

Un bloqueo PostgreSQL frena su consumidor, no directamente el pipeline Flink.
Vigilar el diferencial arrival_timestamp/inserted_at, offsets, freshness y fallos
de refresh. Para un shard saturado, observar throttling y millisBehindLatest;
corregir concentración de claves, capacidad o lectores antes de superar 24 horas
de retención. Aumentar paralelismo sin capacidad de origen o destino no resuelve
la causa. Los análisis de saturación son escenarios razonados, no pruebas ejecutadas.

## Seguridad y límites de la emulación

analytics es legible solo por capstone_analyst y sus miembros. analyst_app no es
superusuario y no puede leer ingestion.offsets; la prueba TCP comprobó pertenencia
y denegación real. ingest_app recibe ingest_writer y permisos limitados sobre
eventos, offsets, watermark y la MV. catalog_app tiene un esquema distinto para
el catálogo JDBC. El administrador PostgreSQL solo se usa en la inicialización.
Las contraseñas de ejemplo se inyectan por configuración y solo sirven en local.

El bucket tiene versionado, AES256 y bloqueo público declarados. El rol Firehose
usa permisos sobre el stream y bucket/prefijo concretos. LocalStack no demuestra
la aplicación real de IAM ni de cifrado gestionado. Las definiciones AWS existentes
de Glue, Managed Flink y Redshift pasaron terraform validate; validate no prueba
permisos efectivos, cuotas ni conectividad. No se amplió una política productiva.

Las etiquetas del stream se desactivan únicamente en la raíz local porque la
versión fijada del emulador no las conserva al crear el recurso con el proveedor
probado. La opción tiene default true en el módulo para AWS. No se usó
ignore_changes para ocultar diferencias: el segundo plan local terminó sin cambios.

## Estado Terraform y paso a AWS

La raíz local usa tfstate local ignorado por Git. No se publican estados, planes
binarios ni secretos. Para un equipo, el backend S3 versionado y locking de las
raíces bootstrap/isolated permiten separar cuentas/entornos y evitar applies
simultáneos. La raíz del módulo hijo no determina el backend de la raíz que lo llama;
terraform validate de isolated informa esa advertencia esperada, no un error.

El paso a AWS requiere endpoints regionales, credenciales temporales mediante
roles IAM, catálogo Glue en vez de JDBC y ejecución del JAR en Managed Flink.
Redshift Streaming Ingestion reemplaza al consumidor/PostgreSQL. La MV raw y una
capa de deduplicación/transformación deben conservar las reglas de negocio y
temporalidad; el SQL histórico de Redshift no adquiere automáticamente la política
local de IDs y tardíos. IAM debe revisarse para las llamadas efectivas y cada
recurso, con excepciones Resource * solo para acciones que AWS no permita acotar.

La frecuencia local de refresh es 2 s. En producción se propone refresco
supervisado inicialmente, con reintentos acotados y backoff para errores transitorios,
alerta por atraso y detención ante errores de esquema/casting. AUTO REFRESH de
Redshift se habilitaría después de medir freshness, estabilidad y costo bajo carga.
No se probó AUTO REFRESH en este laboratorio ni se autorizó un despliegue cloud.

## Evidencia y revisión final

La carpeta docs/evidence/capstone/local contiene el ensayo limpio, el plan sin
cambios, validate local/AWS, fixture y recibos, lectura PostgreSQL/DuckDB,
metadatos Iceberg, checkpoints, recuperación, membresía SQL, denegación de acceso,
métricas y entrega bronze. Los archivos development-run conservan el ensayo previo
y no sustituyen a la ejecución limpia. verification.json distingue comprobaciones
técnicas aprobadas y disponibilidad de capturas, antes de declarar lista la entrega.

Las tres capturas originales fueron revisadas: mismo job y run del ensayo limpio,
Flink RUNNING con 528 checkpoints completados y 0 fallidos, timestamps PostgreSQL
y resultado DuckDB 3 / 33.06 / 11.020000. La captura PostgreSQL posterior al reinicio
muestra lag máximo 0.315964 s y freshness 2775.53 s por inactividad del productor.
No contradice la muestra inicial ni representa un SLA de procesamiento.
El PDF incluye los originales y una ampliación de checkpoints; sus hashes y la
revisión visual se conservan en screenshots-reviewed.json.

| Original | Comprobación visual | Correspondencia |
|---|---|---|
| flink-checkpoints.png | RUNNING y checkpoints sin fallos | Mismo job y restore del checkpoint 7 |
| postgres.png | Llegada, inserción y vista materializada | Mismo run, tardío excluido y métricas correctas |
| duckdb.png | iceberg_scan y metadata_location real | Mismo run y agregado equivalente |

Referencias técnicas: [JDBC Catalog de Iceberg](https://iceberg.apache.org/docs/latest/jdbc/),
[Kinesis en Flink](https://nightlies.apache.org/flink/flink-docs-stable/docs/connectors/datastream/kinesis/),
[Iceberg en DuckDB](https://duckdb.org/docs/stable/extensions/iceberg/overview),
[imágenes de LocalStack](https://docs.localstack.cloud/aws/customization/other-installations/docker-images/).
Las versiones del laboratorio quedan fijadas en Dockerfiles, Compose y lock HCL;
la documentación latest puede describir versiones posteriores.
