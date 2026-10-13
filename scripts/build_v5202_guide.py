"""Render the end-to-end PDF from the editable Markdown guide."""
import json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.utils import ImageReader
from build_v5_guide import register_fonts, make_styles, markdown_flowables, BODY_W, MARGIN, MUTED

ROOT = Path(__file__).resolve().parents[1]


def main():
    register_fonts(); styles=make_styles()
    output=ROOT/'docs/Clinical-Trial-Intelligence-v5.2.0.2-Full-Guide.pdf'
    document=SimpleDocTemplate(str(output),pagesize=A4,leftMargin=MARGIN,rightMargin=MARGIN,
        topMargin=48,bottomMargin=48,title='Clinical Trial Intelligence v5.2.0.2 — End-to-end guide',
        author='Clinical Trial Intelligence project documentation')
    story=[Spacer(1,35),Paragraph('Clinical Trial Intelligence',styles['chapter']),
        Paragraph('Workbench v5.2.0.2',styles['chapter']),Paragraph('End-to-end operating guide',styles['sub']),
        Paragraph('Setup · Data · Roles · Graphs · Prediction · Training · Assistant · Tests',styles['body']),Spacer(1,20)]
    shot=ROOT/'docs/v5202-evidence/overview-desktop.png'
    if shot.exists():
        width,height=ImageReader(str(shot)).getSize()
        story.extend([Image(str(shot),width=BODY_W,height=BODY_W*height/width),Spacer(1,18)])
    story.extend([Paragraph('13 October 2026',styles['caption']),Paragraph('Research decision support with traceable source data, model evidence and explicit assumptions.',styles['body'])])
    source=(ROOT/'docs/V5_2_0_2_FULL_GUIDE.md').read_text(encoding='utf-8')
    story.extend(markdown_flowables(source,styles,json.loads((ROOT/'configs/formulas.json').read_text())))
    def footer(canvas,doc):
        canvas.setFont('CTISans',8);canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN,27,'Clinical Trial Intelligence v5.2.0.2 · Operating guide')
        canvas.drawRightString(A4[0]-MARGIN,27,str(doc.page))
    document.build(story,onFirstPage=footer,onLaterPages=footer)
    print(output)


if __name__ == '__main__':
    main()
