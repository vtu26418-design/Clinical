"""Two fixed prolonged-duration risk candidates on development partitions only.

The original calibration/test rows are never materialized. Labels retain the
original frozen training-derived threshold; this probe never chooses thresholds
or claims that majority-class accuracy establishes useful risk prediction.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd
import pyarrow.dataset as arrow_dataset
import scipy.sparse as sparse
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
                             brier_score_loss, confusion_matrix, log_loss, roc_auc_score)
from threadpoolctl import threadpool_limits

from scripts.phase_accuracy_probe import (
    OUTPUT_ROOT, RAW_FIELDS, CATEGORICAL, NUMERIC, build_features, make_preprocessor, sha256_file, write_json,
)
from src.clinical_trial_intelligence.research import normalize_design_phase

CANDIDATES = {"word_char_risk_logistic": None, "word_char_balanced_risk_logistic": "balanced"}


def build_risk_features(frame):
    features = build_features(frame)
    features["phase"] = frame.get("phase", pd.Series("Unknown", index=frame.index)).fillna("Unknown").map(normalize_design_phase)
    return features


def risk_preprocessor():
    preprocessor = make_preprocessor()
    preprocessor.transformers = [(name, transform, [*CATEGORICAL, "phase"] if name == "categorical" else columns)
                                for name, transform, columns in preprocessor.transformers]
    return preprocessor


def metric_record(labels, probability):
    labels, probability = np.asarray(labels, dtype=int), np.asarray(probability, dtype=float)
    predicted = probability >= .5
    matrix = confusion_matrix(labels, predicted, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()
    both = len(np.unique(labels)) == 2
    return {"n": len(labels), "positive_count": int(labels.sum()), "negative_count": int((labels == 0).sum()),
            "threshold": .5, "accuracy": float(accuracy_score(labels, predicted)),
            "balanced_accuracy": float(balanced_accuracy_score(labels, predicted)),
            "sensitivity": float(tp / (tp + fn)) if tp + fn else None,
            "specificity": float(tn / (tn + fp)) if tn + fp else None,
            "auroc": float(roc_auc_score(labels, probability)) if both else None,
            "average_precision": float(average_precision_score(labels, probability)) if both else None,
            "brier": float(brier_score_loss(labels, probability)),
            "log_loss": float(log_loss(labels, np.column_stack([1 - probability, probability]), labels=[0, 1])),
            "confusion_matrix": matrix.tolist(), "confusion_order": "rows actual0/1,columns predicted0/1",
            "probability_semantics": "raw; uncalibrated"}


def development_frames(prepared):
    prepared = Path(prepared)
    manifest = json.loads((prepared / "preparation_manifest.json").read_text())
    partition_path = prepared / "duration_partitions.csv"
    if sha256_file(partition_path) != manifest["evidence_sha256"]["duration_partitions.csv"]:
        raise ValueError("Duration partition integrity mismatch.")
    roles = pd.read_csv(partition_path, usecols=["nct_id", "split"])
    development = roles.loc[roles.split.isin(["train", "validation"])].copy()
    forbidden = set(roles.loc[~roles.split.isin(["train", "validation"]), "nct_id"])
    if roles.nct_id.duplicated().any() or forbidden.intersection(development.nct_id):
        raise ValueError("Duration role identity is invalid.")
    paths = []
    for shard in manifest["shards"]:
        if not re.fullmatch(r"shards/part-\d{6}\.parquet", shard["file"]):
            raise ValueError("Unsafe shard name.")
        path = prepared / shard["file"]
        if path.is_symlink() or sha256_file(path) != shard["sha256"]:
            raise ValueError("Duration source shard integrity mismatch.")
        paths.append(str(path))
    dataset = arrow_dataset.dataset(paths, format="parquet")
    columns = [field for field in dict.fromkeys(["nct_id", "phase", "start_date", "completion_date", *RAW_FIELDS])
               if field in dataset.schema.names]
    frame = dataset.to_table(filter=arrow_dataset.field("nct_id").isin(development.nct_id.tolist()),
                             columns=columns, use_threads=False).to_pandas()
    if frame.nct_id.duplicated().any() or set(frame.nct_id) != set(development.nct_id):
        raise ValueError("Duration development rows differ from frozen roles.")
    frame["observed_duration_days"] = (pd.to_datetime(frame.completion_date) - pd.to_datetime(frame.start_date)).dt.total_seconds() / 86400
    frame = frame.set_index("nct_id")
    frames = {role: frame.loc[development.loc[development.split.eq(role), "nct_id"]].reset_index()
              for role in ("train", "validation")}
    threshold = manifest["duration"]["threshold_days"]
    if frames["train"].observed_duration_days.quantile(.75) != threshold:
        raise ValueError("Frozen risk endpoint threshold changed.")
    labels = {role: frame.observed_duration_days.gt(threshold).to_numpy(int) for role, frame in frames.items()}
    for role in frames:
        if int(labels[role].sum()) != manifest["duration"]["splits"][role]["risk_support"]["positive"]:
            raise ValueError("Frozen risk support changed.")
    return frames, labels, manifest, {"duration_partitions_sha256": sha256_file(partition_path),
                                      "calibration_and_test_ids_forbidden": len(forbidden), "calibration_and_test_rows_materialized": 0}


def predict_bundle(frame, bundle, candidate):
    return bundle["models"][candidate].predict_proba(bundle["preprocessor"].transform(build_risk_features(frame)))[:, 1]


def run(prepared, output, *, execute=False):
    output = Path(output).resolve()
    if not output.is_relative_to(OUTPUT_ROOT.resolve()) or output == OUTPUT_ROOT.resolve():
        raise ValueError("Risk probe output must be a new child of refinement-dev.")
    plan = {"protocol_id": "risk-refinement-development-v1", "seed": 42, "threads": 1,
            "candidates": {name: {"C": 1., "max_iter": 1000, "class_weight": weight} for name, weight in CANDIDATES.items()},
            "numeric": NUMERIC, "categorical": [*CATEGORICAL, "phase"],
            "preprocessing": "Phase probe word+char TFIDF; training log1p numeric/median/missing indicators/scaling; train one-hot categories. Current enrollment is retrospective.",
            "selection": "Minimum raw tuning Brier, then maximum AUROC, then candidate name; includes frozen original multimodal comparator; threshold fixed0.5. No calibration/test use.",
            "script_sha256": sha256_file(__file__), "feature_helper_sha256": sha256_file(ROOT / "scripts/phase_accuracy_probe.py"),
            "limitations": ["Original final test is already exposed. Development evidence only; no independent final risk cohort is currently available.",
                            "High negative prevalence makes90%accuracy achievable by a trivial all-negative decision; report sensitivity,AUROC,AP,Brier/logloss.",
                            "Current snapshots/enrollment may be post-start; completed-only outcomes and outcome purging cause temporal prevalence shift.",
                            "No automatic promotion or probability recalibration. Preserve verified production absent independent evidence."]}
    if not execute:
        return {"status": "planned_not_fitted", "plan": plan}
    output.mkdir(parents=True, exist_ok=False)
    state = {"status": "started", "plan": plan, "created_at": datetime.now(timezone.utc).isoformat()}
    write_json(output / "development_report.json", state)
    frames, labels, manifest, identity = development_frames(prepared)
    state.update({"dataset_sha256": manifest["dataset_sha256"], "development_identity": identity,
                  "threshold_days": manifest["duration"]["threshold_days"], "results": {},
                  "support": {role: {"rows": len(values), "positive": int(values.sum()), "negative": int((values == 0).sum())} for role, values in labels.items()}})
    if len(np.unique(labels["train"])) < 2 or len(np.unique(labels["validation"])) < 2:
        state.update({"status": "infeasible_development_support", "reason": "Both risk classes are required in training and tuning."})
        write_json(output / "development_report.json", state)
        return state
    prior = float(labels["train"].mean())
    state["baselines"] = {"always_negative": metric_record(labels["validation"], np.zeros(len(labels["validation"]))),
                          "training_prevalence": metric_record(labels["validation"], np.full(len(labels["validation"]), prior))}
    old = json.loads((ROOT / "examples/registry-v5205/duration/manifest.json").read_text())
    state["previous_tuning_champion"] = {"model": old["recommended_model"], "classification": old["models"][old["recommended_model"]]["metrics"]["validation"]["classification"]}
    predictions_path = ROOT / "examples/registry-v5205/duration/held_out_predictions.csv"
    if sha256_file(predictions_path) != old["evaluation_hashes"]["held_out_predictions.csv"]:
        raise ValueError("Original comparator prediction integrity mismatch.")
    historical = arrow_dataset.dataset(str(predictions_path), format="csv")
    comparator = historical.to_table(filter=(arrow_dataset.field("split") == "validation") & (arrow_dataset.field("model_name") == "multimodal"),
                                    columns=["nct_id", "actual_prolonged", "prolonged_probability"], use_threads=False).to_pandas()
    if comparator.nct_id.duplicated().any() or set(comparator.nct_id) != set(frames["validation"].nct_id):
        raise ValueError("Original comparator tuning identities differ.")
    comparator = comparator.set_index("nct_id").loc[frames["validation"].nct_id]
    np.testing.assert_array_equal(comparator.actual_prolonged.to_numpy(), labels["validation"])
    state["results"]["original_multimodal"] = {"metrics": metric_record(labels["validation"], comparator.prolonged_probability.to_numpy()),
                                               "fit_seconds": 0., "fitted_in_this_probe": False}
    features = {role: build_risk_features(frame) for role, frame in frames.items()}
    bundle = {"preprocessor": risk_preprocessor(), "models": {}}
    print(f"Risk fit {len(labels['train']):,}train; {len(labels['validation']):,}tuning with {labels['validation'].sum()}positives; zero calibration/test rows.", flush=True)
    with threadpool_limits(limits=1):
        matrices = {"train": sparse.csr_matrix(bundle["preprocessor"].fit_transform(features["train"]))}
        matrices["validation"] = sparse.csr_matrix(bundle["preprocessor"].transform(features["validation"]))
        state["transformed_shape"] = list(matrices["train"].shape)
        for name, weight in CANDIDATES.items():
            started = time.monotonic()
            model = LogisticRegression(C=1., class_weight=weight, max_iter=1000, solver="lbfgs", random_state=42)
            model.fit(matrices["train"], labels["train"])
            probability = model.predict_proba(matrices["validation"])[:, 1]
            state["results"][name] = {"metrics": metric_record(labels["validation"], probability),
                                      "fit_seconds": time.monotonic() - started, "converged": bool(np.max(model.n_iter_) < 1000)}
            pd.DataFrame({"nct_id": frames["validation"].nct_id, "split": "validation", "actual_prolonged": labels["validation"],
                          "prolonged_probability": probability}).to_csv(output / (name + "_validation_predictions.csv"), index=False)
            bundle["models"][name] = model
            write_json(output / "development_report.json", state)
            print(json.dumps({"candidate": name, **state["results"][name]}), flush=True)
    selected = min(state["results"], key=lambda name: (state["results"][name]["metrics"]["brier"], -state["results"][name]["metrics"]["auroc"], name))
    path = output / "development_candidates.joblib"
    joblib.dump(bundle, path, compress=3)
    reloaded = joblib.load(path)
    for name in CANDIDATES:
        sample = frames["validation"].iloc[[0, -1]]
        np.testing.assert_allclose(predict_bundle(sample, bundle, name), predict_bundle(sample, reloaded, name), rtol=0, atol=0)
    state.update({"status": "completed_development_only", "selected_development_candidate": selected,
                  "artifact_sha256": sha256_file(path), "save_reload_verified": True,
                  "completed_at": datetime.now(timezone.utc).isoformat()})
    write_json(output / "development_report.json", state)
    return {"status": state["status"], "selected_development_candidate": selected, "results": state["results"], "report": str(output / "development_report.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, default=ROOT / "data/registry-v5205-training")
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT / "risk-v1")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.prepared, args.output, execute=args.execute), indent=2))


if __name__ == "__main__":
    main()
