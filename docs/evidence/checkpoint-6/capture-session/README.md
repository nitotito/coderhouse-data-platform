# Sesión autorizada para capturas

Se recreó el mismo módulo Terraform de ocho recursos temporales, con un plan que
no modificó recursos anteriores. El propietario autorizó el costo adicional y el
retiro posterior. Se dejó un cierre de respaldo a los 30 minutos para el UUID
exacto del workgroup, sin autorización para eliminar otro warehouse.

Workgroup ID: `46ecc1f3-981a-4df4-b184-b4e8c80c039a`.
Base de conexión: `analytics`. Usuario de consola comprobado: `IAM:RootIdentity`.
Se le otorgó el rol SQL `checkpoint6_analyst`; no se concedieron permisos a PUBLIC.

La nueva MV recuperó los nueve eventos retenidos del lote original. No se
publicaron eventos nuevos ni se inició Flink. El JOIN volvió a devolver una fila,
dos aprobadas e importe 30.30 de cada lado, diferencias cero.

El propietario guardó las tres capturas originales en la carpeta superior.
`screenshots.json` registra tamaño, resolución y SHA256. Se revisaron visualmente:
incluyen SQL y resultados de eventos, métricas y JOIN en Query Editor v2.
El PDF las incorpora en páginas horizontales mediante vistas ampliadas del
original; los PNG no fueron editados.

Tras recibir las capturas se inició el retiro antes del límite. Como en el primer
ensayo, el provider se detuvo al listar perfiles del rol IAM; el rol exacto, sin
políticas, se eliminó usando DeleteRole autorizado. Se conservan el plan y apply
iniciales del retiro, el recibo `role-removal.json` y la sincronización final.
`cleanup-done.json`, `cleanup-summary.json` y `cleanup-verification.json` registran
el cierre y su comprobación. El archivo de ventana conserva la hora límite
original como antecedente; no significa que el workgroup permanezca activo.

No se solicitan nuevas ampliaciones de acceso: la sesión se retira con los
permisos existentes. Las credenciales temporales no se guardan como evidencias.
