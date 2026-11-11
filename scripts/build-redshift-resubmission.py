"""Build the PE6 resubmission from actual clean-execution evidence.

Imports rendering helpers only. Never queries AWS or synthesizes screenshots.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
from collections import Counter
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate,Frame,PageTemplate,
    PageBreak,NextPageTemplate,Spacer,Preformatted,Table,TableStyle,Image)
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'docs/evidence/checkpoint-6/revision'
OUT=ROOT/'output/pdf/CheckPoint_Redshift_Lopez_Nicolas.pdf'
TMP=ROOT/'tmp/pdfs/redshift-resubmission'
spec=importlib.util.spec_from_file_location('helpers',ROOT/'scripts/build-checkpoint6-pdf.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
p=h.p

def read(name):return json.loads((E/name).read_text(encoding='utf-8'))

def table(headers,rows,widths=None):
    cells=[[p(str(v),'ReportCaption') for v in row] for row in [headers]+rows]
    widths=widths or [166/len(headers)]*len(headers)
    t=Table(cells,colWidths=[v*mm for v in widths],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),h.LIGHT),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LINEBELOW',(0,0),(-1,0),1,h.BLUE),('LINEBELOW',(0,1),(-1,-1),.3,colors.lightgrey),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    return t

def footer(canvas,doc):
    canvas.saveState();w=canvas._pagesize[0]
    canvas.setFont('Helvetica',8);canvas.setFillColor(h.NAVY)
    canvas.drawString(20*mm,13*mm,'Nicolás López | Pre-entrega 6 | Revisión 11/11/2026')
    canvas.drawRightString(w-20*mm,13*mm,str(doc.page));canvas.restoreState()

def main():
    full=read('full-script-summary.json');test=read('test-summary.json')
    security=read('security-summary.json');regression=read('typed-regression-summary.json')
    proof=read('executed-source-proof.json')
    for result in [full,test,security,regression,proof]:
        if result['status']!='PASSED':raise AssertionError('A required live verification did not pass')
    digest=hashlib.sha256((ROOT/'sql/redshift/checkpoint_6_complete.sql').read_bytes()).hexdigest()
    if digest!=proof['consolidated_sha256']:raise AssertionError('Executed SQL differs from current source')
    cleanup=read('cleanup-summary.json') if (E/'cleanup-summary.json').exists() else {'executed':False}
    required=['eventos.png','metricas.png','join.png','membresia.png']
    missing=[name for name in required if not (E/name).exists()]
    ready=cleanup.get('executed') and not missing and (E/'cleanup-done.json').exists()
    metric=test['metrics'][0];joined=test['join'][0]
    story=[Spacer(1,24*mm),p('CODERHOUSE / DATA ENGINEERING','ReportH2'),
        p('Redshift<br/>Streaming Analytics','ReportTitle'),p('Nicolás López · Pre-entrega 6','ReportH1'),
        p('Corrección y ejecución completa desde una base limpia'),Spacer(1,10*mm),
        p('Verificación real: 11 de noviembre de 2026','ReportH2'),
        p('SQL01-08: '+str(len(proof['statements']))+' sentencias finalizadas. '
          'Nueve casos de conversion verificados. Ingesta, metricas, JOIN y permisos comprobados.'),
        p('Prueba y retiro verificados; capturas actuales incorporadas.' if ready else
          'Revision en cierre: '+('faltan capturas '+', '.join(missing)+'. ' if missing else '')+
          ('Retiro pendiente.' if not cleanup.get('executed') else 'Retiro ejecutado.')),
        p('[Repositorio](https://github.com/nitotito/coderhouse-data-platform)'),
        p('[Código de esta revisión](https://github.com/nitotito/coderhouse-data-platform/tree/fix/preentrega-6-reproducible-sql)'),PageBreak(),
        p('1. Arquitectura y alcance','ReportH1'),h.architecture(),
        p('Kinesis alimenta directamente la MV de Redshift. Flink es un consumidor independiente y '
          'produce agregaciones aprobadas Iceberg en S3, registradas en Glue. Redshift consulta ambas '
          'rutas mediante SQL y un esquema externo de Data Catalog.'),
        p('En esta revision se recreo solamente el modulo temporal de Redshift: namespace, workgroup '
          'privado de 4 RPU, rol/politica IAM, grupos de seguridad, endpoint Kinesis y limite de uso. '
          'Terraform: ocho altas, cero cambios y cero bajas. El Lakehouse y Kinesis existentes se conservaron.'),
        p('Flink permanecio READY, sin iniciar. Se publicaron llegadas nuevas con Event Time actual '
          'e historico para contrastar metricas aprobadas equivalentes contra el snapshot PE5. '
          'Esto verifica ingesta y consulta conjunta; no es una prueba simultanea nueva de escritura Flink.'),
        p('2. Correcciones y reproducibilidad','ReportH1'),
        table(['Punto revisado','Resultado'],[
            ['Campos y CTE','payment_method correcto; CTE con parentesis. Vistas creadas realmente en Redshift.'],
            ['Validacion monetaria','NOT (amount_text ~ patron), NULL explicito y TRY_CAST.'],
            ['Timestamp','Epoch ms o ISO con zona; conversion UTC y rechazo de fechas invalidas.'],
            ['Monitoreo','SYS_STREAM_SCAN_ERRORS y demas consultas ejecutadas.'],
            ['Membresia','SQL08 asigna rol al usuario sin password y prueba identidad efectiva.'],
            ['Version exacta','Fuente consolidada, hash y recibos por sentencia enlazados.']],[40,126]),
        PageBreak(),p('3. Ejecución desde cero','ReportH1'),
        p('La precondicion consulto pg_namespace y comprobo ausencia de streaming, analytics, '
          'kinesis_source y lakehouse. No se borraron esquemas para simular una base limpia. '
          'Se ejecutaron SQL01-05, se publico el fixture y se refresco la MV; despues se ejecutaron '
          'todas las sentencias SQL06-08 en una sesion retenida.'),
        table(['Fuente','Sentencias FINISHED'],sorted(Counter(s['source'] for s in proof['statements']).items()),[118,48]),
        p('Los recibos estan en docs/evidence/checkpoint-6/revision. En los dos CREATE EXTERNAL '
          'SCHEMA Redshift oculta IAM_ROLE y REGION en el texto devuelto: la comparacion de esos '
          'recibos se limita al prefijo visible. Las restantes sentencias coinciden con el SQL '
          'devuelto; no se afirma comparacion byte a byte de campos ocultos.'),
        p('SHA256 del consolidado: '+digest,'ReportCaption'),
        p('RunId: '+test['run_id']+'. No se republico el lote para obtener capturas.'),
        p('4. Parseo JSON y conversiones','ReportH1'),
        p('La MV conserva bytes/raw, coordenadas del stream y payload SUPER. CAN_JSON_PARSE guarda '
          'el JSON invalido sin ejecutar JSON_PARSE sobre el. La capa transactions_typed extrae '
          'cinco campos con tipos adecuados; la validacion ocurre antes de agregar.'),
        table(['Campo JSON','Salida','Tipo real observado'],[
            [source,target,next(row['data_type'] for row in read('typed-column-types.json') if row['column_name']==target)]
            for source,target in [('transaction_id','transaction_id'),('timestamp','event_time'),
                                  ('amount','amount'),('payment_method','payment_method'),('status','status')]
        ],[47,47,72]),
        p('amount se define decimal(18,2). El AVG amplia el argumento a decimal(24,6) antes de '
          'agregar y publica decimal(38,6); un cast final por si solo no recupera decimales perdidos.'),
        PageBreak(),p('5. Regresión de timestamp e importe','ReportH1'),
        p('Se ejecuto el SELECT real de SQL03 sobre una tabla TEMP en Redshift, en una sesion '
          'independiente. No es una simulacion Python ni solo un chequeo de gramatica.'),
        table(['Caso','Event Time UTC observado','Clasificacion'],[
            [r['transaction_id'],r['event_time'] or 'NULL',r['validation_error'] or 'valido']
            for r in regression['rows']],[40,70,56]),
        p('ISO Z, offset -03:00 y epoch ms convergen a 2026-11-11 15:00:00 UTC. La fecha '
          'imposible, ausencia de zona, vacio y faltante no producen errores de casting; quedan '
          'clasificados. Se requieren zona explicita y hasta seis decimales de segundo.'),
        p('6. Ingesta y métricas observadas','ReportH1'),
        table(['Metrica','Esperado','Observado'],[
            ['Registros Kinesis del lote',9,9],['Validos tipados',6,6],['Invalidos clasificados',3,3],
            ['Transacciones del grupo actual',3,metric['transaction_count']],
            ['Aprobadas / rechazadas','2 / 1',str(metric['approved_count'])+' / '+str(metric['rejected_count'])],
            ['Importe total','1029.30',metric['total_amount']],['Importe aprobado','30.30',metric['approved_amount']],
            ['Promedio','343.100000',metric['average_amount']]],[80,43,43]),
        p('La muestra incluye dos aprobadas (10.10 y 20.20), una rechazada (999), importe '
          'invalido, timestamp faltante y JSON invalido. Se preservan recibos PutRecord y '
          'shard/sequence_number. arrival_timestamp procede de Kinesis, no del reloj del productor.'),
        PageBreak(),p('7. JOIN con Iceberg','ReportH1'),
        table(['Metrica equivalente','Stream','Iceberg'],[
            ['Ventana UTC',joined['window_start'],joined['window_start']],
            ['Aprobadas',joined['recent_approved_count'],joined['iceberg_approved_count']],
            ['Importe aprobado',joined['recent_approved_amount'],joined['iceberg_approved_amount']],
            ['Diferencia cantidad',joined['count_difference'],0],
            ['Diferencia importe',joined['amount_difference'],'0.00']],[70,48,48]),
        p('El JOIN usa minuto UTC y metodo de pago. Iceberg contiene agregaciones aprobadas, '
          'no eventos raw. Se excluyen rechazadas de la comparacion. La llegada del ensayo es '
          'nueva aunque el Event Time historico sea del 04/11/2026. No se suman dos historias '
          'solapadas ni se promete exactly-once entre consumidores independientes.'),
        p('Glue GetTable y el JSON real de metadatos S3 se volvieron a leer en esta sesion. '
          'Formato observado: '+read('iceberg-read-summary.json')['table_type']+'. Snapshot existente: '
          +str(read('iceberg-read-summary.json')['current_snapshot_id'])+'. '
          'El snapshot PE5 se conservo; no se fabrico una tabla Glue ni se escribieron datos nuevos con Flink.'),
        p('8. IAM, rol SQL y membresía efectiva','ReportH1'),
        p('El rol de ejecucion Redshift usa IAM para Kinesis, KMS, Glue y S3, con ARN/prefijo '
          'acotados. Incluye DescribeStream, GetShardIterator y GetRecords. La red es privada; '
          'el endpoint Kinesis pertenece al modulo temporal. El rol SQL checkpoint6_analyst '
          'separa la lectura analitica de permisos de propietario y refresco.'),
        table(['Usuario observado','Rol','admin_option'],[
            [r['user_name'],r['role_name'],r['admin_option']]
            for r in security['membership']+read('console-membership.json')],[64,72,30]),
        p('Identidad efectiva probada: '+security['identity'][0]['db_user']+'. '
          'SELECT sobre metricas y JOIN permitido; acceso raw y REFRESH denegados. Las dos '
          'respuestas FAILED de esas pruebas son denegaciones esperadas y se conservaron. '
          'No son errores de sintaxis del script consolidado.'),
        PageBreak(),p('9. Refresco, monitoreo y operación','ReportH1'),
        p('Ensayo: AUTO REFRESH NO, publicacion unica, REFRESH explicito y consultas despues '
          'de su finalizacion. El refresco incremental se verifica con SYS_MV_REFRESH_HISTORY; '
          'SYS_STREAM_SCAN_STATES/ERRORS muestran escaneos, posiciones y errores. El intervalo '
          'observado incluye llamadas API y diagnosticos, no es una garantia de latencia automatica.'),
        p('Desde el inicio del envio del lote hasta completar sus diagnosticos se observaron '
          +format(test['observation_upper_bound_seconds'],'.2f')+' segundos. '
          'No equivale a la duracion exclusiva del refresco ni a un SLA de ingesta.'),
        p('Produccion propuesta: orquestador cada 60 segundos, sin solapar refrescos. Conservar '
          'statement_id; ante timeout consultar su estado antes de repetir. Reintentar solo '
          'throttling/indisponibilidad hasta tres veces, con esperas 5/15/30 segundos y jitter. '
          'Detener y alertar ante sintaxis, permisos o casting persistentes. El orquestador '
          'es una politica documentada; no se desplego en esta prueba.'),
        p('Habilitar AUTO REFRESH YES solo tras observar frescura y costo en el workgroup real. '
          'Deshabilitarlo al activar el orquestador, terminar el ensayo o detectar errores/gasto '
          'persistentes. AUTO REFRESH no implica un SLA de 60 segundos.'),
        p('10. Retiro y limitaciones','ReportH1'),
        p('Retiro temporal: '+('confirmado' if cleanup.get('executed',False) else 'pendiente')+'. '
          'El plan de limpieza permite bajas exclusivamente dentro de module.redshift[0]. '
          'No se elimina el stream, Flink, Glue, Iceberg, VPC ni S3 de entregas previas. '
          'Su almacenamiento/stream/logs pueden seguir generando cargos.'),
        p('El retiro del rol termino con DeleteRole acotado despues de confirmar la ausencia '
          'del warehouse, porque el perfil operador carece de la enumeracion '
          'ListInstanceProfilesForRole requerida por el proveedor. Se conservaron ambos intentos '
          'y el recibo IAM. La comprobacion independiente confirma ocho recursos ausentes y '
          'el plan final de Terraform no propone cambios.'),
        p('Sesion autorizada: hasta una hora, objetivo USD3 sin tope de facturacion automatico. '
          'El limite Serverless y la limpieza de seguridad reducen riesgo; no reemplazan una '
          'factura. Los tiempos reales y recibos de retiro se conservan en la evidencia.'),
        p('Fuentes: [TRY_CAST](https://docs.aws.amazon.com/redshift/latest/dg/r_TRY_CAST.html), '
          '[SVV_USER_GRANTS](https://docs.aws.amazon.com/redshift/latest/dg/r_SVV_USER_GRANTS.html), '
          '[Refresco](https://docs.aws.amazon.com/redshift/latest/dg/r_ALTER_MATERIALIZED_VIEW.html), '
          '[Repositorio](https://github.com/nitotito/coderhouse-data-platform).')]
    # Actual user-provided screenshots only. Original PNG files stay unchanged.
    story.append(NextPageTemplate('landscape'))
    for name,title,interpretation in [
        ('eventos.png','Eventos tipados y llegada','Seis validos; cinco campos JSON y llegada Kinesis actual.'),
        ('metricas.png','Metricas por minuto','Dos grupos; tres transacciones, dos aprobadas y 30.30 aprobado por grupo.'),
        ('join.png','Conciliacion con Iceberg','Dos aprobadas y 30.30 por lado; diferencias cero.'),
        ('membresia.png','Membresia efectiva','La identidad de consola tiene checkpoint6_analyst sin admin_option.')]:
        if not (E/name).exists():continue
        story.extend([PageBreak(),p('Captura real: '+title,'ReportH1'),
            p('AWS Query Editor v2 · sesion del 11/11/2026 · captura manual proporcionada por el propietario. '
              +interpretation),p('Vistas ampliadas del PNG original, conservado integro en el repositorio.','ReportCaption')])
        regions={
            'eventos.png':[((.225,.095,.99,.185),'SQL'),((.195,.65,.999,.90),'Seis eventos y llegada Kinesis')],
            'metricas.png':[((.15,.085,.65,.18),'SQL'),((.145,.63,.53,.72),'Ventana, metodo, cantidad y total'),
                            ((.525,.63,.91,.72),'Mismas dos filas: promedio, estados e importe aprobado')],
            'join.png':[((.18,.085,.64,.18),'SQL'),((.16,.68,.48,.745),'Metodo y cantidades aprobadas'),
                        ((.475,.68,.89,.745),'Misma fila: importes y diferencias')],
            'membresia.png':[((.20,.105,.69,.19),'SQL'),((.185,.70,.66,.815),'Usuario efectivo, rol y admin_option')]
        }[name]
        for region,label in regions:
            story.extend([p(label,'ReportCaption'),h.ScreenshotRegion(E/name,region,253*mm),Spacer(1,4*mm)])
    # Glue original is a declared historical antecedent, not a fresh capture.
    glue=ROOT/'docs/evidence/glue-transaction-aggregates.png'
    story.extend([PageBreak(),p('Metadatos Iceberg: antecedente PE5','ReportH1'),
        p('AWS Glue Data Catalog. PNG original de PE5; fecha de captura no embebida. '
          'Muestra formato Iceberg, base y seis columnas. El ensayo nuevo leyo esa tabla mediante el esquema externo.'),
        h.ScreenshotRegion(glue,(0,.12,.50,.51),235*mm)])
    story.extend([PageBreak(),p('Anexo: SQL fuente de esta revisión','ReportH1'),
        p('Archivo ejecutable: sql/redshift/checkpoint_6_complete.sql. SHA256: '+digest,'ReportCaption')])
    code=ParagraphStyle(name='SubmissionCode',parent=h.styles['ReportCode'],fontSize=9,leading=12)
    for part in sorted((ROOT/'sql/redshift').glob('[0-9][0-9]_*.sql')):
        story.extend([p(part.name,'ReportH2'),Preformatted(part.read_text(encoding='utf-8'),code)])
    doc=BaseDocTemplate(str(OUT),pagesize=(210*mm,297*mm),title='Pre-entrega 6 - Redshift - Revision verificada',author='Nicolas Lopez')
    doc.addPageTemplates([
        PageTemplate(id='portrait',pagesize=(210*mm,297*mm),onPage=footer,
            frames=[Frame(22*mm,25*mm,166*mm,252*mm,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)]),
        PageTemplate(id='landscape',pagesize=(297*mm,210*mm),onPage=footer,
            frames=[Frame(18*mm,23*mm,261*mm,169*mm,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)])])
    doc.build(story)
    import pymupdf
    TMP.mkdir(parents=True,exist_ok=True);pdf=pymupdf.open(OUT)
    for i,page in enumerate(pdf):page.get_pixmap(matrix=pymupdf.Matrix(1,1)).save(TMP/f'page-{i+1:02d}.png')
    (E/'pdf-status.json').write_text(json.dumps({'ready':bool(ready),'pages':len(pdf),'missing_screenshots':missing,
        'clean_sql_passed':True,'security_passed':True,'conversion_regression_passed':True,
        'cleanup_executed':cleanup.get('executed',False),'consolidated_sha256':digest},indent=2)+'\n',encoding='utf-8')
    print(str(OUT)+': '+str(len(pdf))+' pages; ready='+str(bool(ready)))

if __name__=='__main__':main()
