import numpy as np
import pandas as pd
import pytest
from src.modeling import train, load_bundle, forecast_saved


def sales():
    dates = pd.date_range('2024-01-01', periods=120)
    return pd.DataFrame({'date': dates, 'store': '1', 'item': '1',
                         'sales': 20 + 3*np.sin(np.arange(120)*2*np.pi/7)})


def test_model_selection_ignores_final_test_values_and_artifact_replays(tmp_path):
    data = sales()
    first = train(data, tmp_path/'first')
    changed = data.copy()
    changed.loc[changed.date > changed.date.max()-pd.Timedelta(days=28), 'sales'] += 500
    second = train(changed, tmp_path/'second')
    assert first['selected_model'] == second['selected_model']
    assert first['validation_metrics'] == second['validation_metrics']
    assert first['test_metrics'] != second['test_metrics']
    bundle = load_bundle(tmp_path/'first'/'model.joblib')
    result = forecast_saved(data, bundle, 7)
    assert len(result) == 7
    assert result.date.min() == pd.Timestamp('2024-04-30')
    assert np.isfinite(result.prediction).all()
    assert bundle['training_end'] == '2024-04-29'


def test_saved_forecast_refuses_unseen_series_and_backdated_history(tmp_path):
    data = sales()
    train(data, tmp_path)
    bundle = load_bundle(tmp_path/'model.joblib')
    with pytest.raises(ValueError, match='unseen'):
        forecast_saved(data.assign(item='NEW'), bundle)
    with pytest.raises(ValueError, match='before'):
        forecast_saved(data.iloc[:-1], bundle)
    with pytest.raises(ValueError, match='7'):
        forecast_saved(data, bundle, 8)
