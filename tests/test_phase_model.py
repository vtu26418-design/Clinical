"""Artificial records here verify software behavior; they are not research evidence."""
import json

import joblib
import numpy as np
import pandas as pd
import pytest

from src.clinical_trial_intelligence.phase_model import (
    PHASE_LABELS, PhaseConfig, _phase_features, evaluate_phase_predictions,
    phase_temporal_split, predict_phase, prepare_phase_cohort,
    redact_phase_mentions, train_phase_experiment,
)


def phase_fixture(n=60):
    return pd.DataFrame({
        "nct_id": [f"SOFTWARE-PHASE-{i:03}" for i in range(n)],
        "phase": ["Phase 1" if i % 2 == 0 else "PHASE2" for i in range(n)],
        "start_date": pd.date_range("2010-01-01", periods=n, freq="7D"),
        "title": [f"Artificial Phase {i % 2 + 1} protocol example" for i in range(n)],
        "brief_summary": ["Software fixture with eligibility criteria" for _ in range(n)],
        "enrollment": [20 + (i % 5) * 10 for i in range(n)],
        "number_of_arms": [1 + i % 3 for i in range(n)],
        "primary_outcomes": 1, "secondary_outcomes": 2, "criteria_count": 5,
        "status": "RECRUITING", "completion_date": None,
    })


@pytest.mark.parametrize("mention", [
    "Phase 2", "PHASE2", "phase-II", "Phase IIIb", "EARLY_PHASE1",
    "Phase I/II", "Phase 1 / Phase 2", "phases II and III", "phase two",
    "PHASE1|PHASE2", "Phase 1-2", "Phase IV", "early phase 1",
])
def test_explicit_phase_mentions_are_removed(mention):
    assert redact_phase_mentions(f"A {mention} protocol") == "A protocol"


def test_phase_exclusions_and_alias_normalization_do_not_require_outcomes():
    df = phase_fixture(10)
    df["phase"] = ["Phase 2", "Phase I", "Early Phase 1", "Phase IV", "Phase 3",
                   "PHASE1|PHASE2", "Phase 1/Phase 2", "NA", None, "unknown"]
    cohort, exclusions = prepare_phase_cohort(df)
    assert cohort.phase.tolist() == ["PHASE2", "PHASE1", "EARLY_PHASE1", "PHASE4", "PHASE3"]
    assert len(exclusions) == 5
    assert set(exclusions.nct_id) == set(df.nct_id[5:])
    assert cohort.status.eq("RECRUITING").all()
    assert cohort.completion_date.isna().all()


def test_invalid_dates_and_duplicate_identifiers_are_not_silently_retained():
    df = phase_fixture(6)
    df["start_date"] = df.start_date.astype(str)
    df.loc[0, "start_date"] = "2020-01"
    df.loc[1, "start_date"] = "2020-02-30"
    cohort, excluded = prepare_phase_cohort(df)
    assert len(cohort) == 4
    assert len(excluded) == 2
    df.loc[1, "nct_id"] = df.loc[0, "nct_id"]
    with pytest.raises(ValueError, match="Duplicate"):
        prepare_phase_cohort(df)


def test_phase_features_whitelist_and_redact_all_protocol_fields():
    df = phase_fixture(2)
    df["detailed_description"] = "Phase III therapeutic exploratory study"
    df["eligibility_criteria"] = "Not in another Phase IV study"
    first = _phase_features(df)
    changed = df.copy()
    changed["phase"] = "PHASE4"
    changed["status"] = "COMPLETED"
    changed["completion_date"] = "2099-01-01"
    changed["start_date"] = "2000-01-01"
    changed["duration_days"] = 99999
    pd.testing.assert_frame_equal(first, _phase_features(changed))
    assert set(first.columns) == {"enrollment", "number_of_arms", "primary_outcomes", "secondary_outcomes", "criteria_count", "protocol_text"}
    assert not first.protocol_text.str.contains("Phase", case=False).any()
    assert first.protocol_text.str.contains("therapeutic exploratory").all()


def test_temporal_split_preserves_whole_date_groups_and_minimum_sizes():
    df = phase_fixture()
    df["start_date"] = pd.Series(pd.date_range("2010-01-01", periods=30, freq="7D")).repeat(2).to_numpy()
    cohort, _ = prepare_phase_cohort(df)
    splits = phase_temporal_split(cohort)
    assert [len(splits[s]) for s in ("train", "validation", "test")] == [36, 12, 12]
    assert splits["train"].start_date.max() < splits["validation"].start_date.min()
    assert splits["validation"].start_date.max() < splits["test"].start_date.min()
    dates = [set(splits[s].start_date) for s in ("train", "validation", "test")]
    assert not (dates[0] & dates[1] or dates[1] & dates[2] or dates[0] & dates[2])
    cohort["start_date"] = pd.Timestamp("2010-01-01")
    with pytest.raises(ValueError, match="three distinct"):
        phase_temporal_split(cohort)


def test_unseen_test_class_remains_an_error_in_all_metrics():
    metrics = evaluate_phase_predictions(["PHASE1", "PHASE3"], ["PHASE1", "PHASE1"], ["PHASE1", "PHASE2"])
    assert metrics["n"] == 2
    assert metrics["accuracy"] == .5
    assert metrics["balanced_accuracy"] == .5
    assert metrics["macro_f1"] == pytest.approx(1 / 3)
    assert metrics["unseen_training_labels"] == ["PHASE3"]
    assert metrics["class_support"]["PHASE3"] == 1
    assert sum(map(sum, metrics["confusion_matrix"])) == 2


@pytest.fixture
def fitted_phase(tmp_path):
    df = phase_fixture()
    df.loc[48:, "enrollment"] = 999999
    df.loc[48:, "brief_summary"] = "heldoutuniquetoken artificial record"
    df.loc[48:, "phase"] = "PHASE3"
    manifest = train_phase_experiment(df, tmp_path, {"dataset_id": "software-fixture", "is_fixture": True}, config=PhaseConfig(max_text_features=100, logistic_cs=(0.1, 1.0)))
    return df, tmp_path, manifest


def test_fitted_transformers_never_learn_test_features_and_preserve_unseen_labels(fitted_phase):
    df, directory, manifest = fitted_phase
    artifact = joblib.load(directory / "phase_models.joblib")
    preprocess = artifact["models"]["phase_logistic"].named_steps["preprocess"]
    assert "heldoutuniquetoken" not in preprocess.named_transformers_["text"].vocabulary_
    assert preprocess.named_transformers_["numeric"].named_steps["scaler"].mean_[0] < 100
    assert manifest["task"] == "phase"
    assert manifest["models"]["phase_logistic"]["metrics"]["test"]["accuracy"] == 0
    assert manifest["models"]["phase_logistic"]["metrics"]["test"]["unseen_training_labels"] == ["PHASE3"]
    heldout = pd.read_csv(directory / "phase_held_out_predictions.csv")
    assert len(heldout) == 48
    assert heldout.loc[heldout.split.eq("test"), "actual_phase"].eq("PHASE3").all()
    assert "SOFTWARE TEST FIXTURE" in manifest["warning"]
    assert manifest["splits"]["train"]["rows"] == 36
    assert sum(manifest["splits"]["test"]["class_support"].values()) == 12
    json.dumps(manifest, allow_nan=False)


def test_prediction_preserves_reported_phase_and_discloses_membership(fitted_phase):
    df, directory, _ = fitted_phase
    result = predict_phase(df.iloc[-1].to_dict(), directory)
    assert result["status"] == "available"
    assert result["reported_phase"] == "PHASE3"
    assert result["predicted_phase"] in {"PHASE1", "PHASE2"}
    assert result["cohort_membership"] == "test"
    assert set(result["class_probabilities"]) == set(PHASE_LABELS)
    assert sum(result["class_probabilities"].values()) == pytest.approx(1)
    assert result["class_probabilities"]["PHASE3"] == 0
    assert "uncalibrated" in result["warning"].lower()
    assert "regulatory" in result["warning"].lower()
    train_result = predict_phase(df.iloc[0].to_dict(), directory)
    assert train_result["cohort_membership"] == "train"
    assert "In-sample" in train_result["prediction_scope"]
    changed_phase = df.iloc[-1].to_dict() | {"phase": "PHASE4", "status": "COMPLETED", "completion_date": "2099-01-01"}
    assert predict_phase(changed_phase, directory)["class_probabilities"] == result["class_probabilities"]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("field,value", [("task", "duration"), ("artifact_version", 99), ("run_id", "other"), ("input_sha256", "wrong"), ("source_metadata", {"dataset_id": "wrong"})])
def test_manifest_incompatibility_is_unavailable(fitted_phase, field, value):
    df, directory, manifest = fitted_phase
    manifest[field] = value
    (directory / "phase_manifest.json").write_text(json.dumps(manifest))
    assert predict_phase(df.iloc[0].to_dict(), directory)["status"] == "unavailable"


def test_absent_and_corrupt_artifacts_are_unavailable(tmp_path, fitted_phase):
    assert predict_phase({"phase": "Phase 2"}, tmp_path / "empty")["predicted_phase"] is None
    df, directory, _ = fitted_phase
    with (directory / "phase_models.joblib").open("ab") as stream:
        stream.write(b"corruption")
    result = predict_phase(df.iloc[0].to_dict(), directory)
    assert result["status"] == "unavailable"
    assert "checksum" in result["reason"].lower()


@pytest.mark.parametrize("size,one_class", [(39, False), (60, True)])
def test_ineligible_training_writes_failure_without_models(tmp_path, size, one_class):
    df = phase_fixture(size)
    if one_class:
        df["phase"] = "PHASE1"
    with pytest.raises(ValueError, match="40 eligible|two phase classes"):
        train_phase_experiment(df, tmp_path)
    assert not (tmp_path / "phase_models.joblib").exists()
    assert json.loads((tmp_path / "phase_error.json").read_text())["status"] == "failed"


@pytest.mark.parametrize("kwargs", [{"max_text_features": 100001}, {"max_iter": 0}, {"logistic_cs": ()}, {"logistic_cs": (float("nan"),)}, {"random_seed": -1}])
def test_phase_configuration_is_bounded(kwargs):
    with pytest.raises(ValueError):
        PhaseConfig(**kwargs).validate()


@pytest.mark.parametrize("mention", ["Phase: II", "Phase (III)", "Phase–II", "Phase Ⅰ", "Phase I, II and III", "Phase—IV"])
def test_punctuated_and_unicode_phase_mentions_are_redacted(mention):
    assert redact_phase_mentions(f"A {mention} protocol") == "A protocol"
