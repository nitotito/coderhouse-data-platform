# Auditoría inicial del Capstone (antes de corregir implementación)

Base: entrega 6 completa, commit 9254d9a. Rama final separada; main no modificado.
Inventario: `docs/evidence/capstone/initial-repository.json`, 294 archivos rastreados,
SHA256 por archivo. Revisión: módulos Terraform, Java/Maven/tests, SQL 01-07,
scripts de despliegue, seis secciones de README, evidencias y laboratorio Kafka/Spark.

| Área | Estado inicial | Brecha / evidencia |
|---|---|---|
| Kinesis y S3 | Implementado y verificado | ACTIVE, versionado/cifrado/bloqueo público consultados |
| Flink/Iceberg/Glue | Implementado y verificado | PE5, checkpoint 2 y snapshot real; Flink hoy READY |
| Redshift y JOIN | Implementado y verificado | PE6, retirado; JOIN con snapshot PE5, no nueva escritura Flink |
| Despliegue desde cero | Parcialmente implementado | JAR fuera de Terraform, SQL manual, nombres ligados a dev |
| Backend reproducible | Parcialmente implementado | Bootstrap imperativo, cuenta y perfil fijos |
| Estructura final requerida | No implementado | Originalmente usa infra/ y app/, no terraform/ y flink-app/ |
| Consistencia simultánea E2E | No implementado | No se ejecutaron ambas rutas sobre un lote nuevo común |
| Duplicados / tardíos | Parcialmente implementado | No deduplicación; descarte tardío sin evidencia específica |
| Recuperación por fallo real | Implementado pero pendiente de verificación | Tests de commits, sin inyección de fallo/restauración |
| Precisión promedio SQL | Parcialmente implementado | AVG(decimal18,2) pierde escala antes del cast final |
| JSON evolutivo | Parcialmente implementado | Mapper rechaza campos desconocidos, incluido arrival_timestamp |
| Observabilidad | Parcialmente implementado | Alarmas throughput y logs CP; faltan contadores de calidad/tardíos |
| IAM de Flink | Parcialmente implementado | Confianza sin restricción de origen; revisar sin cambiar política activa |
| Seguridad de Git | Implementado pero pendiente de verificación exhaustiva | Scan de patrones actual: cero; no prueba ausencia universal histórica |
| Kafka/Spark local | No aplicable al E2E AWS | Laboratorio PE3 distinto; no se conecta artificialmente al pipeline AWS |
| Carga/saturación/fallos Glue | Implementado pero pendiente de verificación | Análisis teórico permitido; no hay pruebas de estrés ni inyección AWS |

Plan inicial existente: No changes. Inventario real de AWS en `initial-aws.json`.
No se ejecutaron apply, despliegues nuevos ni reinicios para esta auditoría.
Los identificadores en evidencias históricas son hechos; deben conservarse. La
configuración operativa nueva debe ser parametrizable y separarse de esos hechos.
