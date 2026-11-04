# Captura requerida por la consigna

**Completada:** [captura real de AWS Glue](evidence/glue-transaction-aggregates.png),
proporcionada por el propietario y revisada visualmente. La imagen muestra la
tabla, la base lakehouse_db, el formato Apache Iceberg, la ubicación S3 y los seis
campos. Está incluida en el README y en el índice de evidencias.

La prueba AWS ya está verificada por API, pero la consigna también exige una
captura de la consola Glue. Una respuesta JSON no sustituye esa captura.

1. Abrir AWS Glue en la región **N. Virginia / us-east-1**.
2. Ir a **Data Catalog → Databases → lakehouse_db → Tables**.
3. Abrir **transaction_aggregates**.
4. Capturar la vista de detalles donde se vean el nombre de la tabla, la base,
   el tipo Iceberg y la ubicación S3. Si Iceberg aparece en propiedades, incluir
   `table_type=ICEBERG` y `metadata_location`.
5. Guardar la imagen real en
   `docs/evidence/glue-transaction-aggregates.png`.

Opcionalmente, agregar una segunda captura de **Schema**, mostrando los seis
campos (`window_start`, `window_end`, `payment_method`, `transaction_count`,
`total_amount`, `average_amount`), como
`docs/evidence/glue-transaction-aggregates-schema.png`.

No es necesario iniciar Flink para estas capturas. La tabla y los datos permanecen
en Glue/S3 mientras Flink está detenido. No incluir credenciales o enlaces de
sesión firmados en las imágenes. Las capturas se incorporan al README solo cuando
los archivos reales existen y se revisaron visualmente.
