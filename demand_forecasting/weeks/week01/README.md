## Week 1 — Data collection, quality and EDA
**Goal:** recreate a validated daily dataset and explain its limitations.

**Topics:** Python functions/collections/files/exceptions; NumPy arrays and descriptive statistics; pandas filtering, groupby and datetime operations; duplicates, missingness and zero versus missing sales; line/bar charts; immutable raw data and provenance.

**What to do and how:**
1. Create your GitHub repository and install the environment using README.md.
2. Read `src/data.py`. Load the practice CSV, inspect columns and count store–item series.
3. Run `python -m src.cli prepare`. Inspect `reports/week01/audit.json`, `series_summary.csv`, `weekday_sales.csv` and `sales_overview.png`.
4. Open `notebooks/01_data_exploration.ipynb` if you use Jupyter. Explain weekday patterns and differences between products.
5. Try a copy with a duplicate key, a missing day or negative sales. The validator should refuse the input instead of concealing the problem.
6. Obtain licensed real sales, prepare a small subset and document the data dictionary.
7. Run `python -m pytest -q`, write your findings in `weeks/week01/README.md`, and commit actual changes.

**Day plan:** Day 1 Python/Git/setup; Day 2 pandas loading/filtering; Day 3 audit dates/keys; Day 4 cleaning functions; Day 5 charts; Day 6 real-data subset and checks; Day 7 report and reproducibility.

**Learn on YouTube:**
- [Corey Schafer: Python beginner playlist](https://www.youtube.com/playlist?list=PL-osiE80TeTt2d9bfVyTiXJA-UTHn6WwU)
- [Corey Schafer: pandas playlist](https://www.youtube.com/playlist?list=PL-osiE80TeTsWmV9i9c58mdDCSskIFdDS)
- [freeCodeCamp: Git/GitHub channel search](https://www.youtube.com/@freecodecamp/search?query=git%20github)

**Learn on websites:** [Python tutorial](https://docs.python.org/3/tutorial/), [pandas introductory tutorials](https://pandas.pydata.org/docs/getting_started/intro_tutorials/), [Seaborn tutorial](https://seaborn.pydata.org/tutorial.html), [GitHub Hello World](https://docs.github.com/en/get-started/start-your-journey/hello-world).

**GitHub deliverables:** validated processing code, source notes/data dictionary, EDA notebook, quality report, charts, tests and Week 1 notes. Completion check: another person can recreate the outputs from untouched raw input.


Record your own observations, commands, measured results, screenshots, mistakes and fixes below.
