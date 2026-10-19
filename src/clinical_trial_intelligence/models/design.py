"""Opt-in retrospective protocol-design candidates with explicit input contracts.

No dates, IDs, current enrollment or outcomes become design predictors. Source
fields may nevertheless be updated after start; this is not pretrial provenance.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import brier_score_loss, mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERIC = ['planned_enrollment', 'number_of_arms', 'primary_outcomes', 'secondary_outcomes',
           'intervention_count', 'eligibility_line_count', 'eligibility_word_count',
           'eligibility_char_count', 'reported_sites', 'reported_countries']
CATEGORICAL = ['study_type', 'phase', 'design_allocation', 'design_masking',
               'primary_purpose', 'sponsor_class', 'intervention_types']


def input_features(*, phase_task=False):
    return {'numeric': list(NUMERIC), 'categorical': [v for v in CATEGORICAL if not (phase_task and v == 'phase')], 'text': []}


def design_features(frame, *, phase_task=False):
    output = pd.DataFrame(index=frame.index)
    for field in NUMERIC:
        values = pd.to_numeric(frame[field], errors='coerce') if field in frame else pd.Series(np.nan, index=frame.index)
        output[field] = values.where(np.isfinite(values) & values.ge(0), np.nan)
    for field in input_features(phase_task=phase_task)['categorical']:
        output[field] = frame[field].fillna('Unknown').astype(str) if field in frame else 'Unknown'
    if not phase_task:
        from ..research import normalize_design_phase
        output['phase'] = output.phase.map(normalize_design_phase)
    return output


def preprocessor(*, phase_task=False, dense=False):
    fields = input_features(phase_task=phase_task)
    return ColumnTransformer([
        ('numeric', Pipeline([('imputer', SimpleImputer(strategy='median', keep_empty_features=True, add_indicator=True)),
                              ('scaler', StandardScaler())]), fields['numeric']),
        ('categorical', OneHotEncoder(handle_unknown='ignore', sparse_output=not dense), fields['categorical']),
    ], remainder='drop', sparse_threshold=0.0 if dense else 1.0)


def _catboost(task, depth, seed, loss=None):
    try:
        from .catboost_compat import CTICatBoostClassifier, CTICatBoostRegressor
    except ImportError as exc:
        raise ValueError('Design CatBoost was requested but is not installed; install release requirements.') from exc
    cls = CTICatBoostRegressor if task == 'regressor' else CTICatBoostClassifier
    return cls(iterations=300, depth=depth, learning_rate=.05, l2_leaf_reg=5,
               random_seed=seed, thread_count=1, task_type='CPU', verbose=False,
               allow_writing_files=False, loss_function=loss or 'Logloss')


def fit_design_models(X_train, duration_train, labels_train, X_tuning, duration_tuning, labels_tuning, config):
    """Frozen bounded grids; calibration and final test are never supplied here."""
    from ..research import _positive_probability
    families = ['design_linear', 'design_log_linear'] + (['design_catboost'] if config.enable_design_catboost else [])
    models, selections = {}, {}
    for family in families:
        pair, trials, chosen = {}, {}, {}
        for task, target in [('regressor', duration_train), ('classifier', labels_train)]:
            trials[task] = []
            if task == 'classifier' and len(np.unique(target)) < 2:
                pair[task] = DummyClassifier(strategy='prior').fit(X_train, target)
                chosen[task] = None
                continue
            grid = ([{'depth': depth, 'loss': loss} for depth in (4, 6) for loss in (('MAE','RMSE') if task == 'regressor' else ('Logloss',))]
                    if family == 'design_catboost' else [{'parameter': value} for value in ((10.,100.) if task == 'regressor' else (.1,1.))])
            best_key = None
            for params in grid:
                estimator = (_catboost(task, params['depth'], config.random_seed, params['loss']) if family == 'design_catboost' else
                             Ridge(alpha=params['parameter'], solver='lsqr') if task == 'regressor' else
                             LogisticRegression(C=params['parameter'], solver='liblinear', max_iter=2000, random_state=config.random_seed))
                fitted = Pipeline([('preprocess', preprocessor(dense=family=='design_catboost')), ('model', estimator)])
                if family == 'design_log_linear' and task == 'regressor':
                    fitted = TransformedTargetRegressor(regressor=fitted, func=np.log1p, inverse_func=np.expm1)
                fitted.fit(X_train, target)
                if task == 'regressor':
                    estimates = np.maximum(0, fitted.predict(X_tuning))
                    key = (float(mean_absolute_error(duration_tuning, estimates)), float(np.sqrt(mean_squared_error(duration_tuning, estimates))))
                    score = {'mae': key[0], 'rmse': key[1]}
                else:
                    key = (float(brier_score_loss(labels_tuning, _positive_probability(fitted, X_tuning))),)
                    score = {'raw_brier': key[0]}
                trials[task].append({'parameters': params, **score})
                if best_key is None or key < best_key:
                    pair[task], chosen[task], best_key = fitted, params, key
            # The first declared grid value wins an exact score tie.
        models[family] = pair
        selections[family] = {'training_rows': len(X_train), 'selection_rows': len(X_tuning), 'selection_split': 'validation',
            'refit_on_validation': False, 'test_used_for_selection': False, 'trials': trials, 'selected_parameters': chosen,
            'regression_selection': 'minimum tuning MAE then RMSE then declared grid order',
            'classification_selection': 'minimum raw tuning Brier then declared grid order',
            'one_class_fallback': chosen['classifier'] is None,
            'preprocessing': 'Training median imputation with missing indicators, scaling and one-hot categories; current enrollment is excluded.'}
    return models, selections


def selected_tasks(models, X, duration, labels):
    from .accuracy import SelectedTaskModel
    from ..research import _positive_probability
    scores = {}
    for name, pair in models.items():
        predicted = np.maximum(0, pair['regressor'].predict(X))
        scores[name] = {'mae': float(mean_absolute_error(duration, predicted)),
                       'rmse': float(np.sqrt(mean_squared_error(duration, predicted))),
                       'raw_brier': float(brier_score_loss(labels, _positive_probability(pair['classifier'], X)))}
    reg = min(scores, key=lambda n: (scores[n]['mae'], scores[n]['rmse'], n))
    cls = min(scores, key=lambda n: (scores[n]['raw_brier'], n))
    pair = {'regressor': SelectedTaskModel(models[reg]['regressor'], reg, 'regressor'),
            'classifier': SelectedTaskModel(models[cls]['classifier'], cls, 'classifier')}
    return pair, {'regressor_component': reg, 'classifier_component': cls, 'selection_split': 'validation',
                  'selection_rows': len(X), 'refit_on_validation': False, 'test_used_for_selection': False,
                  'method': 'Independent minimum tuning MAE/RMSE duration and raw Brier risk; no weights or additional fitting.',
                  'candidate_components': sorted(scores), 'scores': scores}


def fit_phase_design_models(X_train, y_train, X_tuning, y_tuning, config):
    """Phase target never appears in the structured design input contract."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from ..phase_model import evaluate_phase_predictions
    families = ['phase_text', 'phase_design_structured'] + (['phase_design_catboost'] if config.enable_design_catboost else [])
    models, selections = {}, {}
    for family in families:
        grid = (4, 6) if family == 'phase_design_catboost' else tuple(config.logistic_cs)
        best_key, trials = None, []
        for value in grid:
            prep = (ColumnTransformer([('text', TfidfVectorizer(max_features=config.max_text_features,
                    ngram_range=(1,2), sublinear_tf=True, token_pattern=r'(?u)\b\w+\b'), 'protocol_text')])
                    if family == 'phase_text' else preprocessor(phase_task=True, dense=family=='phase_design_catboost'))
            estimator = (_catboost('classifier', value, config.random_seed, 'MultiClass') if family == 'phase_design_catboost' else
                         LogisticRegression(C=value, solver='lbfgs', max_iter=config.max_iter, random_state=config.random_seed))
            model = Pipeline([('preprocess', prep), ('model', estimator)]).fit(X_train, y_train)
            metric = evaluate_phase_predictions(y_tuning, np.asarray(model.predict(X_tuning)).reshape(-1), list(np.unique(y_train)))
            key = (-metric['macro_f1'], -metric['balanced_accuracy'])
            trials.append({'parameter': float(value), 'validation_macro_f1': metric['macro_f1'], 'validation_balanced_accuracy': metric['balanced_accuracy']})
            if best_key is None or key < best_key:
                models[family], selected, best_key = model, float(value), key
        selections[family] = {'parameter': selected, 'parameter_name': 'depth' if family=='phase_design_catboost' else 'C',
            'trials': trials, 'selection_split': 'validation', 'training_rows': len(X_train), 'selection_rows': len(X_tuning),
            'refit_on_validation': False, 'test_used_for_selection': False,
            'rule': 'maximum tuning macro-F1 then balanced accuracy then declared grid order'}
    return models, selections
