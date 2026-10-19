"""Export a hash-bound CSV report from completed immutable reference experiments.

This is postprocessing only: it never predicts, fits, selects, recalibrates,
changes experiment evidence, or changes an approved model catalog.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pandas as pd
from prepare_registry_training import sha256_file, write_json


def metric_records(task, metrics):
    records = []
    def collect(model, split, node, prefix=""):
        if isinstance(node, dict):
            for key, value in node.items():
                collect(model, split, value, prefix + ("." if prefix else "") + str(key))
        elif node is None or isinstance(node, (int, float)) and not isinstance(node, bool):
            records.append({"task": task, "model": model, "split": split, "metric": prefix, "value": node, "defined": node is not None})
    for model, splits in metrics.items():
        for split, values in splits.items():
            collect(model, split, values)
    return records


def export(experiment, output):
    experiment, output = Path(experiment).resolve(), Path(output).resolve()
    if output == experiment or experiment in output.parents:
        raise ValueError("Derived report must be outside immutable experiment evidence.")
    run_path = experiment / "run_manifest.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    if run.get("status") != "completed":
        raise ValueError("Both frozen tasks must complete before this evaluation export.")
    records, inputs = [], {"run_manifest_sha256": sha256_file(run_path)}
    for task in ("duration", "phase"):
        saved = run["tasks"][task]
        if saved["status"] != "completed":
            raise ValueError("An incomplete task cannot be exported as final evidence.")
        for name, expected in saved["files_sha256"].items():
            if Path(name).name != name or (experiment / task / name).is_symlink() or sha256_file(experiment / task / name) != expected:
                raise ValueError("Frozen experiment evidence failed integrity verification.")
        filename = "metrics.json" if task == "duration" else "phase_metrics.json"
        path = experiment / task / filename
        inputs[task + "_metrics_sha256"] = sha256_file(path)
        records.extend(metric_records(task, json.loads(path.read_text(encoding="utf-8"))))
    if output.exists():
        raise ValueError("Derived report output exists; choose a new output directory.")
    output.mkdir(parents=True, exist_ok=False)
    frame = pd.DataFrame(records, columns=["task", "model", "split", "metric", "value", "defined"])
    frame.to_csv(output / "metrics.csv", index=False)
    write_json(output / "metrics.json", {"records": records})
    report = {"schema_version": 1, "operation": "Deterministic scalar flattening of existing frozen metrics JSON; no fitting or evaluation rerun.",
              "dataset_sha256": run["plan"]["dataset_sha256"], "input_sha256": inputs, "exporter_sha256": sha256_file(__file__),
              "rows": len(records), "output_sha256": {name: sha256_file(output / name) for name in ("metrics.csv", "metrics.json")},
              "undefined_policy": "Null/blank values with defined=false remain unavailable. Lists, text and Boolean metadata are not scalar scores."}
    write_json(output / "report_manifest.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = export(args.experiment, args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Metrics export refused: {error}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
