# Python API

Run from the project environment: python -m uvicorn api.main:app --host 127.0.0.1 --port 8000. Use the local /docs page for schemas. src.api:app remains an alias.

| Method | Path | Purpose |
|---|---|---|
| GET | /health | Local service status |
| GET | /models | Registry and available artifact names without deserializing weights |
| POST | /forecast | Forecast one store/item for 1–7 days |
| POST | /inventory | Explicit inventory scenario from a forecast path |

Forecast JSON: {"store":"1","item":"1","horizon":7,"method":"selected"}.
Other methods: linear_regression, random_forest, naive, seasonal_naive. Responses identify source/method and learned-model training cutoff/source. Missing weights cause a clear error instead of silent fitting.

Default files: data/raw/demo_sales.csv and models/demo/selected_model.joblib. Set DEMAND_SALES_CSV and DEMAND_MODEL_PATH for your own compatible source/models. Candidate files resolve inside that model directory and are checksum-checked against its registry.

Inventory JSON: {"forecast":[10,20,30,40,50,60,70],"lead_days":2,"review_days":1,"on_hand":5,"daily_std":0,"service_level":0.95}.
The scenario_only flag is true. Lead-plus-review coverage must fit the forecast. Service target is an assumption, not validated probability. This educational API has no production authentication/deployment configuration.
