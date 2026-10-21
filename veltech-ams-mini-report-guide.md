# veltech-ams-mini — WMAD project report

The report is **28 pages in total**, including the cover, certificate, declaration, approval, abstract, lists, contents and references. It retains all nine original chapters, A4 geometry, Times-family text, blue cover and centered chapter style.

There are **five images/visual items in total**: the cover emblem, architecture diagram, data-flow diagram, Home screenshot and Results screenshot. The cover emblem is unnumbered; the other four appear in the List of Figures. No extra image assets are included in this source ZIP.

## Add your details

Edit **project-info.tex** for student names/register numbers, guide/qualification/designation and submission month/year. Confirm the Head/Dean names copied from the original template. Signatures remain blank. Four student slots are retained; if you have fewer members, remove unused cover/signature rows in frontmatter.tex and adjust TeamNames in project-info.tex.

Use `\&`, `\%` and `\_` for special characters. Longer names or added content can affect pagination; recheck the page count after editing.

## Overleaf

1. New Project → Upload Project → select the source ZIP.
2. Set `main.tex` as the main document and **pdfLaTeX** as compiler.
3. Recompile. Overleaf runs BibTeX when needed. Use Recompile from scratch after changing references if necessary.
4. Download the PDF. The main.bbl file is also included, so existing references are available immediately.

## Windows

Install MiKTeX or TeX Live with pdfLaTeX, BibTeX and the packages used in main.tex. Run from PowerShell in the report folder:

```powershell
.\build.ps1
```

Equivalent commands:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Output: `main.pdf`. No Ubuntu or Biber is required.

## IEEE references

Only the references use IEEE style; the college report layout remains intact. The unmodified **IEEEtran.bst** generates bracketed numeric references in citation order from `references.bib`. Edit those entries and use `\cite{key}` in the chapters. The style's original copyright/license notices are preserved. Sources are the actual project repositories, project documentation, AMS and relevant technical documentation; no research papers, authors or DOIs were invented.

## Contents

- main.tex — master document and template formatting.
- project-info.tex — personal fields to fill manually.
- frontmatter.tex — college front matter and contents/lists.
- chapters/ — shortened project chapters in the original order.
- images/ — exactly five visual resources, including two editable vector diagrams.
- code/security.js — actual selected campus-service source.
- references.bib, references.tex, IEEEtran.bst, main.bbl — IEEE bibliography source/style/output.
- PROVENANCE.md — content and style attribution.

The report describes the combined application and previously recorded verification evidence; it does not change the application or claim a new AMS login. Screenshots use fictional demonstration data. Personal credentials and real student records are excluded. Compilation/page-count/asset and fresh-extraction checks are recorded in the downloadable manifest.
