"""Generated fixtures below are software test data, never research evidence."""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest

from src.clinical_trial_intelligence.research import (
    ExperimentConfig, evaluate_predictions, prepare_cohort, predict_trial,
    temporal_split, train_experiment,
)


def software_fixture(n=100):
    """Deterministic, explicitly artificial records for pipeline verification only."""
    rng = np.random.default_rng(12)
    starts = pd.date_range("2000-01-01", periods=n, freq="45D")
    durations = rng.integers(25, 200, n)
    return pd.DataFrame({
        "nct_id": [f"TEST-ONLY-{i:04}" for i in range(n)],
        "title": [f"Software fixture protocol group {i % 4}" for i in range(n)],
        "brief_summary": ["Synthetic software test only " + ("complex eligibility " * (i % 5 + 1)) for i in range(n)],
        "study_type": "INTERVENTIONAL", "phase": [f"PHASE{i % 3 + 1}" for i in range(n)],
        "enrollment": rng.integers(20, 1000, n), "number_of_arms": rng.integers(1, 6, n),
        "primary_outcomes": rng.integers(1, 4, n), "secondary_outcomes": rng.integers(0, 8, n),
        "criteria_count": rng.integers(3, 30, n), "status": "COMPLETED",
        "completion_date_type": "ACTUAL", "start_date": starts,
        "completion_date": starts + pd.to_timedelta(durations, unit="D"),
    })


def test_sample_is_not_a_research_cohort(tmp_path):
    sample = pd.read_csv(Path(__file__).parents[1] / "data/sample/trials.csv")
    with pytest.raises(ValueError, match="30 eligible"):
        train_experiment(sample, tmp_path)
    assert json.loads((tmp_path / "error.json").read_text())["status"] == "failed"
    assert not (tmp_path / "models.joblib").exists()


def test_unknown_or_nonactual_outcomes_are_excluded():
    df = software_fixture(10)
    df.loc[0, "completion_date_type"] = "ESTIMATED"
    df.loc[1, "status"] = "RECRUITING"
    df.loc[2, "completion_date"] = pd.NaT
    df.loc[3, "completion_date"] = df.loc[3, "start_date"] - pd.Timedelta(days=1)
    cohort, exclusions = prepare_cohort(df)
    assert len(cohort) == 6
    assert len(exclusions) == 4
    assert cohort["duration_days"].gt(0).all()


def test_duplicate_trial_ids_are_rejected():
    df = software_fixture(40)
    df.loc[1, "nct_id"] = df.loc[0, "nct_id"]
    with pytest.raises(ValueError, match="Duplicate"):
        prepare_cohort(df)


def test_date_groups_and_outcome_availability_are_separated():
    df = software_fixture(100)
    df.loc[1, "start_date"] = df.loc[0, "start_date"]
    cohort, _ = prepare_cohort(df)
    splits = temporal_split(cohort)
    train, val, test = [splits[k] for k in ("train", "validation", "test")]
    assert train.start_date.max() < val.start_date.min() < test.start_date.min()
    assert train.completion_date.max() < splits["validation_cutoff"]
    assert val.completion_date.max() < splits["test_cutoff"]
    assert not set(train.nct_id) & set(test.nct_id)
    for date in cohort.start_date.unique():
        memberships = sum(date in frame.start_date.values for frame in (train, val, test))
        assert memberships <= 1


def test_undefined_auc_and_r2_are_null():
    metrics = evaluate_predictions(np.array([50.0]), np.array([50.0]), np.array([0]), np.array([0.1]), bootstrap_samples=10)
    assert metrics["regression"]["r2"] is None
    assert metrics["classification"]["auroc"] is None
    assert metrics["classification"]["average_precision"] is None
    assert metrics["classification"]["brier"] == pytest.approx(0.01)


def test_end_to_end_fits_only_training_and_exports_actual_results(tmp_path):
    df = software_fixture()
    df.loc[85:, "enrollment"] = 999999  # Test-only extremes must not fit preprocessing.
    df.loc[85:, "brief_summary"] = "heldoutuniquetoken synthetic fixture"
    df.loc[85:, "phase"] = "HELD_OUT_ONLY"
    cfg = ExperimentConfig(bootstrap_samples=10)
    manifest = train_experiment(df, tmp_path, {"dataset_id": "fixture", "is_fixture": True}, config=cfg)
    assert manifest["status"] == "completed"
    assert manifest["source_metadata"]["dataset_id"] == "fixture"
    assert "software" in manifest["warning"].lower()
    assert set(manifest["models"]) == {"median_baseline", "structured", "text", "multimodal", "structured_extra_trees", "structured_random_forest", "structured_gradient_boosting", "structured_hist_gradient_boosting", "multimodal_late_fusion"}
    import joblib
    artifact = joblib.load(tmp_path / "models.joblib")
    assert artifact["pci"]["maximum"]["enrollment"] < 999999
    vectorizer = artifact["models"]["text"]["regressor"].named_steps["preprocess"].named_transformers_["text"]
    assert "heldoutuniquetoken" not in vectorizer.vocabulary_
    train_ids = manifest["splits"]["train"]["nct_ids"]
    train_durations = (df.loc[df.nct_id.isin(train_ids), "completion_date"] - df.loc[df.nct_id.isin(train_ids), "start_date"]).dt.days
    assert manifest["target"]["prolonged_threshold_days"] == pytest.approx(train_durations.quantile(.75))
    for name in ("structured", "structured_extra_trees", "structured_random_forest", "structured_gradient_boosting"):
        for task in ("regressor", "classifier"):
            preprocess = artifact["models"][name][task].named_steps["preprocess"]
            assert "HELD_OUT_ONLY" not in preprocess.named_transformers_["categorical"].categories_[1]
            assert preprocess.named_transformers_["numeric"].named_steps["scaler"].mean_[0] == pytest.approx(df.loc[df.nct_id.isin(train_ids), "enrollment"].mean())
    predictions = pd.read_csv(tmp_path / "held_out_predictions.csv")
    assert set(predictions["split"]) == {split for split in ("validation", "calibration", "test") if manifest["splits"][split]["rows"]}
    assert len(predictions) == 9 * sum(manifest["splits"][s]["rows"] for s in ("validation", "calibration", "test"))
    result = predict_trial(df.iloc[-1].to_dict(), tmp_path)
    assert result["status"] == "available"
    assert 0 <= result["probability"] <= 1
    assert result["duration_days"] >= 0
    assert result["explanation"]["method"] == "linear feature contributions"
    assert result["explanation"]["units"] == "log-odds"
    json.dumps(result, allow_nan=False)


def test_prediction_is_unavailable_without_artifact(tmp_path):
    result = predict_trial({}, tmp_path)
    assert result["status"] == "unavailable"
    assert result["probability"] is None
    assert result["duration_days"] is None


def test_invalid_metric_probabilities_and_fractional_labels_are_rejected():
    with pytest.raises(ValueError, match="probabilit"):
        evaluate_predictions([1, 2], [1, 2], [0, 1], [-0.1, 1.1], 0)
    with pytest.raises(ValueError, match="binary"):
        evaluate_predictions([1, 2], [1, 2], [0, 0.5], [0.1, 0.8], 0)


def test_punctuation_only_text_can_be_trained(tmp_path):
    frame = software_fixture(60)
    frame["title"] = "..."
    frame["brief_summary"] = "---"
    result = train_experiment(frame, tmp_path, {"is_fixture": True}, config=ExperimentConfig(bootstrap_samples=0))
    assert result["status"] == "completed"


def test_aact_tables_are_aggregated_without_multiplying_trials(tmp_path):
    from src.clinical_trial_intelligence.ingestion.aact import extract_aact, verify_snapshot
    raw = tmp_path / "raw"
    raw.mkdir()
    studies = pd.DataFrame({"nct_id": ["TEST-ONLY-A", "TEST-ONLY-B"], "brief_title": ["Test A", "Test B"],
                            "overall_status": ["Completed", "Recruiting"], "start_date": ["2020-01-01"] * 2,
                            "completion_date": ["2020-04-01", "2023-01-01"], "completion_date_type": ["Actual", "Anticipated"],
                            "enrollment": [10, 20], "number_of_arms": [2, None]})
    studies.to_csv(raw / "studies.txt", sep="|", index=False)
    pd.DataFrame({"nct_id": ["TEST-ONLY-A"] * 3, "outcome_type": ["primary", "secondary", "secondary"], "id": [1, 2, 3]}).to_csv(raw / "design_outcomes.txt", sep="|", index=False)
    pd.DataFrame({"nct_id": ["TEST-ONLY-A"], "criteria": ["Inclusion Criteria:\n- Adult\n- Able to consent\nExclusion Criteria:\n- Prior therapy"]}).to_csv(raw / "eligibilities.txt", sep="|", index=False)
    # Posted results must not be mistaken for protocol design outcomes.
    pd.DataFrame({"nct_id": ["TEST-ONLY-A"] * 7, "outcome_type": ["Primary"] * 7}).to_csv(raw / "outcomes.txt", sep="|", index=False)
    original = (raw / "studies.txt").read_bytes()
    frame, manifest = extract_aact(raw, snapshot_date="2024-01-01")
    assert len(frame) == 2
    a = frame.set_index("nct_id").loc["TEST-ONLY-A"]
    assert a["primary_outcomes"] == 1
    assert a["secondary_outcomes"] == 2
    assert a["criteria_count"] == 3
    assert a["status"] == "COMPLETED"
    assert a["completion_date_type"] == "ACTUAL"
    assert (raw / "studies.txt").read_bytes() == original
    assert manifest["baseline_provenance"] is False
    verified = verify_snapshot(raw)
    assert verified["tables"]["studies"]["rows"] == 2
    assert verified["tables"]["studies"]["sha256"] == manifest["source_files"]["studies"]["sha256"]
    (raw / "studies.txt").write_bytes(original + b"\n")
    with pytest.raises(ValueError, match="checksum"):
        verify_snapshot(raw, expected=verified)


def test_aact_missing_tables_remain_unknown_and_bad_schema_fails(tmp_path):
    from src.clinical_trial_intelligence.ingestion.aact import extract_aact
    pd.DataFrame({"nct_id": ["TEST-ONLY-A"], "overall_status": ["COMPLETED"], "start_date": ["2020-01-01"],
                  "completion_date": ["2021-01-01"], "completion_date_type": ["ACTUAL"]}).to_csv(tmp_path / "studies.csv", index=False)
    frame, manifest = extract_aact(tmp_path, snapshot_date="2024-01-01")
    assert frame["primary_outcomes"].isna().all()
    assert frame["criteria_count"].isna().all()
    assert "design_outcomes" in manifest["missing_optional_tables"]
    pd.DataFrame({"wrong": ["column"]}).to_csv(tmp_path / "design_outcomes.csv", index=False)
    with pytest.raises(ValueError, match="design_outcomes"):
        extract_aact(tmp_path, snapshot_date="2024-01-01")


def test_survival_training_censors_future_events_at_cutoff():
    from src.clinical_trial_intelligence.models.survival import temporal_survival_cohort
    frame = pd.DataFrame({"nct_id": ["TEST-A", "TEST-B", "TEST-C"],
                          "start_date": ["2020-01-01", "2020-02-01", "2021-01-01"],
                          "followup_date": ["2020-03-01", "2022-01-01", "2021-06-01"],
                          "event_observed": [1, 1, 0], "enrollment": [10, 20, 30]})
    train, test = temporal_survival_cohort(frame, cutoff="2021-01-01")
    assert train["duration_days"].tolist() == [60.0, 335.0]
    assert train["event_observed"].tolist() == [1, 0]
    assert test["duration_days"].tolist() == [151.0]
    frame["event_observed"] = frame["event_observed"].astype(float)
    frame.loc[0, "event_observed"] = 0.5
    with pytest.raises(ValueError, match="binary"):
        temporal_survival_cohort(frame, cutoff="2021-01-01")


def test_optional_explanations_require_training_background():
    from src.clinical_trial_intelligence.explainability.shap_adapter import explain
    result = explain(None, pd.DataFrame({"enrollment": [1]}))
    assert result["status"] == "unavailable"
    assert "training" in result["reason"].lower()


def test_biobert_requires_immutable_revision_before_loading_weights():
    from src.clinical_trial_intelligence.nlp.biobert import BioBERTEncoder
    with pytest.raises(ValueError, match="commit"):
        BioBERTEncoder(revision="main").fit(["software test"])


def test_mismatched_artifact_manifest_is_not_used(tmp_path):
    train_experiment(software_fixture(60), tmp_path, {"dataset_id": "test", "sha256": "fixture", "is_fixture": True}, config=ExperimentConfig(bootstrap_samples=0))
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["source_metadata"]["sha256"] = "changed"
    manifest_path.write_text(json.dumps(manifest))
    result = predict_trial(software_fixture(1).iloc[0].to_dict(), tmp_path)
    assert result["status"] == "unavailable"
    assert "match" in result["reason"].lower()


def test_partial_dates_do_not_become_invented_first_day_outcomes():
    frame = software_fixture(6)
    frame["start_date"] = frame["start_date"].astype(str)
    frame["completion_date"] = frame["completion_date"].astype(str)
    frame.loc[0, "start_date"] = "2000-01"
    frame.loc[1, "completion_date"] = "2001"
    frame.loc[2, "completion_date"] += "T12:00:00Z"
    cohort, exclusions = prepare_cohort(frame)
    assert len(cohort) == 4
    assert set(exclusions.nct_id) == {"TEST-ONLY-0000", "TEST-ONLY-0001"}
    assert exclusions.reason.str.contains("precision").all()


def test_shap_if_installed_reconstructs_fitted_log_odds(tmp_path):
    pytest.importorskip("shap")
    import joblib
    from src.clinical_trial_intelligence.research import _features
    from src.clinical_trial_intelligence.explainability.shap_adapter import explain
    frame = software_fixture(60)
    manifest = train_experiment(frame, tmp_path, {"is_fixture": True}, config=ExperimentConfig(bootstrap_samples=0))
    model = joblib.load(tmp_path / "models.joblib")["models"]["multimodal"]["classifier"]
    background = _features(frame.loc[frame.nct_id.isin(manifest["splits"]["train"]["nct_ids"])])
    query = _features(frame.iloc[[-1]])
    result = explain(model, query, background=background)
    assert result["status"] == "available"
    assert result["units"] == "log-odds"
    assert np.asarray(result["base_values"]).reshape(-1)[0] + np.asarray(result["values"])[0].sum() == pytest.approx(model.decision_function(query)[0])


@pytest.mark.parametrize('suffix,separator', [('.txt', '|'), ('.csv', ',')])
@pytest.mark.parametrize('problem', ['extra_field', 'short_row', 'duplicate_header', 'empty_header'])
def test_aact_rejects_ambiguous_headers_and_malformed_records(tmp_path, suffix, separator, problem):
    from src.clinical_trial_intelligence.ingestion.aact import extract_aact, verify_snapshot
    header = ['nct_id', 'overall_status', 'start_date', 'completion_date', 'completion_date_type']
    record = ['TEST-ONLY-A', 'COMPLETED', '2020-01-01', '2021-01-01', 'ACTUAL']
    if problem == 'extra_field':
        record.append('UNEXPECTED')
    elif problem == 'short_row':
        record.pop()
    else:
        header.append('completion_date_type' if problem == 'duplicate_header' else '')
        record.append('ESTIMATED')
    path = tmp_path / ('studies' + suffix)
    original = (separator.join(header) + '\n' + separator.join(record) + '\n').encode()
    path.write_bytes(original)
    with pytest.raises(ValueError, match='AACT studies'):
        verify_snapshot(tmp_path)
    with pytest.raises(ValueError, match='AACT studies'):
        extract_aact(tmp_path, snapshot_date='2024-01-01')
    assert path.read_bytes() == original


def test_prediction_reports_training_tuning_and_holdout_membership(tmp_path):
    frame = software_fixture(60)
    manifest = train_experiment(frame, tmp_path, {'is_fixture': True}, config=ExperimentConfig(bootstrap_samples=0))
    for membership in ('train', 'validation', 'test'):
        identifier = manifest['splits'][membership]['nct_ids'][0]
        row = frame.loc[frame.nct_id.eq(identifier)].iloc[0].to_dict()
        result = predict_trial(row, tmp_path)
        assert result['cohort_membership'] == membership
        assert result['prediction_scope']
    row['nct_id'] = 'TEST-ONLY-OUTSIDE-SPLITS'
    assert predict_trial(row, tmp_path)['cohort_membership'] == 'not_in_retained_splits'


@pytest.fixture(scope="module")
def advanced_run(tmp_path_factory):
    """One real fit shared by read-only schema and explanation assertions."""
    import joblib
    frame = software_fixture(80)
    directory = tmp_path_factory.mktemp("duration-v3")
    manifest = train_experiment(frame, directory, {"is_fixture": True}, config=ExperimentConfig(bootstrap_samples=0))
    return frame, directory, manifest, joblib.load(directory / "models.joblib")


def test_advanced_models_export_matching_diagnostics_and_phase_metrics(advanced_run):
    frame, directory, manifest, artifact = advanced_run
    assert manifest["artifact_version"] == artifact["artifact_version"] == 3
    assert manifest["task"] == artifact["task"] == "duration"
    predictions = pd.read_csv(directory / "held_out_predictions.csv")
    for name, model in manifest["models"].items():
        assert model["family"] and model["input_mode"] and model["display_name"]
        for split in ("validation", "test"):
            expected = predictions.loc[(predictions.model_name == name) & (predictions.split == split)]
            diagnostic = model["diagnostics"][split]
            assert diagnostic["total_n"] == diagnostic["scatter_n"] == len(expected)
            assert {point["nct_id"] for point in diagnostic["scatter"]} == set(expected.nct_id)
            for point in diagnostic["scatter"]:
                saved = expected.loc[expected.nct_id.eq(point["nct_id"])].iloc[0]
                assert point["actual"] == pytest.approx(saved.actual_duration_days)
                assert point["predicted"] == pytest.approx(saved.predicted_duration_days)
            reliability = diagnostic["reliability"]
            assert sum(b["count"] for b in reliability["bins"]) == len(expected)
            assert reliability["expected_calibration_error"] == pytest.approx(sum(
                b["count"] / len(expected) * abs(b["mean_probability"] - b["observed_fraction"])
                for b in reliability["bins"]))
        phase_groups = model["metrics"]["test"]["by_phase"]
        assert sum(group["n"] for group in phase_groups) == manifest["splits"]["test"]["rows"]
        test_predictions = predictions.loc[(predictions.model_name == name) & (predictions.split == "test")]
        for group in phase_groups:
            ids = set(frame.loc[frame.phase.eq(group["phase"]), "nct_id"])
            expected = test_predictions.loc[test_predictions.nct_id.isin(ids)]
            assert group["n"] == len(expected)
            assert group["positive_count"] == int(expected.actual_prolonged.sum())
            assert group["regression"]["mae"] == pytest.approx(abs(expected.actual_duration_days - expected.predicted_duration_days).mean())
            assert group["classification"]["brier"] == pytest.approx(((expected.actual_prolonged - expected.prolonged_probability) ** 2).mean())
            assert group["caution"]
    json.dumps(manifest, allow_nan=False)


def test_nonlinear_predictions_use_global_importance_not_local_contributions(advanced_run):
    frame, directory, manifest, artifact = advanced_run
    for name in ("structured_extra_trees", "structured_random_forest"):
        assert manifest["models"][name]["input_mode"] == "structured"
        result = predict_trial(frame.iloc[-1].to_dict(), directory, model_name=name)
        assert result["status"] == "available"
        assert result["duration_days"] >= 0
        assert 0 <= result["probability"] <= 1
        for field in ("explanation", "duration_explanation"):
            explanation = result[field]
            assert explanation["scope"] == "global"
            assert "impurity" in explanation["method"]
            assert "not SHAP" in explanation["note"]
            assert explanation["features"]
            assert all(0 <= value["importance"] <= 1 for value in explanation["features"])
            assert all("contribution" not in value for value in explanation["features"])
        for task in ("regressor", "classifier"):
            fitted = artifact["models"][name][task].named_steps["model"]
            assert len(fitted.estimators_) <= 64
            assert all(tree.tree_.max_depth <= 12 for tree in fitted.estimators_)


def test_test_outcomes_cannot_change_fits_or_recommendation(advanced_run, tmp_path):
    import joblib
    from src.clinical_trial_intelligence.research import _features
    frame, _, original, artifact = advanced_run
    mutated = frame.copy()
    heldout = mutated.nct_id.isin(original["splits"]["test"]["nct_ids"])
    mutated.loc[heldout, "completion_date"] = mutated.loc[heldout, "start_date"] + pd.Timedelta(days=9000)
    updated = train_experiment(mutated, tmp_path, {"is_fixture": True}, config=ExperimentConfig(bootstrap_samples=0))
    updated_artifact = joblib.load(tmp_path / "models.joblib")
    assert updated["recommendation"] == original["recommendation"]
    assert updated["recommended_model"] == original["recommended_model"]
    recommendation = updated["recommendation"]
    assert recommendation["metric"] == "brier"
    assert recommendation["split"] == "validation"
    assert recommendation["value"] == min(model["metrics"]["validation"]["classification"]["brier"] for model in updated["models"].values())
    assert recommendation["model_name"] == updated["recommended_model"]
    query = _features(frame.tail(4))
    for name in updated["models"]:
        assert updated["models"][name]["selection"] == original["models"][name]["selection"]
        np.testing.assert_allclose(artifact["models"][name]["regressor"].predict(query), updated_artifact["models"][name]["regressor"].predict(query), rtol=0, atol=0)
        np.testing.assert_allclose(artifact["models"][name]["classifier"].predict_proba(query), updated_artifact["models"][name]["classifier"].predict_proba(query), rtol=0, atol=0)


def test_disabling_advanced_models_keeps_all_four_original_modalities(tmp_path):
    manifest = train_experiment(software_fixture(60), tmp_path, {"is_fixture": True}, config=ExperimentConfig(bootstrap_samples=0, enable_advanced_models=False))
    assert set(manifest["models"]) == {"median_baseline", "structured", "text", "multimodal"}
    with pytest.raises(ValueError, match="boolean"):
        ExperimentConfig(enable_advanced_models="false").validate()


def test_diagnostic_scatter_is_bounded_deterministic_and_reliability_uses_every_row():
    from src.clinical_trial_intelligence.research import _prediction_diagnostics
    ids = np.array([f"TEST-ONLY-{i:04}" for i in range(601)])
    duration = np.arange(601, dtype=float) + 1
    labels, probability = np.zeros(601), np.zeros(601)
    labels[-1], probability[-1] = 1, 1
    metrics = evaluate_predictions(duration, duration + 2, labels, probability, bootstrap_samples=0)
    first = _prediction_diagnostics(ids, duration, duration + 2, metrics)
    assert first == _prediction_diagnostics(ids, duration, duration + 2, metrics)
    assert first["total_n"] == 601
    assert first["scatter_n"] == len(first["scatter"]) == 200
    assert len({point["nct_id"] for point in first["scatter"]}) == 200
    assert sum(b["count"] for b in first["reliability"]["bins"]) == 601
    assert first["reliability"]["expected_calibration_error"] == 0
    assert first["reliability"]["bins"][-1] == {"lower": .9, "upper": 1.0, "count": 1, "mean_probability": 1.0, "observed_fraction": 1.0}


def test_duration_prediction_rejects_wrong_task_even_with_matching_run(advanced_run, tmp_path):
    import joblib
    _, _, manifest, artifact = advanced_run
    changed_manifest = {**manifest, "task": "phase"}
    changed_artifact = {**artifact, "task": "phase"}
    (tmp_path / "manifest.json").write_text(json.dumps(changed_manifest))
    joblib.dump(changed_artifact, tmp_path / "models.joblib")
    assert predict_trial({}, tmp_path)["status"] == "unavailable"


def test_one_class_training_retains_defined_risk_probabilities_and_null_subgroup_auc(tmp_path):
    frame = software_fixture(60)
    frame["completion_date"] = frame["start_date"] + pd.Timedelta(days=75)
    manifest = train_experiment(frame, tmp_path, {"is_fixture": True}, config=ExperimentConfig(bootstrap_samples=0))
    for name, model in manifest["models"].items():
        result = predict_trial(frame.iloc[-1].to_dict(), tmp_path, name)
        assert result["status"] == "available"
        assert result["probability"] == 0
        for group in model["metrics"]["test"]["by_phase"]:
            assert group["classification"]["auroc"] is None
            assert group["classification"]["average_precision"] is None
            assert group["classification"]["brier"] == 0
            assert group["regression"]["r2"] is None
    baseline = predict_trial(frame.iloc[-1].to_dict(), tmp_path, "median_baseline")
    assert baseline["duration_days"] == 75
    assert baseline["explanation"]["method"] == "constant training baseline"


def test_hourly_starts_do_not_bypass_calendar_day_groups():
    df = software_fixture(10)
    df['start_date'] = pd.date_range('2010-01-01', periods=10, freq='h')
    df['completion_date'] = df['start_date'] + pd.Timedelta(minutes=30)
    cohort, _ = prepare_cohort(df)
    with pytest.raises(ValueError, match='three distinct start-date groups'):
        temporal_split(cohort)


def test_known_answer_regression_and_binary_brier_formulas():
    # Errors [1, -2, 1] give MAE 4/3, RMSE sqrt(2), R2 1-6/8.
    result = evaluate_predictions([1, 3, 5], [2, 1, 6], [0, 1, 1], [.2, .7, .9], 0)
    assert result["regression"]["mae"] == pytest.approx(4 / 3)
    assert result["regression"]["rmse"] == pytest.approx(2 ** .5)
    assert result["regression"]["r2"] == pytest.approx(.25)
    assert result["classification"]["brier"] == pytest.approx(.14 / 3)


def test_split_conformal_uses_finite_sample_rank_and_unbounded_null():
    from src.clinical_trial_intelligence.research import split_conformal_quantile
    # n=10, alpha=.2 => ceil(11*.8)=9, ninth ordered residual is 9.
    answer = split_conformal_quantile([10, 1, 3, 2, 5, 4, 8, 6, 9, 7], .2)
    assert answer["rank"] == 9
    assert answer["residual_quantile_days"] == 9
    assert answer["bounded"] is True
    infinite = split_conformal_quantile([1, 2, 3], .1)
    assert infinite["rank"] == 4
    assert infinite["residual_quantile_days"] is None
    assert infinite["bounded"] is False
    json.dumps(infinite, allow_nan=False)
    for alpha in (0, 1, float('nan')):
        with pytest.raises(ValueError, match='alpha'):
            split_conformal_quantile([1, 2], alpha)


def test_validation_partition_preserves_whole_groups_and_falls_back_without_row_loss():
    from src.clinical_trial_intelligence.research import partition_validation
    frame = software_fixture(26)
    frame.loc[1, 'start_date'] = frame.loc[0, 'start_date']
    tuning, calibration, info = partition_validation(frame)
    assert tuning.start_date.max() < calibration.start_date.min()
    assert set(tuning.nct_id).isdisjoint(calibration.nct_id)
    assert set(tuning.nct_id) | set(calibration.nct_id) == set(frame.nct_id)
    assert info['calibration_available'] is True
    small = frame.head(12)
    tuning, calibration, info = partition_validation(small)
    assert set(tuning.nct_id) == set(small.nct_id)
    assert calibration.empty
    assert info['calibration_available'] is False
    assert info['reason']


@pytest.fixture(scope='module')
def calibrated_run(tmp_path_factory):
    import joblib
    frame = software_fixture(160)
    directory = tmp_path_factory.mktemp('duration-v4-calibrated')
    manifest = train_experiment(frame, directory, {'is_fixture': True}, config=ExperimentConfig(bootstrap_samples=0))
    return frame, directory, manifest, joblib.load(directory / 'models.joblib')


def test_calibration_rows_cannot_select_models_or_fit_preprocessing(calibrated_run, tmp_path):
    import joblib
    from src.clinical_trial_intelligence.research import _features
    frame, _, original, artifact = calibrated_run
    ids = original['splits']['calibration']['nct_ids']
    assert len(ids) >= 10
    mutated = frame.copy()
    mask = mutated.nct_id.isin(ids)
    # Retained outcomes remain earlier than test cutoff; only calibration values change.
    mutated.loc[mask, 'completion_date'] = mutated.loc[mask, 'start_date'] + pd.Timedelta(days=1)
    mutated.loc[mask, 'enrollment'] = 99999999
    mutated.loc[mask, 'phase'] = 'CALIBRATION_ONLY'
    mutated.loc[mask, 'title'] = 'calibrationonlytoken'
    changed = train_experiment(mutated, tmp_path, {'is_fixture': True}, config=ExperimentConfig(bootstrap_samples=0))
    fitted = joblib.load(tmp_path / 'models.joblib')
    assert changed['recommendation'] == original['recommendation']
    assert changed['recommended_model'] == original['recommended_model']
    query = _features(frame.tail(3))
    for name in original['models']:
        assert changed['models'][name]['selection'] == original['models'][name]['selection']
        np.testing.assert_array_equal(artifact['models'][name]['regressor'].predict(query), fitted['models'][name]['regressor'].predict(query))
        np.testing.assert_array_equal(artifact['models'][name]['classifier'].predict_proba(query), fitted['models'][name]['classifier'].predict_proba(query))
    assert 'CALIBRATION_ONLY' not in fitted['models']['structured_gradient_boosting']['regressor'].named_steps['preprocess'].named_transformers_['categorical'].categories_[1]


def test_calibrated_prediction_and_test_metrics_share_probability_semantics(calibrated_run):
    frame, directory, manifest, artifact = calibrated_run
    predictions = pd.read_csv(directory / 'held_out_predictions.csv')
    assert set(predictions.split) == {'validation', 'calibration', 'test'}
    for name, model in manifest['models'].items():
        test = predictions.loc[(predictions.model_name == name) & (predictions.split == 'test')]
        assert model['metrics']['test']['classification']['brier'] == pytest.approx(((test.actual_prolonged - test.prolonged_probability) ** 2).mean())
        assert model['metrics']['test']['calibrated_classification']['brier'] == pytest.approx(((test.actual_prolonged - test.calibrated_prolonged_probability) ** 2).mean())
        for identifier in test.nct_id.head(2):
            row = frame.loc[frame.nct_id.eq(identifier)].iloc[0].to_dict()
            result = predict_trial(row, directory, name)
            saved = test.loc[test.nct_id.eq(identifier)].iloc[0]
            assert result['probability'] == pytest.approx(saved.prolonged_probability)
            assert result['calibrated_probability'] == pytest.approx(saved.calibrated_prolonged_probability)
            assert result['uncertainty']['status'] == 'available'
            assert result['uncertainty']['alpha'] == .1
            assert result['calibration']['status'] == 'available'
            assert result['probability_semantics'] == 'raw'
            assert result['uncertainty']['lower_days'] <= result['duration_days'] <= result['uncertainty']['upper_days']
    row = frame.loc[frame.nct_id.eq(manifest['splits']['calibration']['nct_ids'][0])].iloc[0].to_dict()
    assert predict_trial(row, directory)['cohort_membership'] == 'calibration'
    assert manifest['recommendation']['probability_semantics'] == 'raw'
    assert manifest['recommendation']['value'] == min(model['metrics']['validation']['classification']['brier'] for model in manifest['models'].values())


def test_extrapolation_flags_use_only_training_support(calibrated_run):
    frame, directory, manifest, _ = calibrated_run
    row = frame.iloc[-1].to_dict()
    row['enrollment'] = 100000000
    row['phase'] = 'UNSEEN_PROTOCOL_PHASE'
    result = predict_trial(row, directory)
    assert result['extrapolation']['outside_training_support'] is True
    assert 'enrollment' in {flag['feature'] for flag in result['extrapolation']['numeric_out_of_range']}
    assert {'feature': 'phase', 'value': 'UNSEEN_PROTOCOL_PHASE'} in result['extrapolation']['unseen_categories']
    assert 'ood_probability' not in result['extrapolation']
    json.dumps(result, allow_nan=False)


def test_insufficient_calibration_discloses_raw_probability_and_unavailable_intervals(advanced_run):
    frame, directory, manifest, _ = advanced_run
    assert manifest['splits']['calibration']['rows'] == 0
    assert manifest['validation_partition']['calibration_available'] is False
    for name in manifest['models']:
        result = predict_trial(frame.iloc[-1].to_dict(), directory, name)
        assert result['probability'] == result['raw_probability']
        assert result['probability_semantics'] == 'raw'
        assert result['calibration']['status'] == 'unavailable'
        assert result['uncertainty']['status'] == 'unavailable'
        assert result['uncertainty']['lower_days'] is None
        assert result['uncertainty']['upper_days'] is None


def test_probability_calibration_refuses_single_class_support(tmp_path):
    frame = software_fixture(160)
    frame['completion_date'] = frame['start_date'] + pd.Timedelta(days=75)
    manifest = train_experiment(frame, tmp_path, {'is_fixture': True}, config=ExperimentConfig(bootstrap_samples=0))
    assert manifest['splits']['calibration']['rows'] >= 10
    result = predict_trial(frame.iloc[-1].to_dict(), tmp_path)
    assert result['probability'] == result['raw_probability'] == 0
    assert result['calibration']['status'] == 'unavailable'
    assert result['calibration']['class_counts']['1'] == 0
    assert result['uncertainty']['status'] == 'available'


def test_sigmoid_calibration_requires_two_labels_in_each_class():
    from src.clinical_trial_intelligence.research import _fit_probability_calibration
    result = _fit_probability_calibration(np.linspace(.05, .95, 10), np.array([0] * 9 + [1]), ExperimentConfig())
    assert result['metadata']['status'] == 'unavailable'
    assert result['metadata']['class_counts'] == {'0': 9, '1': 1}
    assert result['estimator'] is None


def test_gradient_boosting_has_bounded_training_fitted_capacity(calibrated_run):
    _, _, manifest, artifact = calibrated_run
    name = 'structured_gradient_boosting'
    assert manifest['models'][name]['family'] == 'gradient_boosting'
    for task in ('regressor', 'classifier'):
        model = artifact['models'][name][task].named_steps['model']
        assert len(model.estimators_) == 64
        assert all(tree.tree_.max_depth <= 3 for tree in model.estimators_.flat)
        assert model.random_state == 42


def test_unbounded_conformal_interval_is_json_null(tmp_path):
    frame = software_fixture(160)
    manifest = train_experiment(frame, tmp_path, {'is_fixture': True}, config=ExperimentConfig(bootstrap_samples=0, uncertainty_alpha=.01))
    result = predict_trial(frame.iloc[-1].to_dict(), tmp_path)
    uncertainty = result['uncertainty']
    assert uncertainty['status'] == 'available'
    assert uncertainty['bounded'] is False
    assert uncertainty['rank'] == uncertainty['n'] + 1
    assert uncertainty['residual_quantile_days'] is None
    assert uncertainty['lower_days'] is None
    assert uncertainty['upper_days'] is None
    assert manifest['models']['multimodal']['uncertainty']['test_diagnostics']['observed_coverage'] == 1
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('field,value', [('artifact_version', 2), ('input_sha256', 'changed'), ('pipeline_source_sha256', 'changed')])
def test_duration_prediction_rejects_old_artifacts_and_changed_hashes(advanced_run, tmp_path, field, value):
    import joblib
    _, _, manifest, artifact = advanced_run
    changed = {**manifest, field: value}
    (tmp_path / 'manifest.json').write_text(json.dumps(changed))
    joblib.dump(artifact, tmp_path / 'models.joblib')
    assert predict_trial({}, tmp_path)['status'] == 'unavailable'


def test_test_outcomes_cannot_fit_probability_calibration_or_conformal_quantile(calibrated_run, tmp_path):
    import joblib
    frame, _, original, artifact = calibrated_run
    mutated = frame.copy()
    mask = mutated.nct_id.isin(original['splits']['test']['nct_ids'])
    mutated.loc[mask, 'completion_date'] = mutated.loc[mask, 'start_date'] + pd.Timedelta(days=9000)
    changed = train_experiment(mutated, tmp_path, {'is_fixture': True}, config=ExperimentConfig(bootstrap_samples=0))
    fitted = joblib.load(tmp_path / 'models.joblib')
    assert changed['recommendation'] == original['recommendation']
    for name in original['models']:
        assert fitted['uncertainty'][name]['residual_quantile_days'] == artifact['uncertainty'][name]['residual_quantile_days']
        assert fitted['calibration'][name]['metadata'] == artifact['calibration'][name]['metadata']
        np.testing.assert_array_equal(fitted['calibration'][name]['estimator'].coef_, artifact['calibration'][name]['estimator'].coef_)
        np.testing.assert_array_equal(fitted['calibration'][name]['estimator'].intercept_, artifact['calibration'][name]['estimator'].intercept_)


def test_uncertainty_test_coverage_matches_exported_duration_predictions(calibrated_run):
    _, directory, manifest, _ = calibrated_run
    predictions = pd.read_csv(directory / 'held_out_predictions.csv')
    for name, model in manifest['models'].items():
        rows = predictions.loc[(predictions.model_name == name) & (predictions.split == 'test')]
        quantile = model['uncertainty']['residual_quantile_days']
        covered = abs(rows.actual_duration_days - rows.predicted_duration_days) <= quantile
        report = model['uncertainty']['test_diagnostics']
        assert report['n'] == len(rows)
        assert report['covered_count'] == int(covered.sum())
        assert report['observed_coverage'] == pytest.approx(covered.mean())


def test_conformal_rank_uses_decimal_alpha_at_integer_boundaries():
    from src.clinical_trial_intelligence.research import split_conformal_quantile
    assert split_conformal_quantile(list(range(9)), .7)['rank'] == 3
    assert split_conformal_quantile(list(range(39)), .825)['rank'] == 7


def test_duration_phase_features_normalize_aliases_without_merging_combined_phases():
    from src.clinical_trial_intelligence.research import _features
    source = software_fixture(4)
    source['phase'] = ['PHASE1|PHASE2', 'PHASE1/PHASE2', 'Phase I|Phase II', 'PHASE1']
    features = _features(source)
    assert features.phase.tolist() == ['PHASE1/PHASE2'] * 3 + ['PHASE1']
