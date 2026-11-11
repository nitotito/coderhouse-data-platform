# Pre-entrega 6 — ejecución limpia del 11/11/2026

RunId: `pe6_20261111_222257`. Workgroup temporal: `coderhouse-dev-analytics`.
Base: `analytics`. Perfil operador: `coderhouse-dev`. Flink permaneció READY.

| Evidencia | Resultado |
|---|---|
| deployment-plan.txt / deployment-apply.txt |8 altas Terraform; sin cambios/bajas previas |
|001-clean-database-precondition-results.json |0 esquemas de la entrega antes del setup |
|full-script-summary.json |SQL01-08 ejecutado |
|executed-source-proof.json |42 recibos FINISHED; referencias por sentencia y hash |
|test-summary.json |9 eventos nuevos;6 válidos/3 inválidos; métricas y JOIN correctos |
|typed-regression-summary.json |9 casos de conversión realmente comprobados en Redshift |
|typed-column-types.json |Tipos observados de los cinco campos JSON extraídos |
|security-summary.json |Usuario analítico efectivo; SELECT permitido; raw/REFRESH denegados |
|console-membership.json |IAM:RootIdentity con checkpoint6_analyst; admin_option=false |
|local-validation.json |Parser local, fuente/anexo y recibos reales comparados |
|pdf-status.json |Estado del PDF, capturas faltantes y retiro |
|cleanup-summary.json / cleanup-done.json |Plan acotado y comprobación final de retiro |

Los archivos `*-execution.json` son respuestas DescribeStatement; los
`*-results.json` contienen resultados GetStatementResult. Las consultas raw y
REFRESH del ensayo de seguridad fallan deliberadamente por permisos. No se
confunden esas denegaciones esperadas con fallos del SQL de instalación.

Redshift oculta IAM_ROLE/REGION al devolver los dos CREATE EXTERNAL SCHEMA.
El verificador indica esa excepción explícitamente: compara el prefijo visible,
sin inventar el texto oculto. El resto del SQL coincide con los recibos retornados.

Las capturas manuales de esta sesión se guardan como eventos.png, metricas.png,
join.png y membresia.png. No se fabrican imágenes a partir de tablas API ni se
presentan las capturas del07/11 como si fueran de esta ejecución.

La consulta JOIN contrasta aprobadas por minuto y método contra el snapshot
Iceberg existente. El Event Time histórico es intencional; la llegada al stream
es nueva. No demuestra una nueva escritura simultánea de Flink.

El usuario autorizó una sesión de hasta una hora, objetivo USD3 sin tope
automático y retiro temporal. El watchdog guarda su deadline/ID exacto en
capture-window.json. Los recursos anteriores no se incluyen en la limpieza.
