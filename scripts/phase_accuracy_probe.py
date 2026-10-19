"""Bounded retrospective phase refinement on the frozen development roles only.

The original test has been exposed and is never loaded by this probe. This is
development evidence, not a replacement independent test or a production model.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = Path("/workspace/v5205-work/refinement-dev")
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd
import pyarrow.dataset as arrow_dataset
import scipy.sparse as sparse
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from src.clinical_trial_intelligence.phase_model import (
    NUMERIC_FEATURES, PHASE_LABELS, TEXT_FIELDS, _phase_features,
    evaluate_phase_predictions, normalize_phase,
)
from src.clinical_trial_intelligence.models.design import input_features
from src.clinical_trial_intelligence.models.catboost_compat import CTICatBoostClassifier

DESIGN = input_features(phase_task=True)
NUMERIC = list(dict.fromkeys([*NUMERIC_FEATURES, *DESIGN["numeric"]]))
CATEGORICAL = DESIGN["categorical"]
RAW_FIELDS = list(dict.fromkeys([*NUMERIC, *CATEGORICAL, *TEXT_FIELDS]))
CANDIDATES = {
    "word_char_logistic": {"family": "logistic", "C": 1.0, "class_weight": None, "max_iter": 1000},
    "word_char_balanced_logistic": {"family": "logistic", "C": 1.0, "class_weight": "balanced", "max_iter": 1000},
    "svd128_design_catboost": {"family": "catboost", "svd_components": 128, "iterations": 300,
                               "depth": 6, "learning_rate": 0.05, "l2_leaf_reg": 5},
}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def build_features(frame):
    """Reuse target redaction; source labels/IDs/dates never enter transforms.

    Current enrollment is intentionally retained for retrospective consistency
    classification. It must never be described as planned/baseline enrollment.
    """
    raw = frame.reindex(columns=RAW_FIELDS)
    features = _phase_features(raw, include_design=True)
    # Identifier/date mentions in narratives are removed as an extra precaution.
    features["protocol_text"] = (features.protocol_text
        .str.replace(r"(?i)\bNCT\s*\d{8}\b", " ", regex=True)
        .str.replace(r"\b(?:19|20)\d{2}(?:[-/]\d{1,2}(?:[-/]\d{1,2})?)?\b", " ", regex=True)
        .str.slice(0, 12000).str.replace(r"\s+", " ", regex=True).str.strip())
    features.loc[~features.protocol_text.str.contains(r"\w", regex=True), "protocol_text"] = "missingprotocol"
    return features


def make_preprocessor():
    return ColumnTransformer([
        ("word", TfidfVectorizer(max_features=20000, min_df=3, ngram_range=(1, 2),
                                sublinear_tf=True, dtype=np.float32, token_pattern=r"(?u)\b\w+\b"), "protocol_text"),
        ("character", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3,
                                     max_features=30000, sublinear_tf=True, dtype=np.float32), "protocol_text"),
        ("numeric", Pipeline([
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True, add_indicator=True)),
            ("log1p", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
            ("scaler", StandardScaler()),
        ]), NUMERIC),
        ("categorical", OneHotEncoder(handle_unknown="ignore", dtype=np.float32), CATEGORICAL),
    ], remainder="drop", sparse_threshold=1.0)


def _development_frames(prepared):
    """Verify shards, then Arrow-filter train/tuning IDs before materialization."""
    prepared = Path(prepared)
    manifest = json.loads((prepared / "preparation_manifest.json").read_text())
    if manifest["source_metadata"].get("baseline_provenance") or manifest["source_metadata"].get("is_fixture"):
        raise ValueError("Probe requires the genuine retrospective prepared source.")
    partitions_path = prepared / "phase_partitions.csv"
    if sha256_file(partitions_path) != manifest["evidence_sha256"]["phase_partitions.csv"]:
        raise ValueError("Frozen phase partition checksum mismatch.")
    roles = pd.read_csv(partitions_path, usecols=["nct_id", "split"])
    if roles.nct_id.duplicated().any() or set(roles.split) != {"train", "validation", "test"}:
        raise ValueError("Frozen phase partition identity is invalid.")
    development = roles.loc[roles.split.isin(["train", "validation"])].copy()
    forbidden = set(roles.loc[roles.split.eq("test"), "nct_id"])
    if forbidden.intersection(development.nct_id):
        raise ValueError("Test IDs cannot enter development.")
    paths = []
    for shard in manifest["shards"]:
        if not re.fullmatch(r"shards/part-\d{6}\.parquet", shard["file"]):
            raise ValueError("Unsafe prepared shard path.")
        path = prepared / shard["file"]
        if path.is_symlink() or sha256_file(path) != shard["sha256"]:
            raise ValueError("Frozen input shard integrity mismatch.")
        paths.append(str(path))
    dataset = arrow_dataset.dataset(paths, format="parquet")
    columns = [field for field in ["nct_id", "phase", *RAW_FIELDS] if field in dataset.schema.names]
    selected = dataset.to_table(filter=arrow_dataset.field("nct_id").isin(development.nct_id.tolist()),
                                columns=columns, use_threads=False).to_pandas()
    if selected.nct_id.duplicated().any() or set(selected.nct_id) != set(development.nct_id):
        raise ValueError("Development row identity differs from the frozen partitions.")
    selected["phase"] = selected.phase.map(normalize_phase)
    if selected.phase.isna().any():
        raise ValueError("Development phase labels are unsupported.")
    selected = selected.set_index("nct_id")
    frames = {role: selected.loc[development.loc[development.split.eq(role), "nct_id"]].reset_index()
              for role in ("train", "validation")}
    return frames, manifest, {"train": len(frames["train"]), "validation": len(frames["validation"]),
                              "test_ids_forbidden": len(forbidden), "test_rows_materialized": 0,
                              "phase_partitions_sha256": sha256_file(partitions_path)}


def _aligned_probabilities(model, transformed):
    raw = model.predict_proba(transformed)
    aligned = np.zeros((len(raw), len(PHASE_LABELS)))
    for column, label in enumerate(model.classes_):
        aligned[:, PHASE_LABELS.index(str(label))] = raw[:, column]
    return aligned


def predict_bundle(frame, bundle, candidate):
    transformed = bundle["preprocessor"].transform(build_features(frame))
    if candidate == "svd128_design_catboost":
        text_columns = bundle["text_columns"]
        transformed = np.hstack([
            bundle["svd"].transform(transformed[:, :text_columns]),
            transformed[:, text_columns:].toarray(),
        ])
    model = bundle["models"][candidate]
    return np.asarray(model.predict(transformed)).reshape(-1), _aligned_probabilities(model, transformed)


def run(prepared, output, *, execute=False):
    output = Path(output).resolve()
    if not output.is_relative_to(OUTPUT_ROOT.resolve()) or output == OUTPUT_ROOT.resolve():
        raise ValueError("Probe outputs must use a new child of refinement-dev.")
    plan = {
        "protocol_id": "phase-refinement-development-v1", "random_seed": 42, "thread_count": 1,
        "roles": "Fit frozen train only; compare existing tuning only. Original test is exposed and excluded.",
        "candidates": CANDIDATES, "numeric": NUMERIC, "categorical": CATEGORICAL, "text": list(TEXT_FIELDS),
        "text_preprocessing": "Existing explicit phase redaction; remove NCT identifiers/calendar years/dates; cap concatenated text at12000characters.",
        "tfidf": {"word_features": 20000, "word_ngrams": [1, 2], "character_features": 30000,
                  "character_ngrams": [3, 5], "character_analyzer": "char_wb", "min_df": 3},
        "numeric_preprocessing": "Train median imputation with missing indicators, log1p nonnegative values, train scaling.",
        "selection": "Maximum tuning macro-F1 then balanced accuracy then model name; accuracy reported separately.",
        "limitations": ["Development-only results after earlier model exploration; no independent confirmation.",
                        "Current reported enrollment and source snapshots are retrospective; no baseline/pretrial claim.",
                        "Completed-only source may not transfer to ongoing or noncompleted trials.",
                        "EARLY_PHASE1 has no source support; this probe cannot establish performance for it.",
                        "No automatic promotion or90% guarantee; fresh holdout needed for any final claim."],
        "script_sha256": sha256_file(__file__),
        "source_sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in [
            ROOT / "src/clinical_trial_intelligence/phase_model.py", ROOT / "src/clinical_trial_intelligence/models/design.py",
            ROOT / "src/clinical_trial_intelligence/models/catboost_compat.py"]},
    }
    if not execute:
        return {"status": "planned_not_fitted", "plan": plan, "output": str(output)}
    output.mkdir(parents=True, exist_ok=False)
    state = {"status": "started", "created_at": datetime.now(timezone.utc).isoformat(), "plan": plan}
    write_json(output / "development_report.json", state)
    frames, manifest, identity = _development_frames(prepared)
    state.update({"development_identity": identity, "dataset_sha256": manifest["dataset_sha256"],
                  "results": {}, "baseline": {}})
    baseline_manifest = json.loads((ROOT / "examples/registry-v5205/phase/phase_manifest.json").read_text())
    for name in ("majority_baseline", baseline_manifest["recommended_model"]):
        state["baseline"][name] = baseline_manifest["models"][name]["metrics"]["validation"]
    features = {role: build_features(frame) for role, frame in frames.items()}
    labels = {role: frame.phase.to_numpy() for role, frame in frames.items()}
    classes = list(np.unique(labels["train"]))
    bundle = {"preprocessor": make_preprocessor(), "models": {}, "svd": None, "text_columns": None}
    print(f"Fit transforms on {len(labels['train']):,} train rows; {len(labels['validation']):,} tuning rows; zero test rows.", flush=True)
    started = time.monotonic()
    with threadpool_limits(limits=1):
        matrices = {"train": sparse.csr_matrix(bundle["preprocessor"].fit_transform(features["train"]))}
        matrices["validation"] = sparse.csr_matrix(bundle["preprocessor"].transform(features["validation"]))
        state["transform_seconds"] = time.monotonic() - started
        state["transformed_shape"] = list(matrices["train"].shape)
        state["text_columns"] = sum(len(bundle["preprocessor"].named_transformers_[name].vocabulary_) for name in ("word", "character"))
        bundle["text_columns"] = state["text_columns"]
        write_json(output / "development_report.json", state)
        for name, specification in CANDIDATES.items():
            print("Fitting", name, flush=True)
            started = time.monotonic()
            if specification["family"] == "logistic":
                model = LogisticRegression(C=specification["C"], class_weight=specification["class_weight"],
                                           max_iter=specification["max_iter"], random_state=42, solver="lbfgs")
                inputs = matrices
            else:
                bundle["svd"] = TruncatedSVD(n_components=specification["svd_components"], n_iter=5, random_state=42)
                text = {"train": bundle["svd"].fit_transform(matrices["train"][:, :bundle["text_columns"]])}
                text["validation"] = bundle["svd"].transform(matrices["validation"][:, :bundle["text_columns"]])
                inputs = {role: np.hstack([text[role], matrix[:, bundle["text_columns"]:].toarray()])
                          for role, matrix in matrices.items()}
                model = CTICatBoostClassifier(iterations=specification["iterations"], depth=specification["depth"],
                    learning_rate=specification["learning_rate"], l2_leaf_reg=specification["l2_leaf_reg"],
                    loss_function="MultiClass", random_seed=42, thread_count=1, task_type="CPU",
                    verbose=False, allow_writing_files=False)
            model.fit(inputs["train"], labels["train"])
            predicted = np.asarray(model.predict(inputs["validation"])).reshape(-1)
            metrics = evaluate_phase_predictions(labels["validation"], predicted, classes, bootstrap_samples=200, random_seed=42)
            state["results"][name] = {"metrics": metrics, "fit_and_evaluate_seconds": time.monotonic() - started,
                                      "converged": bool(np.max(model.n_iter_) < specification["max_iter"]) if specification["family"] == "logistic" else None}
            probability = _aligned_probabilities(model, inputs["validation"])
            predictions = pd.DataFrame({"nct_id": frames["validation"].nct_id, "split": "validation", "actual_phase": labels["validation"], "predicted_phase": predicted})
            for column, label in enumerate(PHASE_LABELS):
                predictions["probability_" + label] = probability[:, column]
            predictions.to_csv(output / (name + "_validation_predictions.csv"), index=False)
            bundle["models"][name] = model
            write_json(output / "development_report.json", state)
            print(json.dumps({"candidate": name, **{key: metrics[key] for key in ("accuracy", "balanced_accuracy", "macro_f1")},
                              "seconds": round(state["results"][name]["fit_and_evaluate_seconds"], 2)}), flush=True)
    state["selected_development_candidate"] = min(state["results"], key=lambda name: (
        -state["results"][name]["metrics"]["macro_f1"], -state["results"][name]["metrics"]["balanced_accuracy"], name))
    artifact = output / "development_candidates.joblib"
    joblib.dump(bundle, artifact, compress=3)
    reloaded = joblib.load(artifact)
    replay_rows = frames["validation"].iloc[[0, -1]]
    for name in CANDIDATES:
        first = predict_bundle(replay_rows, bundle, name)
        second = predict_bundle(replay_rows, reloaded, name)
        np.testing.assert_array_equal(first[0], second[0])
        np.testing.assert_allclose(first[1], second[1], rtol=0, atol=0)
    state.update({"status": "completed_development_only", "artifact_sha256": sha256_file(artifact),
                  "save_reload_verified": True, "completed_at": datetime.now(timezone.utc).isoformat()})
    write_json(output / "development_report.json", state)
    return {"status": state["status"], "selected_development_candidate": state["selected_development_candidate"],
            "results": {name: {key: record["metrics"][key] for key in ("accuracy", "balanced_accuracy", "macro_f1")}
                        for name, record in state["results"].items()}, "report": str(output / "development_report.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, default=ROOT / "data/registry-v5205-training")
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT / "phase-v1")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.prepared, args.output, execute=args.execute), indent=2))


if __name__ == "__main__":
    main()
