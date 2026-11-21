"""Render local DAAT and original screenshots; no network or infrastructure calls."""
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Flowable
from io import BytesIO
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/Nicolas_Lopez_Capstone_RealTime.pdf'
EVIDENCE = ROOT / 'docs/evidence/capstone/local'
TMP = ROOT / 'tmp/pdfs/capstone-local'
spec = importlib.util.spec_from_file_location('layout', ROOT / 'scripts/build-capstone-pdf.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)
h = layout.h


def architecture():
    d = Drawing(470, 300)
    boxes = [
        (0, 242, 105, 42, ['Productor', 'JSON / Event Time']),
        (155, 242, 125, 42, ['Kinesis LocalStack', '2 shards / 24 h']),
        (0, 148, 125, 48, ['Flink', 'validar / IDs / ventanas']),
        (160, 148, 125, 48, ['S3 Iceberg', 'Parquet + metadata JSON']),
        (340, 148, 125, 48, ['DuckDB', 'iceberg_scan']),
        (0, 48, 125, 48, ['Consumidor Python', 'eventos + offsets atomicos']),
        (160, 48, 125, 48, ['PostgreSQL', 'MV aprobados por minuto']),
        (340, 48, 125, 48, ['Catalogo JDBC', 'puntero Iceberg']),
        (340, 242, 125, 42, ['Firehose', 'S3 bronze']),
    ]
    for x, y, w, height, labels in boxes:
        d.add(Rect(x, y, w, height, rx=4, ry=4, fillColor=h.LIGHT, strokeColor=h.BLUE))
        for i, label in enumerate(labels):
            d.add(String(x + w/2, y + height - 16 - 13*i, label, textAnchor='middle',
                         fontName='Helvetica-Bold' if i == 0 else 'Helvetica', fontSize=8))

    def arrow(points):
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            d.add(Line(x1, y1, x2, y2, strokeColor=h.BLUE, strokeWidth=1.2))
        (x1, y1), (x2, y2) = points[-2:]
        if x1 == x2:
            sign = 1 if y2 < y1 else -1
            triangle = [x2, y2, x2-3, y2+6*sign, x2+3, y2+6*sign]
        else:
            sign = 1 if x2 > x1 else -1
            triangle = [x2, y2, x2-6*sign, y2+3, x2-6*sign, y2-3]
        d.add(Polygon(triangle, fillColor=h.BLUE, strokeColor=h.BLUE))

    for points in [
        [(105, 263), (155, 263)], [(280, 263), (340, 263)],
        [(185, 242), (185, 218), (62, 218), (62, 196)],
        [(255, 242), (310, 242), (310, 116), (62, 116), (62, 96)],
        [(125, 172), (160, 172)], [(285, 172), (340, 172)],
        [(125, 72), (160, 72)], [(402, 96), (402, 130), (222, 130), (222, 148)],
    ]:
        arrow(points)
    d.add(String(0, 19, 'Terraform crea la infraestructura emulada. Compose ejecuta los procesos.',
                 fontName='Helvetica', fontSize=8, fillColor=h.NAVY))
    d.add(String(0, 4, 'Flink y el consumidor son lectores independientes; no comparten una transaccion.',
                 fontName='Helvetica', fontSize=8, fillColor=h.NAVY))
    return d


def footer(canvas, doc):
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#506174'))
    canvas.drawString(22*mm, 13*mm, 'Nicolas Lopez | Capstone local | ' + ('Revision de capturas pendiente' if not READY else 'DAAT'))
    canvas.drawRightString(188*mm, 13*mm, str(doc.page))


class OriginalViewport(Flowable):
    """A PDF clipping viewport; the original evidence PNG is never modified."""
    def __init__(self, path, region, width):
        super().__init__()
        self.path, self.region, self.width = str(path), region, width
        self.height = region[3] * width / region[2]

    def draw(self):
        left, top, width, height = self.region
        image_width, image_height = ImageReader(self.path).getSize()
        scale = self.width / width
        canvas = self.canv
        canvas.saveState()
        clip = canvas.beginPath()
        clip.rect(0, 0, self.width, self.height)
        canvas.clipPath(clip, stroke=0, fill=0)
        canvas.drawImage(self.path, -left*scale, (top+height-image_height)*scale,
                         width=image_width*scale, height=image_height*scale)
        canvas.restoreState()


def main():
    global READY
    verification = json.loads((EVIDENCE / 'verification.json').read_text())
    assert verification['technical_checks'] == 'PASSED'
    filenames = ['flink-checkpoints.png', 'postgres.png', 'duckdb.png']
    missing = [name for name in filenames if not (EVIDENCE / 'screenshots' / name).exists()]
    # Presence does not imply visual review; the reviewer must record approval separately.
    review_file = EVIDENCE / 'screenshots-reviewed.json'
    review = json.loads(review_file.read_text()) if review_file.exists() else {}
    reviewed = all(review.get(name, {}).get('sha256') == hashlib.sha256((EVIDENCE/'screenshots'/name).read_bytes()).hexdigest()
                   for name in filenames if (EVIDENCE/'screenshots'/name).exists())
    READY = not missing and reviewed and review_file.exists()
    source = (ROOT / 'docs/capstone-daat-local.md').read_text(encoding='utf-8')
    result = json.loads((EVIDENCE/'result.json').read_text())
    assert result['run_id'] in source, 'Update DAAT before rendering a different audit run'
    sections = re.split(r'^## (.+)\n', source, flags=re.M)
    story = [Spacer(1, 22*mm), h.p('Documento de Arquitectura<br/>y Auditoría Técnica', 'ReportTitle'),
             h.p('Pipeline local de transacciones en tiempo real', 'ReportH1'),
             h.p('Nicolás López | Data Engineering | 20 de noviembre de 2026'), Spacer(1, 12*mm),
             h.p('LocalStack · Flink · Iceberg · PostgreSQL · DuckDB', 'ReportH2'),
             h.p('Despliegue limpio, consistencia de agregaciones y recuperación verificados.'),
             h.p('Capturas pendientes de incorporación y revisión. No presentar todavía.' if not READY else 'Evidencia técnica y capturas revisadas.'),
             h.p('[Código y documentación](https://github.com/nitotito/coderhouse-data-platform/tree/feature/capstone-local)'),
             PageBreak(), h.p('Arquitectura local', 'ReportH1'), architecture(), Spacer(1, 8*mm),
             h.p('Cada destino mantiene su progreso. Los archivos bronze y las tablas Iceberg cumplen responsabilidades distintas.'),
             PageBreak()]
    for index, (title, body) in enumerate(zip(sections[1::2], sections[2::2]), 1):
        if title == 'Evidencia y revisión final':
            story.append(PageBreak())
        story.append(h.p(f'{index} {title}', 'ReportH1'))
        story.extend(layout.blocks(body))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=(210*mm, 297*mm), leftMargin=22*mm,
                            rightMargin=22*mm, topMargin=18*mm, bottomMargin=22*mm,
                            title='Arquitectura y auditoría del pipeline local', author='Nicolás López')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    import pymupdf
    body_bytes = OUT.read_bytes()
    body_pages = len(pymupdf.open(stream=body_bytes, filetype='pdf'))
    appendix = []
    captions = [
        'Mismo job del ensayo limpio: RUNNING, 528 checkpoints completados, 0 fallidos y restauración del checkpoint 7. Captura posterior a los recibos iniciales.',
        'Mismo run y timestamps originales de llegada e inserción. MV: 3 / 33.06 / 11.020000. Freshness de 2775.53 s tras permanecer sin nuevos eventos; lag máximo observado en esta captura: 0.315964 s.',
        'Consulta real con iceberg_scan y puntero de metadatos. Resultado: 3 / 33.06 / 11.020000. La versión del puntero avanzó durante la sesión; el agregado permanece igual.',
    ]
    for index, (title, filename) in enumerate(zip(['Flink y checkpoints', 'PostgreSQL y timestamps de llegada', 'DuckDB sobre Iceberg'], filenames)):
        if appendix:
            appendix.append(PageBreak())
        appendix.append(h.p(title, 'ReportH1'))
        path = EVIDENCE / 'screenshots' / filename
        if path.exists():
            width, height = ImageReader(str(path)).getSize()
            scale = min(253*mm/width, 139*mm/height)
            appendix.extend([Image(str(path), width=width*scale, height=height*scale), Spacer(1, 3*mm),
                             h.p(captions[index], 'ReportCaption'),
                             h.p('SHA256: ' + hashlib.sha256(path.read_bytes()).hexdigest(), 'ReportCaption')])
            if index == 0:
                appendix.extend([PageBreak(), h.p('Detalle de checkpoints y restauración', 'ReportH1'),
                                 OriginalViewport(path, (35, 475, 1850, 815), 245*mm), Spacer(1, 3*mm),
                                 h.p('Ampliación del original mediante una ventana del PDF; no se alteró el PNG. Se conservan la vista completa y el archivo original.', 'ReportCaption')])
        else:
            appendix.append(h.p('Captura pendiente.'))
    appendix_bytes = BytesIO()

    def appendix_footer(canvas, page):
        canvas.setFont('Helvetica', 8)
        canvas.drawString(22*mm, 10*mm, 'Nicolas Lopez | Evidencia local')
        canvas.drawRightString(275*mm, 10*mm, str(body_pages+page.page))

    SimpleDocTemplate(appendix_bytes, pagesize=(297*mm, 210*mm), leftMargin=22*mm,
                      rightMargin=22*mm, topMargin=12*mm, bottomMargin=16*mm).build(
                          appendix, onFirstPage=appendix_footer, onLaterPages=appendix_footer)
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.append(BytesIO(body_bytes))
    writer.append(BytesIO(appendix_bytes.getvalue()))
    writer.add_metadata({'/Title': 'Arquitectura y auditoría del pipeline local', '/Author': 'Nicolás López'})
    with OUT.open('wb') as target:
        writer.write(target)
    pdf = pymupdf.open(OUT)
    for i, page in enumerate(pdf):
        page.get_pixmap(matrix=pymupdf.Matrix(1, 1)).save(TMP / f'page-{i+1:02d}.png')
    links = [link.get('uri') for page in pdf for link in page.get_links()]
    assert any('github.com/nitotito/coderhouse-data-platform' in (uri or '') for uri in links)
    text = '\n'.join(page.get_text() for page in pdf)
    assert '33.06' in text and '11.020000' in text and 'local_20261121_014317' in text
    status = dict(ready_to_submit=READY, missing_screenshots=missing, pages=len(pdf), pdf=str(OUT),
                  sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(), source_sha256=hashlib.sha256(source.encode()).hexdigest())
    (EVIDENCE / 'pdf-status.json').write_text(json.dumps(status, indent=2)+'\n')
    print(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()
