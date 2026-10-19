"""Synthetic rows verify arithmetic only, never clinical performance."""
import math

import pytest

from src.clinical_trial_intelligence.model_analysis import analyze_experiment
from test_model_analysis import experiment


def test_quality_adds_median_absolute_error_and_binary_log_loss(tmp_path):
    report = analyze_experiment(experiment(tmp_path))
    row = report['models'][0]
    assert row['regression']['median_absolute_error_days'] == 10
    assert row['classification']['log_loss'] == pytest.approx(-math.log(.8))


def test_filtered_quality_charts_are_bounded_but_metrics_use_every_row(tmp_path):
    rows = [{'nct_id': f'TEST-{i:04}', 'split': 'test', 'model_name': 'model',
             'actual_duration_days': i + 1, 'predicted_duration_days': 10,
             'actual_prolonged': int(i + 1 > 15), 'prolonged_probability': .4,
             'prolonged_threshold_days': 15} for i in range(1200)]
    path = experiment(tmp_path, rows)
    report = analyze_experiment(path, model_names={'model'}, split='test', chart_point_limit=600)
    assert report['models'][0]['n'] == 1200
    assert report['models'][0]['regression']['mae_days'] == pytest.approx(sum(abs(10-i-1) for i in range(1200))/1200)
    scatter = next(chart for chart in report['charts'] if chart['kind'] == 'scatter')
    assert len(scatter['points']) == 600
    assert scatter['population_n'] == 1200
    assert scatter['model_name'] == 'model' and scatter['split'] == 'test'
    assert scatter['points'] == analyze_experiment(path, model_names={'model'}, split='test', chart_point_limit=600)['charts'][0]['points']
    assert 'every' in report['chart_sampling']
