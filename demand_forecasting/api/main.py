"""Local API. Run: python -m uvicorn api.main:app --host 127.0.0.1 --port 8000."""
import json
import os
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from src.data import ROOT, read_sales, source_info
from src.config import DEMO_MODELS
from src.forecasting import forecast_frame
from src.inventory import inventory_scenario

app = FastAPI(title='Demand Forecasting Learning API', version='2.0.0')


class ForecastRequest(BaseModel):
    store: str
    item: str
    horizon: int = Field(default=7, ge=1, le=7)
    method: Literal['naive', 'seasonal_naive', 'selected', 'linear_regression', 'random_forest'] = 'selected'


class InventoryRequest(BaseModel):
    forecast: list[float] = Field(min_length=1, max_length=7)
    lead_days: int = Field(ge=1, le=7)
    on_hand: float = Field(ge=0)
    daily_std: float = Field(ge=0)
    review_days: int = Field(default=0, ge=0, le=6)
    on_order: float = Field(default=0, ge=0)
    backorders: float = Field(default=0, ge=0)
    service_level: float = Field(default=.95, ge=.5, lt=1)
    pack_size: int = Field(default=1, ge=1)
    minimum_order: float = Field(default=0, ge=0)


@app.get('/health')
def health():
    return {'status': 'ok', 'purpose': 'Local educational decision support; no authentication configured'}


@app.get('/models')
def models():
    path = Path(os.environ.get('DEMAND_MODEL_PATH', str(DEMO_MODELS/'selected_model.joblib'))).parent/'registry.json'
    if not path.is_file():
        return {'available': False, 'models': [], 'message': 'Run python -m src.cli train to generate model files.'}
    return {'available': True, **json.loads(path.read_text())}


@app.post('/forecast')
def forecast(request: ForecastRequest):
    path = Path(os.environ.get('DEMAND_SALES_CSV', str(ROOT/'data/raw/demo_sales.csv')))
    try:
        data = read_sales(path)
        data = data[(data.store == request.store) & (data.item == request.item)]
        model_details = {'method': request.method}
        if request.method not in ['naive', 'seasonal_naive']:
            from src.modeling import load_bundle, forecast_saved
            model = Path(os.environ.get('DEMAND_MODEL_PATH', str(DEMO_MODELS/'selected_model.joblib')))
            if request.method != 'selected':
                model = model.parent/f'{request.method}.joblib'
            bundle = load_bundle(model)
            result = forecast_saved(data, bundle, request.horizon)
            model_details = {'method': bundle['model_name'], 'training_end': bundle['training_end'], 'training_source': bundle.get('source')}
        else:
            result = forecast_frame(data, request.horizon, request.method)
        result['date'] = result.date.dt.strftime('%Y-%m-%d')
        return {'source': source_info(path), 'model': model_details, 'forecasts': result.to_dict(orient='records')}
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/inventory')
def inventory(request: InventoryRequest):
    try:
        return inventory_scenario(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
