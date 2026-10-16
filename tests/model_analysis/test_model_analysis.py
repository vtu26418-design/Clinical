"""Artificial examples below verify software arithmetic, not clinical accuracy.

These pure report tests do not need the application's PostgreSQL fixture.
Run: python -m pytest --confcutdir=tests/model_analysis tests/model_analysis -q
"""
import csv
import json
from pathlib import Path

import pytest

from src.clinical_trial_intelligence.model_analysis import (
    analyze_experiment, render_analysis_csv, render_analysis_html, write_analysis_report,
)


def experiment(tmp_path, rows=None, name="run"):
    directory = tmp_path / name
    directory.mkdir()
    rows = rows or [
        {"nct_id": "TEST-A", "split": "test", "model_name": "model", "actual_duration_days": 10, "predicted_duration_days": 20, "actual_prolonged": 0, "prolonged_probability": 0.2, "prolonged_threshold_days": 15},
        {"nct_id": "TEST-B", "split": "test", "model_name": "model", "actual_duration_days": 20, "predicted_duration_days": 10, "actual_prolonged": 1, "prolonged_probability": 0.8, "prolonged_threshold_days": 15},
    ]
    manifest = {"task": "duration", "status": "completed", "run_id": "test-only", "target": {"prolonged_threshold_days": 15}, "models": {"model": {}}, "splits": {"train": {"rows": 1, "nct_ids": ["TRAIN"]}, "test": {"rows": len(rows), "nct_ids": [row["nct_id"] for row in rows]}}, "source_metadata": {"is_fixture": True}}
    (directory / "manifest.json").write_text(json.dumps(manifest))
    (directory / "metrics.json").write_text('{"model":{"test":{"accuracy":999,"mae":0}}}')
    write_rows(directory, rows)
    return directory


def write_rows(directory, rows):
    with (directory / "held_out_predictions.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        writer.writeheader()
        writer.writerows(rows)


def load_rows(directory):
    with (directory / "held_out_predictions.csv").open() as stream:
        return list(csv.DictReader(stream))


def test_recompute_numeric_metrics_instead_of_copying_claims(tmp_path):
    directory = experiment(tmp_path)
    result = analyze_experiment(directory)
    row = result["models"][0]
    assert row["regression"]["mae_days"] == 10
    assert row["regression"]["rmse_days"] == 10
    assert row["regression"]["r2"] == -3
    classification = row["classification"]
    for metric in ("accuracy", "balanced_accuracy", "precision", "recall", "f1", "auroc", "average_precision"):
        assert classification[metric] == 1
    assert classification["brier"] == pytest.approx(0.04)
    assert classification["calibration"]["expected_calibration_error"] == pytest.approx(0.2)
    assert classification["confusion_matrix"] == [[1, 0], [0, 1]]
    assert result["split_counts"]["test"]["n"] == 2
    assert str(tmp_path) not in json.dumps(result)
    assert "currently selected" in result["provenance_scope"]


def test_one_class_and_constant_regression_are_explicitly_undefined(tmp_path):
    directory = experiment(tmp_path)
    rows = load_rows(directory)
    rows[1].update(actual_duration_days=10, actual_prolonged=0, prolonged_probability=0.1)
    write_rows(directory, rows)
    row = analyze_experiment(directory)["models"][0]
    assert row["regression"]["r2"] is None
    for metric in ("auroc", "average_precision", "balanced_accuracy", "precision", "recall", "f1"):
        assert row["classification"][metric] is None
    assert row["classification"]["accuracy"] == 1
    assert row["classification"]["undefined_reasons"]


@pytest.mark.parametrize("field,value", [("prolonged_probability", "nan"), ("prolonged_probability", "1.1"), ("actual_prolonged", ".5"), ("actual_duration_days", "-1"), ("predicted_duration_days", "inf"), ("actual_duration_days", ""), ("actual_prolonged", "1"), ("prolonged_threshold_days", "16"), ("calibrated_prolonged_probability", "-0.1")])
def test_invalid_values_rejected(tmp_path, field, value):
    directory = experiment(tmp_path)
    rows = load_rows(directory)
    rows[0][field] = value
    write_rows(directory, rows)
    with pytest.raises(ValueError):
        analyze_experiment(directory)


def test_duplicate_and_wrong_membership_rejected(tmp_path):
    directory = experiment(tmp_path)
    rows = load_rows(directory)
    write_rows(directory, rows + [rows[0]])
    with pytest.raises(ValueError, match="Duplicated prediction"):
        analyze_experiment(directory)
    rows[0]["nct_id"] = "UNKNOWN"
    write_rows(directory, rows)
    with pytest.raises(ValueError, match="membership"):
        analyze_experiment(directory)


def test_incomplete_membership_rejected(tmp_path):
    directory = experiment(tmp_path)
    write_rows(directory, load_rows(directory)[:1])
    with pytest.raises(ValueError, match="Incomplete"):
        analyze_experiment(directory)


def test_manifest_overlap_rejected(tmp_path):
    directory = experiment(tmp_path)
    manifest = json.loads((directory / "manifest.json").read_text())
    manifest["splits"]["train"]["nct_ids"] = ["TEST-A"]
    (directory / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Duplicated IDs"):
        analyze_experiment(directory)


def test_escaping_reproducibility_and_safe_outputs(tmp_path):
    directory = experiment(tmp_path)
    report = analyze_experiment(directory)
    malicious = '<script>alert("x")</script>'
    report["run"]["run_id"] = malicious
    report["charts"][0]["title"] = malicious
    report["limitations"].append(malicious)
    rendered = render_analysis_html(report)
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "<svg " in rendered
    assert "http://www.w3.org/2000/svg" in rendered
    assert "<script src=" not in rendered
    assert render_analysis_html(report) == rendered
    report["models"][0]["model_name"] = '=HYPERLINK("http://bad")'
    assert "'=HYPERLINK" in render_analysis_csv(report)
    paths = write_analysis_report(directory, tmp_path / "output")
    other = write_analysis_report(directory, tmp_path / "output2")
    for kind in ("json", "html", "csv"):
        assert Path(paths[kind]).read_bytes() == Path(other[kind]).read_bytes()
    with pytest.raises(ValueError, match="outside"):
        write_analysis_report(directory, directory / "report")
    with pytest.raises(ValueError, match="already exists"):
        write_analysis_report(directory, tmp_path / "output")


def test_paired_comparison_requires_same_ids_and_outcomes(tmp_path):
    candidate = experiment(tmp_path, name="candidate")
    baseline = experiment(tmp_path, name="baseline")
    rows = load_rows(baseline)
    rows[0]["predicted_duration_days"] = 30
    write_rows(baseline, rows)
    paired = analyze_experiment(candidate, baseline)["paired_comparison"]
    assert paired["matched_model_deltas"][0]["regression.mae_days_delta"] == -5
    assert "regression.mae_days_delta" in render_analysis_csv(analyze_experiment(candidate, baseline))
    rows[0].update(actual_duration_days=11)
    write_rows(baseline, rows)
    with pytest.raises(ValueError, match="same held-out"):
        analyze_experiment(candidate, baseline)


def test_calibrated_probabilities_are_separate_and_complete(tmp_path):
    directory = experiment(tmp_path)
    rows = load_rows(directory)
    for row in rows:
        row["calibrated_prolonged_probability"] = 0.5
    write_rows(directory, rows)
    result = analyze_experiment(directory)["models"][0]
    assert result["classification"]["brier"] == pytest.approx(.04)
    assert result["calibrated_classification"]["brier"] == .25
    assert result["calibrated_classification"]["confusion_matrix"] == [[0, 1], [0, 1]]
    rows[0]["calibrated_prolonged_probability"] = ""
    write_rows(directory, rows)
    with pytest.raises(ValueError, match="Incomplete calibrated"):
        analyze_experiment(directory)


def test_phase_macro_arithmetic_and_probability_validation(tmp_path):
    directory = tmp_path / "phase"
    directory.mkdir()
    manifest = {"task": "phase", "status": "completed", "run_id": "phase-software-test", "labels": ["A", "B", "C"], "models": {"phase": {}}, "splits": {"test": {"rows": 3, "nct_ids": ["1", "2", "3"]}}}
    (directory / "phase_manifest.json").write_text(json.dumps(manifest))
    (directory / "phase_metrics.json").write_text('{}')
    rows = [
        {"nct_id": "1", "split": "test", "model_name": "phase", "actual_phase": "A", "predicted_phase": "A", "probability_A": .8, "probability_B": .1, "probability_C": .1},
        {"nct_id": "2", "split": "test", "model_name": "phase", "actual_phase": "A", "predicted_phase": "B", "probability_A": .1, "probability_B": .8, "probability_C": .1},
        {"nct_id": "3", "split": "test", "model_name": "phase", "actual_phase": "B", "predicted_phase": "B", "probability_A": .1, "probability_B": .8, "probability_C": .1},
    ]
    def save():
        write_rows(directory, rows)
        (directory / "held_out_predictions.csv").rename(directory / "phase_held_out_predictions.csv")
    save()
    result = analyze_experiment(directory)["models"][0]["classification"]
    assert result["accuracy"] == pytest.approx(2/3)
    assert result["balanced_accuracy"] == .75
    assert result["macro_precision"] == .75
    assert result["macro_recall"] == .75
    assert result["macro_f1"] == pytest.approx(2/3)
    assert result["confusion_matrix"] == [[1, 1, 0], [0, 1, 0], [0, 0, 0]]
    assert result["one_vs_rest"]["C"]["auroc"] is None
    rows[0]["probability_A"] = 1
    save()
    with pytest.raises(ValueError, match="sum to one"):
        analyze_experiment(directory)
    rows[0]["probability_A"] = .8
    rows[0]["actual_phase"] = "UNKNOWN"
    save()
    with pytest.raises(ValueError, match="Unknown actual"):
        analyze_experiment(directory)


def test_bundled_examples_load_without_any_model_deserialization(monkeypatch):
    import joblib
    def forbidden(*args, **kwargs):
        raise AssertionError("Report must never deserialize estimators")
    monkeypatch.setattr(joblib, "load", forbidden)
    root = Path(__file__).resolve().parents[2]
    for name, expected in (("starter-duration-v5", 27), ("starter-phase-v5", 4)):
        report = analyze_experiment(root / "examples" / name)
        assert len(report["models"]) == expected
        assert report["charts"]


def test_optional_pdf_dependency_does_not_affect_html(tmp_path, monkeypatch):
    import builtins
    directory = experiment(tmp_path)
    original = builtins.__import__
    def missing_reportlab(name, *args, **kwargs):
        if name.startswith("reportlab"):
            raise ImportError("not installed in normal Docker image")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", missing_reportlab)
    paths = write_analysis_report(directory, tmp_path / "html-only")
    assert Path(paths["html"]).is_file()
    with pytest.raises(ValueError, match="requires optional reportlab"):
        write_analysis_report(directory, tmp_path / "pdf-missing", pdf=True)
    assert not (tmp_path / "pdf-missing").exists()


def test_artifact_references_cannot_escape_run_folder(tmp_path):
    directory = experiment(tmp_path)
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"] = {"metrics": "../outside.json"}
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="basenames"):
        analyze_experiment(directory)
