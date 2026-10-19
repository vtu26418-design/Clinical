"""Conditional availability-purged risk stress audit after development selection.

This outcome-dependent subgroup is not future/pretrial validation. No threshold
or model changes are permitted after audit scores are observed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd
import pyarrow.dataset as arrow_dataset
from threadpoolctl import threadpool_limits
from scripts.phase_accuracy_probe import OUTPUT_ROOT, RAW_FIELDS, sha256_file, write_json
from scripts.risk_accuracy_probe import metric_record, predict_bundle
from src.clinical_trial_intelligence.research import _features, _positive_probability


def metrics(labels, probability):
    record = metric_record(labels, probability)
    tn, fp = record["confusion_matrix"][0]
    fn, tp = record["confusion_matrix"][1]
    record["precision"] = tp / (tp + fp) if tp + fp else None
    return record


def run(development, holdout, prepared, output):
    development, holdout, prepared, output = map(Path, (development, holdout, prepared, output))
    if not output.resolve().is_relative_to(OUTPUT_ROOT.resolve()):
        raise ValueError("Risk audit output must remain under refinement-dev.")
    report = json.loads((development / "development_report.json").read_text())
    if report["status"] != "completed_development_only" or not report["save_reload_verified"]:
        raise ValueError("Risk development selection must complete before audit.")
    selected = report["selected_development_candidate"]
    ranked = sorted(report["results"], key=lambda name: (report["results"][name]["metrics"]["brier"],
                                                        -report["results"][name]["metrics"]["auroc"], name))
    if selected != ranked[0]:
        raise ValueError("Risk winner differs from frozen development rule.")
    output.mkdir(parents=True, exist_ok=False)
    state = {"status": "selected_before_stress_audit", "selected_candidate": selected,
             "development_report_sha256": sha256_file(development / "development_report.json"),
             "audit_script_sha256": sha256_file(__file__), "selected_at": datetime.now(timezone.utc).isoformat()}
    write_json(output / "stress_report.json", state)
    if selected == "original_multimodal":
        state.update({"status": "not_run_no_development_improvement", "reason": "Frozen original comparator won development selection; no stress-label access or production replacement."})
        write_json(output / "stress_report.json", state)
        return state
    protocol = json.loads((holdout / "protocol.json").read_text())
    if not protocol["frozen_before_refinement_audit_scores"] or sha256_file(holdout / "ids.csv") != protocol["ids_sha256"]:
        raise ValueError("Risk stress freeze integrity mismatch.")
    if sha256_file(prepared / "duration_temporal_exclusions.csv") != protocol["source_sha256"]:
        raise ValueError("Risk stress source identity changed.")
    identifiers = pd.read_csv(holdout / "ids.csv").nct_id.tolist()
    expected = pd.read_csv(prepared / "duration_temporal_exclusions.csv").nct_id.tolist()
    old = pd.read_csv(prepared / "duration_partitions.csv").nct_id
    if len(identifiers) != protocol["rows"] or len(set(identifiers)) != len(identifiers) or set(identifiers) != set(expected) or set(identifiers).intersection(old):
        raise ValueError("Risk stress IDs differ from freeze or overlap an original retained role.")
    state.update({"protocol": protocol, "protocol_sha256": sha256_file(holdout / "protocol.json"),
                  "cohort_frozen_before_scores": True, "threshold_days": report["threshold_days"]})
    write_json(output / "stress_report.json", state)
    path = development / "development_candidates.joblib"
    if sha256_file(path) != report["artifact_sha256"]:
        raise ValueError("Risk development artifact checksum mismatch.")
    bundle = joblib.load(path)
    manifest = json.loads((prepared / "preparation_manifest.json").read_text())
    paths = []
    for shard in manifest["shards"]:
        path = prepared / shard["file"]
        if sha256_file(path) != shard["sha256"]:
            raise ValueError("Risk stress raw source changed.")
        paths.append(str(path))
    source = arrow_dataset.dataset(paths, format="parquet")
    columns = [field for field in dict.fromkeys(["nct_id", "phase", "start_date", "completion_date", *RAW_FIELDS]) if field in source.schema.names]
    frame = source.to_table(filter=arrow_dataset.field("nct_id").isin(identifiers), columns=columns,
                             use_threads=False).to_pandas().set_index("nct_id").loc[identifiers].reset_index()
    duration = (pd.to_datetime(frame.completion_date) - pd.to_datetime(frame.start_date)).dt.total_seconds() / 86400
    labels = duration.gt(report["threshold_days"]).to_numpy(int)
    original_path = ROOT / "examples/registry-v5205/duration/models.joblib"
    original = joblib.load(original_path)
    with threadpool_limits(limits=1):
        candidate = predict_bundle(frame, bundle, selected)
        baseline = _positive_probability(original["models"]["multimodal"]["classifier"], _features(frame, include_design=True))
    first, second = metrics(labels, candidate), metrics(labels, baseline)
    keys = ("accuracy", "balanced_accuracy", "sensitivity", "specificity", "auroc", "average_precision", "brier", "log_loss")
    differences = {key: [] for key in keys}
    rng = np.random.default_rng(42)
    for _ in range(200):
        indices = rng.integers(0, len(labels), len(labels))
        one, two = metrics(labels[indices], candidate[indices]), metrics(labels[indices], baseline[indices])
        for key in keys:
            if one[key] is not None and two[key] is not None:
                differences[key].append(one[key] - two[key])
    comparison = {key: {"difference": first[key] - second[key] if first[key] is not None and second[key] is not None else None,
                        "lower": float(np.quantile(values, .025)) if values else None,
                        "upper": float(np.quantile(values, .975)) if values else None,
                        "valid_resamples": len(values)} for key, values in differences.items()}
    state.update({"status": "completed_conditional_stress_audit", "candidate": first, "original_multimodal": second,
                  "always_negative": metrics(labels, np.zeros(len(labels))),
                  "paired_comparison": {"method": "Paired conditional fitted-model trial bootstrap percentile", "level": .95,
                      "requested_resamples": 200, "seed": 42, "differences": comparison,
                      "direction": "Positive favors refinement except Brier/logloss, where negative favors refinement."},
                  "production_promotion": "None. Outcome-dependent stress evidence does not establish future/pretrial transport.",
                  "completed_at": datetime.now(timezone.utc).isoformat()})
    pd.DataFrame({"nct_id": identifiers, "actual_prolonged": labels, "refined_probability": candidate,
                  "original_multimodal_probability": baseline, "threshold_days": report["threshold_days"]}).to_csv(output / "stress_predictions.csv", index=False)
    write_json(output / "stress_report.json", state)
    return {key: state[key] for key in ("status", "selected_candidate", "candidate", "original_multimodal", "paired_comparison", "production_promotion")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development", type=Path, default=OUTPUT_ROOT / "risk-v1")
    parser.add_argument("--holdout", type=Path, default=Path("/workspace/v5205-work/risk-refinement-holdout"))
    parser.add_argument("--prepared", type=Path, default=ROOT / "data/registry-v5205-training")
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT / "risk-audit-v1")
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        print(json.dumps(run(args.development, args.holdout, args.prepared, args.output), indent=2))


if __name__ == "__main__":
    main()
