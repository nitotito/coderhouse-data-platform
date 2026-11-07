"""Render the reviewed preliminary DAAT; no AWS calls or invented screenshots."""
from pathlib import Path
import importlib.util
import re
import json
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate,Frame,PageTemplate,Paragraph,Spacer,
                               PageBreak,Preformatted,Table,TableStyle,KeepTogether)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.graphics.shapes import Drawing,Rect,String,Line,Polygon

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf/Nicolas_Lopez_Capstone_RealTime.pdf'
TMP=ROOT/'tmp/pdfs/capstone'
spec=importlib.util.spec_from_file_location('pdf_helpers',ROOT/'scripts/build-checkpoint6-pdf.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
h.styles['ReportH1'].keepWithNext=True
h.styles['ReportH2'].keepWithNext=True

def p(text,style='ReportBody'):
    return h.p(text.replace('→',' -> ').replace('≥','>='),style)

def architecture():
    d=Drawing(470,245)
    boxes=[(0,170,105,48,['Productor JSON','PutRecord / run_id']),
           (155,170,125,48,['Kinesis','Log / offsets separados']),
           (345,170,125,48,['Redshift MV','Raw / SUPER / llegada']),
           (155,70,125,48,['Flink','Validar / aprobadas / 1 min']),
           (345,70,125,48,['Iceberg + S3','Glue / commits por CP']),
           (345,0,125,40,['Consulta SQL','JOIN / metricas equivalentes'])]
    for x,y,w,z,labels in boxes:
        d.add(Rect(x,y,w,z,rx=5,ry=5,fillColor=h.LIGHT,strokeColor=h.BLUE))
        for i,label in enumerate(labels):d.add(String(x+w/2,y+z-17-i*14,label,textAnchor='middle',fontName='Helvetica',fontSize=8))
    def arrow(x1,y1,x2,y2):
        d.add(Line(x1,y1,x2,y2,strokeColor=h.BLUE,strokeWidth=1.4))
        if y1==y2:d.add(Polygon([x2,y2,x2-6,y2+3,x2-6,y2-3],fillColor=h.BLUE,strokeColor=h.BLUE))
        else:d.add(Polygon([x2,y2,x2-3,y2+6,x2+3,y2+6],fillColor=h.BLUE,strokeColor=h.BLUE))
    for points in [(105,194,155,194),(280,194,345,194),(217,170,217,118),(280,94,345,94),(407,70,407,40)]:arrow(*points)
    d.add(Line(470,194,478,194,strokeColor=h.BLUE));d.add(Line(478,194,478,20,strokeColor=h.BLUE))
    d.add(Line(478,20,470,20,strokeColor=h.BLUE))
    d.add(String(0,15,'Consumidores independientes;',fontSize=9,fillColor=h.NAVY))
    d.add(String(0,1,'sin backpressure directo Redshift -> Flink.',fontSize=9,fillColor=h.NAVY))
    return d

def blocks(text):
    lines=text.strip().splitlines();result=[];i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith('```'):
            code=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):code.append(lines[i]);i+=1
            result.append(Preformatted('\n'.join(code),h.styles['ReportCode'],maxLineLength=96));i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[v.strip() for v in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch('[-:]+',v) for v in cells):rows.append([p(v,'ReportCaption') for v in cells])
                i+=1
            n=len(rows[0]);widths={3:[37*mm,52*mm,77*mm],4:[79*mm,27*mm,29*mm,31*mm]}.get(n,[166*mm/n]*n)
            table=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),h.LIGHT),('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LINEBELOW',(0,0),(-1,0),1,h.BLUE),('LINEBELOW',(0,1),(-1,-1),.25,colors.lightgrey),
                ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
                ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            result.extend([table,Spacer(1,10)]);continue
        para=[line];i+=1
        if line.startswith('- '):result.append(p('• '+line[2:]));continue
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('```','|','- ')):
            para.append(lines[i].strip());i+=1
        result.append(p(' '.join(para)))
    return result

def footer(canvas,doc):
    canvas.saveState();canvas.setFont('Helvetica',7);canvas.setFillColor(h.NAVY)
    canvas.drawString(22*mm,14*mm,'Nicolas Lopez | DAAT Capstone | PRELIMINAR - prueba AWS pendiente')
    canvas.drawRightString(188*mm,14*mm,str(doc.page));canvas.restoreState()

class Document(BaseDocTemplate):
    def afterFlowable(self,flowable):
        if getattr(flowable,'section',None):
            title=flowable.section;key='section-'+title.split('.')[0]
            self.canv.bookmarkPage(key);self.canv.addOutlineEntry(title,key,0)
            self.notify('TOCEntry',(0,title,self.page,key))

def captures():
    story=[]
    items=[('Glue: tabla Iceberg','docs/evidence/glue-transaction-aggregates.png',
            'AWS Glue Data Catalog. Captura aportada para PE5; fecha exacta de captura no embebida. '
            'La consola muestra actualización del 04/11/2026. Revisada el 07/11/2026. '
            'Confirma nombre/base, formato Iceberg y seis columnas; no prueba datos del fixture capstone.',
            [((0,.12,.50,.51),'Tabla, base y formato Iceberg'),((.25,.64,.60,.91),'Esquema: nombres y tipos de las seis columnas')]),
            ('Redshift: eventos recibidos','docs/evidence/checkpoint-6/redshift-eventos.png',
             'Query Editor v2, sesión PE6 del 07/11/2026. Seis registros válidos, con aprobados y rechazados. '
             'Son eventos del ensayo histórico; no corresponden al nuevo despliegue.',
             [((.21,.08,1,.175),'SQL ejecutado'),((.21,.64,1,.89),'Seis eventos válidos')]),
            ('Redshift: métricas por minuto','docs/evidence/checkpoint-6/redshift-metricas.png',
             'Query Editor v2, sesión PE6 del 07/11/2026. Dos grupos, tres transacciones y dos aprobadas por grupo; '
             'importe aprobado 30.30. El promedio de este lote no detectaba el problema de escala corregido.',
             [((.15,.075,.55,.145),'SQL ejecutado'),((.14,.65,.54,.75),'Identificación y totales'),
              ((.53,.65,.945,.75),'Promedio, estados e importe aprobado')]),
            ('Redshift: JOIN con histórico','docs/evidence/checkpoint-6/redshift-join.png',
             'Query Editor v2, sesión PE6 del 07/11/2026. Una fila concilia 2 aprobadas y 30.30 contra el snapshot PE5. '
             'Flink estaba detenido; esto prueba consulta conjunta, no actualización simultánea de ambas rutas.',
             [((.15,.10,.56,.155),'SQL ejecutado'),((.14,.71,.535,.785),'Ventana, método y cantidades'),
              ((.525,.71,.92,.785),'Importes y diferencias')])]
    for title,path,caption,regions in items:
        story.extend([PageBreak(),p('Evidencia histórica · '+title,'ReportH1'),p(caption)])
        for region,label in regions:
            story.extend([p(label,'ReportCaption'),h.ScreenshotRegion(ROOT/path,region,166*mm),Spacer(1,4*mm)])
    return story

def main():
    OUT.parent.mkdir(parents=True,exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
    source=(ROOT/'docs/capstone-daat.md').read_text(encoding='utf-8')
    sections=re.split(r'^# (.+)\n',source,flags=re.M)[1:]
    story=[Spacer(1,25*mm),p('CODERHOUSE · DATA ENGINEERING','ReportH2'),
           p('Arquitectura y<br/>Auditoría Técnica','ReportTitle'),p('Capstone Real-Time Data Platform','ReportH1'),
           p('Nicolás López · 7 de noviembre de 2026'),Spacer(1,15*mm),
           p('PRELIMINAR','ReportH1'),p('Pendiente de despliegue limpio y prueba simultánea en AWS.'),
           p('Validaciones locales verificadas. Evidencias PE5/PE6 identificadas como antecedentes.'),
           p('[Repositorio GitHub](https://github.com/nitotito/coderhouse-data-platform)'),PageBreak(),
           p('Contenido','ReportH1')]
    toc=TableOfContents();toc.levelStyles=[h.styles['ReportCaption']];story.extend([toc,PageBreak()])
    for title,body in zip(sections[::2],sections[1::2]):
        heading=p(title,'ReportH1');heading.section=title;story.append(heading)
        if title.startswith('6.'):story.extend([architecture(),Spacer(1,7*mm)])
        story.extend(blocks(body))
        if title.startswith('25.'):
            story.extend(captures());story.append(PageBreak())
    doc=Document(str(OUT),pagesize=(210*mm,297*mm),title='DAAT Capstone Real-Time - PRELIMINAR',
                 author='Nicolas Lopez',leftMargin=22*mm,rightMargin=22*mm,topMargin=20*mm,bottomMargin=25*mm)
    doc.addPageTemplates([PageTemplate(id='main',onPage=footer,frames=[Frame(22*mm,25*mm,166*mm,252*mm,
                         leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)])])
    doc.multiBuild(story)
    import pymupdf
    document=pymupdf.open(OUT)
    for i,page in enumerate(document):page.get_pixmap(matrix=pymupdf.Matrix(1,1)).save(TMP/f'page-{i+1:02d}.png')
    links=[v['uri'] for page in document for v in page.get_links() if 'uri' in v]
    text='\n'.join(page.get_text() for page in document)
    if 'https://github.com/nitotito/coderhouse-data-platform' not in links:raise AssertionError('Missing repo hyperlink')
    if '30. Enlace al repositorio' not in text:raise AssertionError('Missing required last section')
    print(json.dumps({'pdf':str(OUT),'pages':len(document),'hyperlinks':len(links),'rendered':str(TMP),'status':'PRELIMINARY'},indent=2))

if __name__=='__main__':main()
