"""Artificial fixtures verify leakage boundaries, never research accuracy."""
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from src.clinical_trial_intelligence.research import (
    ExperimentConfig, _features, predict_trial, train_experiment,
)
from test_research import software_fixture


NEW_MODELS = {'accuracy_mean', 'accuracy_phase_shrinkage', 'accuracy_log_structured', 'accuracy_task_selected'}


def test_accuracy_models_are_explicitly_opt_in():
    assert ExperimentConfig().enable_accuracy_models is False
    with pytest.raises(ValueError, match='enable_accuracy_models'):
        ExperimentConfig(enable_accuracy_models='true').validate()


def test_accuracy_candidates_preserve_cohorts_and_replay(tmp_path):
    frame = software_fixture(150)
    cfg = dict(bootstrap_samples=0, enable_advanced_models=False, max_text_features=100)
    old = train_experiment(frame, tmp_path / 'old', {'is_fixture': True}, config=ExperimentConfig(**cfg))
    new = train_experiment(frame, tmp_path / 'new', {'is_fixture': True}, config=ExperimentConfig(**cfg, enable_accuracy_models=True))
    assert new['splits'] == old['splits']
    assert new['target'] == old['target']
    assert set(new['models']) - set(old['models']) == NEW_MODELS
    helper = Path(__file__).parents[1] / 'src/clinical_trial_intelligence/models/accuracy.py'
    assert new['additional_model_source_sha256'] == {'models/accuracy.py': hashlib.sha256(helper.read_bytes()).hexdigest()}
    artifact = joblib.load(tmp_path / 'new/models.joblib')
    old_artifact = joblib.load(tmp_path / 'old/models.joblib')
    X = _features(frame)
    for name in old_artifact['models']:
        for task in ('regressor', 'classifier'):
            np.testing.assert_allclose(artifact['models'][name][task].predict(X), old_artifact['models'][name][task].predict(X), rtol=0, atol=0)
    predictions = pd.read_csv(tmp_path / 'new/held_out_predictions.csv')
    row = frame.iloc[-1].to_dict()
    for name in NEW_MODELS:
        result = predict_trial(row, tmp_path / 'new', name)
        saved = predictions[(predictions.nct_id == row['nct_id']) & (predictions.model_name == name)].iloc[0]
        assert result['status'] == 'available'
        assert result['duration_days'] == pytest.approx(saved.predicted_duration_days)
        assert result['raw_probability'] == pytest.approx(saved.prolonged_probability)
        assert result['probability'] == result['raw_probability']
        assert result['duration_explanation']['units'] in ('days', 'log1p(days)', 'days (before nonnegative clipping)')
        if name in {'accuracy_phase_shrinkage', 'accuracy_log_structured'}:
            assert result['duration_explanation']['status'] == 'unavailable'
            assert result['duration_explanation']['features'] == []
        json.dumps(result, allow_nan=False)
    selected = new['models']['accuracy_task_selected']['selection']
    assert selected['selection_split'] == 'validation'
    assert selected['refit_on_validation'] is False
    assert selected['regressor_component'] in old['models'] or selected['regressor_component'] in NEW_MODELS - {'accuracy_task_selected'}


def test_calibration_and_test_mutations_do_not_fit_or_select(tmp_path):
    frame = software_fixture(150)
    cfg = ExperimentConfig(bootstrap_samples=0, enable_advanced_models=False, max_text_features=100, enable_accuracy_models=True)
    original = train_experiment(frame, tmp_path / 'original', {'is_fixture': True}, config=cfg)
    assert original['splits']['calibration']['rows'] >= 10
    mutated = frame.copy()
    heldout = mutated.nct_id.isin(original['splits']['calibration']['nct_ids'] + original['splits']['test']['nct_ids'])
    mutated.loc[heldout, 'enrollment'] = 999999999
    mutated.loc[heldout, 'phase'] = 'UNSEEN_HELDOUT'
    mutated.loc[heldout, 'brief_summary'] = 'heldoutuniquetoken'
    # One-day outcome changes preserve completion eligibility and temporal purging.
    mutated.loc[heldout, 'completion_date'] += pd.Timedelta(days=1)
    changed = train_experiment(mutated, tmp_path / 'changed', {'is_fixture': True}, config=cfg)
    assert original['splits'] == changed['splits']
    for name in NEW_MODELS:
        assert original['models'][name]['selection'] == changed['models'][name]['selection']
    first = joblib.load(tmp_path / 'original/models.joblib')
    second = joblib.load(tmp_path / 'changed/models.joblib')
    X = _features(frame)
    for name in NEW_MODELS:
        np.testing.assert_array_equal(first['models'][name]['regressor'].predict(X), second['models'][name]['regressor'].predict(X))
        np.testing.assert_array_equal(first['models'][name]['classifier'].predict_proba(X), second['models'][name]['classifier'].predict_proba(X))
    prep = second['models']['accuracy_log_structured']['regressor'].regressor_.named_steps['preprocess']
    train_values = frame.loc[frame.nct_id.isin(changed['splits']['train']['nct_ids']), 'enrollment']
    assert prep.named_transformers_['numeric'].named_steps['imputer'].statistics_[0] == pytest.approx(train_values.median())
    assert 'UNSEEN_HELDOUT' not in prep.named_transformers_['categorical'].categories_[1]


def test_missing_accuracy_artifact_has_no_invented_evidence(tmp_path):
    result = predict_trial({}, tmp_path, 'accuracy_task_selected')
    assert result['status'] == 'unavailable'
    assert result['duration_days'] is None
    assert result['raw_probability'] is None


def test_phase_statistics_shrink_small_groups_and_use_training_fallback():
    from src.clinical_trial_intelligence.models.accuracy import PhaseShrinkage
    X = pd.DataFrame({'phase': ['Phase 1', 'Phase 1', 'Phase 2']})
    target = np.array([100., 200., 900.])
    fitted = PhaseShrinkage().fit(X, target)
    result = fitted.predict(pd.DataFrame({'phase': ['Phase 1', 'Phase 2', 'NEW']}))
    np.testing.assert_allclose(result, [(300 + 20 * 400) / 22, (900 + 20 * 400) / 21, 400])
    one_class = PhaseShrinkage(task='classifier').fit(X, np.ones(3))
    np.testing.assert_array_equal(one_class.predict_proba(pd.DataFrame({'phase': ['NEW']})), [[0., 1.]])


def test_one_class_accuracy_fit_and_unavailable_calibration(tmp_path):
    frame = software_fixture(60)
    frame['completion_date'] = frame['start_date'] + pd.Timedelta(days=30)
    cfg = ExperimentConfig(enable_accuracy_models=True, enable_advanced_models=False, bootstrap_samples=0, max_text_features=100)
    manifest = train_experiment(frame, tmp_path, {'is_fixture': True}, config=cfg)
    assert manifest['splits']['calibration']['rows'] == 0
    for name in NEW_MODELS:
        result = predict_trial(frame.iloc[-1].to_dict(), tmp_path, name)
        assert result['status'] == 'available'
        assert result['raw_probability'] == 0.
        assert result['calibrated_probability'] is None
        assert result['uncertainty']['status'] == 'unavailable'
        assert result['calibration']['status'] == 'unavailable'
    assert manifest['models']['accuracy_log_structured']['selection']['one_class_fallback'] is True
    unavailable = predict_trial(frame.iloc[-1].to_dict(), tmp_path, 'nonexistent_accuracy_model')
    assert unavailable['status'] == 'unavailable'
