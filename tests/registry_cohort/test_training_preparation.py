"""Artificial software fixtures validate preparation/runner logic, not accuracy."""
import gzip
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name="prepare_registry_training"):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def rows(count=80):
    return pd.DataFrame([{"nct_id": f"NCT{index + 1:08d}", "start_date": str(pd.Timestamp("2000-01-01") + pd.Timedelta(days=index * 100))[:10],
                          "completion_date": str(pd.Timestamp("2000-01-01") + pd.Timedelta(days=index * 100 + 20))[:10],
                          "start_date_type": "ACTUAL", "completion_date_type": "ACTUAL", "status": "COMPLETED",
                          "phase": f"PHASE{index % 4 + 1}", "source_retrieved_at": "2026-10-18T12:00:00+00:00"} for index in range(count)])


def source_fixture(tmp_path, m, frame=None):
    source = tmp_path / "source"
    (source / "raw").mkdir(parents=True)
    (source / "shards").mkdir()
    frame = rows() if frame is None else frame
    raw = b'{"software_fixture": true}'
    compressed = gzip.compress(raw, mtime=0)
    (source / "raw/page-000001.json.gz").write_bytes(compressed)
    frame.drop(columns="source_retrieved_at").to_parquet(source / "shards/part-000001.parquet", index=False)
    state = {"acquisition_complete": True, "is_fixture": False, "baseline_provenance": False, "rows": len(frame),
             "pages": [{"file": "raw/page-000001.json.gz", "canonical_file": "shards/part-000001.parquet", "canonical_rows": len(frame),
                        "gzip_sha256": m.sha256_file(source / "raw/page-000001.json.gz"), "uncompressed_bytes": len(raw),
                        "response_sha256": __import__("hashlib").sha256(raw).hexdigest(), "canonical_sha256": m.sha256_file(source / "shards/part-000001.parquet"),
                        "retrieved_at": "2026-10-18T12:00:00+00:00"}]}
    # Only a software test transport fixture; this flag exercises the production
    # metadata gate. These records are never fitted or reported as research.
    (source / "metadata.json").write_text(json.dumps(state))
    return source


def test_historical_union_includes_raw_excluded_rows_and_every_old_manifest(tmp_path):
    m = module()
    (tmp_path / "data/starter/raw").mkdir(parents=True)
    (tmp_path / "data/clinicaltrials-v5-recovered").mkdir(parents=True)
    (tmp_path / "examples/old").mkdir(parents=True)
    (tmp_path / "examples/registry-v5205").mkdir()
    (tmp_path / "data/starter/trials.csv").write_text("nct_id\nNCT00000001\n")
    (tmp_path / "data/starter/raw/page.json.gz").write_bytes(gzip.compress(b'{"nctId":"NCT00000002"}'))
    (tmp_path / "data/clinicaltrials-v5-recovered/metadata.json").write_text('{"id":"NCT00000003"}')
    (tmp_path / "examples/old/manifest.json").write_text('{"splits":{"test":{"nct_ids":["NCT00000004"]}}}')
    (tmp_path / "examples/registry-v5205/manifest.json").write_text('{"id":"NCT00000005"}')
    ids, inventory = m.historical_exposure(tmp_path)
    assert set(ids) == {f"NCT{index:08d}" for index in range(1, 5)}
    assert len(inventory) == 4


def test_duration_exact_actual_observed_dates_do_not_filter_phase_target(tmp_path):
    m = module()
    frame = rows(7)
    frame.loc[1, "completion_date"] = "2027-01-01"
    frame.loc[2, "start_date"] = "2000-02"
    frame.loc[3, "completion_date_type"] = "ESTIMATED"
    frame.loc[4, "start_date_type"] = "Not reported"
    frame.loc[5, "completion_date"] = "2000-02-30"
    frame.loc[6, "phase"] = "PHASE1|PHASE2"
    original = frame.copy(deep=True)
    duration, excluded, phase, phase_excluded = m.eligibility(frame)
    assert set(duration.nct_id) == {"NCT00000001", "NCT00000007"}
    assert "completion_after_source_retrieval_day" in excluded.loc[excluded.nct_id.eq("NCT00000002"), "reason"].iloc[0]
    assert set(phase.nct_id) == {"NCT00000001", "NCT00000002", "NCT00000004", "NCT00000005", "NCT00000006"}
    assert "combined_phase" in phase_excluded.loc[phase_excluded.nct_id.eq("NCT00000007"), "reason"].iloc[0]
    pd.testing.assert_frame_equal(frame, original)


def test_preparation_freezes_partitions_excludes_union_and_detects_tampering(tmp_path):
    m = module()
    source = source_fixture(tmp_path, m)
    (tmp_path / "data/starter").mkdir(parents=True)
    (tmp_path / "data/starter/trials.csv").write_text("nct_id\nNCT00000001\n")
    output = tmp_path / "prepared"
    manifest = m.prepare(source, output, root=tmp_path)
    assert manifest["counts"]["source_unique_rows"] == 80
    assert manifest["counts"]["historical_source_rows_excluded"] == 1
    assert manifest["counts"]["duration_eligible_rows"] == 79
    frame, verified = m.load_prepared(output, task="duration")
    assert "NCT00000001" not in set(frame.nct_id)
    assert verified["dataset_sha256"] == manifest["dataset_sha256"]
    assert m.prepare(source, output, root=tmp_path, resume=True)["dataset_sha256"] == manifest["dataset_sha256"]
    with pytest.raises(ValueError, match="exists"):
        m.prepare(source, output, root=tmp_path)
    (output / "duration_partitions.csv").write_text("tampered")
    with pytest.raises(ValueError, match="checksum"):
        m.load_prepared(output)


def test_runner_default_checks_fixture_partitions_without_fitting_or_writing(tmp_path, monkeypatch):
    m, runner = module(), module("train_reference_models")
    source = source_fixture(tmp_path, m)
    prepared = tmp_path / "prepared"
    m.prepare(source, prepared, root=tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail("Software preparation checks must never fit a model")
    monkeypatch.setattr(runner, "train_experiment", forbidden)
    monkeypatch.setattr(runner, "train_phase_experiment", forbidden)
    output = tmp_path / "never-written"
    result = runner.run(prepared, output)
    assert result["status"] == "checked_not_fitted"
    assert set(result["split_rows"]) == {"duration", "phase"}
    assert not output.exists()


def test_resume_refuses_failed_fit_and_checks_completed_evidence(tmp_path):
    runner = module("train_reference_models")
    with pytest.raises(ValueError, match="incomplete"):
        runner._verify_completed(tmp_path, {"status": "failed"})
    (tmp_path / "evidence.json").write_text("saved actual evidence")
    record = {"status": "completed", "files_sha256": {"evidence.json": runner.sha256_file(tmp_path / "evidence.json")}}
    runner._verify_completed(tmp_path, record)
    (tmp_path / "evidence.json").write_text("changed")
    with pytest.raises(ValueError, match="integrity"):
        runner._verify_completed(tmp_path, record)


def test_metrics_export_preserves_nested_undefined_values_and_evidence(tmp_path):
    exporter = module("export_reference_metrics")
    records = exporter.metric_records("duration", {"fixture_model": {"test": {"regression": {"mae": 2.5}, "classification": {"auroc": None}, "interval": [1, 3]}}})
    assert records == [{"task": "duration", "model": "fixture_model", "split": "test", "metric": "regression.mae", "value": 2.5, "defined": True},
                       {"task": "duration", "model": "fixture_model", "split": "test", "metric": "classification.auroc", "value": None, "defined": False}]
    experiment = tmp_path / "experiment"
    experiment.mkdir()
    state = {"status": "completed", "plan": {"dataset_sha256": "software-fixture"}, "tasks": {}}
    originals = {}
    for task in ("duration", "phase"):
        directory = experiment / task
        directory.mkdir()
        filename = "metrics.json" if task == "duration" else "phase_metrics.json"
        path = directory / filename
        path.write_text(json.dumps({"fixture_model": {"test": {"mae": 2.5}}}))
        originals[path] = path.read_bytes()
        state["tasks"][task] = {"status": "completed", "files_sha256": {filename: exporter.sha256_file(path)}}
    (experiment / "run_manifest.json").write_text(json.dumps(state))
    report = exporter.export(experiment, tmp_path / "report")
    assert report["rows"] == 2
    for path, original in originals.items():
        assert path.read_bytes() == original
    with pytest.raises(ValueError, match="exists"):
        exporter.export(experiment, tmp_path / "report")
