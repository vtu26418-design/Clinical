# Reference and design choices

The user supplied https://github.com/Aryansgit-web/Demand-Forecasting-Inventory-Optimization-Using-Machine-Learning as an organizational reference. Its README/tree were inspected read-only at commit 36d6f7ae1b361a3fc068f49e710d24e2dae7f82c.

This project uses a similar api/app/data/docs/models/notebooks/reports/src/tests layout. No implementation, data, artifacts or reported metrics are copied. Its own evaluated workflow is daily store/item demand with a seven-day recursive horizon, Linear Regression/Random Forest candidates and naive/weekly-repeat baselines. The reference uses UCI transactions and different weekly models. Its accuracy figures are not this project's results.

Serving weights are included under models/demo with a registry/card; dashboard runs persist separately. Python and four Jupyter notebooks follow the PDF. Inventory values remain explicitly assumed what-if scenarios.
