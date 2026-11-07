"""Build the report from reviewed Markdown + numbered SQL; render with PyMuPDF.

Dependencies: reportlab, pypdf, pymupdf. Does not call AWS or modify infrastructure.
"""
from pathlib import Path
from xml.sax.saxutils import escape
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                Preformatted, Table, TableStyle, KeepTogether, Image)

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
    d.add(String(0,13,'Ramas existentes: Kinesis / Flink / Lakehouse. Redshift: pendiente de despliegue.',
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
            table = Table(rows, colWidths=[99*mm/3, 167*mm/3, 214*mm/3], repeatRows=1,
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
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#','```','|','- ')):
            paragraph.append(lines[i]); i += 1
        result.append(p(' '.join(paragraph)))
    return result


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(BLUE)
    canvas.line(22*mm,19*mm,188*mm,19*mm)
    canvas.setFont('Helvetica',8)
    canvas.setFillColor(NAVY)
    canvas.drawString(22*mm,14*mm,'Nicolas Lopez | Data Engineering | Checkpoint 6')
    canvas.drawRightString(188*mm,14*mm,str(doc.page))
    canvas.restoreState()


def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    TMP.mkdir(parents=True,exist_ok=True)
    story = [Spacer(1,35*mm), p('CODERHOUSE / DATA ENGINEERING','ReportH2'),
             p('Redshift<br/>Streaming Analytics','ReportTitle'),
             p('Pre-entrega 6 · Nicolás López','ReportH1'),
             p('Kinesis, Apache Flink, Iceberg, AWS Glue y Amazon Redshift'),
             Spacer(1,14*mm),
             p('Implementación preparada. Despliegue y pruebas Redshift pendientes de autorización.'),
             p('Documento de avance técnico - 6 de noviembre de 2026','ReportCaption'),
             p('Repositorio: https://github.com/nitotito/coderhouse-data-platform'),
             PageBreak()]
    story.extend(markdown_blocks((ROOT/'docs/redshift-checkpoint-6.md').read_text(encoding='utf-8')))
    story.extend([PageBreak(),p('Evidencia real del Lakehouse existente','ReportH1'),
                  p('Captura proporcionada por el propietario en la entrega 5. Confirma catálogo, '
                    'formato Iceberg y esquema; no demuestra un despliegue de Redshift.'),
                  Image(str(ROOT/'docs/evidence/glue-transaction-aggregates.png'),width=166*mm,height=81*mm),
                  p('Antecedente PE5: Athena verificó dos aprobadas, total 30.30 y promedio 15.150000. '
                    'Snapshot 8171898520026477263. Nuevos resultados Redshift: pendientes.'),
                  p('Resultados locales y pendientes','ReportH1'),
                  p('Terraform fmt y validate: correctos. Plan: ocho altas, cero cambios, cero bajas. '
                    'Parser SQL local: cobertura parcial; las extensiones específicas de AWS requieren '
                    'ejecución real. El runner compila y su modo predeterminado no llama AWS.'),
                  p('Conclusiones técnicas','ReportH1'),
                  p('La separación de ingesta, validación y métricas reduce el riesgo de bloquear el '
                    'stream por conversiones. La conciliación por minuto y método respeta la granularidad '
                    'de Iceberg. El diseño conserva las entregas previas. Falta desplegar, confirmar '
                    'privilegios SQL, ejecutar el ensayo y adjuntar capturas Redshift para aceptar '
                    'funcionalmente la entrega.'), PageBreak(),p('Anexo: SQL reproducible','ReportH1')])
    for part in sorted((ROOT/'sql/redshift').glob('[0-9][0-9]_*.sql')):
        story.append(p(part.name,'ReportH2'))
        story.append(Preformatted(part.read_text(encoding='utf-8'),styles['ReportCode'],maxLineLength=99))
    doc = SimpleDocTemplate(str(OUT),pagesize=(210*mm,297*mm),rightMargin=22*mm,
                            leftMargin=22*mm,topMargin=20*mm,bottomMargin=25*mm,
                            title='Checkpoint 6 - Redshift Streaming Analytics',author='Nicolas Lopez')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    import pymupdf
    document = pymupdf.open(OUT)
    for index,page in enumerate(document):
        page.get_pixmap(matrix=pymupdf.Matrix(1.1,1.1)).save(TMP/f'checkpoint6-{index+1:02d}.png')
    print(f'{OUT}: {len(document)} pages; rendered in {TMP}')


if __name__ == '__main__':
    main()
