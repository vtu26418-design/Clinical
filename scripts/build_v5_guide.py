"""Build the complete v5 operating manual from its reviewed Markdown source.

Run from any directory: python scripts/build_v5_guide.py
Requires ReportLab. No application/provider calls are made. The Markdown is the
editable content source; diagrams below illustrate exact formulas and roles.
"""
from __future__ import annotations

import argparse
from functools import partial
from html import escape
import json
from pathlib import Path
import re
import textwrap

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, NextPageTemplate, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/V5_FULL_GUIDE.md"
OUTPUT = ROOT / "docs/Clinical-Trial-Intelligence-v5-Full-Guide.pdf"
NAVY = colors.HexColor("#102C40")
TEAL = colors.HexColor("#087F80")
INK = colors.HexColor("#253C4B")
MUTED = colors.HexColor("#5E7180")
LINE = colors.HexColor("#DCE6EB")
PALE = colors.HexColor("#F1F7F8")
PAGE_W, PAGE_H = A4
MARGIN = 52
BODY_W = PAGE_W - 2 * MARGIN


def register_fonts() -> None:
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/local/share/fonts/dejavu"),
    ]
    directory = next((p for p in candidates if (p / "DejaVuSans.ttf").exists()), None)
    if directory:
        for name, file in [
            ("CTISans", "DejaVuSans.ttf"),
            ("CTIBold", "DejaVuSans-Bold.ttf"),
            ("CTIMono", "DejaVuSansMono.ttf"),
        ]:
            pdfmetrics.registerFont(TTFont(name, str(directory / file)))
        pdfmetrics.registerFontFamily("CTISans", normal="CTISans", bold="CTIBold", italic="CTISans", boldItalic="CTIBold")
    else:
        # Built-in PDF fonts keep this generator portable on a fresh machine.
        for alias, face in [("CTISans", "Helvetica"), ("CTIBold", "Helvetica-Bold"), ("CTIMono", "Courier")]:
            pdfmetrics.registerFont(pdfmetrics.Font(alias, face, "WinAnsiEncoding"))
        pdfmetrics.registerFontFamily("CTISans", normal="CTISans", bold="CTIBold", italic="CTISans", boldItalic="CTIBold")


def rich(text: str) -> str:
    # The source uses only this small subset of Markdown; never permit raw HTML.
    text = escape(text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<link href="\2" color="#087F80">\1</link>', text)
    text = re.sub(r"`([^`]+)`", r'<font name="CTIMono" size="8.6">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


def make_styles() -> dict[str, ParagraphStyle]:
    base = dict(fontName="CTISans", fontSize=9.6, leading=13.8, textColor=INK, splitLongWords=1, spaceAfter=8)
    return {
        "body": ParagraphStyle("body", **base),
        "chapter": ParagraphStyle("chapter", fontName="CTIBold", fontSize=21, leading=26, textColor=NAVY, spaceAfter=18, keepWithNext=True),
        "sub": ParagraphStyle("sub", fontName="CTIBold", fontSize=12, leading=17, textColor=TEAL, spaceBefore=9, spaceAfter=8, keepWithNext=True),
        "table": ParagraphStyle("table", fontName="CTISans", fontSize=8.1, leading=11.2, textColor=INK, spaceAfter=0, splitLongWords=1),
        "tablehead": ParagraphStyle("tablehead", fontName="CTIBold", fontSize=8.5, leading=12, textColor=colors.white, spaceAfter=0, splitLongWords=1),
        "code": ParagraphStyle("code", fontName="CTIMono", fontSize=8.1, leading=11.4, textColor=INK, spaceAfter=0, splitLongWords=1),
        "list": ParagraphStyle("list", **{**base, "leftIndent": 17, "firstLineIndent": -17, "spaceAfter": 7}),
        "caption": ParagraphStyle("caption", fontName="CTISans", fontSize=8.5, leading=12.3, textColor=MUTED, spaceAfter=10),
        "toc": ParagraphStyle("toc", fontName="CTISans", fontSize=9.3, leading=17.2, textColor=INK, leftIndent=0, firstLineIndent=0, spaceBefore=0, spaceAfter=0),
    }


class Cover(Flowable):
    def __init__(self) -> None:
        Flowable.__init__(self)
        self.width, self.height = BODY_W, 675

    def draw(self) -> None:
        c = self.canv
        c.setFillColor(NAVY)
        c.roundRect(0, 144, BODY_W, 514, 16, stroke=0, fill=1)
        c.setFillColor(TEAL)
        c.roundRect(24, 609, 95, 24, 8, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("CTIBold", 10)
        c.drawString(35, 617, "CTI / v5")
        c.setFont("CTIBold", 30)
        for y, line in [(554, "Clinical Trial"), (514, "Intelligence"), (474, "Workbench")]:
            c.drawString(30, y, line)
        c.setStrokeColor(colors.HexColor("#3D697C"))
        c.line(30, 436, BODY_W - 30, 436)
        c.setFont("CTIBold", 16)
        c.drawString(30, 402, "Full operating & testing guide")
        c.setFont("CTISans", 10.5)
        for y, line in [
            (370, "Import. Predict. Review. Preserve."),
            (339, "Saved models, project access and traceable research evidence."),
            (318, "Windows / macOS / Linux - Python 3.12"),
            (297, "A local research workbench with a real optional AI assistant."),
        ]:
            c.drawString(30, y, line)
        c.setFillColor(colors.HexColor("#75D2C6"))
        for i, label in enumerate(["PROTOCOL", "EVIDENCE", "SCENARIO"]):
            x = 30 + 143 * i
            c.circle(x + 10, 225, 10, stroke=0, fill=1)
            c.setFont("CTIBold", 8)
            c.drawString(x, 196, label)
        c.setFillColor(INK)
        c.setFont("CTIBold", 10)
        c.drawString(0, 110, "Research decision support - not clinical or regulatory advice")
        c.setFont("CTISans", 9)
        c.setFillColor(MUTED)
        for y, line in [(86, "Includes first-owner setup, every-screen checks and model governance."),
                        (66, "Static preview and full Python backend have different capabilities."),
                        (35, "Manual edition: 9 October 2026  |  Research use only")]:
            c.drawString(0, y, line)


class Diagram(Flowable):
    def __init__(self, kind: str, config: dict) -> None:
        Flowable.__init__(self)
        self.kind, self.config = kind, config
        self.width = BODY_W
        self.height = {"planning": 135, "validation": 142, "pci": 172}[kind]

    def draw(self) -> None:
        c = self.canv
        c.setFillColor(PALE)
        c.roundRect(0, 0, self.width, self.height, 9, fill=1, stroke=0)
        c.setFont("CTIBold", 10)
        c.setFillColor(NAVY)
        titles = {"planning": "Planning known answer: 21 months under stated assumptions", "validation": "Chronological roles - diagram is explanatory, with no invented counts", "pci": "PCI known answer: every value at half its ceiling gives 50 points"}
        c.drawString(14, self.height - 23, titles[self.kind])
        if self.kind == "planning":
            x, y, w, h = 14, 55, self.width - 28, 31
            for months, name, col in [(3, "Startup", NAVY), (6, "Recruitment", TEAL), (12, "Follow-up", colors.HexColor("#2BABB0"))]:
                sw = w * months / 21
                c.setFillColor(col)
                c.rect(x, y, sw, h, fill=1, stroke=0)
                c.setFillColor(colors.white)
                c.setFont("CTIBold", 8.6)
                c.drawCentredString(x + sw / 2, y + 11, f"{months} months")
                c.setFillColor(INK)
                c.setFont("CTISans", 8.5)
                c.drawCentredString(x + sw / 2, y - 14, name)
                x += sw
            c.setFont("CTIMono", 8.5)
            c.setFillColor(MUTED)
            c.drawString(14, 15, "120 / (10 sites * 2 participants/site/month) = 6 recruitment months")
        elif self.kind == "validation":
            roles = [("TRAIN", "Fit preprocessing", "and model pipelines"), ("TUNE", "Choose parameters", "and risk branch"), ("CALIBRATE", "Residual intervals;", "supported calibration"), ("TEST", "Held-out metrics;", "no model selection")]
            gap = 8
            sw = (self.width - 28 - 3 * gap) / 4
            for i, (name, line1, line2) in enumerate(roles):
                x = 14 + i * (sw + gap)
                c.setFillColor(NAVY if i in (0, 3) else TEAL)
                c.roundRect(x, 53, sw, 49, 6, fill=1, stroke=0)
                c.setFillColor(colors.white)
                c.setFont("CTIBold", 9)
                c.drawCentredString(x + sw / 2, 79, name)
                c.setFont("CTISans", 7.1)
                c.drawCentredString(x + sw / 2, 66, line1)
                c.drawCentredString(x + sw / 2, 56, line2)
            c.setFillColor(MUTED)
            c.setFont("CTISans", 8)
            c.drawString(14, 30, "Whole start-date groups remain intact. Outcome availability is purged at cutoffs.")
            c.drawString(14, 15, "Earlier original-validation groups tune; later groups calibrate. Inspect actual manifest IDs.")
        else:
            components = self.config["fixed_reference_pci"]["components"]
            maxbar = 230
            for i, comp in enumerate(components):
                y = 124 - i * 19
                label = comp["label"]
                weight = comp["weight"]
                c.setFont("CTISans", 8)
                c.setFillColor(INK)
                c.drawString(14, y + 1, label)
                c.setFillColor(LINE)
                c.roundRect(160, y - 2, maxbar, 10, 3, fill=1, stroke=0)
                c.setFillColor(TEAL)
                c.roundRect(160, y - 2, maxbar * (weight / 2) / 25, 10, 3, fill=1, stroke=0)
                c.setFillColor(INK)
                c.setFont("CTIMono", 8)
                c.drawString(402, y, f"{weight / 2:g} / {weight:g}")
            c.setFont("CTISans", 7.8)
            c.setFillColor(MUTED)
            c.drawString(14, 12, "Bars use one common 0-25 contribution scale. These are formula inputs, not trial outcomes.")


class GuideDoc(BaseDocTemplate):
    def __init__(self, path: Path, styles: dict) -> None:
        super().__init__(str(path), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=64, bottomMargin=52, title="Clinical Trial Intelligence Workbench v5 - Full Guide",
                         author="Clinical Trial Intelligence Workbench", subject="Operating, testing, formulas, troubleshooting and upgrade manual")
        self.styles = styles
        self.chapter_title = "Full operating and testing guide"
        frame = Frame(MARGIN, 52, BODY_W, PAGE_H - 116, id="body", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id="cover", frames=[frame], onPage=self.cover_page),
            PageTemplate(id="body", frames=[frame], onPage=self.body_page),
        ])

    def cover_page(self, c, doc) -> None:
        c.setFillColor(TEAL)
        c.rect(0, PAGE_H - 9, PAGE_W, 9, fill=1, stroke=0)

    def body_page(self, c, doc) -> None:
        c.saveState()
        c.setFillColor(TEAL)
        c.rect(0, PAGE_H - 5, PAGE_W, 5, fill=1, stroke=0)
        c.setFont("CTIBold", 8.4)
        c.setFillColor(NAVY)
        c.drawString(MARGIN, PAGE_H - 33, "CTI WORKBENCH / v5")
        c.setFont("CTISans", 8)
        c.setFillColor(MUTED)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - 33, "OPERATING + TESTING MANUAL")
        c.setStrokeColor(LINE)
        c.line(MARGIN, 39, PAGE_W - MARGIN, 39)
        c.setFont("CTISans", 7.6)
        c.drawString(MARGIN, 25, "Research decision support | source and model evidence remain distinct")
        c.setFont("CTIBold", 8)
        c.drawRightString(PAGE_W - MARGIN, 25, str(doc.page))
        c.restoreState()

    def afterFlowable(self, flowable) -> None:
        if isinstance(flowable, Paragraph) and flowable.style.name == "chapter":
            label = flowable.getPlainText()
            key = "chapter_" + re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(label, key, level=0, closed=False)
            self.notify("TOCEntry", (0, label, self.page, key))


def table(rows: list[list[str]], styles: dict) -> Table:
    columns = len(rows[0])
    if columns == 2:
        ratios = [0.29, 0.71]
    elif columns == 3:
        ratios = [0.22, 0.37, 0.41]
    elif columns == 4:
        ratios = [0.28, 0.40, 0.16, 0.16]
    else:
        ratios = [1 / columns] * columns
    # Narrower content in the dedicated PCI table leaves labels/keys readable.
    cells = [[Paragraph(rich(cell), styles["tablehead"] if i == 0 else styles["table"]) for cell in row] for i, row in enumerate(rows)]
    t = Table(cells, colWidths=[BODY_W * r for r in ratios], repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, NAVY),
        ("LINEBELOW", (0, 1), (-1, -1), 0.35, LINE),
    ]))
    t.spaceAfter = 13
    return t


def code_block(lines: list[str], styles: dict) -> Table:
    # Wrap long commands as visual continuation lines without altering the source.
    # No shell continuation token is inserted: copy exact commands from Markdown.
    wrapped = []
    mono_char_w = pdfmetrics.stringWidth("M", "CTIMono", styles["code"].fontSize)
    width = max(40, int((BODY_W - 24) / mono_char_w))
    for line in lines:
        wrapped.extend(textwrap.wrap(line, width=width, subsequent_indent="  ", break_long_words=True,
                                     break_on_hyphens=False, replace_whitespace=False, drop_whitespace=False) or [""])
    content = "<br/>".join(escape(line).replace(" ", "&#160;") for line in wrapped)
    t = Table([[Paragraph(content, styles["code"])]], colWidths=[BODY_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                           ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    t.spaceAfter = 13
    return t


def validate_formula_table(source: str, config: dict) -> None:
    for comp in config["fixed_reference_pci"]["components"]:
        expected = f"| {comp['label']} | `{comp['key']}` | {comp['ceiling']:g} | {comp['weight']:g} |"
        if expected not in source:
            raise ValueError(f"Guide PCI table disagrees with shared formula configuration: {comp['key']}")


def markdown_flowables(source: str, styles: dict, config: dict) -> list:
    items = []
    lines = source.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("# "):
            i += 1
            continue
        if line.startswith("## "):
            items.extend([PageBreak(), Paragraph(rich(line[3:]), styles["chapter"])])
            i += 1
            continue
        if line.startswith("### "):
            items.append(Paragraph(rich(line[4:]), styles["sub"]))
            i += 1
            continue
        if line.startswith("```"):
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            items.append(code_block(block, styles))
            i += 1
            continue
        if line.startswith("| "):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c.replace(" ", "")) for c in row):
                    rows.append(row)
                i += 1
            if any(len(row) != len(rows[0]) for row in rows):
                raise ValueError("Markdown table has uneven columns")
            items.append(table(rows, styles))
            continue
        figure = re.fullmatch(r"<!-- figure:(\w+) -->", line)
        if figure:
            items.extend([Diagram(figure.group(1), config), Spacer(1, 11)])
            i += 1
            continue
        pagebreak = re.fullmatch(r"<!-- pagebreak: (.+) -->", line)
        if pagebreak:
            items.extend([PageBreak(), Paragraph(rich(pagebreak.group(1)), styles["sub"])])
            i += 1
            continue
        if re.match(r"^\d+\. ", line):
            items.append(Paragraph(rich(line), styles["list"]))
            i += 1
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,3} |\| |```|<!--|\d+\. )", lines[i].strip()):
            paragraph.append(lines[i].strip())
            i += 1
        items.append(Paragraph(rich(" ".join(paragraph)), styles["body"]))
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    register_fonts()
    styles = make_styles()
    source = args.source.read_text(encoding="utf-8")
    config = json.loads((ROOT / "configs/formulas.json").read_text(encoding="utf-8"))
    validate_formula_table(source, config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    toc = TableOfContents()
    toc.levelStyles = [styles["toc"]]
    toc.dotsMinLevel = 0
    toc.tableStyle = TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                ("TOPPADDING", (0, 0), (-1, -1), 1),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 1)])
    doc = GuideDoc(args.output, styles)
    story = [Cover(), NextPageTemplate("body"), PageBreak(), Paragraph("Contents", styles["chapter"]),
             Paragraph("Use chapter bookmarks in your PDF viewer. The operating sequence, every-screen checks and research limits are all included.", styles["body"]), toc,
             *markdown_flowables(source, styles, config)]
    # Contents itself is not a chapter: avoid a self-referential TOC/bookmark.
    story[3].style = ParagraphStyle("contents-title", parent=styles["chapter"])
    def invariant_canvas(*canvas_args, **canvas_kwargs):
        canvas_kwargs["invariant"] = 1
        return canvas.Canvas(*canvas_args, **canvas_kwargs)
    doc.multiBuild(story, canvasmaker=invariant_canvas)
    print(f"Created {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
