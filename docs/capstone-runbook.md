# Capstone: despliegue limpio, prueba y retiro

Estado: preparado y validado localmente. **No se ejecutó el despliegue aislado.**
La aprobación requerida por la consigna debe cubrir creación, inicio, prueba y
eliminación de los recursos temporales identificados por el manifiesto. No usar
el estado `dev` ni destruir recursos de entregas anteriores.

## Prerrequisitos y preparación sin despliegue

Terraform >=1.10, AWS CLI v2, Python >=3.11, Java17 y Maven. Credenciales AWS
externas al repositorio, permisos de creación de los servicios/IAM y cuotas
disponibles. El perfil debe identificar un principal IAM habilitado para asumir
el rol de auditoría; un ARN de sesión STS no sirve como principal persistente.
Los permisos de operador de PE6 son específicos de dev y **no bastan** para un
entorno capstone nuevo. Revisar la política concreta antes de ampliarla.

```powershell
mvn -f flink-app/pom.xml clean package
python scripts/verify-iceberg-jar.py
terraform -chdir=terraform fmt -recursive -check
terraform -chdir=terraform validate
terraform -chdir=terraform/bootstrap validate
terraform -chdir=terraform/isolated validate
python -m unittest discover -s scripts -p 'test_*.py'
python scripts/capstone.py prepare --profile coderhouse-dev --region us-east-1
```

El último comando solo consulta STS/KMS y escribe `.capstone/cap-<id>/`. Ese
directorio ignorado contiene manifiesto, configuración del backend y variables
específicas. No hay secretos, apply, publicación ni inicio de servicios. Guardar
el manifiesto hasta completar el retiro. El JAR se identifica por SHA256.

`prepare` también genera `preview/main.tf` con backend local. Se puede ejecutar
init y plan allí con `'-var-file=../platform.tfvars.json'`, sin apply. Ya se
verificaron 36 altas/0 cambios/0 bajas y 4 altas del bootstrap. Es revisión desde
estado vacío, no evidencia de despliegue. **Nunca aplicar el plan preview.**

## Plan y despliegue: requieren aprobación previa

Sustituir `cap-<id>` por el nombre generado; nunca inventar un nombre dev.
Estos comandos son instrucciones, **no una ejecución registrada**:

```powershell
$capDir = (Resolve-Path '.capstone/cap-<id>').Path
terraform -chdir=terraform/bootstrap init -input=false
terraform -chdir=terraform/bootstrap plan -input=false "-var-file=$capDir/bootstrap.tfvars.json" "-state=$capDir/bootstrap.tfstate" "-out=$capDir/bootstrap.tfplan"
# Revisar: solo un backend NUEVO, versionado, cifrado y bloqueo público.
terraform -chdir=terraform/bootstrap apply "$capDir/bootstrap.tfplan"
terraform -chdir=terraform/isolated init -input=false -reconfigure "-backend-config=$capDir/isolated.backend.hcl"
terraform -chdir=terraform/isolated plan -input=false "-var-file=$capDir/platform.tfvars.json" "-out=$capDir/platform.tfplan"
# Revisar altas, cuenta, región, nombres y presupuesto antes de aplicar.
terraform -chdir=terraform/isolated apply "$capDir/platform.tfplan"
terraform -chdir=terraform/isolated output -json
```

El bootstrap usa estado local separado; luego se crea un backend S3 nuevo con
versionado y bloqueo nativo S3. No reutiliza la tabla de locks ni el bucket del
estado dev. El módulo aislado reutiliza la plataforma modular; Terraform avisa
que ignora el backend del módulo hijo: manda únicamente el backend de la raíz
`isolated`. No es migración del estado existente.

Orden: red/IAM/buckets/stream → carga versionada del JAR → Flink iniciado →
tabla Iceberg creada por GlueCatalog → Redshift y endpoint → inicialización
SQL vía Data API. El catálogo/base pertenece a Terraform; la tabla Iceberg y su
puntero de metadatos pertenecen a Iceberg. La inicialización SQL espera la tabla,
crea MV/esquemas/vistas/rol y conserva recibos por sentencia. No usa credenciales
de base ni fabrica un `metadata_location`. El SQL usa IAM_ROLE default.

Un apply exitoso no basta: exigir job RUNNING, SQL inicializado y la prueba
siguiente. Un fallo IAM/cuota/servicio deja el entorno pendiente, con recursos
posiblemente facturables; inspeccionar y retirar lo creado, sin afirmar éxito.

## Prueba controlada nueva

```powershell
python scripts/capstone.py e2e --manifest "$capDir/manifest.json"  # vista previa
python scripts/capstone.py e2e --manifest "$capDir/manifest.json" --execute
```

Publica diez registros, en dos fases y una misma partition key. Iniciales:
tres aprobados (uno fuera de orden y un identificador repetido), un rechazado,
un pendiente, JSON inválido, campos faltantes y un evento rechazado que adelanta
el watermark. Espera una ventana Iceberg confirmada: **3 / 30.01 / 10.003333**.
Después publica una aprobada tardía de 1000 y otro avance temporal. Exige el
hash del evento en `LATE_DROPPED` antes de conciliar.

Redshift debe tener diez registros raw; cuatro aprobados válidos suman 1030.01.
Al excluir exclusivamente el tardío confirmado por Flink, las métricas
equivalentes son 3 / 30.01 / 10.003333. La diferencia bruta de 1000 es esperada.
El identificador repetido cuenta dos veces: no hay deduplicación de negocio.
La exclusión usa el oráculo del fixture; en producción hace falta persistir un
registro durable de descartes/decisiones temporales para reproducir ese filtro.

El guard `send-started.json` impide republicar automáticamente tras un fallo.
No borrarlo para volver a intentar a ciegas. Revisar recibos o crear un entorno
nuevo autorizado. `produced_at` es dato del productor; `arrival_timestamp` es
el timestamp aproximado de Kinesis conservado por la MV, no la hora del evento.

Evidencias de la ejecución, si se autoriza: fixture, recibos PutRecord, SQL y
respuestas Data API, log de descarte, Glue GetTable, JSON real de metadatos y
reconciliación. Además capturar Dashboard Flink RUNNING/checkpoints, Iterator
Age en CloudWatch y Query Editor con eventos/arrival_timestamp y JOIN.
Registrar título, servicio, fecha UTC y conclusión por captura. Conservar los
originales y no presentar capturas PE5/PE6 como prueba del despliegue nuevo.

## Recuperación

La prueba Java local inyecta un fallo después de varios checkpoints y verifica
20 registros finales y múltiples snapshots. No prueba restauración del servicio
AWS, resharding ni equivalencia de identidades entre JAR1.1 y JAR1.2. Los UIDs
nuevos son para el entorno limpio: no actualizar dev suponiendo compatibilidad
de savepoints. En AWS registrar snapshot/versión/configuración antes de parar;
restaurar explícitamente desde snapshot compatible y verificar offsets, ventanas,
checkpoints y ausencia de incrementos inesperados. Una fuente nueva con
TRIM_HORIZON sobre una tabla existente puede volver a insertar agregaciones.

## Retiro seguro: autorización explícita de eliminación

1. Comprobar STS contra `account` del manifiesto y tags Environment exactos en
   aplicación, buckets y recursos. Verificar que el backend cacheado de
   `terraform/isolated/.terraform/terraform.tfstate` coincide con state_bucket/key.
2. Guardar evidencia y PDF fuera de los buckets temporales. Detener **solo**
   `application` del manifiesto y esperar READY. No detener dev.
3. La base Glue tiene `prevent_destroy` para proteger dev. En el entorno
   aislado, tras verificar nombre `cap_<id>_lakehouse`, location en data_bucket y
   tags, eliminar únicamente su tabla Iceberg y esa base vía Glue. Esto es una
   excepción de limpieza documentada, no una dependencia para desplegar.
4. Ejecutar `terraform -chdir=terraform/isolated plan -destroy` con su var-file y
   guardar plan. Debe refrescar la base ya ausente y proponer solo bajas del
   manifiesto. No desactivar prevent_destroy globalmente ni usar `state rm`.
5. Aplicar únicamente ese plan revisado. `force_destroy` está habilitado solo
   para buckets capstone, por lo que borrará también datos/versiones temporales.
6. Comprobar ausencia de workgroup, namespace, aplicación, stream, endpoint,
   roles, logs y bucket del manifiesto. Retirar después el bootstrap usando
   su estado local específico y un plan destroy separado. El backend temporal
   se elimina al final; conservar recibos locales.
7. Repetir inventario dev y comparar con el inicial. No afirmar costo cero:
   el stream dev de dos shards, S3/versiones, logs y backend previos siguen vivos.

## Costo y ventana propuesta

Modelo público us-east-1 revisado 07/11/2026; cálculo reproducible en
`docs/evidence/capstone/cost-model.json`. Una hora de cómputo/recursos estimados:
Redshift4RPU USD1.50 + Flink1KPU de proceso y1 de orquestación USD0.22 +
Kinesis2shards USD0.03 + endpoint2AZ USD0.02 = **USD1.77/h**.
Dos horas: USD3.54 antes de almacenamiento, solicitudes, Glue/KMS, logs,
transferencia e impuestos. Propuesta: autorizar una sesión de hasta dos horas,
con objetivo de gasto de USD5 y retiro inmediato. **No es un tope automático**;
los fallos o el tiempo de eliminación pueden extender cargos. Streaming y
AUTO REFRESH pueden mantener cómputo activo. No se consultó una factura real.

Fuentes: [Redshift](https://aws.amazon.com/redshift/pricing/),
[Flink](https://aws.amazon.com/managed-service-apache-flink/pricing/),
[Kinesis](https://aws.amazon.com/kinesis/data-streams/pricing/),
[PrivateLink](https://aws.amazon.com/privatelink/pricing/).
