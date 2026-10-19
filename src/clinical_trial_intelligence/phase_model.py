"""Separate, auditable registry-phase classification for educational checks.

Only deserialize artifacts produced locally by this application in trusted
storage. Phase is a protocol classification, never an outcome or a regulatory
recommendation. Current registry snapshots do not establish baseline provenance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version as package_version
import json
from pathlib import Path
import pickle
import platform
import re
from typing import Any
import uuid
import unicodedata

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ARTIFACT_VERSION = 1
TASK = "phase"
PHASE_LABELS = ("EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4")
NUMERIC_FEATURES = ("enrollment", "number_of_arms", "primary_outcomes", "secondary_outcomes", "criteria_count")
TEXT_FIELDS = ("title", "brief_summary", "detailed_description", "eligibility_criteria")
SPLIT_NAMES = ("train", "validation", "test")
MODEL_NAME = "phase_logistic"

_PHASE_NUMBER = r"(?:three|four|zero|one|two|iv|iii|ii|i|[0-4])[ab]?(?![a-z0-9])"
_PHASE_PREFIX = r"(?:early[\s_–—-]*)?phases?[\s_:–—(\-]*"
_PHASE_MENTION = re.compile(
    rf"(?<![a-z0-9]){_PHASE_PREFIX}{_PHASE_NUMBER}"
    rf"\)?(?:\s*(?:/|\||\+|,|&|and\b|or\b|to\b|[-–—])\s*(?:{_PHASE_PREFIX})?{_PHASE_NUMBER}\)?)*",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class PhaseConfig:
    """Bound resource use; chronological split fractions stay fixed at .6/.2/.2."""

    max_text_features: int = 20000
    logistic_cs: tuple[float, ...] = (0.1, 1.0, 10.0)
    max_iter: int = 2000
    random_seed: int = 42
    enable_design_models: bool = False
    enable_design_catboost: bool = False
    bootstrap_samples: int = 0

    def validate(self):
        for name in ('enable_design_models', 'enable_design_catboost'):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(name + ' must be a boolean.')
        if self.enable_design_catboost and not self.enable_design_models:
            raise ValueError('enable_design_catboost requires enable_design_models.')
        if isinstance(self.bootstrap_samples, bool) or not isinstance(self.bootstrap_samples, int) or not 0 <= self.bootstrap_samples <= 10000:
            raise ValueError('bootstrap_samples must be an integer between0 and10000.')
        for field, lower, upper in (("max_text_features", 10, 50000), ("max_iter", 100, 5000), ("random_seed", 0, 2**32 - 1)):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= upper:
                raise ValueError(f"{field} must be an integer between {lower} and {upper}.")
        if not isinstance(self.logistic_cs, (tuple, list)) or not 1 <= len(self.logistic_cs) <= 8:
            raise ValueError("logistic_cs must contain between 1 and 8 candidate values.")
        if any(isinstance(c, bool) or not isinstance(c, (int, float)) or not np.isfinite(c) or not 0.0001 <= c <= 100 for c in self.logistic_cs):
            raise ValueError("Every logistic C must be finite and between 0.0001 and 100.")


def _text(value: Any) -> str:
    return "" if value is None or (np.isscalar(value) and pd.isna(value)) else str(value).strip()


def normalize_phase(value: Any) -> str | None:
    """Normalize single registry phases; do not guess combined or unknown labels."""
    compact = re.sub(r"[\s_-]+", "", _text(value)).upper()
    aliases = {"EARLYPHASE1": "EARLY_PHASE1", "EARLYPHASEI": "EARLY_PHASE1"}
    for number, roman, word in ((1, "I", "ONE"), (2, "II", "TWO"), (3, "III", "THREE"), (4, "IV", "FOUR")):
        for suffix in (str(number), roman, word):
            aliases["PHASE" + suffix] = f"PHASE{number}"
    return aliases.get(compact)


def redact_phase_mentions(value: Any) -> str:
    """Remove explicit Arabic, Roman, word, early and combined phase mentions."""
    return " ".join(_PHASE_MENTION.sub(" ", unicodedata.normalize("NFKC", _text(value))).split())


def _json_write(path: Path, value: dict):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False, default=str), encoding="utf-8")
    temporary.replace(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare_phase_cohort(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Include single-phase trials with a known day-precision start date.

    Recruiting/ongoing trials may qualify: no completion status or outcome date
    is required. Original phase strings remain in ``reported_phase`` for audit.
    """
    missing = sorted({"nct_id", "phase", "start_date"} - set(df.columns))
    if missing:
        raise ValueError("Missing required phase columns: " + ", ".join(missing))
    data = df.copy().reset_index(drop=True)
    if data.nct_id.isna().any() or data.nct_id.astype(str).str.strip().eq("").any():
        raise ValueError("Every record must have a non-empty nct_id.")
    data["nct_id"] = data.nct_id.astype(str).str.strip()
    if data.nct_id.duplicated().any():
        raise ValueError("Duplicate nct_id values are not allowed: aggregate related tables before training.")
    data["reported_phase"] = data.phase.map(_text)
    data["phase"] = data.phase.map(normalize_phase)
    raw_dates = data.start_date.map(_text)
    imprecise = raw_dates.ne("") & ~raw_dates.str.match(r"^\d{4}-\d{2}-\d{2}(?:$|[T ])")
    data["start_date"] = pd.to_datetime(raw_dates.where(~imprecise), errors="coerce", utc=True, format="mixed").dt.tz_convert(None)
    # Date groups are calendar days, even when a CSV contains timestamps.
    data["start_date"] = data.start_date.dt.normalize()
    reason = pd.Series("", index=data.index, dtype=object)
    for i in data.index[data.phase.isna()]:
        reported = data.at[i, "reported_phase"].upper()
        compact = re.sub(r"[\s_.-]+", "", reported)
        if compact in {"NA", "N/A", "NOTAPPLICABLE", "NONE"}:
            label = "phase_not_applicable"
        elif re.search(r"[/|+&]|\bAND\b|\bOR\b", reported) or len(re.findall(r"PHASE", reported)) > 1 or re.search(r"(?:[1-4]|I{1,3})\s*[-–]\s*(?:[1-4]|I{1,3})", reported):
            label = "combined_phase"
        else:
            label = "phase_unknown_or_unsupported"
        reason.at[i] += label + ";"
    reason.loc[imprecise] += "start_date_day_precision_not_established;"
    reason.loc[data.start_date.isna()] += "missing_or_invalid_start_date;"
    excluded = reason.ne("")
    exclusions = pd.DataFrame({"nct_id": data.loc[excluded, "nct_id"], "reported_phase": data.loc[excluded, "reported_phase"], "reason": reason.loc[excluded].str.rstrip(";")})
    return data.loc[~excluded].sort_values(["start_date", "nct_id"]).reset_index(drop=True), exclusions.reset_index(drop=True)


def phase_temporal_split(cohort: pd.DataFrame) -> dict:
    """Assign whole chronological start-date groups in fixed 60/20/20 shares.

    Shares refer to distinct dates, not rows; unequal group sizes can therefore
    require a larger cohort to satisfy the training sample guard.
    """
    dates = sorted(cohort.start_date.dropna().unique())
    if len(dates) < 3:
        raise ValueError("At least three distinct start-date groups are required for temporal phase evaluation.")
    train_end = max(1, min(len(dates) - 2, int(len(dates) * 0.6)))
    validation_end = max(train_end + 1, min(len(dates) - 1, int(len(dates) * 0.8)))
    validation_cutoff, test_cutoff = pd.Timestamp(dates[train_end]), pd.Timestamp(dates[validation_end])
    return {
        "train": cohort.loc[cohort.start_date < validation_cutoff].copy(),
        "validation": cohort.loc[(cohort.start_date >= validation_cutoff) & (cohort.start_date < test_cutoff)].copy(),
        "test": cohort.loc[cohort.start_date >= test_cutoff].copy(),
        "validation_cutoff": validation_cutoff, "test_cutoff": test_cutoff,
    }


def _phase_features(df: pd.DataFrame, *, include_design=False) -> pd.DataFrame:
    """Whitelist protocol inputs; never pass labels, IDs, status or dates."""
    output = pd.DataFrame(index=df.index)
    for name in NUMERIC_FEATURES:
        values = pd.to_numeric(df[name], errors="coerce") if name in df else pd.Series(np.nan, index=df.index)
        output[name] = values.where(np.isfinite(values) & values.ge(0), np.nan)
    texts = [df[field].map(redact_phase_mentions) for field in TEXT_FIELDS if field in df]
    output["protocol_text"] = pd.concat(texts, axis=1).agg(" ".join, axis=1).str.strip() if texts else ""
    output.loc[~output.protocol_text.str.contains(r"\w", regex=True), "protocol_text"] = "missingprotocol"
    if include_design:
        from .models.design import design_features
        for field, values in design_features(df, phase_task=True).items():
            output[field] = values
    return output


def _preprocessor(config: PhaseConfig) -> ColumnTransformer:
    return ColumnTransformer([
        ("numeric", Pipeline([("imputer", SimpleImputer(strategy="median", keep_empty_features=True)), ("scaler", StandardScaler())]), list(NUMERIC_FEATURES)),
        ("text", TfidfVectorizer(max_features=config.max_text_features, ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"(?u)\b\w+\b"), "protocol_text"),
    ], remainder="drop", sparse_threshold=1.0)


def _class_support(labels) -> dict[str, int]:
    values = np.asarray(labels)
    return {label: int(np.sum(values == label)) for label in PHASE_LABELS}


def evaluate_phase_predictions(actual, predicted, training_classes, bootstrap_samples=0, random_seed=42) -> dict:
    """Keep every held-out label, including phase classes absent in training."""
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    if actual.ndim != 1 or predicted.ndim != 1 or not len(actual) or len(actual) != len(predicted):
        raise ValueError("Phase metric arrays must be one-dimensional, non-empty and equally sized.")
    if not set(actual).union(predicted).issubset(PHASE_LABELS):
        raise ValueError("Phase metrics only accept normalized supported phase labels.")
    matrix = confusion_matrix(actual, predicted, labels=list(PHASE_LABELS))
    supports = matrix.sum(axis=1)
    recalls = np.diag(matrix)[supports > 0] / supports[supports > 0]
    metric_labels = [label for label in PHASE_LABELS if label in set(actual).union(predicted)]
    result = {
        "n": len(actual), "accuracy": float(accuracy_score(actual, predicted)),
        "balanced_accuracy": float(recalls.mean()),
        "macro_f1": float(f1_score(actual, predicted, labels=metric_labels, average="macro", zero_division=0)),
        "labels": list(PHASE_LABELS), "confusion_matrix": matrix.tolist(),
        "class_support": _class_support(actual), "macro_f1_labels": metric_labels,
        "unseen_training_labels": [label for label in PHASE_LABELS if label in actual and label not in training_classes],
    }
    result['per_class'] = {label: {'precision': float(matrix[i,i] / matrix[:,i].sum()) if matrix[:,i].sum() else 0.,
                                   'recall': float(matrix[i,i] / supports[i]) if supports[i] else 0.,
                                   'f1': float(2 * matrix[i,i] / (matrix[:,i].sum() + supports[i])) if matrix[:,i].sum() + supports[i] else 0.,
                                   'support': int(supports[i])}
                           for i, label in enumerate(PHASE_LABELS)}
    if isinstance(bootstrap_samples, bool) or not isinstance(bootstrap_samples, int) or not 0 <= bootstrap_samples <= 10000:
        raise ValueError('bootstrap_samples must be an integer between0 and10000.')
    if bootstrap_samples:
        rng = np.random.default_rng(random_seed)
        scores = {key: [] for key in ('accuracy', 'balanced_accuracy', 'macro_f1')}
        for _ in range(bootstrap_samples):
            index = rng.integers(0, len(actual), len(actual))
            sampled = evaluate_phase_predictions(actual[index], predicted[index], training_classes)
            for key in scores:
                scores[key].append(sampled[key])
        result['confidence_intervals'] = {'method': 'conditional fitted-model trial bootstrap percentile', 'level': .95,
            'requested_resamples': bootstrap_samples, 'random_seed': random_seed,
            **{key: {'lower': float(np.quantile(values, .025)), 'upper': float(np.quantile(values, .975)),
                     'valid_resamples': len(values)} for key, values in scores.items()}}
    return result


def _probabilities(model, features: pd.DataFrame) -> np.ndarray:
    raw = model.predict_proba(features)
    aligned = np.zeros((len(features), len(PHASE_LABELS)))
    for i, label in enumerate(model.classes_):
        aligned[:, PHASE_LABELS.index(str(label))] = raw[:, i]
    return aligned


def train_phase_experiment(df: pd.DataFrame, output_dir: str | Path, source_metadata: dict | None = None, *, config: PhaseConfig | None = None) -> dict:
    """Fit train-only transforms; tune logistic C by validation macro-F1.

    Test is evaluated only after selection, and validation is never refitted.
    Output names cannot collide with duration artifacts. A failed attempt writes
    ``phase_error.json``; a completed output directory must not be overwritten.
    """
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    if any((directory / name).exists() for name in ("phase_manifest.json", "phase_models.joblib")):
        raise ValueError("Experiment directory already contains a phase artifact; use a new output directory.")
    config, metadata = config or PhaseConfig(), dict(source_metadata or {})
    run_id = str(uuid.uuid4())
    try:
        config.validate()
        # Use JSON-compatible provenance/config in both files so equality checks
        # are stable across serialization, including list-valued C candidates.
        metadata = json.loads(json.dumps(metadata, allow_nan=False, default=str))
        config_record = json.loads(json.dumps(asdict(config), allow_nan=False))
        cohort, exclusions = prepare_phase_cohort(df)
        exclusions.to_csv(directory / "phase_cohort_exclusions.csv", index=False)
        if len(cohort) < 40:
            raise ValueError(f"At least 40 eligible single-phase trials are required; found {len(cohort)}. The sample-size guard is not evidence of research validity.")
        splits = phase_temporal_split(cohort)
        if len(splits["train"]) < 20 or min(len(splits[split]) for split in ("validation", "test")) < 5:
            raise ValueError("Temporal phase splitting requires at least 20 training and 5 validation/test trials; use more distinct start-date groups or a larger cohort.")
        training_classes = [label for label in PHASE_LABELS if label in set(splits["train"].phase)]
        if len(training_classes) < 2:
            raise ValueError("Training requires at least two phase classes in the chronological training split.")
        features = {name: _phase_features(splits[name], include_design=config.enable_design_models) for name in SPLIT_NAMES}
        labels = {name: splits[name].phase.to_numpy() for name in SPLIT_NAMES}
        baseline = DummyClassifier(strategy="most_frequent").fit(features["train"], labels["train"])
        selected_model, selected_key, selected_c = None, None, None
        candidates = []
        for c in config.logistic_cs:
            model = Pipeline([("preprocess", _preprocessor(config)), ("model", LogisticRegression(C=c, max_iter=config.max_iter, solver="lbfgs", random_state=config.random_seed))])
            model.fit(features["train"], labels["train"])
            metric = evaluate_phase_predictions(labels["validation"], model.predict(features["validation"]), training_classes)
            key = (-metric['macro_f1'], -metric['balanced_accuracy']) if config.enable_design_models else (-metric['macro_f1'],)
            candidates.append({"logistic_C": float(c), "validation_macro_f1": metric['macro_f1'],
                               "validation_balanced_accuracy": metric['balanced_accuracy']})
            if selected_key is None or key < selected_key:
                selected_model, selected_key, selected_c = model, key, float(c)
        models = {"majority_baseline": baseline, MODEL_NAME: selected_model}
        extra_selections = {}
        if config.enable_design_models:
            from .models.design import fit_phase_design_models
            extra_models, extra_selections = fit_phase_design_models(features['train'], labels['train'], features['validation'], labels['validation'], config)
            models.update(extra_models)
        tuning = {name: evaluate_phase_predictions(labels['validation'], np.asarray(model.predict(features['validation'])).reshape(-1), training_classes)
                  for name, model in models.items()}
        recommended_model = (min(models, key=lambda name: (-tuning[name]['macro_f1'], -tuning[name]['balanced_accuracy'], name))
                             if config.enable_design_models else MODEL_NAME)
        model_records, predictions = {}, []
        for model_name, model in models.items():
            selection = {"rule": "most frequent training phase"} if model_name == "majority_baseline" else {"rule": "maximum validation macro-F1; first candidate wins ties", "logistic_C": selected_c, "candidates": candidates}
            if model_name == MODEL_NAME and config.enable_design_models:
                selection['rule'] = 'maximum tuning macro-F1 then balanced accuracy then declared grid order'
            if model_name in extra_selections:
                selection = extra_selections[model_name]
            if model_name == 'majority_baseline':
                contract, mode = {'numeric': [], 'categorical': [], 'text': []}, 'baseline'
            elif model_name.startswith('phase_design_'):
                from .models.design import input_features
                contract, mode = input_features(phase_task=True), 'structured'
            else:
                contract = {'numeric': [] if model_name == 'phase_text' else list(NUMERIC_FEATURES), 'categorical': [], 'text': list(TEXT_FIELDS)}
                mode = 'text' if model_name == 'phase_text' else 'multimodal'
            model_records[model_name] = {'input_features': contract, 'input_mode': mode, "selection": selection, "metrics": {}}
            for split in ("validation", "test"):
                predicted = np.asarray(model.predict(features[split])).reshape(-1)
                probability = _probabilities(model, features[split])
                model_records[model_name]["metrics"][split] = evaluate_phase_predictions(labels[split], predicted, training_classes, config.bootstrap_samples, config.random_seed)
                frame = pd.DataFrame({"nct_id": splits[split].nct_id.to_numpy(), "split": split, "model_name": model_name, "reported_phase": splits[split].reported_phase.to_numpy(), "actual_phase": labels[split], "predicted_phase": predicted, "correct": labels[split] == predicted})
                for index, label in enumerate(PHASE_LABELS):
                    frame["probability_" + label] = probability[:, index]
                predictions.append(frame)
        warning = "Educational registry-phase consistency check only; not clinical advice or regulatory phase assignment. Class probabilities are uncalibrated model outputs, not clinical success probabilities. Minimum sample guards do not establish scientific validity."
        if metadata.get("is_fixture") or metadata.get("fixture"):
            warning += " SOFTWARE TEST FIXTURE: generated or bundled records and their metrics are not scientific evidence."
        if not metadata.get("baseline_provenance"):
            warning += " RETROSPECTIVE SNAPSHOT: baseline feature and label availability is unverified; registry updates and indirect narrative cues may cause leakage. Do not claim prospective validation."
        split_records = {name: {"rows": len(splits[name]), "start_date_min": splits[name].start_date.min().isoformat(), "start_date_max": splits[name].start_date.max().isoformat(), "nct_ids": splits[name].nct_id.tolist(), "class_support": _class_support(labels[name])} for name in SPLIT_NAMES}
        feature_contract = {kind: list(dict.fromkeys(field for record in model_records.values() for field in record['input_features'][kind]))
                            for kind in ('numeric', 'categorical', 'text')}
        shared = {
            "task": TASK, "artifact_version": ARTIFACT_VERSION, "run_id": run_id,
            "source_metadata": metadata, "dataset_id": metadata.get("dataset_id"),
            "input_sha256": hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest(),
            "pipeline_source_sha256": _sha256_file(Path(__file__)), "config": config_record,
            "labels": list(PHASE_LABELS), "training_classes": training_classes,
            "splits": split_records, "warning": warning,
        }
        manifest = {
            **shared, "status": "completed", "created_at": datetime.now(timezone.utc).isoformat(),
            "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__, "scikit_learn": sklearn.__version__, "joblib": joblib.__version__,
                            **({'catboost': package_version('catboost')} if config.enable_design_catboost else {})},
            "cohort": {"input_rows": len(df), "eligible_rows": len(cohort), "excluded_rows": len(exclusions), "target": "normalized single registry phase"},
            "temporal_cutoffs": {"validation": splits["validation_cutoff"].isoformat(), "test": splits["test_cutoff"].isoformat(), "policy": "Whole start-date groups; fixed 60/20/20 shares of distinct dates. No refit on validation. No outcome-availability purge: phase is a protocol label, with baseline availability separately unverified."},
            "features": {**feature_contract, "redaction": "Explicit Arabic/Roman/word phase labels, early labels and combined mentions removed before TF-IDF.",
                         "excluded": ["phase", "reported_phase", "nct_id", "status", "start_date", "completion_date", "completion_date_type", "duration_days", "prolonged"] + ([] if config.enable_design_models else ['study_type'])},
            "models": model_records, "recommended_model": recommended_model,
            "recommendation": {'split': 'validation', 'metric': 'macro_f1', 'value': tuning[recommended_model]['macro_f1'],
                               'rule': 'Maximum tuning macro-F1 then balanced accuracy then model name including majority baseline.' if config.enable_design_models else 'Legacy logistic hyperparameter selection; unchanged default.'},
            "additional_model_source_sha256": {name: _sha256_file(Path(__file__).parent / name) for name in
                (['models/design.py'] if config.enable_design_models else [])
                + (['models/catboost_compat.py'] if config.enable_design_catboost else [])},
            "limitations": [
                "This task predicts recorded phase from protocol characteristics; it does not predict progression or trial success.",
                "Combined, NA and unknown phases are excluded. Class support can be small or absent, and classes absent from training have zero predicted probability.",
                "All held-out records count, including labels absent from training. Confusion matrices use the five canonical labels (rows actual, columns predicted); macro-F1 averages the union of actual/predicted labels; balanced accuracy averages recall for actual supported classes.",
                "Validation scores are optimistic after hyperparameter selection; untouched test scores are the held-out estimate. No performance improvement is guaranteed.",
                "Redaction removes explicit phase mentions but cannot eliminate indirect phase cues or post-start updates in current registry snapshots.",
                "Temporal ordering does not establish that current registry labels or protocol features existed at trial start; baseline provenance must be established separately.",
            ],
            "files": {"artifact": "phase_models.joblib", "metrics": "phase_metrics.json", "predictions": "phase_held_out_predictions.csv", "cohort_exclusions": "phase_cohort_exclusions.csv"},
        }
        pd.concat(predictions, ignore_index=True).to_csv(directory / manifest["files"]["predictions"], index=False)
        _json_write(directory / "phase_metrics.json", {name: value["metrics"] for name, value in model_records.items()})
        artifact_path = directory / "phase_models.joblib"
        temporary = directory / "phase_models.joblib.tmp"
        joblib.dump({**shared, "models": models, "recommended_model": recommended_model}, temporary)
        temporary.replace(artifact_path)
        manifest["artifact_sha256"] = _sha256_file(artifact_path)
        _json_write(directory / "phase_manifest.json", manifest)
        (directory / "phase_error.json").unlink(missing_ok=True)
        return manifest
    except Exception as exc:
        _json_write(directory / "phase_error.json", {"task": TASK, "run_id": run_id, "status": "failed", "error_type": type(exc).__name__, "error": str(exc), "source_metadata": metadata})
        raise


def predict_phase(row: dict, artifact_dir: str | Path) -> dict:
    """Predict from a matching trusted local phase artifact, or return unavailable.

    The HTTP service must additionally match this artifact's source metadata to
    the selected registered dataset before calling this function.
    """
    reported = _text(row.get("phase")) or None
    unavailable = {"status": "unavailable", "task": TASK, "model_name": MODEL_NAME, "reported_phase": reported, "normalized_reported_phase": normalize_phase(reported), "predicted_phase": None, "class_probabilities": None}
    directory = Path(artifact_dir)
    manifest_path, model_path = directory / "phase_manifest.json", directory / "phase_models.joblib"
    if directory.is_symlink() or any(path.is_symlink() or not path.is_file() for path in (manifest_path, model_path)):
        return {**unavailable, "reason": "No completed compatible trained phase artifact is available."}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "completed" or manifest.get("task") != TASK or manifest.get("artifact_version") != ARTIFACT_VERSION or not manifest.get("run_id"):
            return {**unavailable, "reason": "Phase artifact task or version is incompatible."}
        if manifest.get("artifact_sha256") != _sha256_file(model_path):
            return {**unavailable, "reason": "Phase artifact checksum does not match its manifest; rerun the experiment."}
        artifact = joblib.load(model_path)
        shared_fields = ("task", "artifact_version", "run_id", "source_metadata", "dataset_id", "input_sha256", "pipeline_source_sha256", "config", "labels", "training_classes", "splits", "warning")
        if any(field not in manifest or artifact.get(field) != manifest[field] for field in shared_fields):
            return {**unavailable, "reason": "Phase artifact and manifest do not match; rerun the experiment."}
        if manifest["labels"] != list(PHASE_LABELS) or set(artifact["models"]) != set(manifest["models"]) or MODEL_NAME not in artifact["models"]:
            return {**unavailable, "reason": "Phase artifact model labels or model catalog are incompatible."}
        selected_name = manifest.get('recommended_model', MODEL_NAME)
        if selected_name != artifact.get('recommended_model', MODEL_NAME) or selected_name not in artifact['models']:
            return {**unavailable, 'reason': 'Phase recommended branch differs from its fitted artifact.'}
        model = artifact["models"][selected_name]
        if set(model.classes_) != set(manifest["training_classes"]):
            return {**unavailable, "reason": "Phase model classes do not match the training manifest."}
        features = _phase_features(pd.DataFrame([row]), include_design=manifest.get("config", {}).get("enable_design_models", False))
        probabilities = _probabilities(model, features)[0]
        if not np.isfinite(probabilities).all() or (probabilities < 0).any() or (probabilities > 1).any() or not np.isclose(probabilities.sum(), 1):
            return {**unavailable, "reason": "Phase artifact produced invalid class probabilities."}
        predicted = str(np.asarray(model.predict(features)).reshape(-1)[0])
        identifier = _text(row.get("nct_id"))
        membership = next((split for split in SPLIT_NAMES if identifier in manifest["splits"][split]["nct_ids"]), "not_in_retained_splits")
        scope = {
            "train": "In-sample estimate for a trial used to fit the classifier; not held-out evidence.",
            "validation": "Validation estimate for a trial used to select hyperparameters; not an untouched test result.",
            "test": "Held-out test estimate; source-provenance and retrospective snapshot limitations still apply.",
            "not_in_retained_splits": "Trial is outside retained splits; no validation claim is established for this record.",
        }[membership]
        return {**unavailable, "status": "available", "run_id": artifact["run_id"], "model_name": selected_name, "predicted_phase": predicted,
                "class_probabilities": {label: float(probabilities[i]) for i, label in enumerate(PHASE_LABELS)},
                "cohort_membership": membership, "prediction_scope": scope, "warning": artifact["warning"]}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, EOFError, ImportError, IndexError, pickle.UnpicklingError):
        return {**unavailable, "reason": "Phase artifact could not be used; rerun a compatible local experiment."}
