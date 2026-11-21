# Capturas de la entrega final local

Guardar los originales PNG en `docs/evidence/capstone/local/screenshots/`.
Estas deben corresponder al run local actual, no a AWS ni a las preentregas.

1. `flink-checkpoints.png`: abrir http://localhost:8081, entrar al job activo y a
   Checkpoints. Mostrar estado RUNNING y checkpoints completados. La restauración
   tras reiniciar TaskManager tiene recibo JSON separado. Es normal que el historial
   incluya el reinicio controlado; no presentarlo como un fallo inexplicado.
2. `postgres.png`: ejecutar en la terminal del repositorio y capturar consulta y
   resultados, especialmente arrival_timestamp/inserted_at y las métricas:

```powershell
docker compose --profile tools run --rm audit python /repo/scripts/local-capture.py postgres
```

3. `duckdb.png`: ejecutar y capturar SQL, puntero metadata real y resultado:

```powershell
docker compose --profile tools run --rm audit python /repo/scripts/local-capture.py duckdb
```

Ambas consultas deben mostrar 3 / 33.06 / 11.020000 para el run actual.
Ampliar la terminal si se cortan columnas. La herramienta no dibuja capturas ni
simula consolas: imprime resultados obtenidos de los motores reales.
No detener el laboratorio hasta tomar las capturas. No usa servicios AWS.
