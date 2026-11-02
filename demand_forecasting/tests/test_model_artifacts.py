import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from src.modeling import train, load_bundle, forecast_saved


def sample():
    return pd.DataFrame({'date': pd.date_range('2024-01-01', periods=120), 'store': '01', 'item': '001',
                         'sales': 20 + np.sin(np.arange(120)*2*np.pi/7)*3})


def test_separate_models_directory_contains_replayable_candidates_and_registry(tmp_path):
    models, reports = tmp_path/'models', tmp_path/'reports'
    result = train(sample(), reports, {'data_kind': 'synthetic test fixture'}, model_directory=models)
    registry = json.loads((models/'registry.json').read_text())
    entries = {entry['name']: entry for entry in registry['models']}
    assert set(entries) == {'naive', 'seasonal_naive', 'linear_regression', 'random_forest'}
    assert registry['selected_model'] == result['selected_model']
    assert 'synthetic' in registry['source']['data_kind']
    for name in ['linear_regression', 'random_forest']:
        bundle = load_bundle(models/entries[name]['file'])
        assert bundle['model_name'] == name
        forecast = forecast_saved(sample(), bundle)
        assert len(forecast) == 7 and np.isfinite(forecast.prediction).all()
    selected = load_bundle(models/'selected_model.joblib')
    assert selected['model_name'] == result['selected_model']
    assert (reports/'test_predictions.csv').is_file()
    card = json.loads((models/'model_card.json').read_text())
    assert card['forecast_horizon_days'] == 7
    assert card['independent_business_validation'] is False


def test_registry_checksum_rejects_tampered_candidate_before_loading(tmp_path):
    train(sample(), tmp_path/'reports', model_directory=tmp_path/'models')
    path = tmp_path/'models'/'linear_regression.joblib'
    path.write_bytes(b'not a trusted model')
    with pytest.raises(ValueError, match='checksum'):
        load_bundle(path)
