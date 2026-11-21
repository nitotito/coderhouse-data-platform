# Cumplimiento de la entrega final local

| Requisito | Resultado | Evidencia |
|---|---|---|
| Compose en la raíz y carpetas requeridas | Implementado | docker-compose.yml, terraform, flink-app, ingest-consumer, sql |
| tflocal apply desde cero | Aprobado: 20 recursos | local/clean-precondition.json y clean-terraform-apply.txt |
| Segundo plan sin cambios | Aprobado: exit 0 | local/terraform-idempotent-plan.txt |
| Terraform AWS validate | Aprobado sin apply | local/terraform-*-validation.json |
| Kinesis a ambos destinos | Aprobado sobre lote nuevo | local/result.json |
| Semántica equivalente | 3 / 33.06 / 11.020000 | local/postgres-metrics.json y duckdb-iceberg.json |
| Duplicados y tardíos | Aprobado para el fixture | local/fixture.json y result.json |
| Restauración tras reinicio TaskManager | Checkpoint 7 restaurado | local/recovery-after.json |
| Lag, freshness y checkpoints | Medidos | local/health.json y flink-metrics.json |
| Roles PostgreSQL | Membresía y denegación comprobadas | local/security.json |
| Firehose bronze | Cuatro objetos observados | local/firehose-bronze.json |
| Capturas locales | Tres originales revisados y consistentes | local/screenshots-reviewed.json |
| PDF final | Capturas incorporadas y revisión visual | local/pdf-status.json |

Rutas relativas a `docs/evidence/capstone/`. La equivalencia multi-shard bajo
intercalaciones distintas requiere centralizar decisiones temporales; no se afirma
probada por este fixture de una sola partition key. LocalStack no valida enforcement
IAM productivo. AWS no fue desplegado en esta sesión.
