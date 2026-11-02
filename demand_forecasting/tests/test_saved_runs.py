from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from src.artifacts import dataset_signature, restore_run, run_locations
from src.modeling import train


def example():
    return pd.DataFrame({'date': pd.date_range('2024-01-01', periods=120), 'store': '01', 'item': '001',
                         'sales': 20 + np.sin(np.arange(120)*2*np.pi/7)*3})


def test_saved_run_restores_and_rejects_different_dataset(tmp_path):
    data = example()
    models, reports = run_locations(dataset_signature(data), tmp_path)
    train(data, reports, {'data_kind': 'synthetic fixture'}, model_directory=models)
    restored = restore_run(data, models, reports)
    assert restored['manifest']['selected_model'] in ['naive', 'seasonal_naive', 'linear_regression', 'random_forest']
    assert len(restored['forecasts']) == 7
    assert restored['forecasts'].date.min() == pd.Timestamp('2024-04-30')
    assert set(restored['test'].store) == {'01'}
    assert restore_run(data.assign(sales=data.sales+1), models, reports) is None


def test_dashboard_restores_saved_model_without_retraining(tmp_path, monkeypatch):
    data = example()
    csv = tmp_path/'sales.csv'
    data.to_csv(csv, index=False)
    # Round-trip the CSV exactly as the UI will so the canonical signature matches.
    from src.data import read_sales
    data = read_sales(csv)
    models, reports = run_locations(dataset_signature(data), tmp_path)
    train(data, reports, {'data_kind': 'synthetic fixture'}, model_directory=models)
    monkeypatch.setenv('DEMAND_RUN_ROOT', str(tmp_path))
    monkeypatch.setenv('DEMAND_SALES_CSV', str(csv))
    def fitting_forbidden(*args, **kwargs):
        raise AssertionError('Startup must reuse saved weights, not fit a new model.')
    monkeypatch.setattr('src.modeling.train', fitting_forbidden)
    root = Path(__file__).resolve().parents[1]
    at = AppTest.from_file(str(root/'app/dashboard.py'), default_timeout=90).run()
    assert not at.exception
    assert len(at.metric) >= 4
    assert any(tab.label == 'Models' for tab in at.tabs)
    assert (models/'selected_model.joblib').is_file()


def test_canonical_api_and_legacy_entrypoints_share_application():
    from api.main import app as canonical
    from src.api import app as legacy
    assert canonical is legacy


def test_restore_rejects_reports_from_another_same_dataset_experiment(tmp_path):
    data = example()
    train(data,tmp_path/'reports_a',{'data_kind':'synthetic experiment A'},model_directory=tmp_path/'models_a')
    train(data,tmp_path/'reports_b',{'data_kind':'synthetic experiment B'},model_directory=tmp_path/'models_b')
    with pytest.raises(ValueError,match='different model|model.*report|report.*model'):
        restore_run(data,tmp_path/'models_a',tmp_path/'reports_b')


def test_restore_rejects_modified_prediction_report(tmp_path):
    data = example()
    train(data,tmp_path/'reports',model_directory=tmp_path/'models')
    report=tmp_path/'reports/test_predictions.csv'
    content=pd.read_csv(report,dtype={'store':str,'item':str})
    content.loc[0,'actual'] += 1000
    content.to_csv(report,index=False)
    with pytest.raises(ValueError,match='report checksum'):
        restore_run(data,tmp_path/'models',tmp_path/'reports')
