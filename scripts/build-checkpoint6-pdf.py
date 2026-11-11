"""Build the report from reviewed Markdown + numbered SQL; render with PyMuPDF.

Dependencies: reportlab, pypdf, pymupdf. Does not call AWS or modify infrastructure.
"""
from pathlib import Path
from xml.sax.saxutils import escape
import re
import json
import hashlib

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, NextPageTemplate,
                                Flowable, Paragraph, Spacer, PageBreak,
                                Preformatted, Table, TableStyle, KeepTogether, Image)
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/CheckPoint_Redshift_Lopez_Nicolas.pdf'
TMP = ROOT / 'tmp/pdfs'
NAVY = colors.HexColor('#122841')
BLUE = colors.HexColor('#126E82')
LIGHT = colors.HexColor('#EAF3F5')
AMBER = colors.HexColor('#9D4F00')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='ReportTitle', fontName='Helvetica-Bold', fontSize=30,
                         leading=35, textColor=NAVY, spaceAfter=20))
styles.add(ParagraphStyle(name='ReportBody', fontName='Helvetica', fontSize=10,
                         leading=14.5, spaceAfter=8, textColor=NAVY))
styles.add(ParagraphStyle(name='ReportH1', fontName='Helvetica-Bold', fontSize=19,
                         leading=23, spaceBefore=16, spaceAfter=12, textColor=BLUE))
styles.add(ParagraphStyle(name='ReportH2', fontName='Helvetica-Bold', fontSize=13,
                         leading=17, spaceBefore=12, spaceAfter=8, textColor=BLUE))
styles.add(ParagraphStyle(name='ReportCode', fontName='Courier', fontSize=7.2,
                         leading=10, backColor=LIGHT, borderPadding=7, spaceAfter=10))
styles.add(ParagraphStyle(name='ReportCaption', fontSize=8, leading=11,
                         textColor=colors.HexColor('#506174'), spaceAfter=8))
styles['ReportH1'].keepWithNext = True
styles['ReportH2'].keepWithNext = True


def markup(text):
    text = escape(text).replace('&lt;br/&gt;', '<br/>')
    text = re.sub(r'\[([^]]+)\]\(([^)]+)\)',
                  lambda m: '<link href="'+m[2]+'" color="#126E82">'+m[1]+'</link>'
                  if m[2].startswith('https://') else m[1], text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    return re.sub(r'`([^`]+)`', r'<font name="Courier">\1</font>', text)


def p(text, style='ReportBody'):
    return Paragraph(markup(text), styles[style])


def architecture():
    d = Drawing(480, 235)
    boxes = [
        (0,155,92,48,['Kinesis','transacciones JSON']),
        (133,155,130,48,['Redshift Serverless','Streaming MV / SUPER']),
        (315,155,150,48,['Vistas analiticas','eventos / metricas']),
        (0,42,92,48,['Flink','ventanas aprobadas']),
        (133,42,130,48,['S3 + Iceberg v2','Glue Data Catalog']),
        (315,42,150,48,['Esquema lakehouse','JOIN minuto + pago']),
    ]
    for x,y,w,h,labels in boxes:
        d.add(Rect(x,y,w,h,rx=5,ry=5,fillColor=LIGHT,strokeColor=BLUE))
        for index,label in enumerate(labels):
            d.add(String(x+w/2,y+h-19-index*13,label,textAnchor='middle',
                         fontName='Helvetica-Bold' if index == 0 else 'Helvetica',
                         fontSize=9 if index == 0 else 8,fillColor=NAVY))
    for x1,y1,x2,y2 in [(92,179,133,179),(263,179,315,179),(46,155,46,90),
                          (92,66,133,66),(263,66,315,66),(390,155,390,90)]:
        d.add(Line(x1,y1,x2,y2,strokeColor=BLUE,strokeWidth=1.5))
        if x1 == x2:
            points=[x2,y2,x2-3,y2+6,x2+3,y2+6]
        else:
            points=[x2,y2,x2-6,y2+3,x2-6,y2-3]
        d.add(Polygon(points,fillColor=BLUE,strokeColor=BLUE))
    d.add(String(0,13,'Ramas existentes: Kinesis / Flink / Lakehouse. Redshift: ensayo temporal validado en AWS.',
                 fontName='Helvetica',fontSize=8,fillColor=AMBER))
    return d


def markdown_blocks(source):
    lines = source.splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith('# '):
            i += 1
            continue
        if line.startswith('```'):
            language = line[3:].strip()
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]); i += 1
            if language == 'mermaid':
                result.append(architecture())
            else:
                result.append(Preformatted('\n'.join(code), styles['ReportCode'], maxLineLength=99))
            i += 1
            continue
        if line.startswith('## '):
            result.append(p(line[3:], 'ReportH1')); i += 1
            continue
        if line.startswith('### '):
            result.append(p(line[4:], 'ReportH2')); i += 1
            continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = [x.strip() for x in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[-:]+', x) for x in cells):
                    rows.append([p(x,'ReportCaption') for x in cells])
                i += 1
            widths=([48*mm,118*mm] if len(rows[0])==2 else [99*mm/3,167*mm/3,214*mm/3])
            table = Table(rows, colWidths=widths, repeatRows=1,
                          hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),
                                       ('VALIGN',(0,0),(-1,-1),'TOP'),
                                       ('LINEBELOW',(0,0),(-1,0),1,BLUE),
                                       ('LINEBELOW',(0,1),(-1,-1),0.3,colors.lightgrey),
                                       ('LEFTPADDING',(0,0),(-1,-1),5),
                                       ('RIGHTPADDING',(0,0),(-1,-1),5)]))
            result.extend([table,Spacer(1,10)])
            continue
        paragraph = [line]
        i += 1
        if line.startswith('- '):
            result.append(p('• '+line[2:])); continue
        if re.match(r'^\d+[.] ',line):
            result.append(p(line)); continue
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#','```','|','- ')) and not re.match(r'^\d+[.] ',lines[i]):
            paragraph.append(lines[i]); i += 1
        result.append(p(' '.join(paragraph)))
    return result


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(BLUE)
    page_width = canvas._pagesize[0]
    canvas.line(22*mm,19*mm,page_width-22*mm,19*mm)
    canvas.setFont('Helvetica',8)
    canvas.setFillColor(NAVY)
    canvas.drawString(22*mm,14*mm,'Nicolas Lopez | Data Engineering | Checkpoint 6')
    canvas.drawRightString(page_width-22*mm,14*mm,str(doc.page))
    canvas.restoreState()


class ScreenshotRegion(Flowable):
    """PDF viewport into an unchanged original PNG; no raster file is edited."""
    def __init__(self, path, region, width):
        super().__init__()
        self.path = str(path)
        iw, ih = ImageReader(self.path).getSize()
        left, top, right, bottom = region
        self.scale = width / ((right-left)*iw)
        self.width = width
        self.height = (bottom-top)*ih*self.scale
        self.image_width, self.image_height = iw*self.scale, ih*self.scale
        self.x_offset = -left*iw*self.scale
        self.y_offset = -(1-bottom)*ih*self.scale

    def draw(self):
        self.canv.saveState()
        clip = self.canv.beginPath()
        clip.rect(0,0,self.width,self.height)
        self.canv.clipPath(clip,stroke=0,fill=0)
        self.canv.drawImage(self.path,self.x_offset,self.y_offset,
                           width=self.image_width,height=self.image_height,mask='auto')
        self.canv.restoreState()


def main():
    revision=ROOT/'docs/evidence/checkpoint-6/revision'
    if (revision/'executed-source-proof.json').exists() and (revision/'security-summary.json').exists():
        import importlib.util
        spec=importlib.util.spec_from_file_location('resubmission',ROOT/'scripts/build-redshift-resubmission.py')
        report=importlib.util.module_from_spec(spec);spec.loader.exec_module(report)
        report.main()
        return
    OUT.parent.mkdir(parents=True,exist_ok=True)
    TMP.mkdir(parents=True,exist_ok=True)
    evidence = ROOT/'docs/evidence/checkpoint-6'
    actual = json.loads((evidence/'test-summary.json').read_text(encoding='utf-8'))
    security = json.loads((evidence/'security-summary.json').read_text(encoding='utf-8'))
    cleanup_file = evidence/'capture-session/cleanup-summary.json'
    if not cleanup_file.exists():
        cleanup_file = evidence/'cleanup-summary.json'
    cleanup = json.loads(cleanup_file.read_text(encoding='utf-8'))
    state = 'Antecedente del 07/11/2026: pruebas funcionales y seguridad PASSED. '
    state += 'Recursos temporales retirados.' if cleanup['executed'] else 'Retiro temporal en proceso.'
    story = [Spacer(1,35*mm), p('CODERHOUSE / DATA ENGINEERING','ReportH2'),
             p('Redshift<br/>Streaming Analytics','ReportTitle'),
             p('Pre-entrega 6 · Nicolás López','ReportH1'),
             p('Kinesis, Apache Flink, Iceberg, AWS Glue y Amazon Redshift'),
             Spacer(1,14*mm),
             p('Revisión 11/11/2026: pendiente de ejecución desde base limpia.','ReportH2'),
             p(state),
             p('Informe de ensayo real - 7 de noviembre de 2026','ReportCaption'),
             p('Incluye capturas reales de Query Editor v2 y resultados API verificados.','ReportCaption'),
             p('Repositorio: https://github.com/nitotito/coderhouse-data-platform'),
             PageBreak()]
    story.extend(markdown_blocks((ROOT/'docs/redshift-revision-6.md').read_text(encoding='utf-8')))
    story.append(PageBreak())
    story.extend(markdown_blocks((ROOT/'docs/redshift-checkpoint-6.md').read_text(encoding='utf-8')))
    story.extend([PageBreak(),p('Resultados reales del ensayo AWS','ReportH1'),
                  p('RunId: '+actual['run_id']+'. Un único envío de nueve registros a Kinesis.'),
                  p('Las siguientes tablas son resultados exportados de Data API. No son capturas de consola.','ReportCaption')])
    def table(headers,rows,widths):
        cells=[[p(str(x),'ReportCaption') for x in row] for row in [headers]+rows]
        item=Table(cells,colWidths=[w*mm for w in widths],repeatRows=1,hAlign='LEFT')
        item.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),
                                  ('LINEBELOW',(0,0),(-1,0),1,BLUE),
                                  ('VALIGN',(0,0),(-1,-1),'TOP'),
                                  ('TOPPADDING',(0,0),(-1,-1),6),
                                  ('BOTTOMPADDING',(0,0),(-1,-1),6)]))
        return item
    metric=actual['metrics'][0]
    story.append(table(['Metrica actual','Valor observado'],
                        [[key,metric[key]] for key in ['window_start','transaction_count','total_amount',
                         'average_amount','approved_count','rejected_count','approved_amount']], [90,76]))
    story.extend([Spacer(1,10*mm),p('Conciliacion con Iceberg','ReportH2')])
    joined=actual['join'][0]
    story.append(table(['Fuente','Aprobadas','Importe'],
                        [['Streaming',joined['recent_approved_count'],joined['recent_approved_amount']],
                         ['Iceberg',joined['iceberg_approved_count'],joined['iceberg_approved_amount']],
                         ['Diferencia',joined['count_difference'],joined['amount_difference']]], [70,48,48]))
    story.extend([Spacer(1,7*mm),p('Seguridad y calidad','ReportH2'),
                  p('Usuario SQL comprobado: '+security['identity'][0]['db_user']+'. '
                    'SELECT sobre metricas y JOIN permitido; raw y REFRESH denegados. '
                    'Seis eventos validos y tres invalidos clasificados. Cero errores de escaneo observados.'),
                  p('Refresco incremental manual exitoso: 9.735348 s. Ensayo completo: '
                    +str(actual['observation_upper_bound_seconds'])+' s, incluyendo envio y diagnosticos. '
                    'No es una medida de latencia automatica ni una factura de AWS.'),
                  PageBreak(),p('Evidencia real del Lakehouse existente','ReportH1'),
                  p('Captura proporcionada por el propietario en la entrega 5. Confirma catálogo, '
                    'formato Iceberg y esquema; no demuestra un despliegue de Redshift.'),
                  Image(str(ROOT/'docs/evidence/glue-transaction-aggregates.png'),width=166*mm,height=81*mm),
                  p('Antecedente PE5: Athena verificó dos aprobadas, total 30.30 y promedio 15.150000. '
                    'Snapshot 8171898520026477263. Redshift leyo y concilio esta muestra durante el ensayo.'),
                  p('Resultados y cierre','ReportH1'),
                  p('Terraform: ocho altas exitosas y retiro limitado al modulo temporal. '
                    'Tres pruebas locales del runner correctas. SQL ejecutado realmente en Redshift. '
                    +state+' Las entregas anteriores permanecen desplegadas.'),
                  p('Conclusiones técnicas','ReportH1'),
                  p('La separación de ingesta, validación y métricas reduce el riesgo de bloquear el '
                    'stream por conversiones. La conciliación por minuto y método respeta la granularidad '
                    'de Iceberg. Se comprobaron ingesta, conversiones, metricas, JOIN y privilegios SQL. '
                    'Las capturas reales de Query Editor v2 documentan eventos, metricas y conciliacion. '
                    'Los originales PNG permanecen sin modificar en el repositorio.')])
    captures = [
        ('Eventos recibidos desde Kinesis','redshift-eventos.png',
         'Cinco campos JSON extraidos y seis registros validos del lote retenido.',
         [((.21,.08,1,.175),'SQL ejecutado'),((.21,.64,1,.89),'Resultado: seis eventos validos')]),
        ('Metricas por minuto y metodo','redshift-metricas.png',
         'Dos ventanas: tres transacciones, dos aprobadas, una rechazada; aprobado 30.30 en cada una.',
         [((.15,.075,.55,.145),'SQL ejecutado'),((.14,.65,.54,.75),'Resultado: identificacion, cantidad y total'),
          ((.53,.65,.945,.75),'Mismas filas: promedio, aprobadas, rechazadas e importe aprobado')]),
        ('JOIN con el Lakehouse Iceberg','redshift-join.png',
         'Una fila conciliada: 2/2 aprobadas, importes 30.30/30.30 y diferencias cero.',
         [((.15,.10,.56,.155),'SQL ejecutado'),((.14,.71,.535,.785),'Resultado: ventana, metodo y cantidades'),
          ((.525,.71,.92,.785),'Misma fila: importes y diferencias')]),
    ]
    story.append(NextPageTemplate('captures'))
    for title, filename, caption, regions in captures:
        story.extend([PageBreak(),p('Captura real: '+title,'ReportH1'),p(caption),
                      p('AWS Query Editor v2. Vistas ampliadas del original; archivo: '+filename,'ReportCaption')])
        for region, label in regions:
            story.extend([p(label,'ReportCaption'),ScreenshotRegion(evidence/filename,region,253*mm),Spacer(1,4*mm)])
    digest=hashlib.sha256((ROOT/'sql/redshift/checkpoint_6_complete.sql').read_bytes()).hexdigest()
    story.extend([PageBreak(),p('Anexo: SQL fuente de esta revisión','ReportH1'),
                  p('Archivo ejecutable: sql/redshift/checkpoint_6_complete.sql. '
                    'El anexo usa las mismas fuentes numeradas; no hay correcciones manuales ocultas.'),
                  p('SHA256 del consolidado: '+digest,'ReportCaption')])
    appendix=ParagraphStyle(name='RevisionSQL',parent=styles['ReportCode'],fontSize=9,leading=12)
    for part in sorted((ROOT/'sql/redshift').glob('[0-9][0-9]_*.sql')):
        story.append(p(part.name,'ReportH2'))
        story.append(Preformatted(part.read_text(encoding='utf-8'),appendix))
    doc = BaseDocTemplate(str(OUT),pagesize=(210*mm,297*mm),rightMargin=22*mm,
                            leftMargin=22*mm,topMargin=20*mm,bottomMargin=25*mm,
                            title='Checkpoint 6 - Redshift Streaming Analytics',author='Nicolas Lopez')
    doc.addPageTemplates([
        PageTemplate(id='portrait',pagesize=(210*mm,297*mm),onPage=footer,
                     frames=[Frame(22*mm,25*mm,166*mm,252*mm,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)]),
        PageTemplate(id='captures',pagesize=(297*mm,210*mm),onPage=footer,
                     frames=[Frame(18*mm,23*mm,261*mm,169*mm,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)])])
    doc.build(story)
    import pymupdf
    document = pymupdf.open(OUT)
    for index,page in enumerate(document):
        page.get_pixmap(matrix=pymupdf.Matrix(1.1,1.1)).save(TMP/f'checkpoint6-{index+1:02d}.png')
    print(f'{OUT}: {len(document)} pages; rendered in {TMP}')


if __name__ == '__main__':
    main()
