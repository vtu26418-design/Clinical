"""Run frozen real-registry duration/phase experiments, without activating models.

Default is a prefit integrity/count check. Explicit --execute starts fitting.
--resume skips hash-verified completed tasks and runs only untouched tasks;
incomplete attempted fits are never overwritten or silently fitted again.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

# Bound native libraries before numpy/sklearn are imported; one fit at a time.
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import pandas as pd
from threadpoolctl import threadpool_limits
from prepare_registry_training import load_prepared, sha256_file, object_hash, write_json
from src.clinical_trial_intelligence.research import ExperimentConfig, prepare_cohort, temporal_split, partition_validation, train_experiment
from src.clinical_trial_intelligence.phase_model import PhaseConfig, prepare_phase_cohort, phase_temporal_split, train_phase_experiment


def task_config(task, prepared, config_path=None):
    path = Path(config_path or ROOT / "configs" / ("research-design.json" if task == "duration" else "phase-design.json"))
    if sha256_file(path) != prepared["contract"][task + "_config_sha256"]:
        raise ValueError("Training configuration changed after cohort/partition freeze.")
    config_type = ExperimentConfig if task == "duration" else PhaseConfig
    config = config_type(**json.loads(path.read_text(encoding="utf-8")))
    config.validate()
    return config, path


def verify_task_partitions(frame, prepared, task, config, prepared_dir):
    if task == "duration":
        cohort, excluded = prepare_cohort(frame, prepared["source_metadata"])
        if len(excluded):
            raise ValueError("Prepared duration eligibility drifted.")
        splits = temporal_split(cohort, config)
        splits["validation"], splits["calibration"], _ = partition_validation(splits["validation"])
        threshold = float(splits["train"].duration_days.quantile(config.prolonged_quantile))
        if threshold != prepared["duration"]["threshold_days"]:
            raise ValueError("Training-derived endpoint threshold changed after cohort freeze.")
    else:
        cohort, excluded = prepare_phase_cohort(frame)
        if len(excluded):
            raise ValueError("Prepared phase eligibility drifted.")
        splits = phase_temporal_split(cohort)
    expected = pd.read_csv(Path(prepared_dir) / f"{task}_partitions.csv")
    for role, summary in prepared[task]["splits"].items():
        identifiers = splits[role].nct_id.tolist()
        if identifiers != expected.loc[expected.split.eq(role), "nct_id"].tolist() or len(identifiers) != summary["rows"]:
            raise ValueError("Task split IDs differ from the prefit freeze.")
    if task == "duration" and (len(splits["train"]) < 12 or min(len(splits[s]) for s in ("validation", "test")) < 3):
        raise ValueError("Duration software support guard failed before fitting.")
    if task == "phase" and (len(splits["train"]) < 20 or min(len(splits[s]) for s in ("validation", "test")) < 5 or splits["train"].phase.nunique() < 2):
        raise ValueError("Phase software support guard failed before fitting.")
    return {role: len(splits[role]) for role in prepared[task]["splits"]}


def _code_inventory():
    files = ["scripts/train_reference_models.py", "scripts/prepare_registry_training.py", "src/clinical_trial_intelligence/research.py", "src/clinical_trial_intelligence/phase_model.py", "src/clinical_trial_intelligence/models/accuracy.py", "src/clinical_trial_intelligence/models/design.py", "src/clinical_trial_intelligence/models/catboost_compat.py"]
    return {name: sha256_file(ROOT / name) for name in files}


def _flatten_metrics(metrics):
    records = []
    for model, splits in metrics.items():
        for split, values in splits.items():
            if not isinstance(values, dict):
                continue
            for metric, value in values.items():
                if value is None or isinstance(value, (int, float)) and not isinstance(value, bool):
                    records.append({"model": model, "split": split, "metric": metric, "value": value})
    return pd.DataFrame(records, columns=["model", "split", "metric", "value"])


def _verify_completed(directory, record):
    if record.get("status") != "completed":
        raise ValueError("An incomplete attempted fit cannot resume or overwrite evidence; inspect its error and use a newly authorized experiment.")
    for name, expected in record["files_sha256"].items():
        if Path(name).name != name or (directory / name).is_symlink() or sha256_file(directory / name) != expected:
            raise ValueError("Completed experiment file integrity check failed.")


def run(prepared_dir, output_dir, *, task="all", execute=False, resume=False, duration_config=None, phase_config=None):
    if task not in ("all", "duration", "phase"):
        raise ValueError("Unknown task.")
    prepared_dir, output_dir = Path(prepared_dir).resolve(), Path(output_dir).resolve()
    _, prepared = load_prepared(prepared_dir, load_rows=False)
    # Frozen protocol and configurations are always checked, even when one task
    # was already completed, so changing a later comparison cannot be silent.
    protocol = ROOT / "configs/v5205-frozen-experiment.json"
    if sha256_file(protocol) != prepared["contract"]["protocol_sha256"]:
        raise ValueError("Frozen experiment protocol changed after cohort preparation.")
    configs = {name: task_config(name, prepared, duration_config if name == "duration" else phase_config)[0] for name in ("duration", "phase")}
    plan = {"dataset_id": prepared["dataset_id"], "dataset_sha256": prepared["dataset_sha256"],
            "preparation_manifest_sha256": sha256_file(prepared_dir / "preparation_manifest.json"),
            "protocol_sha256": prepared["contract"]["protocol_sha256"], "code_sha256": _code_inventory(),
            "configs": {name: json.loads(json.dumps(asdict(config))) for name, config in configs.items()},
            "promotion": "No catalog changes or project activation. Selection uses frozen tuning objectives; test is evaluation only.",
            "resume": "Skip verified completed tasks only. Never overwrite or repeat an incomplete attempted fit."}
    tasks = ("duration", "phase") if task == "all" else (task,)
    checks = {}
    for name in tasks:
        frame, _ = load_prepared(prepared_dir, task=name)
        checks[name] = verify_task_partitions(frame, prepared, name, configs[name], prepared_dir)
        del frame
    if not execute:
        return {"status": "checked_not_fitted", "dataset_sha256": prepared["dataset_sha256"], "counts": prepared["counts"], "split_rows": checks}
    if output_dir == prepared_dir or prepared_dir in output_dir.parents:
        raise ValueError("Experiment output must be separate from frozen prepared data.")
    state_path = output_dir / "run_manifest.json"
    if output_dir.exists():
        if not resume or not state_path.is_file():
            raise ValueError("Output exists; --resume requires an existing immutable run manifest.")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state["plan"] != plan:
            raise ValueError("Resume data/configuration/code differs from the original run.")
    else:
        output_dir.mkdir(parents=True, exist_ok=False)
        state = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(), "status": "running", "plan": plan, "tasks": {}}
        write_json(state_path, state)
    for name in tasks:
        directory = output_dir / name
        if name in state["tasks"]:
            _verify_completed(directory, state["tasks"][name])
            print(f"Skipped verified completed {name} experiment; no re-evaluation.", flush=True)
            continue
        if directory.exists():
            raise ValueError("Untracked task output already exists; no evidence will be overwritten.")
        state["tasks"][name] = {"status": "started", "started_at": datetime.now(timezone.utc).isoformat()}
        write_json(state_path, state)
        frame, _ = load_prepared(prepared_dir, task=name)
        metadata = {**prepared["source_metadata"], "dataset_id": prepared["dataset_id"], "source_sha256": prepared["dataset_sha256"],
                    "source_file": "verified derived Parquet shard collection", "prepared_manifest_sha256": plan["preparation_manifest_sha256"],
                    "frozen_protocol_sha256": plan["protocol_sha256"], "cohort_preparation_counts": prepared["counts"],
                    "historical_exclusion_manifest_sha256": prepared["evidence_sha256"]["historical_exposed_ids.csv"],
                    "baseline_provenance": False, "is_fixture": False, "snapshot_type": "latest registry state; retrospective"}
        print(f"Fitting {name} once on {len(frame):,} real eligible records; fixed split rows {checks[name]}.", flush=True)
        try:
            trainer = train_experiment if name == "duration" else train_phase_experiment
            with threadpool_limits(limits=1):
                result = trainer(frame, directory, metadata, config=configs[name])
            expected = pd.read_csv(prepared_dir / f"{name}_partitions.csv")
            for role in prepared[name]["splits"]:
                if result["splits"][role]["nct_ids"] != expected.loc[expected.split.eq(role), "nct_id"].tolist():
                    raise ValueError("Fitted experiment split differs from frozen partition IDs.")
            metrics_name = "metrics.json" if name == "duration" else "phase_metrics.json"
            prediction_name = "held_out_predictions.csv" if name == "duration" else "phase_held_out_predictions.csv"
            result["evaluation_hashes"] = {filename: sha256_file(directory / filename) for filename in (metrics_name, prediction_name)}
            write_json(directory / ("manifest.json" if name == "duration" else "phase_manifest.json"), result)
            _flatten_metrics(json.loads((directory / metrics_name).read_text(encoding="utf-8"))).to_csv(directory / "metrics_summary.csv", index=False)
            hashes = {path.name: sha256_file(path) for path in sorted(directory.iterdir()) if path.is_file()}
            state["tasks"][name] = {"status": "completed", "run_id": result["run_id"], "completed_at": datetime.now(timezone.utc).isoformat(), "files_sha256": hashes}
            write_json(state_path, state)
        except Exception as error:
            state["status"] = "failed"
            state["tasks"][name].update({"status": "failed", "error_type": type(error).__name__, "error": str(error)})
            write_json(state_path, state)
            raise
        finally:
            del frame
    state["status"] = "completed" if all(state["tasks"].get(name, {}).get("status") == "completed" for name in ("duration", "phase")) else "partially_completed"
    write_json(state_path, state)
    return {"status": state["status"], "dataset_sha256": prepared["dataset_sha256"], "tasks": state["tasks"], "manifest": str(state_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, default=ROOT / "data/registry-v5205-training")
    parser.add_argument("--output", type=Path, default=ROOT / "examples/registry-v5205")
    parser.add_argument("--task", choices=("all", "duration", "phase"), default="all")
    parser.add_argument("--execute", action="store_true", help="Explicitly fit/evaluate the frozen real-data experiment")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args.prepared, args.output, task=args.task, execute=args.execute, resume=args.resume)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Reference experiment refused: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
