# Demand Forecasting & Inventory Optimization — Month 1

A complete four-week Python data-science learning project, delivered as cumulative weekly milestones. It includes strict sales-data validation, exploratory analysis, leakage-safe recursive forecasting, baseline/model comparisons, inventory scenarios, a Streamlit dashboard, SQL reporting and an optional FastAPI service.

## Download

| Package | Includes |
|---|---|
| [Complete month project](https://raw.githubusercontent.com/vtu26418-design/Clinical/demand-forecasting-month1/downloads/demand-forecasting-month1/Demand_Forecasting_Complete_Month.zip) | Final working project and all four weekly learning guides |
| [Week 1 ZIP](https://raw.githubusercontent.com/vtu26418-design/Clinical/demand-forecasting-month1/downloads/demand-forecasting-month1/Demand_Forecasting_Week_1.zip) | Data validation, cleaning, EDA and charts |
| [Week 2 ZIP](https://raw.githubusercontent.com/vtu26418-design/Clinical/demand-forecasting-month1/downloads/demand-forecasting-month1/Demand_Forecasting_Week_2.zip) | Week 1 plus lag/rolling features and baseline evaluation |
| [Week 3 ZIP](https://raw.githubusercontent.com/vtu26418-design/Clinical/demand-forecasting-month1/downloads/demand-forecasting-month1/Demand_Forecasting_Week_3.zip) | Earlier stages plus model selection, evaluation, forecasts and inventory scenarios |
| [Week 4 ZIP](https://raw.githubusercontent.com/vtu26418-design/Clinical/demand-forecasting-month1/downloads/demand-forecasting-month1/Demand_Forecasting_Week_4.zip) | Complete application, exports, SQL, API and functional tests |

The complete-month ZIP and Week 4 ZIP contain the same final project. All ZIPs share the `demand_forecasting` root folder. Use one evolving Git repository; compare later milestones before copying files so you preserve your own changes and Git history.

- [Browse project source](demand_forecasting/)
- [Read setup instructions](demand_forecasting/README.md)
- [Read the weekly tasks and learning links](demand_forecasting/WEEKLY_LEARNING_PLAN.md)
- [Download the learning guide](https://raw.githubusercontent.com/vtu26418-design/Clinical/demand-forecasting-month1/downloads/demand-forecasting-month1/Month_1_Weekly_Learning_Plan.md)
- [Download verification report](https://raw.githubusercontent.com/vtu26418-design/Clinical/demand-forecasting-month1/downloads/demand-forecasting-month1/VERIFICATION.txt)
- [Download SHA-256 checksums](https://raw.githubusercontent.com/vtu26418-design/Clinical/demand-forecasting-month1/downloads/demand-forecasting-month1/SHA256SUMS.txt)

## Start

Install Python 3.12, extract a ZIP and open a terminal inside `demand_forecasting`. The README contains Windows and macOS/Linux setup commands. Install dependencies in a virtual environment using `requirements-lock.txt`, run `python run_week.py`, and start the final dashboard with `python -m streamlit run app/streamlit_app.py`.

## Learning and evidence

Every weekly guide explains what to do, how to implement it, topics to learn, YouTube/website resources, checks and GitHub deliverables. Source code, notebooks and tests are included. The complete project passed 39 automated tests; each weekly archive was also extracted and its workflow tested independently.

**Bundled sales are explicitly labelled synthetic practice data.** They make the project runnable without a Kaggle account or API key. For real internship findings, download licensed historical sales from [Store Item Demand Forecasting](https://www.kaggle.com/competitions/demand-forecasting-kernels-only/data) and follow `docs/DATA_GUIDE.md`. Inventory quantities are explicit what-if assumptions; no observed stock or supplier records are bundled. Distinguish supplied starter code and your own experiments in submissions.

This project is published on the `demand-forecasting-month1` branch. The original Clinical release on `main` is preserved.
