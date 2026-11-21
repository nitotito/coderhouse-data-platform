# Capstone local: instrucciones para el auditor

Este laboratorio reemplaza el alcance AWS del plan preliminar. No utiliza perfiles
ni monta `~/.aws`. Los endpoints y nombres se configuran en Compose mediante
variables; `local/example.env` documenta sus valores locales predeterminados.
LocalStack 4.12.0 está fijado para permitir el laboratorio sin token; no se presenta
como emulación completa de garantías o autorización de AWS.
El emulador legado no conserva tags iniciales del stream con el proveedor probado;
`enable_resource_tags=false` se usa exclusivamente en la raíz local. AWS mantiene
el valor predeterminado true; no se oculta drift mediante ignore_changes.

## Arranque desde cero

Requisitos: Docker Desktop con contenedores Linux, Compose v2, Internet para la
primera construcción y memoria suficiente para LocalStack, Flink y PostgreSQL.
No requiere Java, Maven, Terraform ni Python instalados en el host: se construyen
y ejecutan en imágenes. Ejecutar desde la raíz:

```powershell
docker compose up -d --build
docker compose ps -a
docker compose logs terraform
docker compose --profile tools run --rm audit
```

Terraform debe terminar con código 0. El job debe estar RUNNING en localhost:8081.
El auditor guarda recibos y resultados en `docs/evidence/capstone/local/`.
Se conserva el offset junto con los eventos en la misma transacción de PostgreSQL.
El primer ID válido gana; repetirlo no incrementa las métricas. Los IDs deben ser
inmutables. Flink mantiene IDs en estado checkpointed sin TTL: costo de estado
creciente, a dimensionar antes de producción. Un arranque sin checkpoint compatible
sobre una tabla existente puede reprocesar ventanas: no es una restauración segura.

## Consultas y seguridad SQL

```powershell
docker compose exec postgres psql -U analyst_app -d capstone -f /docker-entrypoint-initdb.d/validate.sql
```

La conexión por socket local puede usar trust para usuarios locales; para validar
contraseñas y acceso de aplicación, el auditor usa conexión TCP con analyst_app.
El rol puede leer `analytics`, pero no `ingestion.offsets` ni `iceberg_catalog`.
La prueba automatizada exige esa denegación. El consumidor no es superusuario.
El catálogo JDBC usa otra identidad y un esquema separado. Credenciales de ejemplo
son exclusivas de una red local, nunca secretas ni válidas para AWS. Puertos del
host publicados únicamente en 127.0.0.1. LocalStack no prueba IAM productivo.

## Semántica equivalente

Flink filtra aprobados, deduplica por transaction_id y agrega por minuto UTC y
payment_method. Watermark: máximo Event Time observado menos 10 s menos 1 ms;
ventana de 60 s y sin allowed lateness. PostgreSQL conserva eventos válidos únicos,
marca elegibilidad temporal y materializa solamente aprobados elegibles.
El consumidor actual recorre shards; la prueba controlada usa una misma partition
key y paralelismo 1. No se afirma equivalencia general bajo intercalaciones diferentes
entre múltiples shards o paralelismos: antes de escalar, centralizar decisiones
aceptado/tardío en Flink o transportar sus agregados al destino analítico.

El fixture incluye duplicados, rechazo, JSON inválido, fuera de orden y un tardío
publicado después de confirmar el cierre en Iceberg. Se comparan conteo, suma y
promedio de la misma ventana, no filas raw contra agregados. DuckDB lee el puntero
actual del catálogo JDBC y los manifests/parquet de S3; no una copia CSV.
Freshness = ahora menos última inserción; lag = inserted_at menos el timestamp
aproximado de llegada a Kinesis. Event Time del productor es otra magnitud.

## Ciclo de vida y estado

El estado local de Terraform se conserva en `terraform/local` (ignorado por Git).
El estado remoto S3 y locking de AWS siguen definidos en `terraform/bootstrap`
y `terraform/isolated`; no deben apuntarse a LocalStack ni a dev por accidente.
Un laboratorio personal puede usar estado local; un equipo debe separar backend,
credenciales y locking, y no versionar tfstate. No ejecutar dos applies simultáneos.

`docker compose stop` detiene cómputo conservando contenedores y volúmenes.
`docker compose down` retira contenedores/red y conserva PostgreSQL/checkpoints.
LocalStack sin persistencia configurada pierde recursos al recrear su contenedor;
por eso no se debe confundir un down/up con restauración del entorno completo.
Para un ensayo nuevo: retirar únicamente este proyecto, limpiar su estado local
y sus volúmenes deliberadamente, y repetir el arranque. Nunca borrar estados dev.

## Dimensionamiento y fallos

Dos shards separan capacidad y permiten analizar distribución; paralelismo 1 deja
la prueba determinista, con cuatro slots disponibles para el job y sinks. Retención
24 h limita la ventana de recuperación. En AWS dimensionar con tamaño medio,
registros/s y bytes/s por shard; una partition key caliente no se corrige sumando
shards si su hash sigue concentrado. Vigilar IteratorAge, throttling y registros
leídos/escritos. Saturación sostenida puede superar la retención y perder datos.

El consumidor PostgreSQL y Flink son lectores independientes. Un bloqueo en
PostgreSQL reduce la lectura de ESE consumidor y aumenta su lag; no genera una
presión directa sobre Flink ni sobre el productor de Kinesis. Un S3 lento sí frena
el sink de Flink, propaga backpressure a sus operadores y fuente, retrasa checkpoints
y aumenta el atraso del lector Flink. Kinesis desacopla ambos mediante retención.

Refresco local cada 2 s, secuencial; una falla persistente aborta el proceso y Compose lo reinicia con on-failure. La transacción conserva offsets solo tras persistir eventos. En producción:
reintentos acotados con backoff/jitter para fallos transitorios, alertas por atraso y
refresh > frecuencia objetivo; no reintentar indefinidamente errores de esquema.
Para Redshift iniciar con refresco manual supervisado y habilitar AUTO REFRESH solo
tras medir costo, freshness y ausencia de errores de parseo en carga representativa.

## Paso a AWS

Cambiar endpoint local por resolución regional; credenciales estáticas de prueba
por roles IAM/STS; JDBC por GlueCatalog; cluster Docker por Managed Flink; PostgreSQL
por Redshift Streaming Ingestion. Conservamos módulos AWS para validate, no apply.
El diseño de idempotencia de PostgreSQL no se traslada automáticamente a una MV
raw de Redshift: requiere una capa por ID y la misma política temporal de Flink.
Los permisos productivos ya están acotados a recursos y prefijos; las operaciones
Describe que AWS solo permite con Resource * deben justificarse individualmente.
No se declara IAM de producción validado por la emulación local.

## Generación del documento

El texto vigente está en `docs/capstone-daat-local.md`. El constructor
`python scripts/build-capstone-pdf.py` usa automáticamente la evidencia local
cuando está presente. Dependencias de edición: reportlab, pymupdf y pypdf.
Genera `output/pdf/Nicolas_Lopez_Capstone_RealTime.pdf`. No declarar listo el PDF
hasta incorporar las tres capturas originales y revisarlas visualmente;
`pdf-status.json` registra ese estado separado del resultado de las pruebas.

## Prueba real de recuperación

Después de un audit exitoso:

```powershell
docker compose --profile tools run --rm audit python /repo/scripts/local-recovery.py before
docker compose restart taskmanager consumer
docker compose --profile tools run --rm audit python /repo/scripts/local-recovery.py after
```

Exige un checkpoint restaurado en el mismo job y reproduce un ID ya procesado.
El resultado de ambas capas debe permanecer 3 / 33.06 / 11.020000. No demuestra
recuperación del JobManager sin HA, ni pérdida completa de discos del host.

Para verificar nuevamente desde cero, `python scripts/local-clean-start.py` retira
**solo el proyecto Compose actual**, sus volúmenes y sus dos archivos tfstate
locales; conserva evidencia anterior en development-run. Este comando elimina
datos del laboratorio y no debe usarse para restaurar un job existente.
