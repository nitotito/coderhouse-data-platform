# Revisión de preentrega 6 — 11/11/2026

Estado de ejecución del 11/11/2026: **PASSED en Redshift desde una base limpia**.
Se verificaron las 42 sentencias de SQL01-08, nueve casos de conversión,
ingesta, métricas, JOIN, membresía y permisos efectivos. Las cuatro capturas
actuales están incorporadas al PDF. Los ocho recursos temporales se retiraron:
ausencia comprobada por API y plan final Terraform sin cambios. Los recibos
están en `docs/evidence/checkpoint-6/revision/`.
La evidencia del 07/11/2026 queda como antecedente separado.

El retiro IAM utilizó DeleteRole directo tras confirmar la ausencia del warehouse,
por falta de ListInstanceProfilesForRole en el perfil operador. Se preservaron
el intento Terraform y el recibo IAM; el estado se refrescó y verificó sin ampliar
la política activa del operador. Kinesis, Flink READY y metadatos Iceberg previos
permanecen preservados.

## Respuesta a la devolución

| Observación | Cambio o comprobación |
|---|---|
| payload.bayment_method | El fuente y el anexo usan payment_method; vista creada y consultada en Redshift |
| CTE con llaves | WITH ... AS (...) revisado localmente y ejecutado en Redshift |
| Operador !- | Se reemplaza !~ por NOT (amount_text ~ patrón), más legible y sin ambigüedad visual |
| Timestamp | Epoch de13 dígitos o ISO8601 con zona explícita; TRY_CAST comprueba conversión, salida UTC; faltantes/invalidables se clasifican |
| sys_stream_scan_errorss | La fuente usa SYS_STREAM_SCAN_ERRORS; nombre conservado en el consolidado |
| Tres campos JSON tipados | transactions_typed extrae transaction_id/payment_method/status varchar, amount decimal(18,2), event_time timestamp UTC |
| Membresía analítica | SQL08 crea un usuario SQL sin contraseña, asigna el rol, consulta SVV_USER_GRANTS y cambia a esa identidad para probar lectura |
| PDF | Nombre exacto CheckPoint_Redshift_Lopez_Nicolas.pdf; anexo SQL ampliado y hash del consolidado |

La nueva revisión enlaza fuente, hash, texto del PDF y recibos de ejecución real.
Redshift oculta autenticación/región en los dos CREATE EXTERNAL SCHEMA devueltos:
para esos recibos se compara el prefijo visible, sin afirmar igualdad byte a byte
de lo que el servicio oculta. Las demás sentencias coinciden con el SQL retornado.

## Orden reproducible desde base limpia

Prerrequisito: workgroup temporal autorizado, base analytics vacía, IAM y
endpoint Kinesis configurados, tabla Iceberg PE5 existente. No borrar esquemas
del entorno existente para simular una base limpia. El usuario autorizó esta
sesión de hasta una hora, objetivo USD3 sin tope automático y retiro posterior.

1. Revisar SQL01-08 y regenerar checkpoint_6_complete.sql.
2. En el warehouse temporal, ejecutar setup con --require-clean: consulta
   pg_namespace y rechaza si ya existe algún esquema de la entrega; no hace DROP.
3. Ejecutar la regresión de conversiones con tabla TEMP en una sesión retenida.
   Usa el SELECT real de03_analytics.sql, no una reimplementación de sus reglas.
4. Publicar el lote controlado una sola vez y refrescar la MV manualmente.
5. Consultar eventos tipados y métricas; exigir los valores esperados del fixture.
6. Ejecutar JOIN contra Iceberg y comprobar diferencias cero para la muestra
   histórica. No afirmar que Flink estuvo escribiendo simultáneamente.
7. Asignar rol a usuario SQL de prueba sin contraseña; guardar SVV_USER_GRANTS,
   current_user, SELECT permitido y raw/REFRESH denegados.
8. Capturar resultados actuales y reexportar PDF; después retirar únicamente
   recursos temporales con aprobación y recibos de ausencia.

Comandos preparados; los que llevan --execute requieren autorización AWS:

```powershell
python scripts/redshift-checkpoint6.py
python scripts/redshift-sql-regression.py
python scripts/redshift-checkpoint6.py --execute --setup --require-clean --evidence-dir docs/evidence/checkpoint-6/revision
python scripts/redshift-sql-regression.py --execute
python scripts/redshift-checkpoint6.py --execute --smoke --evidence-dir docs/evidence/checkpoint-6/revision
python scripts/redshift-security-smoke.py --execute --evidence-dir docs/evidence/checkpoint-6/revision
```

Setup y smoke se ejecutan por separado para correr
la regresión entre ambos. Los tres runners
admiten --profile, --region y --workgroup. No reenviar smoke tras un fallo parcial:
conservar recibos e inspeccionar datos existentes antes de reintentar.

Para verificar **todas** las fuentes numeradas desde cero, usar este recorrido
en un warehouse nuevo autorizado (no después de ejecutar setup):

```powershell
python scripts/redshift-checkpoint6.py --execute --setup --require-clean --smoke --full-validation --evidence-dir docs/evidence/checkpoint-6/revision
python scripts/redshift-sql-regression.py --execute
python scripts/redshift-security-smoke.py --execute --evidence-dir docs/evidence/checkpoint-6/revision
```

El primer comando ejecuta SQL01-05, publica el fixture, comprueba métricas/JOIN y
ejecuta todas las sentencias SQL06-08 en una sesión retenida. SQL08 demuestra
GRANT, membresía y usuario efectivo; el runner de seguridad agrega las denegaciones
esperadas sin dejar errores sin manejar en el consolidado. Se guardan respuestas
por sentencia y full-script-summary.json solo si termina correctamente.

La regresión preparada cubre: ISO Z, offset -03:00 equivalente a UTC, epoch ms,
fecha imposible, ausencia de zona, timestamp vacío/faltante e importe inválido/
faltante. Los nueve casos pasaron realmente en Redshift, usando el SELECT de
SQL03 sobre una tabla TEMP. Un parser local por sí solo no prueba ejecución real.

## Evidencia explícita de membresía

Después del GRANT y antes de cambiar de usuario:

```sql
SELECT user_name,role_name,admin_option
FROM svv_user_grants
WHERE user_name='checkpoint6_access_test'
  AND role_name='checkpoint6_analyst';
```

Se espera exactamente una fila. Luego current_user debe identificar al usuario
de prueba y sus permisos efectivos deben permitir las vistas pero denegar raw y
REFRESH. La prueba de API usa checkpoint6_access_test. La identidad de consola
confirmada fue IAM:RootIdentity y recibió solo el rol SQL analítico, sin admin_option;
su captura demuestra esa membresía, separada de los privilegios IAM de la cuenta.

## Política de refresco de producción propuesta

Para este ensayo académico: AUTO REFRESH NO, un REFRESH explícito después de
publicar el lote, y comprobación de SYS_MV_REFRESH_HISTORY/scan states antes de
consultar. No ejecutar refrescos simultáneos desde dos mecanismos.

En producción con control de frecuencia/costo: mantener AUTO REFRESH NO y un
orquestador externo cada60 segundos. Conservar el statement_id; si un refresco
anterior está en curso, omitir el tick. Ante timeout de cliente, consultar ese ID
antes de crear otra sentencia. Reintentar únicamente fallos transitorios
(throttling/indisponibilidad) hasta3 veces, backoff5/15/30 segundos con jitter.
No reintentar indefinidamente sintaxis, permisos, cast o referencias inexistentes:
detener programación y alertar. Medir duración/estado y frescura con eventos
nuevos, no solo edad de la última llegada cuando el stream está inactivo.

Habilitar AUTO REFRESH YES solamente tras validar en el workgroup/región su
comportamiento, frescura objetivo y costo durante una ventana observada;
deshabilitarlo con AUTO REFRESH NO ante errores persistentes, gasto inesperado,
fin de prueba o al habilitar el orquestador. AUTO REFRESH no es un SLA de60 s.
El orquestador y su política son una propuesta documentada, no recursos desplegados.

Fuentes: [TRY_CAST](https://docs.aws.amazon.com/redshift/latest/dg/r_TRY_CAST.html),
[SVV_USER_GRANTS](https://docs.aws.amazon.com/redshift/latest/dg/r_SVV_USER_GRANTS.html),
[ALTER MATERIALIZED VIEW](https://docs.aws.amazon.com/redshift/latest/dg/r_ALTER_MATERIALIZED_VIEW.html).
