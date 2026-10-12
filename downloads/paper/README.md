# Clinical Trial Intelligence v5.2 — LaTeX paper

## Open and compile

Upload `CTI-v5.2-LaTeX-Source.zip` to Overleaf using **New Project → Upload Project**, select `paper.tex` as the main document, and use **pdfLaTeX**. Locally, run `latexmk -pdf -interaction=nonstopmode -halt-on-error paper.tex` from the extracted directory. No account keys, external services, Python code, or model training are needed to compile the manuscript.

`paper.tex` is the standalone LaTeX source; it needs the accompanying `figures/` directory. `CTI-v5.2-Images.zip` provides that directory separately. The diagrams and chart have vector PDF versions used by LaTeX plus PNG copies. The screenshot is a PNG from the actual running application. `CTI-v5.2-Paper.pdf` is the verified seven-page preview.

## Preserved layout

The supplied custom article class, two-column letter-paper geometry, fonts, title, four-author block, twelve-section sequence, six figure slots, four tables, figure widths/aspect ratios, and seven-page length are preserved. All six figures remain on their original pages and in their original columns. Revised text causes small changes in vertical positions, documented in `verification/manuscript-verification.json`.

Sections VIII and IX have accurate registry-study headings in place of the old synthetic/AACT descriptions. Unsupported pilot numbers were replaced with measurements from the project's frozen ClinicalTrials.gov experiment. The original custom layout is **not the official IEEE Access template**. Actual IEEE Access submission requires the journal's template, which may change pagination; this package follows the user's explicit request to preserve the supplied format.

## Numerical evidence

The frozen 800-record starter snapshot yields 312 eligible trials and 123 temporal exclusions, leaving 105 training, nine tuning, 11 calibration and 64 test records. The prolonged-duration threshold is strictly greater than 1,101 days. Independent calculations reproduce all 27 model/split metric sets, and saved-artifact replay reproduces 756 held-out duration predictions.

The text branch's test MAE is 314.70094620585854 days, RMSE 366.98233683691484 days, and AUROC 0.8074712643678161. Early fusion has MAE 332.9980175278577 days and AUROC 0.7614942528735632. Tuning selects a constant median model for duration and the text model for raw risk. The illustrated duration bundle has a constant 482-day estimate and raw prevalence risk of 26/105; it is not the offline text-risk recommendation. Its nominal 90% interval covers 48/64 test observations (75%).

Full-precision metrics and verification receipts are in `verification/`. These are retrospective research results from a completed-only convenience cohort. Baseline feature availability is unverified. No prospective, clinical, or regulatory validation is claimed. The six-component fixed-reference PCI and five-component training-relative PCI are distinguished explicitly.

## References, figures and authorship

Fourteen relevant references are ordered by first citation and formatted in IEEE numeric style. Original method/dataset sources are used regardless of publisher. Reference metadata was checked against Crossref, PubMed, official sites, and author-maintained project citations where applicable. A list of checked metadata is included in the verification files.

Figures 1–4 and 6 are deterministic diagrams/plots rendered with Matplotlib from project implementation/configuration/data. Figure 5 is a cropped browser screenshot. No image-generation model was used. These assets should not be described as human-only or hand-drawn: Codex assisted the manuscript revision and figure-rendering code. That assistance is disclosed in the acknowledgment, with affected sections and figures identified.

No plagiarism or AI-detector score is certified. StealthWriter's public site was checked, but the manuscript was not submitted to its humanizer or detector. The requested Consensus, Canva, Firecrawl, Supabase, Higgsfield, Context7, LaTeX Document Maker and Zotero plugins were not callable in this session; their use is not claimed.

IEEE guidance consulted:
- https://ieeeaccess.ieee.org/authors/preparing-your-article/
- https://ieeeaccess.ieee.org/authors/post-acceptance-guide/
- https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/ethical-requirements/
- https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/resolution-and-size/

The named authors should review the scientific interpretation, author details, and final submission requirements before submitting.
