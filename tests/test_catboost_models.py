"""CatBoost checks use artificial records solely to verify software behavior."""
import json

import joblib
import numpy as np
import pandas as pd
import pytest

from src.clinical_trial_intelligence.research import ExperimentConfig, predict_trial, train_experiment


def records():
    rng = np.random.default_rng(41)
    start = pd.date_range('2000-01-01', periods=80, freq='60D')
    return pd.DataFrame({
        'nct_id': [f'SOFTWARE-ONLY-CAT-{i:03}' for i in range(80)],
        'title': [f'Software test protocol {i % 3}' for i in range(80)],
        'brief_summary': 'Artificial records for automated testing only',
        'phase': [f'PHASE{i % 3 + 1}' for i in range(80)],
        'study_type': 'INTERVENTIONAL', 'status': 'COMPLETED',
        'completion_date_type': 'ACTUAL', 'start_date': start,
        'completion_date': start + pd.to_timedelta(rng.integers(30, 180, 80), unit='D'),
        'enrollment': rng.integers(10, 500, 80), 'number_of_arms': rng.integers(1, 4, 80),
        'primary_outcomes': rng.integers(1, 4, 80), 'secondary_outcomes': rng.integers(0, 5, 80),
        'criteria_count': rng.integers(2, 20, 80),
    })


def test_catboost_is_opt_in_and_config_requires_boolean():
    assert ExperimentConfig().enable_catboost is False
    with pytest.raises(ValueError, match='enable_catboost'):
        ExperimentConfig(enable_catboost='yes').validate()


def test_catboost_fits_training_only_and_provides_additive_native_shap(tmp_path):
    frame = records()
    frame.loc[70:, 'enrollment'] = 999_999
    frame.loc[70:, 'phase'] = 'TEST_ONLY_NEW_CATEGORY'
    cfg = ExperimentConfig(bootstrap_samples=0, enable_catboost=True)
    manifest = train_experiment(frame, tmp_path, {'is_fixture': True, 'dataset_id': 'software-test'}, config=cfg)
    branch = manifest['models']['structured_catboost']
    assert branch['family'] == 'catboost'
    assert branch['input_mode'] == 'structured'
    artifact = joblib.load(tmp_path / 'models.joblib')
    preprocess = artifact['models']['structured_catboost']['regressor'].named_steps['preprocess']
    training_ids = manifest['splits']['train']['nct_ids']
    assert preprocess.named_transformers_['numeric'].named_steps['scaler'].mean_[0] == pytest.approx(
        frame.loc[frame.nct_id.isin(training_ids), 'enrollment'].mean())
    assert 'TEST_ONLY_NEW_CATEGORY' not in preprocess.named_transformers_['categorical'].categories_[1]
    result = predict_trial(frame.iloc[55].to_dict(), tmp_path, 'structured_catboost')
    assert result['status'] == 'available'
    explanation = result['duration_explanation']
    assert explanation['method'] == 'TreeSHAP'
    assert explanation['scope'] == 'local'
    assert explanation['intercept'] + explanation['sum_all_contributions'] == pytest.approx(result['duration_days'], abs=1e-6)
    assert sum(item['contribution'] for item in explanation['features']) == pytest.approx(explanation['sum_all_contributions'], abs=1e-6)
    risk = result['explanation']
    assert risk['method'] == 'TreeSHAP'
    assert risk['units'] == 'log-odds'
    assert 1 / (1 + np.exp(-(risk['intercept'] + risk['sum_all_contributions']))) == pytest.approx(result['probability'], abs=1e-6)
    assert branch['selection']['refit_on_validation'] is False
    assert branch['selection']['native_task'] == 'CPU'
    json.dumps(result, allow_nan=False)
