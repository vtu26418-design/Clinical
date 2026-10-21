# Smart College Management Platform — LaTeX report

This report completes your pasted college template with the project information from your uploaded report archive. The implementation is named **veltech-ams-mini**.

The template's report class, Times-family text, A4 paper, 20 mm margins, blue college cover, centred chapter headings, front-matter order, Roman/Arabic numbering and nine-chapter order are retained. Its sample car-rental abstract and blank sections are replaced with this project's content. Missing braces, a duplicate environment closure and conflicting package setup in the pasted source are repaired. The student table and declaration use the three entries actually supplied in your project data.

## Open and compile

1. In Overleaf, select **New Project → Upload Project** and upload this ZIP.
2. Set the main file to **main.tex** and the compiler to **pdfLaTeX**.
3. Recompile; if the contents or figure numbers need another pass, recompile again.

All report text, author details and references are in **main.tex**. Keep the included `images/` and `code/` folders beside it. `references-only.tex` is a convenience copy of the references already included in `main.tex`; do not input it again unless you remove the inline copy first.

The bibliography is inline and needs neither BibTeX nor Biber. It contains verified IEEE publications and official university/framework/security documentation. It contains no GitHub repositories or self-references. References are numbered by their first citation in the report.

On Windows with MiKTeX or TeX Live installed, run `build.ps1` from PowerShell. Alternatively, run this command three times:

```powershell
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
```

The output is `main.pdf`. No Ubuntu or Docker installation is needed to compile this report.

## Details and figures

Edit the named commands near the top of `main.tex` to update students, register numbers, guide or date. The three supplied student entries and guide details are retained. The submission date is October, 2026. Choose the appropriate Head/Assistant Head alternative before submission; signature and examination dates remain blank.

The supplied PDF has 32 physical pages, 16 numbered figures (12 in Chapter 3), 3 tables and 12 external references. Images, captions and explanations describe this project's own implementation. Screenshots use fictional demonstration records, explicitly identified in the report. The cover seal is the shared university emblem extracted with its original transparency from the faculty reference. No unrelated project screenshots are included.

The result example uses the requested conversion **Percentage = (CGPA − 0.5) × 10**, so 8.40 gives 79%. This is the project's requested estimate; it is not represented as a newly verified university regulation. Published source percentages take priority.

Historical application test and AMS observations are retained as recorded evidence, without citing an unrelated IEEE paper as their source. This report update does not perform a university login, alter academic records, send Internet email or establish a public deployment. Recheck the page count after editing.
