"""Small deterministic CPU candidates; fitting receives training/tuning only.

Registry baseline provenance remains the caller's responsibility. These models
consume only the existing structured feature whitelist and introduce no text,
dates, IDs or completion information as predictors.
"""
from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import brier_score_loss, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler


class PhaseShrinkage(BaseEstimator):
    """Phase mean shrunk by a fixed prior sample size; unseen phases use global mean."""

    def __init__(self, task='regressor', prior_rows=20.0):
        self.task = task
        self.prior_rows = prior_rows

    def fit(self, X, y):
        target = np.asarray(y, dtype=float)
        self.global_mean_ = float(target.mean())
        phases = X['phase'].astype(str).to_numpy()
        self.phase_means_ = {}
        self.phase_counts_ = {}
        for phase in sorted(set(phases)):
            selected = target[phases == phase]
            self.phase_counts_[phase] = len(selected)
            self.phase_means_[phase] = float((selected.sum() + self.prior_rows * self.global_mean_) / (len(selected) + self.prior_rows))
        self.classes_ = np.array([0, 1])
        return self

    def predict(self, X):
        values = np.array([self.phase_means_.get(str(phase), self.global_mean_) for phase in X['phase']])
        return (values >= .5).astype(int) if self.task == 'classifier' else values

    def predict_proba(self, X):
        values = np.array([self.phase_means_.get(str(phase), self.global_mean_) for phase in X['phase']])
        return np.column_stack([1 - values, values])


class SelectedTaskModel:
    """Pickle-safe reference to an already fitted, tuning-selected task branch."""

    def __init__(self, estimator, component, task):
        self.estimator = estimator
        self.component = component
        self.task = task
        if task == 'classifier':
            self.classes_ = estimator.classes_

    def predict(self, X):
        return self.estimator.predict(X)

    def predict_proba(self, X):
        return self.estimator.predict_proba(X)


def log_structured_preprocessor(numeric, categorical):
    return ColumnTransformer([
        ('numeric', Pipeline([
            ('imputer', SimpleImputer(strategy='median', keep_empty_features=True)),
            ('log1p', FunctionTransformer(np.log1p, feature_names_out='one-to-one')),
            ('scaler', StandardScaler()),
        ]), numeric),
        ('categorical', OneHotEncoder(handle_unknown='ignore'), categorical),
    ], remainder='drop', sparse_threshold=1.0)


def fit_accuracy_models(X_train, duration_train, labels_train, X_tuning, duration_tuning,
                        labels_tuning, config, existing_models, numeric, categorical):
    """Declared grids are frozen and small; calibration/test are absent by design."""
    # Local import avoids a research -> helper -> research import cycle at load.
    from ..research import _positive_probability

    models = {
        'accuracy_mean': {
            'regressor': DummyRegressor(strategy='mean').fit(X_train, duration_train),
            'classifier': DummyClassifier(strategy='prior').fit(X_train, labels_train),
        },
        'accuracy_phase_shrinkage': {
            'regressor': PhaseShrinkage().fit(X_train, duration_train),
            'classifier': PhaseShrinkage(task='classifier').fit(X_train, labels_train),
        },
    }
    common = {'selection_split': 'validation', 'selection_rows': len(X_tuning), 'training_rows': len(X_train),
              'refit_on_validation': False, 'test_used_for_selection': False, 'native_task': 'CPU'}
    selection = {
        'accuracy_mean': {**common, 'regression': 'training duration arithmetic mean', 'classification': 'training prolonged prevalence', 'tuned': False},
        'accuracy_phase_shrinkage': {**common, 'prior_rows': 20.0, 'tuned': False,
            'method': 'Training phase duration mean and prolonged prevalence shrunk toward training global means; unseen phases use global means.'},
    }
    pair, trials, chosen = {}, {}, {}
    for task, target, grid in (('regressor', duration_train, (10.0, 100.0)), ('classifier', labels_train, (.1, 1.0))):
        trials[task] = []
        if task == 'classifier' and len(np.unique(labels_train)) < 2:
            pair[task] = DummyClassifier(strategy='prior').fit(X_train, labels_train)
            chosen[task] = None
            continue
        best_score = float('inf')
        for value in grid:
            estimator = (Ridge(alpha=value, solver='lsqr') if task == 'regressor' else
                         LogisticRegression(C=value, solver='liblinear', max_iter=2000, random_state=config.random_seed))
            candidate = Pipeline([('preprocess', log_structured_preprocessor(numeric, categorical)), ('model', estimator)])
            if task == 'regressor':
                candidate = TransformedTargetRegressor(regressor=candidate, func=np.log1p, inverse_func=np.expm1)
            candidate.fit(X_train, target)
            score = (float(np.sqrt(mean_squared_error(duration_tuning, np.maximum(0, candidate.predict(X_tuning))))) if task == 'regressor'
                     else float(brier_score_loss(labels_tuning, _positive_probability(candidate, X_tuning))))
            trials[task].append({'parameter': value, 'metric': 'rmse' if task == 'regressor' else 'brier', 'score': score})
            if score < best_score:
                pair[task], chosen[task], best_score = candidate, value, score
    models['accuracy_log_structured'] = pair
    selection['accuracy_log_structured'] = {**common, 'ridge_alpha': chosen['regressor'], 'logistic_C': chosen['classifier'],
        'candidate_ridge_alpha': [10.0, 100.0], 'candidate_logistic_C': [.1, 1.0], 'trials': trials,
        'one_class_fallback': chosen['classifier'] is None, 'tie_breaker': 'first candidate in declared order',
        'regression_selection': 'minimum tuning validation RMSE in days', 'classification_selection': 'minimum raw tuning validation Brier',
        'preprocessing': 'Training median imputation, log1p nonnegative numeric features, training scaling and categorical encoding. Regression fits log1p(days), inverse expm1 without bias correction; not an arithmetic conditional mean.'}

    available = {**existing_models, **models}
    duration_scores = {name: float(np.sqrt(mean_squared_error(duration_tuning, np.maximum(0, pair['regressor'].predict(X_tuning))))) for name, pair in available.items()}
    risk_scores = {name: float(brier_score_loss(labels_tuning, _positive_probability(pair['classifier'], X_tuning))) for name, pair in available.items()}
    regressor = min(duration_scores, key=lambda name: (duration_scores[name], name))
    classifier = min(risk_scores, key=lambda name: (risk_scores[name], name))
    models['accuracy_task_selected'] = {
        'regressor': SelectedTaskModel(available[regressor]['regressor'], regressor, 'regressor'),
        'classifier': SelectedTaskModel(available[classifier]['classifier'], classifier, 'classifier'),
    }
    selection['accuracy_task_selected'] = {**common, 'regressor_component': regressor, 'classifier_component': classifier,
        'candidate_components': sorted(available), 'tuning_rmse': duration_scores, 'tuning_raw_brier': risk_scores,
        'tie_breaker': 'model name', 'method': 'Independent minimum tuning RMSE duration and minimum raw tuning Brier risk branches; no additional fitting or ensemble weights.'}
    return models, selection
