import numpy as np
import pandas as pd
import pytest
from src.forecasting import make_training, forecast_frame, metrics, evaluate_origins, split_windows


def history(days=120):
    return pd.DataFrame({'date': pd.date_range('2024-01-01', periods=days), 'store': 'A', 'item': 'X', 'sales': np.arange(1, days+1)})


def test_features_never_use_target_or_other_series():
    first = history(32)
    second = history(32).assign(item='Y', sales=np.arange(101, 133))
    result = make_training(pd.concat([second, first]))
    row = result[(result.item == 'X') & (result.date == '2024-01-29')].iloc[0]
    assert row.lag_1 == 28
    assert row.lag_7 == 22
    assert row.mean_7 == 25
    assert row.sales == 29


def test_seasonal_naive_repeats_prior_week_recursively():
    result = forecast_frame(history(28), 9, 'seasonal_naive')
    assert result.prediction.tolist() == [22, 23, 24, 25, 26, 27, 28, 22, 23]
    assert result.date.min() == pd.Timestamp('2024-01-29')


def test_recursive_model_consumes_earlier_prediction():
    class AddOne:
        def predict(self, frame):
            return frame.lag_1.to_numpy() + 1
    result = forecast_frame(history(28), 3, 'regression', AddOne())
    assert result.prediction.tolist() == [29, 30, 31]


def test_metric_known_answers_and_zero_denominator():
    result = metrics([0, 2], [1, 0])
    assert result['mae'] == 1.5
    assert result['rmse'] == pytest.approx(np.sqrt(2.5))
    assert result['bias'] == -0.5
    assert result['wape_percent'] == 150
    assert metrics([0, 0], [1, 1])['wape_percent'] is None


def test_validation_and_test_do_not_overlap():
    windows = split_windows(history())
    assert windows['train_end'] < windows['validation_start']
    assert windows['validation_end'] < windows['test_start']
    assert windows['test_end'] == pd.Timestamp('2024-04-29')


def test_backtest_is_fixed_origin_not_one_step_peeking():
    data = history(40)
    result = evaluate_origins(data, 'naive', [pd.Timestamp('2024-01-28')], 3)
    assert result.prediction.tolist() == [28, 28, 28]
    assert result.actual.tolist() == [29, 30, 31]


def test_rejects_unaligned_series_ends_and_incomplete_truth():
    data = pd.concat([history(40), history(39).assign(item='Y')])
    with pytest.raises(ValueError, match='same last date'):
        forecast_frame(data, 7, 'naive')
    with pytest.raises(ValueError, match='actual'):
        evaluate_origins(history(40), 'naive', [pd.Timestamp('2024-02-09')], 7)
