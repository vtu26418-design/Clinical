"""Render the v5.2 operating guide; optional build dependency: reportlab."""
import json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from build_v5_guide import register_fonts, make_styles, markdown_flowables, BODY_W, MARGIN, NAVY, MUTED

ROOT=Path(__file__).resolve().parents[1]

def main():
    register_fonts();styles=make_styles()
    output=ROOT/'docs/Clinical-Trial-Intelligence-v5.2.0-Full-Guide.pdf'
    doc=SimpleDocTemplate(str(output),pagesize=A4,leftMargin=MARGIN,rightMargin=MARGIN,topMargin=48,bottomMargin=48,
                          title='Clinical Trial Intelligence Workbench v5.2.0 — End-to-end guide',author='CTI project documentation')
    story=[Spacer(1,38),Paragraph('Clinical Trial Intelligence',styles['chapter']),Paragraph('Workbench v5.2.0',styles['chapter']),
           Paragraph('End-to-end operating guide',styles['sub']),Paragraph('Install · Run · Import · Predict · Review · Train · Deploy',styles['body']),
           Spacer(1,18),Paragraph('11 October 2026',styles['caption'])]
    shot=ROOT/'docs/v52-evidence/home-desktop.png'
    if shot.exists():
        from reportlab.lib.utils import ImageReader
        w,h=ImageReader(str(shot)).getSize();story.extend([Image(str(shot),width=BODY_W,height=BODY_W*h/w),Spacer(1,18)])
    story.extend([Paragraph('Research decision support. Source records, assumptions and model evidence remain distinct.',styles['body']),
                  Paragraph('This guide describes the delivered development release. Live services and production deployment require operator configuration.',styles['caption'])])
    source=(ROOT/'docs/V5_2_FULL_GUIDE.md').read_text()
    story.extend(markdown_flowables(source,styles,json.loads((ROOT/'configs/formulas.json').read_text())))
    def footer(canvas,doc):
        canvas.setFont('CTISans',8);canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN,27,'Clinical Trial Intelligence v5.2.0 · Research use')
        canvas.drawRightString(A4[0]-MARGIN,27,str(doc.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(output)

if __name__=='__main__':main()
