"""Audit a development-selected portable phase candidate on frozen fresh IDs.

The audit is an ID-disjoint partial-date registry subgroup, not a chronological
or prospective test. Selection must already be complete before source rows load.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd
import pyarrow.dataset as arrow_dataset
from threadpoolctl import threadpool_limits

from scripts.phase_accuracy_probe import (OUTPUT_ROOT, RAW_FIELDS, NUMERIC, CATEGORICAL,
                                          _development_frames, sha256_file, write_json)
from src.clinical_trial_intelligence.phase_model import (
    PHASE_LABELS, TEXT_FIELDS, _phase_features, evaluate_phase_predictions, normalize_phase, predict_phase,
)
from src.clinical_trial_intelligence.models.phase_refinement import PhaseRefinementClassifier


def canonical_phase_features(frame):
    # Preserve explicit empty narrative slots used when fitting the probe. The
    # manifest records this requirement for inference adapters outside the frozen
    # phase_model.py; whitespace before the character cap must be reproducible.
    return _phase_features(frame.reindex(columns=RAW_FIELDS), include_design=True)


def aligned(model, features):
    if isinstance(model, PhaseRefinementClassifier):
        probability = model.estimator.predict_proba(model._matrix(features))
    else:
        probability = model.predict_proba(features)
    matrix = np.zeros((len(features), len(PHASE_LABELS)))
    for index, label in enumerate(model.classes_):
        matrix[:, PHASE_LABELS.index(str(label))] = probability[:, index]
    predicted = np.array(PHASE_LABELS)[matrix.argmax(axis=1)]
    return predicted, matrix


def paired_comparison(actual, candidate, baseline):
    classes = list(PHASE_LABELS)
    first = evaluate_phase_predictions(actual, candidate, classes)
    second = evaluate_phase_predictions(actual, baseline, classes)
    keys = ("accuracy", "balanced_accuracy", "macro_f1")
    values = {key: [] for key in keys}
    rng = np.random.default_rng(42)
    for _ in range(200):
        indices = rng.integers(0, len(actual), len(actual))
        one = evaluate_phase_predictions(actual[indices], candidate[indices], classes)
        two = evaluate_phase_predictions(actual[indices], baseline[indices], classes)
        for key in keys:
            values[key].append(one[key] - two[key])
    return {"method": "Paired conditional fitted-model trial bootstrap percentile", "level": .95,
            "requested_resamples": 200, "seed": 42, "positive_favors": "refinement",
            "interpretation": "Conditional subgroup evidence; excludes fitting/clustering uncertainty and selection optimism. Not chronological/prospective validation.",
            **{key: {"difference": first[key] - second[key], "lower": float(np.quantile(values[key], .025)),
                     "upper": float(np.quantile(values[key], .975))} for key in keys}}


def _prediction_frame(raw, role, name, predicted, probability):
    result = pd.DataFrame({"nct_id": raw.nct_id, "split": role, "model_name": name,
                           "reported_phase": raw.phase, "actual_phase": raw.phase.map(normalize_phase),
                           "predicted_phase": predicted, "correct": raw.phase.map(normalize_phase).to_numpy() == predicted})
    for index, label in enumerate(PHASE_LABELS):
        result["probability_" + label] = probability[:, index]
    return result


def run(development_dir, holdout_dir, output, *, prepared, export_dir):
    development_dir, holdout_dir, output, prepared = map(Path, (development_dir, holdout_dir, output, prepared))
    if not output.resolve().is_relative_to(OUTPUT_ROOT.resolve()):
        raise ValueError("Audit outputs must remain under refinement-dev.")
    dev = json.loads((development_dir / "development_report.json").read_text())
    if dev["status"] != "completed_development_only" or not dev["save_reload_verified"]:
        raise ValueError("Development selection/replay must complete before audit.")
    winner = dev["selected_development_candidate"]
    ranking = sorted(dev["results"], key=lambda name: (-dev["results"][name]["metrics"]["macro_f1"],
                                                     -dev["results"][name]["metrics"]["balanced_accuracy"], name))
    if winner != ranking[0]:
        raise ValueError("Development winner differs from its frozen selection rule.")
    primary_tie = len(ranking) > 1 and all(dev["results"][ranking[0]]["metrics"][key] == dev["results"][ranking[1]]["metrics"][key]
                                         for key in ("macro_f1", "balanced_accuracy"))
    if primary_tie:
        raise ValueError("Conflicting development/audit tie rules require review before fresh scores.")
    artifact_path = development_dir / "development_candidates.joblib"
    if sha256_file(artifact_path) != dev["artifact_sha256"]:
        raise ValueError("Development artifact integrity mismatch.")
    protocol = json.loads((holdout_dir / "protocol.json").read_text())
    if not protocol["frozen_before_refinement_holdout_scores"] or sha256_file(holdout_dir / "ids.csv") != protocol["ids_sha256"]:
        raise ValueError("Fresh audit freeze is invalid.")
    if sha256_file(prepared / "preparation_manifest.json") != protocol["source_manifest_sha256"]:
        raise ValueError("Fresh audit source changed after freeze.")
    output.mkdir(parents=True, exist_ok=False)
    state = {"status": "selected_before_audit", "selected_candidate": winner,
             "selection_has_no_primary_tie": True, "development_report_sha256": sha256_file(development_dir / "development_report.json"),
             "holdout_protocol": protocol, "holdout_protocol_sha256": sha256_file(holdout_dir / "protocol.json"),
             "audit_script_sha256": sha256_file(__file__), "adapter_sha256": sha256_file(ROOT / "src/clinical_trial_intelligence/models/phase_refinement.py"),
             "predeclared_gate": "Positive paired accuracy point difference and nonnegative macro-F1 point difference vs original phase_logistic; no audit model selection.",
             "selected_at": datetime.now(timezone.utc).isoformat()}
    write_json(output / "audit_report.json", state)
    probe = joblib.load(artifact_path)
    portable = PhaseRefinementClassifier(preprocessor=probe["preprocessor"], estimator=probe["models"][winner],
        svd=probe["svd"] if winner == "svd128_design_catboost" else None,
        text_columns=probe["text_columns"] if winner == "svd128_design_catboost" else None)
    portable_path = output / "portable_refinement.joblib"
    joblib.dump(portable, portable_path, compress=3)
    portable = joblib.load(portable_path)
    # Replay every tuning record before loading any fresh audit source values.
    frames, prepared_manifest, _ = _development_frames(prepared)
    validation = frames["validation"]
    features = canonical_phase_features(validation)
    predicted, probability = aligned(portable, features)
    expected = pd.read_csv(development_dir / (winner + "_validation_predictions.csv")).set_index("nct_id").loc[validation.nct_id]
    np.testing.assert_array_equal(predicted, expected.predicted_phase.to_numpy())
    expected_probability = expected[["probability_" + label for label in PHASE_LABELS]].to_numpy()
    np.testing.assert_allclose(probability, expected_probability, rtol=0, atol=1e-14)
    state["portable_development_replay"] = {"rows": len(validation), "predictions_equal": True,
                                           "maximum_probability_difference": float(np.abs(probability - expected_probability).max()),
                                           "portable_sha256": sha256_file(portable_path), "class_module": type(portable).__module__}
    write_json(output / "audit_report.json", state)
    print(f"Portable replay verified for all {len(validation):,} tuning records; selected {winner} before audit.", flush=True)
    identifiers = pd.read_csv(holdout_dir / "ids.csv").nct_id.tolist()
    old_roles = pd.read_csv(prepared / "phase_partitions.csv", usecols=["nct_id"])
    if len(identifiers) != protocol["rows"] or len(set(identifiers)) != len(identifiers) or set(identifiers).intersection(old_roles.nct_id):
        raise ValueError("Fresh audit identities overlap an exposed phase role or differ from freeze.")
    paths = []
    for shard in prepared_manifest["shards"]:
        path = prepared / shard["file"]
        if sha256_file(path) != shard["sha256"]:
            raise ValueError("Fresh source shard changed.")
        paths.append(str(path))
    dataset = arrow_dataset.dataset(paths, format="parquet")
    columns = [field for field in ["nct_id", "phase", *RAW_FIELDS] if field in dataset.schema.names]
    fresh = dataset.to_table(filter=arrow_dataset.field("nct_id").isin(identifiers), columns=columns,
                             use_threads=False).to_pandas().set_index("nct_id").loc[identifiers].reset_index()
    labels = fresh.phase.map(normalize_phase).to_numpy()
    if any(label is None for label in labels):
        raise ValueError("Fresh audit labels violate the frozen pure-phase eligibility.")
    fresh_features = canonical_phase_features(fresh)
    original_dir = ROOT / "examples/registry-v5205/phase"
    original_manifest = json.loads((original_dir / "phase_manifest.json").read_text())
    if sha256_file(original_dir / "phase_models.joblib") != original_manifest["artifact_sha256"]:
        raise ValueError("Original comparator artifact integrity mismatch.")
    original = joblib.load(original_dir / "phase_models.joblib")
    refined_name = "phase_refinement_v1"
    models = {"majority_baseline": original["models"]["majority_baseline"],
              "phase_logistic": original["models"]["phase_logistic"], refined_name: portable}
    metrics, prediction_frames, held_predictions = {}, [], {}
    with threadpool_limits(limits=1):
        for name, model in models.items():
            metrics[name] = {}
            for role, raw, input_features in (("validation", validation, features), ("test", fresh, fresh_features)):
                predicted, probability = aligned(model, input_features)
                target = raw.phase.map(normalize_phase).to_numpy()
                metrics[name][role] = evaluate_phase_predictions(target, predicted, original["training_classes"], bootstrap_samples=200, random_seed=42)
                metrics[name][role]["evaluation_role"] = "original development tuning" if role == "validation" else "ID-disjoint partial-start-date subgroup audit; not chronological"
                prediction_frames.append(_prediction_frame(raw, role, name, predicted, probability))
                if role == "test":
                    held_predictions[name] = predicted
            print(json.dumps({"model": name, "fresh_audit": {key: metrics[name]["test"][key] for key in ("accuracy", "balanced_accuracy", "macro_f1")}}), flush=True)
    comparison = paired_comparison(labels, held_predictions[refined_name], held_predictions["phase_logistic"])
    gate = comparison["accuracy"]["difference"] > 0 and comparison["macro_f1"]["difference"] >= 0
    state.update({"status": "audit_completed", "metrics": metrics, "paired_comparison": comparison,
                  "predeclared_gate_passed": bool(gate), "fresh_rows": len(fresh),
                  "completed_at": datetime.now(timezone.utc).isoformat()})
    pd.concat(prediction_frames, ignore_index=True).to_csv(output / "audit_predictions.csv", index=False)
    write_json(output / "audit_report.json", state)
    write_json(output / "confirmatory_evaluation.json", state)
    if gate:
        export_dir = Path(export_dir).resolve()
        if export_dir != (ROOT / "examples/registry-phase-refinement-v5205").resolve():
            raise ValueError("Refinement export must use its dedicated new example folder.")
        export_dir.mkdir(parents=True, exist_ok=False)
        model_records = {name: deepcopy(original_manifest["models"][name]) for name in ("majority_baseline", "phase_logistic")}
        model_records[refined_name] = {"input_mode": "multimodal", "input_features": {"numeric": NUMERIC, "categorical": CATEGORICAL, "text": list(TEXT_FIELDS)},
            "selection": {"rule": dev["plan"]["selection"], "selected_development_candidate": winner,
                          "candidates": {name: record["metrics"] for name, record in dev["results"].items()},
                          "selection_split": "validation", "test_used_for_selection": False, "refit_on_validation": False}}
        for name in model_records:
            model_records[name]["metrics"] = metrics[name]
        splits = deepcopy(original_manifest["splits"])
        splits["test"] = {"rows": len(fresh), "role": "ID-disjoint partial-start-date subgroup audit",
                          "start_date_min": None, "start_date_max": None, "nct_ids": identifiers,
                          "class_support": metrics[refined_name]["test"]["class_support"]}
        source_identity = {"prepared_dataset_sha256": prepared_manifest["dataset_sha256"],
                           "original_training_and_tuning_partitions_sha256": sha256_file(prepared / "phase_partitions.csv"),
                           "fresh_audit_ids_sha256": protocol["ids_sha256"], "development_plan_sha256": hashlib.sha256(json.dumps(dev["plan"], sort_keys=True).encode()).hexdigest()}
        input_digest = hashlib.sha256(json.dumps(source_identity, sort_keys=True).encode()).hexdigest()
        warning = "Retrospective research phase-consistency model. Current reported enrollment is not planned enrollment. Test schema slot identifies an ID-disjoint partial-start-date subgroup audit, not chronological/prospective validation. Original exact-date test was exposed and is not this branch's test. Class probabilities are uncalibrated; no clinical/regulatory phase assignment or success claim."
        shared = {key: deepcopy(original[key]) for key in ("task", "artifact_version", "labels", "training_classes", "config", "pipeline_source_sha256")}
        shared.update({"run_id": str(uuid.uuid4()), "dataset_id": "registry-phase-refinement-" + input_digest[:16],
            "source_metadata": {**original["source_metadata"], "baseline_provenance": False, "is_fixture": False,
                                "dataset_id": "registry-phase-refinement-" + input_digest[:16],
                                "refinement_parent_run_id": original["run_id"], "input_identity": source_identity,
                                "independent_evaluation": protocol["purpose"], "canonical_empty_text_fields": list(TEXT_FIELDS)},
            "input_sha256": input_digest, "splits": splits, "warning": warning})
        artifact = {**shared, "models": models, "recommended_model": refined_name}
        joblib.dump(artifact, export_dir / "phase_models.joblib", compress=3)
        exported = {**shared, "status": "completed", "created_at": datetime.now(timezone.utc).isoformat(),
            "environment": original_manifest["environment"], "models": model_records, "recommended_model": refined_name,
            "cohort": {"input_rows": prepared_manifest["counts"]["unexposed_source_rows"],
                       "eligible_rows": sum(record["rows"] for record in splits.values()),
                       "excluded_rows": prepared_manifest["counts"]["unexposed_source_rows"] - sum(record["rows"] for record in splits.values()),
                       "target": "normalized single registry phase; original train/tuning plus frozen new partial-date audit"},
            "temporal_cutoffs": {**original_manifest["temporal_cutoffs"], "test": None,
                "policy": "Original exact-date training/tuning roles preserved. Test slot is fixed ID-disjoint partial-date subgroup; no chronological boundary or future-validation claim."},
            "features": {"numeric": NUMERIC, "categorical": CATEGORICAL, "text": list(TEXT_FIELDS),
                         "canonical_empty_text_fields": list(TEXT_FIELDS),
                         "excluded": ["phase", "reported_phase", "nct_id", "status", "start_date", "completion_date", "duration_days", "prolonged"],
                         "redaction": "Existing explicit phase redaction plus NCT/date stripping and12000-character cap; canonical empty narrative slots required."},
            "additional_model_source_sha256": {**original_manifest.get("additional_model_source_sha256", {}),
                "models/phase_refinement.py": state["adapter_sha256"]},
            "experiment_source_sha256": {"scripts/phase_accuracy_probe.py": dev["plan"]["script_sha256"],
                                         "scripts/audit_phase_refinement.py": state["audit_script_sha256"]},
            "refinement_evidence": {"development_report_sha256": state["development_report_sha256"],
                "audit_evaluation_file": "confirmatory_evaluation.json", "audit_evaluation_sha256": sha256_file(output / "confirmatory_evaluation.json"), "audit_protocol": protocol,
                "paired_comparison": comparison, "predeclared_gate_passed": True,
                "activation": "No catalog or project activation performed; requires controller review."},
            "recommendation": {"metric": "macro_f1", "split": "validation", "value": metrics[refined_name]["validation"]["macro_f1"],
                               "rule": "Development-only selection; fresh audit was confirmatory under a predeclared gate, never model/threshold tuning."},
            "limitations": [*original_manifest["limitations"], warning, "Conditional trial bootstrap excludes sponsor/site clustering, fitting uncertainty and development selection optimism."],
            "files": {"artifact": "phase_models.joblib", "metrics": "phase_metrics.json", "predictions": "phase_held_out_predictions.csv", "cohort_exclusions": "phase_cohort_exclusions.csv"}}
        pd.concat(prediction_frames, ignore_index=True).to_csv(export_dir / "phase_held_out_predictions.csv", index=False)
        write_json(export_dir / "phase_metrics.json", metrics)
        exclusions = pd.read_csv(prepared / "phase_eligibility_exclusions.csv")
        exclusions = exclusions.loc[~exclusions.nct_id.isin(identifiers)].copy()
        old_test = pd.read_csv(prepared / "phase_partitions.csv")
        old_test = old_test.loc[old_test.split.eq("test"), ["nct_id"]].assign(reported_phase="", reason="exposed_original_exact_date_test_excluded_from_refinement_audit")
        exclusions = pd.concat([exclusions, old_test], ignore_index=True)
        if len(exclusions) != exported["cohort"]["excluded_rows"] or exclusions.nct_id.duplicated().any():
            raise ValueError("Refinement exclusion counts/identities do not reconcile.")
        exclusions.to_csv(export_dir / "phase_cohort_exclusions.csv", index=False)
        exported["artifact_sha256"] = sha256_file(export_dir / "phase_models.joblib")
        exported["evaluation_hashes"] = {name: sha256_file(export_dir / name) for name in ("phase_metrics.json", "phase_held_out_predictions.csv")}
        write_json(export_dir / "phase_manifest.json", exported)
        sample = fresh.iloc[0].to_dict()
        for field in TEXT_FIELDS:
            sample.setdefault(field, "")
        result = predict_phase(sample, export_dir)
        if result["status"] != "available" or result["model_name"] != refined_name:
            raise ValueError("Compatible refinement artifact did not load through predict_phase.")
        state["compatible_export"] = {"directory": str(export_dir), "run_id": shared["run_id"],
                                      "phase_predict_verified": True, "artifact_sha256": exported["artifact_sha256"]}
        write_json(output / "audit_report.json", state)
    return {"status": state["status"], "selected_candidate": winner, "predeclared_gate_passed": bool(gate),
            "paired_comparison": comparison, "compatible_export": state.get("compatible_export"),
            "report": str(output / "audit_report.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development", type=Path, default=OUTPUT_ROOT / "phase-v1")
    parser.add_argument("--holdout", type=Path, default=Path("/workspace/v5205-work/phase-refinement-holdout"))
    parser.add_argument("--prepared", type=Path, default=ROOT / "data/registry-v5205-training")
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT / "phase-audit-v1")
    parser.add_argument("--export", type=Path, default=ROOT / "examples/registry-phase-refinement-v5205")
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        print(json.dumps(run(args.development, args.holdout, args.output, prepared=args.prepared, export_dir=args.export), indent=2))


if __name__ == "__main__":
    main()
