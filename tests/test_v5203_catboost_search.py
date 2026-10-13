"""Artificial software fixtures verify search; scores are not research evidence."""
import json

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sklearn.metrics import brier_score_loss, mean_squared_error

from backend.app.config import Settings
from backend.app.main import create_research_app
from backend.app.schemas import ExperimentRequest
from src.clinical_trial_intelligence import research
from test_catboost_models import records


def test_search_defaults_are_backward_compatible():
    assert research.ExperimentConfig().catboost_search == 'basic'
    assert research.ExperimentConfig().enable_catboost is False
    assert ExperimentRequest().catboost_search == 'basic'
    assert ExperimentRequest().enable_catboost is False


def test_expanded_mode_does_not_enable_catboost_by_itself(tmp_path):
    config = research.ExperimentConfig(catboost_search='expanded', enable_advanced_models=False, bootstrap_samples=0)
    manifest = research.train_experiment(records(), tmp_path, {'is_fixture': True}, config=config)
    assert manifest['config']['enable_catboost'] is False
    assert manifest['config']['catboost_search'] == 'expanded'
    assert set(manifest['models']) == {'median_baseline', 'structured', 'text', 'multimodal'}


@pytest.mark.parametrize('value', ['wide', '', None, True, 1])
def test_search_rejects_unknown_modes(value):
    with pytest.raises(ValueError, match='catboost_search'):
        research.ExperimentConfig(catboost_search=value).validate()
    with pytest.raises(ValidationError, match='catboost_search'):
        ExperimentRequest(catboost_search=value)


def test_basic_grid_preserves_native_parameters_and_order():
    frame = records()
    X = research._features(frame)
    duration = (frame.completion_date - frame.start_date).dt.days.to_numpy()
    labels = (duration > np.quantile(duration[:24], .75)).astype(int)
    models, selection = research._fit_catboost_models(
        X.iloc[:24], duration[:24], labels[:24], X.iloc[24:32], duration[24:32], labels[24:32],
        research.ExperimentConfig(enable_catboost=True))
    details = selection['structured_catboost']
    assert details['search_mode'] == 'basic'
    for task, metric in [('regressor', 'rmse'), ('classifier', 'brier')]:
        trials = details['trials'][task]
        assert [trial['parameters']['depth'] for trial in trials] == [4, 6]
        for trial in trials:
            assert trial['parameters'] == {
                'iterations': 120, 'depth': trial['parameters']['depth'], 'learning_rate': .05,
                'random_seed': 42, 'thread_count': 1, 'task_type': 'CPU', 'verbose': False,
                'allow_writing_files': False, 'loss_function': 'RMSE' if task == 'regressor' else 'Logloss',
            }
            assert trial['metric'] == metric
        selected = min(trials, key=lambda trial: trial['score'])
        assert details[f'{task}_parameters'] == selected['parameters']
        assert models['structured_catboost'][task].named_steps['model'].get_params() == selected['parameters']


def test_expanded_native_search_exports_actual_trials_and_training_only_state(tmp_path):
    frame = records()
    frame.loc[48:, 'enrollment'] = 999_999
    frame.loc[48:, 'phase'] = 'HELD_OUT_ONLY'
    config = research.ExperimentConfig(enable_catboost=True, catboost_search='expanded',
                                       enable_advanced_models=False, bootstrap_samples=0)
    manifest = research.train_experiment(frame, tmp_path, {'is_fixture': True}, config=config)
    details = manifest['models']['structured_catboost']['selection']
    assert json.loads((tmp_path / 'manifest.json').read_text())['models']['structured_catboost']['selection'] == details
    assert manifest['config']['catboost_search'] == 'expanded'
    assert details['search_mode'] == 'expanded'
    assert details['selection_split'] == 'validation'
    assert details['selection_rows'] == manifest['splits']['validation']['rows']
    assert details['refit_on_validation'] is False
    assert details['tie_breaker'] == 'first candidate in declared order'
    artifact = joblib.load(tmp_path / 'models.joblib')
    train_ids = manifest['splits']['train']['nct_ids']
    tuning_ids = manifest['splits']['validation']['nct_ids']
    X_tuning = research._features(frame.loc[frame.nct_id.isin(tuning_ids)])
    tuning_duration = (frame.loc[frame.nct_id.isin(tuning_ids), 'completion_date'] -
                       frame.loc[frame.nct_id.isin(tuning_ids), 'start_date']).dt.days.to_numpy()
    tuning_labels = (tuning_duration > artifact['threshold_days']).astype(int)
    expected_grid = {(depth, l2, iterations) for depth in (4, 6) for l2 in (3, 10) for iterations in (120, 300)}
    for task in ('regressor', 'classifier'):
        trials = details['trials'][task]
        assert len(trials) == 8
        assert {(trial['parameters']['depth'], trial['parameters']['l2_leaf_reg'], trial['parameters']['iterations'])
                for trial in trials} == expected_grid
        assert all(np.isfinite(trial['score']) and trial['score'] >= 0 for trial in trials)
        assert all(trial['parameters']['task_type'] == 'CPU' and trial['parameters']['thread_count'] == 1
                   and trial['parameters']['random_seed'] == 42 for trial in trials)
        winner = min(trials, key=lambda trial: trial['score'])
        assert details[f'{task}_parameters'] == winner['parameters']
        model = artifact['models']['structured_catboost'][task]
        actual_score = (np.sqrt(mean_squared_error(tuning_duration, np.maximum(0, model.predict(X_tuning))))
                        if task == 'regressor' else brier_score_loss(tuning_labels, research._positive_probability(model, X_tuning)))
        assert winner['score'] == pytest.approx(actual_score)
        preprocess = model.named_steps['preprocess']
        assert preprocess.named_transformers_['numeric'].named_steps['scaler'].mean_[0] == pytest.approx(
            frame.loc[frame.nct_id.isin(train_ids), 'enrollment'].mean())
        assert 'HELD_OUT_ONLY' not in preprocess.named_transformers_['categorical'].categories_[1]
    assert manifest['recommendation']['metric'] == 'brier'
    assert manifest['recommendation']['split'] == 'validation'
    assert manifest['duration_recommendation']['metric'] == 'rmse'
    assert manifest['duration_recommendation']['split'] == 'validation'


def test_one_class_fallback_records_only_trials_actually_fitted():
    frame = records()
    X = research._features(frame)
    duration = (frame.completion_date - frame.start_date).dt.days.to_numpy()
    models, selection = research._fit_catboost_models(
        X.iloc[:24], duration[:24], np.zeros(24), X.iloc[24:32], duration[24:32], np.zeros(8),
        research.ExperimentConfig(enable_catboost=True, catboost_search='expanded'))
    details = selection['structured_catboost']
    assert details['one_class_fallback'] is True
    assert details['classifier_parameters'] is None
    assert details['trials']['classifier'] == []
    assert np.all(research._positive_probability(models['structured_catboost']['classifier'], X.iloc[24:32]) == 0)


def test_calibration_and_test_changes_cannot_change_expanded_search_selection(tmp_path):
    original = records()
    duration = (original.completion_date - original.start_date).dt.days.to_numpy()
    frame = original.iloc[np.arange(120) % len(original)].reset_index(drop=True)
    frame['nct_id'] = [f'SOFTWARE-ONLY-SEARCH-{index:03}' for index in range(120)]
    frame['start_date'] = pd.date_range('2000-01-01', periods=120, freq='60D')
    frame['completion_date'] = frame.start_date + pd.to_timedelta(np.resize(duration, 120), unit='D')
    config = research.ExperimentConfig(enable_catboost=True, catboost_search='expanded',
                                       enable_advanced_models=False, bootstrap_samples=0)
    before = research.train_experiment(frame, tmp_path / 'before', {'is_fixture': True}, config=config)
    assert before['splits']['calibration']['rows'] >= 10
    held_out = before['splits']['calibration']['nct_ids'] + before['splits']['test']['nct_ids']
    changed = frame.copy()
    mask = changed.nct_id.isin(held_out)
    changed.loc[mask, 'enrollment'] = 999_999
    changed.loc[mask, 'phase'] = 'UNSEEN_CALIBRATION_AND_TEST'
    changed.loc[mask, 'completion_date'] = changed.loc[mask, 'start_date'] + pd.Timedelta(days=1)
    after = research.train_experiment(changed, tmp_path / 'after', {'is_fixture': True}, config=config)
    for split in ('train', 'validation', 'calibration', 'test'):
        assert before['splits'][split]['nct_ids'] == after['splits'][split]['nct_ids']
    before_branch, after_branch = [manifest['models']['structured_catboost'] for manifest in (before, after)]
    assert before_branch['selection'] == after_branch['selection']
    assert before['recommended_model'] == after['recommended_model']
    assert before['recommended_duration_model'] == after['recommended_duration_model']
    assert before_branch['metrics']['test']['regression']['rmse'] != after_branch['metrics']['test']['regression']['rmse']


@pytest.mark.parametrize('search', ['basic', 'expanded'])
def test_api_records_and_forwards_search_choice(tmp_path, monkeypatch, search):
    captured = []
    # Transport test only: native training is exercised above; avoid rerunning all model families.
    def capture_training(df, output, source_metadata, *, config):
        captured.append(config)
        return {'status': 'completed', 'config': {'catboost_search': config.catboost_search}}
    monkeypatch.setattr(research, 'train_experiment', capture_training)
    app = create_research_app(Settings(storage_dir=str(tmp_path), _env_file=None))
    with TestClient(app) as client:
        starter = client.post('/api/v1/datasets/starter').json()
        payload = {'dataset_id': starter['id'], 'enable_catboost': True}
        if search == 'expanded':
            payload['catboost_search'] = search
        response = client.post('/api/v1/experiments', json=payload)
        assert response.status_code == 202
        assert response.json()['catboost_search'] == search
        saved = client.get('/api/v1/experiments/' + response.json()['id']).json()
        assert saved['status'] == 'completed'
        assert saved['catboost_search'] == search
        assert captured[0].enable_catboost is True
        assert captured[0].catboost_search == search
        assert client.post('/api/v1/experiments', json={**payload, 'catboost_search': 'unbounded'}).status_code == 422
