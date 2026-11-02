from pathlib import Path
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest
from src.api import app


def test_api_forecast_and_inventory_use_validated_inputs():
    client = TestClient(app)
    response = client.post('/forecast', json={'store': '1', 'item': '1', 'horizon': 3, 'method': 'seasonal_naive'})
    assert response.status_code == 200
    assert len(response.json()['forecasts']) == 3
    assert 'synthetic' in response.json()['source']['data_kind']
    assert client.post('/forecast', json={'store': 'UNKNOWN', 'item': '1', 'horizon': 3}).status_code == 400
    assert client.post('/forecast', json={'store': '1', 'item': '1', 'horizon': 99}).status_code == 422
    result = client.post('/inventory', json={'forecast': [10, 20, 30], 'lead_days': 2, 'on_hand': 5, 'daily_std': 0})
    assert result.status_code == 200
    assert result.json()['scenario_only'] is True
    assert result.json()['suggested_order_units'] == 25


def test_real_dashboard_trains_filters_and_calculates_inventory():
    root = Path(__file__).resolve().parents[1]
    at = AppTest.from_file(str(root/'app/streamlit_app.py'), default_timeout=90).run()
    assert not at.exception
    assert any('synthetic' in element.value.lower() for element in at.warning)
    button = next(button for button in at.button if button.label == 'Train / evaluate')
    button.click().run(timeout=90)
    assert not at.exception
    assert len(at.metric) >= 4
    store = next(widget for widget in at.selectbox if widget.label == 'Store')
    store.select('2').run()
    assert not at.exception
    button = next(button for button in at.button if button.label == 'Calculate scenario')
    button.click().run()
    assert not at.exception
    assert any('scenario_only' in element.value for element in at.json)


def test_dashboard_rejects_missing_identifiers_before_filtering(tmp_path, monkeypatch):
    import pandas as pd
    root = Path(__file__).resolve().parents[1]
    data = pd.read_csv(root/'data/raw/demo_sales.csv', dtype={'store': str, 'item': str})
    data.loc[0, 'store'] = None
    path = tmp_path/'invalid.csv'
    data.to_csv(path, index=False)
    monkeypatch.setenv('DEMAND_SALES_CSV', str(path))
    at = AppTest.from_file(str(root/'app/streamlit_app.py')).run()
    assert not at.exception
    assert any('identifiers' in error.value for error in at.error)


def test_dashboard_heldout_export_preserves_string_ids(tmp_path, monkeypatch):
    import pandas as pd
    root = Path(__file__).resolve().parents[1]
    dates = pd.date_range('2024-01-01', periods=120)
    data = pd.concat([pd.DataFrame({'date': dates, 'store': store, 'item': '01', 'sales': 20}) for store in ['001', '1']])
    path = tmp_path/'string_ids.csv'
    data.to_csv(path, index=False)
    monkeypatch.setenv('DEMAND_SALES_CSV', str(path))
    at = AppTest.from_file(str(root/'app/streamlit_app.py'), default_timeout=90).run()
    next(button for button in at.button if button.label == 'Train / evaluate').click().run(timeout=90)
    assert not at.exception
    assert set(at.session_state['result']['test'].store) == {'001', '1'}
