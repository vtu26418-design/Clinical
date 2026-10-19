"""Artificial fixtures verify a portable adapter; never accuracy evidence."""
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from scripts.phase_accuracy_probe import build_features, make_preprocessor
from src.clinical_trial_intelligence.phase_model import _phase_features
from src.clinical_trial_intelligence.models.phase_refinement import PhaseRefinementClassifier, refinement_features
from backend.app.services.phase_service import normalize_phase_input
from src.clinical_trial_intelligence.phase_model import TEXT_FIELDS
import pytest


def test_adapter_matches_probe_features_and_reloads_without_main_classes(tmp_path):
    frame = pd.DataFrame({'phase': ['PHASE1', 'PHASE2'] * 6,
                          'brief_summary': ['A phase I medication safety study NCT00000001 in2012-02-01.',
                                            'A phase II treatment effectiveness study NCT00000002 in2013-02-01.'] * 6,
                          'enrollment': [20, 200] * 6, 'design_masking': ['NONE', 'DOUBLE'] * 6})
    preprocess = make_preprocessor()
    transformed = preprocess.fit_transform(build_features(frame))
    model = LogisticRegression(max_iter=100).fit(transformed, frame.phase)
    adapter = PhaseRefinementClassifier(preprocessor=preprocess, estimator=model)
    expected = model.predict_proba(transformed)
    inputs = _phase_features(frame, include_design=True)
    np.testing.assert_array_equal(adapter.predict_proba(inputs), expected)
    changed = frame.copy()
    changed['phase'] = 'PHASE4'
    np.testing.assert_array_equal(adapter.predict_proba(_phase_features(changed, include_design=True)), expected)
    path = tmp_path / 'portable.joblib'
    joblib.dump(adapter, path)
    reloaded = joblib.load(path)
    assert type(reloaded).__module__ == 'src.clinical_trial_intelligence.models.phase_refinement'
    np.testing.assert_array_equal(reloaded.predict_proba(inputs), expected)
    np.testing.assert_array_equal(reloaded.predict(inputs), model.predict(transformed))


def test_manifest_narrative_slots_preserve_canonical_long_text_at_runtime():
    # Missing slots used to move the 12,000-character boundary at inference.
    row = {'brief_summary': 'A brain medication trial. ' * 600,
           'enrollment': 40, 'design_masking': 'DOUBLE'}
    manifest = {'features': {'canonical_empty_text_fields': list(TEXT_FIELDS)}}
    normalized = normalize_phase_input(row, manifest)
    expected = {**row, **{field: row.get(field, '') for field in TEXT_FIELDS}}
    canonical = build_features(pd.DataFrame([expected]))
    runtime = refinement_features(_phase_features(pd.DataFrame([normalized]), include_design=True))
    pd.testing.assert_frame_equal(canonical, runtime)
    assert all(field in normalized for field in TEXT_FIELDS)
    assert normalize_phase_input(row, {}) == row
    assert row.keys() == {'brief_summary', 'enrollment', 'design_masking'}
    with pytest.raises(ValueError, match='narrative input contract'):
        normalize_phase_input(row, {'features': {'canonical_empty_text_fields': ['phase']}})
