"""Artificial fixtures check software behavior only; never evidence of model quality."""
import json

import joblib
import numpy as np
import pandas as pd
import pytest

from src.clinical_trial_intelligence import research
from test_research import software_fixture


@pytest.fixture(scope='module')
def v5_run(tmp_path_factory):
    frame = software_fixture(160)
    frame.loc[140:, 'enrollment'] = 999999
    frame.loc[140:, 'brief_summary'] = 'heldoutuniquetoken ' * 200
    directory = tmp_path_factory.mktemp('v5-models')
    manifest = research.train_experiment(frame, directory, {'is_fixture': True},
        config=research.ExperimentConfig(bootstrap_samples=20))
    return frame, directory, manifest, joblib.load(directory / 'models.joblib')


def test_histogram_candidate_excludes_test_extremes_from_fitting(v5_run):
    frame, directory, manifest, artifact = v5_run
    assert 'structured_hist_gradient_boosting' in manifest['models']
    pair = artifact['models']['structured_hist_gradient_boosting']
    train = frame.loc[frame.nct_id.isin(manifest['splits']['train']['nct_ids'])]
    for task in ('regressor', 'classifier'):
        pipeline = pair[task]
        assert pipeline.named_steps['preprocess'].named_transformers_['numeric'].named_steps['scaler'].mean_[0] == pytest.approx(train.enrollment.mean())
        # No randomized internal holdout is allowed to replace chronological tuning.
        assert pipeline.named_steps['model'].early_stopping is False
        query = research._features(frame.tail(2))
        assert isinstance(pipeline.named_steps['preprocess'].transform(query), np.ndarray)
    result = research.predict_trial(frame.iloc[-1].to_dict(), directory, 'structured_hist_gradient_boosting')
    assert result['status'] == 'available'
    assert 'constant' not in result['explanation']['method']
    assert result['explanation']['features'] == []


def test_late_fusion_is_exact_tuning_selected_blend(v5_run):
    frame, directory, manifest, artifact = v5_run
    assert 'multimodal_late_fusion' in manifest['models']
    selection = manifest['models']['multimodal_late_fusion']['selection']
    query = research._features(frame.tail(4))
    pair = artifact['models']['multimodal_late_fusion']
    for task in ('regressor', 'classifier'):
        weight = selection[task + '_structured_weight']
        assert weight in (.25, .5, .75)
        first = artifact['models']['structured_hist_gradient_boosting'][task]
        second = artifact['models']['text'][task]
        if task == 'regressor':
            expected = weight * np.maximum(0, first.predict(query)) + (1 - weight) * np.maximum(0, second.predict(query))
            np.testing.assert_allclose(pair[task].predict(query), expected)
        else:
            expected = weight * research._positive_probability(first, query) + (1 - weight) * research._positive_probability(second, query)
            np.testing.assert_allclose(research._positive_probability(pair[task], query), expected)
    prediction = research.predict_trial(frame.iloc[-1].to_dict(), directory, 'multimodal_late_fusion')
    assert prediction['status'] == 'available'
    assert prediction['explanation']['method'] == 'weighted late fusion'
    assert len(prediction['explanation']['components']) == 2


def test_paired_baseline_comparison_preserves_trial_pairing_and_zero_resample_state():
    assert hasattr(research, 'paired_baseline_comparison')
    result = research.paired_baseline_comparison(
        [10, 20, 30], [11, 21, 31], [12, 22, 32],
        [0, 1, 0], [.1, .9, .1], [.2, .8, .2], bootstrap_samples=30, random_seed=7)
    # Per-trial differences are identical, so every paired resample agrees exactly.
    assert result['mae_delta']['estimate'] == pytest.approx(-1)
    assert result['mae_delta']['lower'] == pytest.approx(-1)
    assert result['mae_delta']['upper'] == pytest.approx(-1)
    assert result['brier_delta']['estimate'] == pytest.approx(-.03)
    assert result['brier_delta']['lower'] == pytest.approx(-.03)
    assert result['brier_delta']['upper'] == pytest.approx(-.03)
    empty = research.paired_baseline_comparison([10], [11], [12], [0], [.1], [.2], bootstrap_samples=0)
    assert empty['mae_delta']['lower'] is None
    assert empty['mae_delta']['valid_resamples'] == 0


def test_distribution_diagnostics_fit_only_training_and_warn_about_tails():
    frame = software_fixture(100)
    frame['enrollment'] = np.arange(100)
    features = research._features(frame)
    support = research._fit_training_support(features)
    assert 'lower_quantile' in support['numeric']['enrollment']
    assert support['numeric']['enrollment']['lower_quantile'] == pytest.approx(.99)
    query = features.iloc[[0]].copy()
    query['enrollment'] = 0.5  # Inside min/max, outside the training central 98%.
    query['protocol_text'] = 'unusually long narrative ' * 1000
    report = research._extrapolation(query, support)
    assert report['outside_training_support'] is False
    assert report['distribution_warning'] is True
    assert 'enrollment' in [item['feature'] for item in report['numeric_tail_features']]
    assert report['text_length']['outside_observed_range'] is True
    assert support['text_length']['maximum'] < len(query.iloc[0].protocol_text)


def test_duration_recommendation_and_baseline_intervals_use_correct_split(v5_run):
    _, directory, manifest, _ = v5_run
    assert 'duration_recommendation' in manifest
    recommendation = manifest['duration_recommendation']
    assert recommendation['split'] == 'validation'
    assert recommendation['metric'] == 'rmse'
    expected = min(manifest['models'], key=lambda name: (manifest['models'][name]['metrics']['validation']['regression']['rmse'], name))
    assert recommendation['model_name'] == expected
    predictions = pd.read_csv(directory / 'held_out_predictions.csv')
    baseline = predictions.loc[(predictions.model_name == 'median_baseline') & (predictions.split == 'test')]
    for name, model in manifest['models'].items():
        comparison = model['metrics']['test']['comparison_to_baseline']
        assert comparison['n'] == manifest['splits']['test']['rows']
        assert comparison['mae_delta']['valid_resamples'] == 20
        rows = predictions.loc[(predictions.model_name == name) & (predictions.split == 'test')]
        delta = abs(rows.actual_duration_days.to_numpy() - rows.predicted_duration_days.to_numpy()).mean() - abs(baseline.actual_duration_days.to_numpy() - baseline.predicted_duration_days.to_numpy()).mean()
        assert comparison['mae_delta']['estimate'] == pytest.approx(delta)
    json.dumps(manifest, allow_nan=False)
