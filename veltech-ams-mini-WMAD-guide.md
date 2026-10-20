# veltech-ams-mini — WMAD project report

This is the LaTeX report source for the combined veltech-ams-mini V1.8 project, based on the supplied `WMAD-SS2627-REPORT-LATEX.docx` template.

## Add your personal details

Edit **project-info.tex**. Fill in the four student names/register numbers, guide name/qualification/designation, and submission month/year. The same fields update the cover, certificate, declaration and approval sheet. The four student slots follow the template. If your team has fewer members, remove the unused cover rows and signature blocks in `frontmatter.tex`, and remove those names from `TeamNames` in `project-info.tex`.

The Head/Assistant Head and Dean names were copied from your template. Confirm/update them before submission. Signatures and dates are deliberately blank. The course code, degree, department and SUMMER 2026–2027 label are retained from the supplied template.

Escape LaTeX special characters in entered text: use `\&` for `&`, `\%` for `%`, and `\_` for `_`.

## Compile on Overleaf

1. Create a new project → Upload Project → select the LaTeX source ZIP.
2. Open `main.tex` and select it as the main document.
3. Set the compiler to **pdfLaTeX** and click Recompile. Compile again if the contents or figure/table lists need updating.
4. Edit `project-info.tex`, recompile and download the resulting PDF.

## Compile on Windows

Install MiKTeX or TeX Live with the packages used in `main.tex` (including TikZ, sectsty, enumitem, listings and xurl). In PowerShell inside this report folder, run:

```powershell
.\build.ps1
```

Or run the following command three times:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
```

The output is `main.pdf`. No Ubuntu, Python, Node.js, database, app credentials or Biber is required to compile the report.

## Files

- `main.tex`: main document and template styling.
- `project-info.tex`: editable personal metadata.
- `frontmatter.tex`: cover, certificate, declaration, approval, abstract and lists.
- `chapters/`: all nine chapters in the supplied order.
- `images/`: original project screenshots/assets and editable TikZ diagrams.
- `code/`: selected actual project files used by the source-code chapter.
- `references.tex`: numbered bibliography.
- `PROVENANCE.md`: content, image and verification sources.

## Template handling

The report retains the 10pt report class, Times-family body, A4 geometry (20mm left/right/top and 250mm text height), blue title page, centered chapter headings, roman front matter, arabic chapters, section hierarchy and nine-chapter order. Unsupported sample technologies in the section titles were renamed to the technologies actually used by this project; the heading levels/order are unchanged.

Minimal compilation repairs address an unmatched flushleft, unsafe contents paragraph writing, enumerate/enumitem load order and the duplicated geometry package invocation. The unused biblatex loader was replaced by a standard numbered bibliography so the supplied source compiles with pdfLaTeX alone. Compatible xcolor supports the original colors and diagrams. Small front-page spacing adjustments keep the four template student slots on their intended pages. Code uses local monospace formatting with the template's framed, numbered listing style. The original geometry's redundant width setting may issue an over-specification warning; the effective margins and output match the template.

## Content boundaries

The report describes the actual combined V1.8 implementation and existing project verification evidence as of 20 October 2026. It is not a claim of a new live university test. All screenshot student names, grades, attendance, posts, events and classroom records are demonstration fixtures. No actual student credentials, cookies, private reports or signing keys are included. Published AMS values and locally calculated estimates are distinguished. Missing source/provider data and incomplete Android/production validation are identified in the report.
