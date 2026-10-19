"""Artificial fixtures check software contracts; never accuracy evidence."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest
from src.clinical_trial_intelligence.research import ExperimentConfig, evaluate_predictions
from src.clinical_trial_intelligence.phase_model import PhaseConfig, evaluate_phase_predictions


def test_design_config_is_opt_in_and_rejects_invalid_values():
    assert ExperimentConfig().enable_design_models is False
    assert ExperimentConfig().duration_selection_metric == 'rmse'
    assert PhaseConfig().enable_design_models is False
    for config in (ExperimentConfig(enable_design_models='yes'), ExperimentConfig(duration_selection_metric='test_mae'),
                   ExperimentConfig(enable_design_catboost=True), PhaseConfig(enable_design_models='yes')):
        with pytest.raises(ValueError):
            config.validate()


def test_design_whitelist_has_no_outcomes_or_phase_label_for_phase_task():
    from src.clinical_trial_intelligence.models.design import design_features, input_features
    frame = pd.DataFrame({'enrollment': [500], 'planned_enrollment': [np.nan], 'phase': ['PHASE3'],
                          'status': ['COMPLETED'], 'duration_days': [900], 'design_masking': ['DOUBLE'],
                          'eligibility_word_count': [12], 'completion_date': ['2020-01-01']})
    duration = design_features(frame)
    phase = design_features(frame, phase_task=True)
    assert pd.isna(duration.planned_enrollment.iloc[0])  # no actual-to-planned substitution
    assert duration.phase.iloc[0] == 'PHASE3'
    assert 'phase' not in phase and 'reported_phase' not in phase
    assert not {'enrollment', 'status', 'duration_days', 'completion_date'} & set(duration.columns)
    assert input_features(phase_task=True)['categorical'] == [c for c in input_features()['categorical'] if c != 'phase']


def test_metrics_include_real_median_error_logloss_and_phase_uncertainty():
    result = evaluate_predictions([10, 20, 30], [11, 24, 32], [0, 1, 1], [.1, .8, .7], bootstrap_samples=10)
    assert result['regression']['median_absolute_error'] == 2
    assert result['classification']['log_loss'] == pytest.approx(-np.log([.9, .8, .7]).mean())
    phase = evaluate_phase_predictions(['PHASE1','PHASE2','PHASE2'], ['PHASE1','PHASE1','PHASE2'], ['PHASE1','PHASE2'], bootstrap_samples=20)
    assert phase['per_class']['PHASE2']['recall'] == .5
    assert phase['confidence_intervals']['accuracy']['valid_resamples'] == 20
    json.dumps(phase, allow_nan=False)


def test_selected_task_contract_follows_only_the_selected_task_recursively():
    from src.clinical_trial_intelligence.research import model_input_features, model_task_input_features, NUMERIC_FEATURES, CATEGORICAL_FEATURES
    choices = {
        'accuracy_task_selected': {'regressor_component': 'text', 'classifier_component': 'structured'},
        'design_task_selected': {'regressor_component': 'median_baseline', 'classifier_component': 'accuracy_task_selected'},
    }
    expected = {'numeric': list(NUMERIC_FEATURES), 'categorical': list(CATEGORICAL_FEATURES), 'text': []}
    assert model_input_features('design_task_selected', choices) == expected
    assert model_task_input_features('design_task_selected', choices, 'regressor') == {'numeric': [], 'categorical': [], 'text': []}
    assert model_task_input_features('design_task_selected', choices, 'classifier') == expected
    choices['structured'] = {'one_class_fallback': True}
    assert model_input_features('design_task_selected', choices) == {'numeric': [], 'categorical': [], 'text': []}


def test_new_phase_feature_metadata_matches_the_consumed_whitelist(tmp_path):
    from src.clinical_trial_intelligence.phase_model import train_phase_experiment
    from src.clinical_trial_intelligence.models.design import input_features
    manifest = train_phase_experiment(design_fixture(60), tmp_path, {'is_fixture': True},
                                      config=PhaseConfig(max_text_features=100, logistic_cs=(1.,), enable_design_models=True))
    design = input_features(phase_task=True)
    assert set(design['numeric']) <= set(manifest['features']['numeric'])
    assert manifest['features']['categorical'] == design['categorical']
    assert not set(design['categorical']) & set(manifest['features']['excluded'])
    assert 'phase' in manifest['features']['excluded']


def design_fixture(n=150):
    from test_research import software_fixture
    frame = software_fixture(n)
    frame['planned_enrollment'] = np.where(np.arange(n)%3, frame.enrollment, np.nan)
    frame['design_allocation'] = np.where(np.arange(n)%2, 'RANDOMIZED', 'NON_RANDOMIZED')
    frame['design_masking'] = np.where(np.arange(n)%3, 'DOUBLE', 'NONE')
    frame['intervention_types'] = 'DRUG'
    frame['sponsor_class'] = np.where(np.arange(n)%2, 'INDUSTRY', 'OTHER')
    frame['eligibility_word_count'] = np.arange(n)%17 + 10
    return frame


def test_design_training_preserves_legacy_predictions_and_serialized_contract(tmp_path):
    from src.clinical_trial_intelligence.research import train_experiment, predict_trial, _features
    frame = design_fixture()
    common = dict(bootstrap_samples=0, enable_advanced_models=False, max_text_features=100)
    before = train_experiment(frame, tmp_path/'old', {'is_fixture':True}, config=ExperimentConfig(**common))
    after = train_experiment(frame, tmp_path/'new', {'is_fixture':True}, config=ExperimentConfig(**common, enable_design_models=True, enable_design_catboost=True, duration_selection_metric='mae'))
    assert before['splits'] == after['splits']
    assert before['target'] == after['target']
    old, new = [joblib.load(tmp_path/folder/'models.joblib') for folder in ('old','new')]
    for name in old['models']:
        np.testing.assert_array_equal(old['models'][name]['regressor'].predict(_features(frame)), new['models'][name]['regressor'].predict(_features(frame, include_design=True)))
    assert after['models']['median_baseline']['input_features'] == {'numeric':[], 'categorical':[], 'text':[]}
    assert after['models']['median_baseline']['task_input_features']['regressor'] == {'numeric':[], 'categorical':[], 'text':[]}
    assert after['duration_recommendation']['metric'] == 'mae'
    assert 'models/catboost_compat.py' in after['additional_model_source_sha256']
    assert after['environment']['catboost']
    task_choice = after['models']['design_task_selected']['selection']
    scores = task_choice['scores']
    assert task_choice['regressor_component'] == min(scores, key=lambda name: (scores[name]['mae'], scores[name]['rmse'], name))
    assert task_choice['classifier_component'] == min(scores, key=lambda name: (scores[name]['raw_brier'], name))
    from src.clinical_trial_intelligence.models.design import input_features
    assert set(input_features()['numeric']) <= set(after['features']['numeric'])
    assert set(input_features()['categorical']) <= set(after['features']['categorical'])
    for name in ('design_linear', 'design_log_linear', 'design_catboost'):
        selection = after['models'][name]['selection']
        trials = selection['trials']
        assert len(trials['regressor']) == (4 if name == 'design_catboost' else 2)
        assert len(trials['classifier']) == 2
        best = min(trials['regressor'], key=lambda trial: (trial['mae'], trial['rmse']))
        assert selection['selected_parameters']['regressor'] == best['parameters']
        best = min(trials['classifier'], key=lambda trial: trial['raw_brier'])
        assert selection['selected_parameters']['classifier'] == best['parameters']
        assert selection['test_used_for_selection'] is False
    saved = pd.read_csv(tmp_path/'new/held_out_predictions.csv')
    for name in ('design_linear','design_log_linear','design_catboost','design_task_selected'):
        result = predict_trial(frame.iloc[-1].to_dict(), tmp_path/'new', name)
        assert result['status'] == 'available', result
        expected = saved.loc[(saved.nct_id == frame.iloc[-1].nct_id)&(saved.model_name == name)].iloc[0]
        assert result['duration_days'] == pytest.approx(expected.predicted_duration_days)
        assert result['raw_probability'] == pytest.approx(expected.prolonged_probability)
        assert 'completion_date' not in str(after['models'][name]['input_features'])
        json.dumps(result, allow_nan=False)


def test_phase_design_candidate_prediction_ignores_true_label_and_replays(tmp_path):
    from src.clinical_trial_intelligence.phase_model import train_phase_experiment, predict_phase
    frame = design_fixture(100)
    config = PhaseConfig(max_text_features=100, enable_design_models=True, enable_design_catboost=True, bootstrap_samples=5)
    manifest = train_phase_experiment(frame, tmp_path/'phase', {'is_fixture':True}, config=config)
    assert {'phase_text','phase_design_structured','phase_design_catboost'} <= set(manifest['models'])
    choices = manifest['models']
    assert 'models/catboost_compat.py' in manifest['additional_model_source_sha256']
    assert manifest['environment']['catboost']
    expected = min(choices, key=lambda n: (-choices[n]['metrics']['validation']['macro_f1'], -choices[n]['metrics']['validation']['balanced_accuracy'], n))
    assert manifest['recommended_model'] == expected
    selection = manifest['models']['phase_logistic']['selection']
    expected_c = min(selection['candidates'], key=lambda trial: (-trial['validation_macro_f1'], -trial['validation_balanced_accuracy']))['logistic_C']
    assert selection['logistic_C'] == expected_c
    for name in choices:
        assert 'phase' not in choices[name]['input_features']['categorical']
    row = frame.iloc[-1].to_dict()
    first = predict_phase(row, tmp_path/'phase')
    assert first['status'] == 'available', first
    row['phase'] = 'PHASE4'
    second = predict_phase(row, tmp_path/'phase')
    assert first['class_probabilities'] == second['class_probabilities']
    assert first['model_name'] == expected
    stored = pd.read_csv(tmp_path/'phase/phase_held_out_predictions.csv')
    value = stored.loc[(stored.nct_id==row['nct_id'])&(stored.model_name==expected)].iloc[0]
    assert first['predicted_phase'] == value.predicted_phase
    from src.clinical_trial_intelligence.phase_model import _phase_features
    original = frame.iloc[-1].to_dict()
    original['brief_summary'] = 'A phase I/II study of medication safety.'
    changed = {**original, 'phase': 'PHASE4', 'reported_phase': 'PHASE4',
               'brief_summary': 'A phase III/IV study of medication safety.'}
    original_features = _phase_features(pd.DataFrame([original]), include_design=True)
    changed_features = _phase_features(pd.DataFrame([changed]), include_design=True)
    pd.testing.assert_frame_equal(original_features, changed_features)
    artifact = joblib.load(tmp_path/'phase/phase_models.joblib')
    for model in artifact['models'].values():
        np.testing.assert_array_equal(model.predict_proba(original_features), model.predict_proba(changed_features))


def test_legacy_bundles_still_replay_with_new_code():
    from src.clinical_trial_intelligence.research import predict_trial
    from src.clinical_trial_intelligence.phase_model import predict_phase
    root = Path(__file__).parents[1]
    row = pd.read_csv(root/'data/starter/trials.csv').iloc[0].to_dict()
    assert predict_trial(row, root/'examples/starter-duration-v5', 'median_baseline')['status'] == 'available'
    assert predict_phase(row, root/'examples/starter-phase-v5')['status'] == 'available'
