# Smart College Management Platform — project report

This LaTeX project contains the updated report for **veltech-ams-mini**. Project facts and the three students' details come from your uploaded LaTeX archive. The faculty's PDF is used for presentation and chapter structure; its E-Payment content, student details and screenshots are not included.

The report retains A4 pages, Times-family text, the blue college cover, centred chapter headings, Roman front-matter numbering and Arabic main-matter numbering. It contains all nine chapters in the supplied order and an IEEE-style numerical bibliography. The compiled report has **32 physical pages**.

## Match to the faculty reference

Chapter 3 follows the reference's **12-page figure-and-explanation sequence**. It occupies physical pages 14–25, printed pages 4–15, as in the sample. Each subsection places a centred illustration and numbered caption above its explanation. Most illustrations use a 150 mm × 100 mm frame; the sitemap and data-flow diagram retain their different reference frame sizes. Screenshots keep their original aspect ratio.

The sequence is sitemap, data flow, Home, login, validation, academic parsing/results, Node.js server, three-tier architecture, reactive form, routing, services and deployment. The reference's Angular, jQuery and MySQL examples are replaced with this project's actual React, Python/DOM and MongoDB implementation. Terminal/code figures show actual project excerpts and recorded local verification; they do not claim a public deployment.

## Open in Overleaf

1. Choose **New Project → Upload Project** and upload this ZIP.
2. Choose **main.tex** as the main document and **pdfLaTeX** as the compiler.
3. Click **Recompile**. Overleaf runs BibTeX when required.
4. Download the PDF. The generated `main.bbl` is included for the existing references.

## Edit your details

Edit `project-info.tex` to change the project title, student names/register numbers, guide, academic session and submission date. The three student entries supplied in your archive are preserved. The numeric submission month is displayed as **October, 2026**.

The Head/Assistant Head alternatives and staff details are retained from your source. Select the applicable Head/Assistant Head before final submission. Signature and examination date spaces remain blank. Use `\&`, `\%` and `\_` for special characters. Recheck the page count after changing content.

## Build on Windows

Install MiKTeX or TeX Live with pdfLaTeX and BibTeX, or use Overleaf without installing anything. In PowerShell, open the extracted report folder and run:

```powershell
.\build.ps1
```

If local PowerShell execution policy blocks that script, run the following commands directly:

```powershell
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
```

The result is `main.pdf`. Ubuntu, Docker and Biber are not needed to compile this report.

## Figures, tables and results

Figures and tables are included where useful, without a five-item limit. The report contains **16 numbered figures**, including **12 in Chapter 3**, and **3 tables**. They cover this project's architecture, data flow, Home, login, validation, attendance, results, registration, events, community and implementation evidence. The university cover seal is unnumbered. Screenshots use clearly identified fictional demonstration records.

The result calculation and screenshot use **Percentage = (CGPA − 0.5) × 10**, as requested: the example CGPA of 8.40 produces 79%. Published source percentages retain priority. This is described as the project's requested conversion, not an independently verified university regulation.

The three tables cover software, recorded verification and a credit-weighted calculation example. They do not contain the faculty sample's payment records.

## Source layout

- `main.tex` — main file and college report formatting.
- `project-info.tex` — student, guide and submission information.
- `frontmatter.tex` — cover, certificate, declaration, approval, abstract, lists and contents.
- `chapters/` — nine project chapters.
- `images/` — project screenshots, university emblem and editable TikZ diagrams.
- `code/` — selected security and server source, Compose keys and recorded local verification output.
- `references.bib`, `references.tex`, `IEEEtran.bst`, `main.bbl` — bibliography data, style and generated entries.
- `PROVENANCE.md` — source and image attribution.

See the supplied PDF and `REPORT-CHECKS.json` for the verified page count and packaging checks. The source ZIP was extracted into a clean directory and rebuilt with pdfLaTeX and BibTeX. Existing application test and live-source observations are historical evidence from the project archive, not new tests performed while preparing this report. Report compilation does not authenticate to AMS or send email.
