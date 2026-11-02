# Mapping to the uploaded Data Science PDF

Source: Data Science (1).pdf, Project 1, Technology Stack (page 2) and four-week phases (pages 2–4). The execution PDF supplies GitHub/team/review rules.

| PDF item | Implementation |
|---|---|
| Python 3.9+ | Python 3.12 tested; application and notebook kernels are Python |
| pandas / NumPy | Daily sales, validation, features and metrics |
| scikit-learn | Pipelines, Linear Regression and Random Forest |
| XGBoost where appropriate | Optional in the PDF; not required/installed here. CPU-friendly existing candidates and baselines suit this bounded scope |
| statsmodels | Training-series seasonal decomposition in notebook 01; descriptive diagnostic, not forecasting input |
| SQL | SQLite tables/SQL aggregation through Python in src/reporting.py and notebook 04 |
| FastAPI | api/main.py with schemas and functional tests |
| Plotly or Streamlit | Python Streamlit dashboard and Plotly charts |
| Suitable visualization/testing tools | matplotlib, pytest, HTTPX and Streamlit tests |
| requirements.txt | Pinned direct requirements and tested requirements-lock.txt |
| Reproducible notebooks | Four executable Python Jupyter notebooks with tasks and explanations |
| Source/assumptions | DATA_GUIDE.md, registry, model card and explicit inventory inputs |

Jupyter Notebook is the document/development format; its kernel language is Python. GitHub language percentages describe file contents. They are not versions and are not prescribed by the PDFs. No language-statistics manipulation is used.

There is no custom JavaScript/TypeScript/HTML/CSS frontend or batch/shell implementation. Streamlit and Jupyter supply their own interfaces as Python dependencies; SQL exercises run through Python. start_dashboard.py is the launcher.
