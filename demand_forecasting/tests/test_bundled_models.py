"""Integration check for the actual weights and measured examples shipped to the user."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from src.data import read_sales, source_info
from src.modeling import load_bundle, forecast_saved
from src.forecasting import metrics


def test_distributed_weights_replay_forecasts_and_heldout_metrics():
    root=Path(__file__).resolve().parents[1]
    data=read_sales(root/'data/raw/demo_sales.csv')
    models=root/'models/demo'
    reports=root/'reports/evaluation/demo'
    registry=json.loads((models/'registry.json').read_text())
    manifest=json.loads((reports/'manifest.json').read_text())
    assert registry['source']['source_sha256']==source_info(root/'data/raw/demo_sales.csv')['source_sha256']
    bundle=load_bundle(models/'selected_model.joblib')
    generated=forecast_saved(data,bundle)
    stored=pd.read_csv(reports/'forecast.csv',dtype={'store':str,'item':str})
    np.testing.assert_allclose(generated.prediction,stored.prediction,rtol=1e-10,atol=1e-10)
    for name in ['linear_regression','random_forest']:
        assert load_bundle(models/f'{name}.joblib')['model_name']==name
    heldout=pd.read_csv(reports/'test_predictions.csv')
    for name, group in heldout.groupby('model'):
        recomputed=metrics(group.actual,group.prediction)
        assert recomputed['mae']==manifest['test_metrics'][name]['mae']
