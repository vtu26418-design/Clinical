"""Expose saved-model explanations without substituting demonstration SHAP.

The fitted research pipeline owns attribution computation. Linear contributions,
global impurity importance and fusion branch outputs retain their actual labels.
This adapter never calls them SHAP and never invents an explanation fallback.
"""
from __future__ import annotations

from typing import Any


def _unavailable(reason: str, predicted_value=None) -> dict[str, Any]:
    return {'status': 'unavailable', 'method': 'unavailable', 'scope': 'unavailable',
            'units': 'days', 'features': [], 'components': [], 'feature_names': [],
            'shap_values': None, 'base_value': None, 'predicted_value': predicted_value,
            'is_demo': False, 'reason': reason, 'explanation': reason}


def get_demo_shap_values(study_row=None, predicted_value=None) -> dict[str, Any]:
    """Deprecated compatibility entry point; demonstrations are unavailable."""
    return _unavailable('Demonstration attributions are disabled. Select an available saved model.')


def explain_prediction(prediction: Any, study_row: dict[str, Any], feature_names=None) -> dict[str, Any]:
    """Adapt a genuine ``predict`` response's duration_explanation only."""
    if not isinstance(prediction, dict) or prediction.get('status') != 'available':
        return _unavailable(prediction.get('reason', 'No compatible saved model is available.')
                            if isinstance(prediction, dict) else 'A genuine saved-model prediction is required.')
    value = prediction.get('duration_days')
    explanation = prediction.get('duration_explanation')
    if not isinstance(explanation, dict):
        return _unavailable('This saved model does not provide duration attribution.', value)
    method = explanation.get('method', 'unavailable')
    if method == 'constant training baseline':
        from src.clinical_trial_intelligence.research import NUMERIC_FEATURES, CATEGORICAL_FEATURES, TEXT_FIELDS
        names = feature_names or [*NUMERIC_FEATURES, *CATEGORICAL_FEATURES, *TEXT_FIELDS]
        explanation = {**explanation, 'scope': 'constant', 'base_value': value,
                       'sum_all_contributions': 0.0,
                       'features': [{'feature': name, 'value': study_row.get(name), 'contribution': 0.0} for name in names]}
    supported = method in {'constant training baseline', 'linear feature contributions',
                           'global impurity feature importance', 'weighted late fusion', 'TreeSHAP'}
    features = explanation.get('features', [])
    note = explanation.get('note', '')
    return {**explanation, 'status': 'available' if supported else 'unavailable',
            'method': method, 'features': features, 'components': explanation.get('components', []),
            'feature_names': [feature['feature'] for feature in features],
            'shap_values': [feature['contribution'] for feature in features] if method == 'TreeSHAP' else None,
            'base_value': explanation.get('base_value', explanation.get('intercept')),
            'predicted_value': value, 'is_demo': False, 'explanation': note,
            **({'reason': note or 'This fitted model does not support local attribution.'} if not supported else {})}
