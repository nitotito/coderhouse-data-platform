# Matriz de cumplimiento Capstone — revisión 07/11/2026

La clasificación se limita a la evidencia indicada. «Verificado» local no implica
desplegado en AWS. La matriz inicial se conserva separada para trazabilidad.

| Requisito | Clasificación | Evidencia / pendiente |
|---|---|---|
| Inventario y auditoría de seis entregas | Implementado y verificado | initial-repository.json, initial-aws.json, matriz inicial |
| Carpetas terraform/flink-app/sql | Implementado y verificado | Fuentes trasladadas y referencias corregidas |
| Terraform modular | Implementado y verificado | Tres raíces validate; fmt; módulos conservados |
| Backend remoto dev conservado | Implementado y verificado | Bucket/clave intactos; plan solo output |
| Backend nuevo reproducible | Implementado pero pendiente de verificación | Bootstrap plan4 altas; apply no ejecutado |
| Cuenta AWS parametrizable | Implementado y verificado | Sin ID numérico fijo en Terraform activo; STS |
| Ausencia de secretos en Git | Parcialmente implementado | Scan de patrones sin hallazgos; no escaneo histórico exhaustivo |
| Carga JAR versionado desde Terraform | Implementado pero pendiente de verificación | aws_s3_object y dependencia object_version; JAR local inspeccionado |
| Inicio limpio Flink | Implementado pero pendiente de verificación | start_application=true solo aislado |
| Inicialización Iceberg | Implementado pero pendiente de verificación | GlueCatalog probado PE5; nueva config no desplegada |
| Inicialización SQL automatizada | Implementado pero pendiente de verificación | terraform_data/Runner; ejecución nueva pendiente |
| Despliegue completo desde cero | Parcialmente implementado | Preview36 altas + bootstrap4; sin apply autorizado |
| Filtros y importes Java | Implementado y verificado | Pruebas locales parser/agregación |
| Tolerancia a metadatos JSON | Implementado y verificado | Test de campo adicional |
| Duplicados de negocio | No implementado | Se cuentan deliberadamente; documentado, no se promete dedup |
| Watermarks y tardíos | Implementado y verificado | Prueba local con watermark determinístico y side output |
| Contadores de calidad/tardíos | Implementado pero pendiente de verificación | Código presente; exposición AWS pendiente |
| Recuperación de tarea y commits | Implementado y verificado | Inyección local,20 registros finales, snapshots; no recuperación AWS |
| Migración de snapshot1.1 a1.2 | No aplicable, con justificación | Prueba aislada nueva; no se actualiza dev |
| Persistencia y consulta Lakehouse histórica | Implementado y verificado | PE5 snapshot/CP/Athena reales |
| Ingesta y JOIN Redshift histórico | Implementado y verificado | PE6 recibos y capturas; servicio retirado |
| Precisión AVG SQL corregida | Implementado pero pendiente de verificación | Widen antes de AVG; falta ejecutar nueva expresión AWS |
| Reconciliación simultánea nueva | Implementado pero pendiente de verificación | Fixture/oráculo/script sin publicación AWS |
| Arrival timestamp nuevo | Implementado pero pendiente de verificación | Alias en vista; captura actual pendiente |
| Prueba de carga/caos AWS | No implementado | Análisis documentado; requiere aprobación aparte |
| Backpressure y fallos analizados | Implementado y verificado | DAAT19/20, consumidores independientes |
| Observabilidad completa actual | Parcialmente implementado | Logs/alarmas previas; faltan capturas CP/IteratorAge nuevas |
| IAM mínimo y rol SQL | Parcialmente implementado | PE6 seguridad pasada; trust capstone/operador pendientes AWS |
| Costos | Implementado y verificado | Modelo público calculado; no factura ni presupuesto garantizado |
| Retiro seguro aislado | Implementado pero pendiente de verificación | Runbook y protección de nombres; sin eliminación ejecutada |
| Kafka/Spark en E2E AWS | No aplicable, con justificación | Laboratorio local PE3 separado |
| PDF DAAT | Parcialmente implementado |30 secciones, imágenes reales, enlaces; preliminar por prueba AWS faltante |
| Merge main | No aplicable, con justificación | Prohibido hasta autorización final |

La aprobación propuesta debe abarcar una sesión aislada de hasta dos horas,
objetivo USD5 sin tope automático, incluyendo retiro de los recursos temporales.
El entorno existente queda preservado y sus cargos persistentes se informan.
