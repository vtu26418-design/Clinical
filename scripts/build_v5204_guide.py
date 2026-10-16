"""Build the v5.2.0.4 operating PDF from editable Markdown and actual screenshots.

Run with the optional requirements-docs.txt environment. No application/provider
calls are made; absent screenshots are omitted instead of inventing evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable, Image, NextPageTemplate, PageBreak, Paragraph, Spacer, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

from build_v5_guide import (
    BODY_W, GuideDoc, MARGIN, PAGE_H, PAGE_W, make_styles, markdown_flowables,
    register_fonts,
)

ROOT = Path(__file__).resolve().parents[1]
EMERALD = colors.HexColor("#17776D")
INK = colors.HexColor("#183531")
SLATE = colors.HexColor("#647A78")
STONE = colors.HexColor("#F3F6F5")
LINE = colors.HexColor("#DCE5E3")


class ReleaseCover(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = BODY_W, 650

    def draw(self):
        c = self.canv
        c.setFillColor(STONE)
        c.roundRect(0, 184, BODY_W, 448, 18, fill=1, stroke=0)
        c.setFillColor(EMERALD)
        c.roundRect(28, 576, 127, 27, 8, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("CTIBold", 10)
        c.drawString(41, 585, "CTI / v5.2.0.4")
        c.setFillColor(INK)
        c.setFont("CTIBold", 32)
        for y, label in [(521, "Clinical Trial"), (478, "Intelligence"), (435, "Workbench")]:
            c.drawString(28, y, label)
        c.setStrokeColor(LINE)
        c.line(28, 410, BODY_W - 28, 410)
        c.setFont("CTIBold", 16)
        c.drawString(28, 374, "Full operating & testing guide")
        c.setFont("CTISans", 11)
        c.setFillColor(SLATE)
        for y, label in [
            (342, "Windows with Docker Desktop — PostgreSQL included"),
            (315, "Source data, saved predictions and guided explanations"),
            (288, "All 26 sections · accuracy reports + acceptance checks · explicit evidence limits"),
        ]:
            c.drawString(28, y, label)
        c.setFillColor(EMERALD)
        c.setFont("CTIBold", 9)
        for i, label in enumerate(["SET UP", "IMPORT", "PREDICT", "REVIEW"]):
            x = 30 + i * 116
            c.circle(x + 5, 243, 5, stroke=0, fill=1)
            c.drawString(x, 217, label)
        c.setFillColor(INK)
        c.setFont("CTIBold", 10)
        c.drawString(0, 141, "Research decision support with source and model provenance")
        c.setFillColor(SLATE)
        c.setFont("CTISans", 9)
        for y, label in [
            (115, "Editable Markdown accompanies this PDF. Use the PDF chapter bookmarks."),
            (92, "Historical approved models, raw records and metrics remain preserved."),
            (69, "Not clinical or regulatory advice. Final release evidence has its own report."),
            (31, "Docker operating manual edition · 16 October 2026"),
        ]:
            c.drawString(0, y, label)


class ReleaseDoc(GuideDoc):
    def __init__(self, path, styles):
        super().__init__(path, styles)
        self.title = "Clinical Trial Intelligence v5.2.0.4 — Full operating guide"
        self.author = "Clinical Trial Intelligence project documentation"
        self.subject = "Docker, model analysis, virtual clinical scenes, research workflows, evidence, governance and testing"

    def cover_page(self, c, doc):
        c.setFillColor(EMERALD)
        c.rect(0, PAGE_H - 7, PAGE_W, 7, fill=1, stroke=0)

    def body_page(self, c, doc):
        c.saveState()
        c.setFillColor(EMERALD)
        c.rect(0, PAGE_H - 4, PAGE_W, 4, fill=1, stroke=0)
        c.setFont("CTIBold", 8.2)
        c.setFillColor(INK)
        c.drawString(MARGIN, PAGE_H - 32, "CTI WORKBENCH / v5.2.0.4")
        c.setFont("CTISans", 8)
        c.setFillColor(SLATE)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - 32, "OPERATING + TESTING GUIDE")
        c.setStrokeColor(LINE)
        c.line(MARGIN, 39, PAGE_W - MARGIN, 39)
        c.setFont("CTISans", 7.7)
        c.drawString(MARGIN, 25, "Research use · source, model and conceptual explanations remain distinct")
        c.setFont("CTIBold", 8)
        c.drawRightString(PAGE_W - MARGIN, 25, str(doc.page))
        c.restoreState()


def screenshot_gallery(styles):
    directory = ROOT / "docs/v5204-evidence"
    preferred = [
        ("overview-desktop.png", "Overview · full-cohort research workspace"),
        ("explainability-desktop.png", "Explainability · actual attribution and guided evidence"),
        ("home-desktop.png", "Research home · DNA introduction and workflow actions"),
        ("settings-desktop.png", "Settings · browser appearance and visual explanations"),
        ("overview-mobile.png", "Mobile · responsive research workspace"),
    ]
    found = [(directory / name, caption) for name, caption in preferred if (directory / name).is_file()]
    if not found:
        return []
    items = [PageBreak(), Paragraph("24. Actual application screenshots", styles["chapter"]),
             Paragraph("Screenshots captured from the application during release verification. Read the accompanying report for exercised workflows and limits.", styles["body"])]
    for index, (path, caption) in enumerate(found):
        if index:
            items.append(PageBreak())
        width, height = ImageReader(str(path)).getSize()
        scale = min(BODY_W / width, 555 / height)
        items.extend([Paragraph(caption, styles["sub"]),
                      Image(str(path), width=width * scale, height=height * scale),
                      Spacer(1, 12), Paragraph(path.name, styles["caption"])])
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "docs/v5.2.0.4-full-guide.md")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/Clinical-Trial-Intelligence-v5.2.0.4-Full-Guide.pdf")
    args = parser.parse_args()
    register_fonts()
    styles = make_styles()
    styles["chapter"].textColor = INK
    styles["sub"].textColor = EMERALD
    styles["body"].fontSize = 10
    styles["body"].leading = 14.6
    styles["list"].fontSize = 10
    styles["list"].leading = 14.6
    source = args.source.read_text(encoding="utf-8")
    config = json.loads((ROOT / "configs/formulas.json").read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    toc = TableOfContents()
    toc.levelStyles = [styles["toc"]]
    toc.dotsMinLevel = 0
    toc.tableStyle = TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0)])
    contents_style = ParagraphStyle("contents-title", parent=styles["chapter"])
    story = [ReleaseCover(), NextPageTemplate("body"), PageBreak(),
             Paragraph("Contents", contents_style),
             Paragraph("Begin with Windows Docker startup in chapter 2. Chapters 6–14 explain data and research use; chapters 15–22 cover testing, every section, files and evidence. Commands are provided in the accompanying Markdown for exact copying.", styles["body"]),
             toc, *markdown_flowables(source, styles, config), *screenshot_gallery(styles)]

    def invariant_canvas(*canvas_args, **canvas_kwargs):
        canvas_kwargs["invariant"] = 1
        return canvas.Canvas(*canvas_args, **canvas_kwargs)

    ReleaseDoc(args.output, styles).multiBuild(story, canvasmaker=invariant_canvas)
    print(f"Created {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
