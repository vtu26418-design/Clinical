"""Reproducible temporal experiments. No model is available before real fitting.

All transformation state and the prolonged-duration threshold are fitted on the
training cohort. Registry snapshots without baseline provenance are retrospective.
Only load the joblib artifacts produced by this application from trusted storage.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import platform
import pickle
import re
from typing import Any, Literal
import uuid

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (ExtraTreesClassifier, ExtraTreesRegressor, GradientBoostingClassifier,
                              GradientBoostingRegressor, HistGradientBoostingClassifier,
                              HistGradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import average_precision_score, brier_score_loss, mean_absolute_error, mean_squared_error, r2_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

ARTIFACT_VERSION = 3
MIN_CALIBRATION_ROWS = 10
NUMERIC_FEATURES = ["enrollment", "number_of_arms", "primary_outcomes", "secondary_outcomes", "criteria_count"]
CATEGORICAL_FEATURES = ["study_type", "phase"]
TEXT_FIELDS = ["title", "brief_summary", "detailed_description", "eligibility_criteria"]
MODEL_METADATA = {
    "median_baseline": {"family": "constant_baseline", "input_mode": "baseline", "display_name": "Median / prevalence baseline"},
    "structured": {"family": "ridge_logistic", "input_mode": "structured", "display_name": "Structured linear"},
    "text": {"family": "ridge_logistic", "input_mode": "text", "display_name": "Text linear (TF-IDF)"},
    "multimodal": {"family": "ridge_logistic", "input_mode": "multimodal", "display_name": "Multimodal linear"},
    "structured_extra_trees": {"family": "extra_trees", "input_mode": "structured", "display_name": "Structured Extra Trees"},
    "structured_random_forest": {"family": "random_forest", "input_mode": "structured", "display_name": "Structured Random Forest"},
    "structured_gradient_boosting": {"family": "gradient_boosting", "input_mode": "structured", "display_name": "Structured Gradient Boosting"},
    "structured_hist_gradient_boosting": {"family": "hist_gradient_boosting", "input_mode": "structured", "display_name": "Structured Histogram Boosting"},
    "structured_catboost": {"family": "catboost", "input_mode": "structured", "display_name": "Structured CatBoost"},
    "multimodal_late_fusion": {"family": "weighted_late_fusion", "input_mode": "multimodal", "display_name": "Text + Histogram Boosting Fusion"},
}


@dataclass(frozen=True)
class ExperimentConfig:
    train_fraction: float = 0.6
    validation_fraction: float = 0.2
    prolonged_quantile: float = 0.75
    bootstrap_samples: int = 200
    random_seed: int = 42
    max_text_features: int = 20000
    enable_advanced_models: bool = True
    enable_catboost: bool = False
    uncertainty_alpha: float = 0.1
    catboost_search: Literal['basic', 'expanded'] = 'basic'

    def validate(self):
        if not (0 < self.train_fraction < 1 and 0 < self.validation_fraction < 1 and self.train_fraction + self.validation_fraction < 1):
            raise ValueError("Train and validation fractions must be positive and leave a test split.")
        if not 0 < self.prolonged_quantile < 1:
            raise ValueError("prolonged_quantile must lie strictly between 0 and 1.")
        if not 0 <= self.bootstrap_samples <= 10000:
            raise ValueError("bootstrap_samples must be between 0 and 10000.")
        if self.max_text_features < 10:
            raise ValueError("max_text_features must be at least 10.")
        if not isinstance(self.enable_advanced_models, bool):
            raise ValueError("enable_advanced_models must be a boolean.")
        if not isinstance(self.enable_catboost, bool):
            raise ValueError("enable_catboost must be a boolean.")
        if self.catboost_search not in ('basic', 'expanded'):
            raise ValueError("catboost_search must be 'basic' or 'expanded'.")
        if isinstance(self.uncertainty_alpha, bool) or not np.isfinite(self.uncertainty_alpha) or not 0 < self.uncertainty_alpha < 1:
            raise ValueError("uncertainty_alpha must be finite and strictly between 0 and 1.")


def _json_write(path: Path, obj: dict):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(obj, indent=2, allow_nan=False, default=str), encoding="utf-8")
    temporary.replace(path)


def prepare_cohort(df: pd.DataFrame, source_metadata: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return observed completed outcomes and auditable row exclusions.

    Actual dates require per-row completion_date_type=ACTUAL or an explicit
    completion_dates_actual=True source guarantee. Estimated dates never qualify.
    """
    required = {"nct_id", "start_date", "completion_date", "status"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError("Missing required outcome columns: " + ", ".join(missing))
    data = df.copy().reset_index(drop=True)
    if data["nct_id"].isna().any() or data["nct_id"].astype(str).str.strip().eq("").any():
        raise ValueError("Every record must have a non-empty nct_id.")
    data["nct_id"] = data["nct_id"].astype(str).str.strip()
    if data["nct_id"].duplicated().any():
        raise ValueError("Duplicate nct_id values are not allowed: join related tables before training.")
    imprecise = {}
    for field in ("start_date", "completion_date"):
        raw = data[field].astype(str).str.strip()
        imprecise[field] = data[field].notna() & ~raw.str.match(r"^\d{4}-\d{2}-\d{2}(?:$|[T ])")
        data[field] = pd.to_datetime(raw.where(~imprecise[field]), errors="coerce", utc=True, format="mixed").dt.tz_convert(None)
    data["duration_days"] = (data["completion_date"] - data["start_date"]).dt.total_seconds() / 86400
    if "completion_date_type" in data:
        actual = data["completion_date_type"].fillna("").astype(str).str.strip().str.upper().eq("ACTUAL")
    else:
        actual = pd.Series((source_metadata or {}).get("completion_dates_actual") is True, index=data.index)
    conditions = {
        "status_not_completed": ~data["status"].fillna("").astype(str).str.strip().str.upper().eq("COMPLETED"),
        "actual_completion_not_established": ~actual,
        "start_date_day_precision_not_established": imprecise["start_date"],
        "completion_date_day_precision_not_established": imprecise["completion_date"],
        "missing_or_invalid_start_date": data["start_date"].isna(),
        "missing_or_invalid_completion_date": data["completion_date"].isna(),
        "nonpositive_duration": data["duration_days"].le(0),
    }
    reason = pd.Series("", index=data.index, dtype=object)
    for label, excluded in conditions.items():
        reason.loc[excluded] += label + ";"
    excluded = reason.ne("")
    exclusions = pd.DataFrame({"nct_id": data.loc[excluded, "nct_id"], "reason": reason.loc[excluded].str.rstrip(";")})
    return data.loc[~excluded].sort_values(["start_date", "nct_id"]).reset_index(drop=True), exclusions.reset_index(drop=True)


def temporal_split(cohort: pd.DataFrame, config: ExperimentConfig | None = None) -> dict:
    """Split whole start-date groups, then purge outcomes unavailable at each cutoff."""
    config = config or ExperimentConfig()
    config.validate()
    # Group calendar days even for timestamp-bearing uploads. Preserve the
    # timestamps for duration and outcome-availability calculations.
    start_days = cohort['start_date'].dt.normalize()
    dates = sorted(start_days.dropna().unique())
    if len(dates) < 3:
        raise ValueError("At least three distinct start-date groups are required for temporal evaluation.")
    train_end = max(1, min(len(dates) - 2, int(len(dates) * config.train_fraction)))
    val_end = max(train_end + 1, min(len(dates) - 1, int(len(dates) * (config.train_fraction + config.validation_fraction))))
    validation_cutoff, test_cutoff = pd.Timestamp(dates[train_end]), pd.Timestamp(dates[val_end])
    train = cohort.loc[start_days < validation_cutoff].copy()
    validation = cohort.loc[(start_days >= validation_cutoff) & (start_days < test_cutoff)].copy()
    test = cohort.loc[start_days >= test_cutoff].copy()
    purged_train = train.loc[train.completion_date >= validation_cutoff]
    purged_validation = validation.loc[validation.completion_date >= test_cutoff]
    return {
        "train": train.loc[train.completion_date < validation_cutoff].copy(),
        "validation": validation.loc[validation.completion_date < test_cutoff].copy(),
        "test": test,
        "validation_cutoff": validation_cutoff,
        "test_cutoff": test_cutoff,
        "purged": pd.concat([
            purged_train.assign(reason="training_outcome_unavailable_at_validation_cutoff"),
            purged_validation.assign(reason="validation_outcome_unavailable_at_test_cutoff"),
        ], ignore_index=True)[["nct_id", "reason"]],
    }


def partition_validation(validation: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Reserve later whole calendar-day groups; never discard a small cohort."""
    days = validation.start_date.dt.normalize()
    dates = sorted(days.dropna().unique())
    midpoint = max(1, len(dates) // 2)
    cutoff = pd.Timestamp(dates[midpoint]) if midpoint < len(dates) else None
    tuning = validation.loc[days < cutoff].copy() if cutoff is not None else validation.copy()
    calibration = validation.loc[days >= cutoff].copy() if cutoff is not None else validation.iloc[:0].copy()
    available = len(calibration) >= MIN_CALIBRATION_ROWS and len(tuning) > 0
    if not available:
        tuning, calibration = validation.copy(), validation.iloc[:0].copy()
    info = {
        "method": "Earlier tuning / later calibration, split by whole start-date calendar-day groups near the halfway group",
        "original_validation_rows": len(validation), "original_validation_nct_ids": validation.nct_id.tolist(),
        "original_validation_date_groups": len(dates), "tuning_split": "validation", "calibration_split": "calibration",
        "tuning_rows": len(tuning), "calibration_rows": len(calibration), "minimum_calibration_rows": MIN_CALIBRATION_ROWS,
        "calibration_available": available, "calibration_cutoff": cutoff.isoformat() if available else None,
        "reason": "Independent later validation groups reserved for calibration; no refit on tuning/calibration."
                  if available else "Fewer than 10 later calibration rows or no earlier tuning rows: all original validation rows tune models; uncertainty and probability calibration are unavailable.",
    }
    return tuning, calibration, info


def split_conformal_quantile(residuals, alpha: float = 0.1) -> dict:
    """Exact split-conformal order statistic, including an infinite quantile."""
    if isinstance(alpha, bool) or not np.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be finite and strictly between 0 and 1.")
    residuals = np.asarray(residuals, dtype=float)
    if residuals.ndim != 1 or not len(residuals) or not np.isfinite(residuals).all() or (residuals < 0).any():
        raise ValueError("Residuals must be a non-empty vector of finite nonnegative absolute errors.")
    rank = math.ceil((len(residuals) + 1) * (1 - Fraction(str(alpha))))
    bounded = rank <= len(residuals)
    return {"n": len(residuals), "alpha": float(alpha), "nominal_coverage": float(1 - alpha), "rank": rank,
            "residual_quantile_days": float(np.sort(residuals)[rank - 1]) if bounded else None, "bounded": bounded}


def _logit_probability(probability):
    clipped = np.clip(np.asarray(probability, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped)).reshape(-1, 1)


def _fit_probability_calibration(probability, labels, config) -> dict:
    counts = {str(value): int((labels == value).sum()) for value in (0, 1)}
    available = len(labels) >= MIN_CALIBRATION_ROWS and min(counts.values()) >= 2
    metadata = {"status": "available" if available else "unavailable", "n": len(labels), "class_counts": counts,
                "method": "sigmoid calibration of clipped raw-probability logit", "split": "calibration",
                "minimum_rows": MIN_CALIBRATION_ROWS, "minimum_per_class": 2,
                "clip_epsilon": 1e-6, "regularization_C": 1.0,
                "reason": "Fitted only on reserved calibration labels; never used for model selection."
                          if available else "Requires at least 10 reserved calibration rows and at least two labels of each class; raw probabilities remain available."}
    estimator = None
    if available:
        estimator = LogisticRegression(C=1.0, solver="lbfgs", random_state=config.random_seed, max_iter=2000)
        estimator.fit(_logit_probability(probability), labels)
    return {"estimator": estimator, "metadata": metadata}


def _calibrated_probability(probability, calibration):
    estimator = calibration["estimator"]
    return estimator.predict_proba(_logit_probability(probability))[:, list(estimator.classes_).index(1)] if estimator is not None else None


def _fit_training_support(X):
    return {"numeric": {feature: {"minimum": float(X[feature].min()) if X[feature].notna().any() else None,
                                  "maximum": float(X[feature].max()) if X[feature].notna().any() else None,
                                  "lower_quantile": float(X[feature].quantile(.01)) if X[feature].notna().any() else None,
                                  "upper_quantile": float(X[feature].quantile(.99)) if X[feature].notna().any() else None,
                                  "missing_fraction": float(X[feature].isna().mean())}
                        for feature in NUMERIC_FEATURES},
            "categorical": {feature: sorted(set(X[feature])) for feature in CATEGORICAL_FEATURES},
            "text_length": {"minimum": int(X.protocol_text.str.len().min()), "maximum": int(X.protocol_text.str.len().max()),
                            "lower_quantile": float(X.protocol_text.str.len().quantile(.01)),
                            "upper_quantile": float(X.protocol_text.str.len().quantile(.99)), "unit": "characters"},
            "training_rows": len(X), "tail_quantiles": [.01, .99],
            "method": "Training-only observed numeric ranges, central 98% marginal ranges, text lengths and categorical levels"}


def _extrapolation(X, support):
    row, numeric, unseen, tails = X.iloc[0], [], [], []
    for feature, limits in support["numeric"].items():
        value = row[feature]
        if pd.notna(value) and (limits["minimum"] is None or value < limits["minimum"] or value > limits["maximum"]):
            numeric.append({"feature": feature, "value": float(value), **limits})
        if (pd.notna(value) and limits.get("lower_quantile") is not None
                and (value < limits["lower_quantile"] or value > limits["upper_quantile"])):
            tails.append({"feature": feature, "value": float(value), "lower_quantile": limits["lower_quantile"], "upper_quantile": limits["upper_quantile"]})
    for feature, observed in support["categorical"].items():
        if row[feature] not in observed:
            unseen.append({"feature": feature, "value": str(row[feature])})
    length_support = support.get("text_length")
    text_length = None if not length_support else {**length_support, "value": len(row.protocol_text),
        "outside_observed_range": not length_support["minimum"] <= len(row.protocol_text) <= length_support["maximum"],
        "outside_central_range": not length_support["lower_quantile"] <= len(row.protocol_text) <= length_support["upper_quantile"]}
    return {"outside_training_support": bool(numeric or unseen), "numeric_out_of_range": numeric, "unseen_categories": unseen,
            "numeric_tail_features": tails, "text_length": text_length,
            "distribution_warning": bool(numeric or unseen or tails or (text_length and text_length["outside_central_range"])),
            "missing_numeric_features": [feature for feature in NUMERIC_FEATURES if pd.isna(row[feature])],
            "method": support["method"], "interpretation": "Descriptive marginal distribution warnings, not an OOD probability or a validity guarantee. Central 98% cutoffs are heuristic and not multiplicity-adjusted. In-range inputs may still differ from training; text length does not measure semantic novelty."}


def normalize_design_phase(value) -> str:
    """Canonical exact phase labels, including slash/pipe combined aliases."""
    from .phase_model import normalize_phase
    text = str(value or "Not reported").strip()
    normalized = [normalize_phase(part) for part in re.split(r"[|/]", text)]
    if normalized and all(normalized):
        return "/".join(normalized)
    # Only known clinical phase aliases are canonicalized. Preserve unknown
    # labels so extrapolation diagnostics retain the supplied category.
    return text


def _features(df: pd.DataFrame) -> pd.DataFrame:
    """Whitelist baseline-like inputs; never retain IDs, statuses, dates or targets."""
    output = pd.DataFrame(index=df.index)
    for name in NUMERIC_FEATURES:
        values = pd.to_numeric(df[name], errors="coerce") if name in df else pd.Series(np.nan, index=df.index)
        output[name] = values.where(np.isfinite(values) & values.ge(0), np.nan)
    for name in CATEGORICAL_FEATURES:
        output[name] = df[name].fillna("Unknown").astype(str) if name in df else "Unknown"
    output["phase"] = output["phase"].map(normalize_design_phase)
    texts = [df[field].fillna("").astype(str) for field in TEXT_FIELDS if field in df]
    output["protocol_text"] = pd.concat(texts, axis=1).agg(" ".join, axis=1) if texts and len(df) else ""
    output["protocol_text"] = output["protocol_text"].str.strip()
    output.loc[~output["protocol_text"].str.contains(r"\w", regex=True), "protocol_text"] = "missingprotocol"
    return output


def _preprocessor(kind: str, config: ExperimentConfig, *, dense=False) -> ColumnTransformer:
    parts = []
    if kind in ("structured", "multimodal"):
        parts.extend([
            ("numeric", Pipeline([("imputer", SimpleImputer(strategy="median", keep_empty_features=True)), ("scaler", StandardScaler())]), NUMERIC_FEATURES),
            ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=not dense), CATEGORICAL_FEATURES),
        ])
    if kind in ("text", "multimodal"):
        parts.append(("text", TfidfVectorizer(max_features=config.max_text_features, ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"(?u)\b\w+\b"), "protocol_text"))
    return ColumnTransformer(parts, remainder="drop", sparse_threshold=0.0 if dense else 1.0)


def _positive_probability(model, X) -> np.ndarray:
    probabilities = model.predict_proba(X)
    classes = list(model.classes_)
    return probabilities[:, classes.index(1)] if 1 in classes else np.zeros(len(X))


def _point_metrics(duration, estimate, labels, probability):
    both_classes = len(np.unique(labels)) == 2
    return {
        "regression": {
            "mae": float(mean_absolute_error(duration, estimate)),
            "rmse": float(np.sqrt(mean_squared_error(duration, estimate))),
            "r2": float(r2_score(duration, estimate)) if len(duration) > 1 and np.ptp(duration) > 0 else None,
        },
        "classification": {
            "auroc": float(roc_auc_score(labels, probability)) if both_classes else None,
            "average_precision": float(average_precision_score(labels, probability)) if both_classes else None,
            "brier": float(brier_score_loss(labels, probability)),
        },
    }


def evaluate_predictions(duration, estimate, labels, probability, bootstrap_samples=200, random_seed=42) -> dict:
    """Paired per-trial bootstrap; undefined discrimination metrics remain null."""
    duration, estimate = np.asarray(duration, dtype=float), np.asarray(estimate, dtype=float)
    labels, probability = np.asarray(labels, dtype=float), np.asarray(probability, dtype=float)
    if any(v.ndim != 1 for v in (duration, estimate, labels, probability)):
        raise ValueError("Metric arrays must be one-dimensional.")
    if not len(duration) or not (len(duration) == len(estimate) == len(labels) == len(probability)):
        raise ValueError("Metric arrays must be non-empty and have equal lengths.")
    if not all(np.isfinite(v).all() for v in (duration, estimate, labels, probability)):
        raise ValueError("Metric arrays must contain only finite values.")
    if not np.isin(labels, [0, 1]).all():
        raise ValueError("Classification labels must be binary 0 or 1.")
    if ((probability < 0) | (probability > 1)).any():
        raise ValueError("Classification probabilities must be between 0 and 1.")
    if not isinstance(bootstrap_samples, int) or not 0 <= bootstrap_samples <= 10000:
        raise ValueError("bootstrap_samples must be an integer between 0 and 10000.")
    labels = labels.astype(int)
    result = _point_metrics(duration, estimate, labels, probability)
    bins = []
    assignment = np.minimum((probability * 10).astype(int), 9)
    for b in range(10):
        mask = assignment == b
        if mask.any():
            bins.append({"lower": b / 10, "upper": (b + 1) / 10, "count": int(mask.sum()), "mean_probability": float(probability[mask].mean()), "observed_fraction": float(labels[mask].mean())})
    result["calibration"] = {"method": "10 equal-width reliability bins; probabilities are not post-hoc calibrated", "bins": bins,
                             "expected_calibration_error": float(sum(v["count"] / len(labels) * abs(v["mean_probability"] - v["observed_fraction"]) for v in bins))}
    result["n"] = len(duration)
    result["positive_count"] = int(labels.sum())
    result["confidence_intervals"] = {"method": "paired trial bootstrap percentile", "level": 0.95, "requested_resamples": bootstrap_samples, "random_seed": random_seed}
    rng = np.random.default_rng(random_seed)
    samples = {key: [] for group in ("regression", "classification") for key in result[group]}
    for _ in range(bootstrap_samples):
        indices = rng.integers(0, len(duration), len(duration))
        values = _point_metrics(duration[indices], estimate[indices], labels[indices], probability[indices])
        for group in values.values():
            for metric, value in group.items():
                if value is not None and np.isfinite(value):
                    samples[metric].append(value)
    for metric, values in samples.items():
        interval = np.quantile(values, [0.025, 0.975]).tolist() if len(values) >= 2 else [None, None]
        result["confidence_intervals"][metric] = {"lower": interval[0], "upper": interval[1], "valid_resamples": len(values)}
    return result


def paired_baseline_comparison(duration, estimate, baseline_estimate, labels, probability, baseline_probability,
                               bootstrap_samples=200, random_seed=42) -> dict:
    """Conditional paired trial-bootstrap differences; negative means lower loss.

    Models are already frozen. This descriptive test comparison must never select
    models, and does not correct comparisons across multiple model branches.
    """
    arrays = [np.asarray(values, dtype=float) for values in
              (duration, estimate, baseline_estimate, labels, probability, baseline_probability)]
    if any(values.ndim != 1 or not np.isfinite(values).all() for values in arrays) or not len(arrays[0]) or len({len(values) for values in arrays}) != 1:
        raise ValueError("Comparison arrays must be equally sized, nonempty finite vectors.")
    if not isinstance(bootstrap_samples, int) or not 0 <= bootstrap_samples <= 10000:
        raise ValueError("bootstrap_samples must be an integer between 0 and 10000.")
    y, prediction, baseline, labels, probability, baseline_probability = arrays
    if not np.isin(labels, [0, 1]).all() or any(((values < 0) | (values > 1)).any() for values in (probability, baseline_probability)):
        raise ValueError("Comparison requires binary labels and probabilities between 0 and 1.")
    losses = {"mae_delta": np.abs(y - prediction) - np.abs(y - baseline),
              "brier_delta": (labels - probability) ** 2 - (labels - baseline_probability) ** 2}
    rng = np.random.default_rng(random_seed)
    draws = {name: [] for name in losses}
    for _ in range(bootstrap_samples):
        indices = rng.integers(0, len(y), len(y))
        for name, values in losses.items():
            draws[name].append(float(values[indices].mean()))
    result = {"reference_model": "median_baseline", "n": len(y), "method": "paired trial bootstrap percentile of model-minus-baseline loss",
              "level": .95, "requested_resamples": bootstrap_samples, "random_seed": random_seed,
              "interpretation": "Negative differences favor the candidate. Conditional on fixed models and independent trials; excludes fitting uncertainty, clustering and multiple-comparison correction. Descriptive test evidence only; never model selection."}
    for name, values in losses.items():
        bounds = np.quantile(draws[name], [.025, .975]).tolist() if len(draws[name]) >= 2 else [None, None]
        result[name] = {"estimate": float(values.mean()), "lower": bounds[0], "upper": bounds[1], "valid_resamples": len(draws[name])}
    return result


class FittedLateFusion:
    """Blend two training-fitted branches without fitting any extra input transform."""

    def __init__(self, structured, text, structured_weight, task):
        if task not in ("regressor", "classifier") or not 0 <= structured_weight <= 1:
            raise ValueError("Fusion requires a supported task and a weight between zero and one.")
        self.structured = structured
        self.text = text
        self.structured_weight = float(structured_weight)
        self.task = task
        self.classes_ = np.array([0, 1])

    def predict(self, X):
        if self.task == "classifier":
            return (self.predict_proba(X)[:, 1] >= .5).astype(int)
        return (self.structured_weight * np.maximum(0, self.structured.predict(X))
                + (1 - self.structured_weight) * np.maximum(0, self.text.predict(X)))

    def predict_proba(self, X):
        probability = (self.structured_weight * _positive_probability(self.structured, X)
                       + (1 - self.structured_weight) * _positive_probability(self.text, X))
        return np.column_stack([1 - probability, probability])


def _fit_late_fusion(models, X_validation, duration_validation, labels_validation):
    pair, selected = {}, {}
    for task, target in (("regressor", duration_validation), ("classifier", labels_validation)):
        candidates = []
        for weight in (.25, .5, .75):
            candidate = FittedLateFusion(models["structured_hist_gradient_boosting"][task], models["text"][task], weight, task)
            loss = (mean_squared_error(target, candidate.predict(X_validation)) if task == "regressor"
                    else brier_score_loss(target, candidate.predict_proba(X_validation)[:, 1]))
            candidates.append((float(loss), weight, candidate))
        _, weight, pair[task] = min(candidates, key=lambda item: (item[0], item[1]))
        selected[task + "_structured_weight"] = weight
    return pair, {**selected, "candidate_structured_weights": [.25, .5, .75],
                  "components": ["structured_hist_gradient_boosting", "text"],
                  "regression_selection": "minimum tuning validation RMSE", "classification_selection": "minimum raw tuning validation Brier",
                  "refit_on_validation": False, "method": "Convex late fusion of already training-fitted branches; weights chosen separately for each task on tuning only."}


def _prediction_diagnostics(nct_ids, duration, estimate, metrics: dict) -> dict:
    """Bound only plotted points; reliability and metrics retain the entire split."""
    total = len(duration)
    indices = np.linspace(0, total - 1, min(total, 200), dtype=int)
    calibration = metrics["calibration"]
    return {
        "scatter": [{"nct_id": str(nct_ids[i]), "actual": float(duration[i]), "predicted": float(estimate[i])} for i in indices],
        "reliability": {"bins": calibration["bins"], "expected_calibration_error": calibration["expected_calibration_error"]},
        "total_n": total, "scatter_n": len(indices),
    }


def _phase_metrics(phases, duration, estimate, labels, probability) -> list[dict]:
    """Descriptive test subgroups; never used for tuning or model recommendation."""
    groups = []
    for phase in sorted(set(phases)):
        selected = phases == phase
        n, positive = int(selected.sum()), int(labels[selected].sum())
        caution = "Exploratory held-out subgroup; registry phase labels do not establish clinical validity."
        if n < 30:
            caution += " Fewer than 30 trials: estimates may be unstable."
        if positive in (0, n):
            caution += " Only one risk class is present; AUROC and average precision are undefined."
        if n < 2 or np.ptp(duration[selected]) == 0:
            caution += " R-squared is undefined without at least two varying outcomes."
        groups.append({"phase": str(phase), "n": n, "positive_count": positive,
                       **_point_metrics(duration[selected], estimate[selected], labels[selected], probability[selected]),
                       "caution": caution})
    return groups


def _fit_advanced_models(X_train, duration_train, labels_train, X_validation, duration_validation, labels_validation, config):
    """Small deterministic structured-only grid. This helper never receives test data."""
    models, selection = {}, {}
    for name, regressor, classifier in (
        ("structured_extra_trees", ExtraTreesRegressor, ExtraTreesClassifier),
        ("structured_random_forest", RandomForestRegressor, RandomForestClassifier),
        ("structured_gradient_boosting", GradientBoostingRegressor, GradientBoostingClassifier),
        ("structured_hist_gradient_boosting", HistGradientBoostingRegressor, HistGradientBoostingClassifier),
    ):
        pair, selected = {}, {}
        common = {"n_estimators": 64, "max_depth": 12, "max_features": "sqrt", "random_state": config.random_seed, "n_jobs": 1}
        if name == "structured_gradient_boosting":
            common = {"n_estimators": 64, "max_depth": 3, "learning_rate": 0.05, "random_state": config.random_seed}
        if name == "structured_hist_gradient_boosting":
            common = {"max_iter": 100, "max_leaf_nodes": 15, "learning_rate": .05,
                      "l2_regularization": 1.0, "early_stopping": False, "random_state": config.random_seed}
        for task, estimator, target in (("regressor", regressor, duration_train), ("classifier", classifier, labels_train)):
            if task == "classifier" and len(np.unique(labels_train)) < 2:
                pair[task] = DummyClassifier(strategy="prior").fit(X_train, labels_train)
                selected[task] = None
                continue
            best, best_score, best_params = None, float("inf"), None
            for leaf in (2, 5):
                params = {**common, "min_samples_leaf": leaf}
                candidate = Pipeline([("preprocess", _preprocessor("structured", config, dense=name == "structured_hist_gradient_boosting")), ("model", estimator(**params))])
                candidate.fit(X_train, target)
                if task == "regressor":
                    score = float(mean_squared_error(duration_validation, np.maximum(0, candidate.predict(X_validation))))
                else:
                    score = float(brier_score_loss(labels_validation, _positive_probability(candidate, X_validation)))
                if score < best_score:
                    best, best_score, best_params = candidate, score, params
            pair[task], selected[task] = best, best_params
        models[name] = pair
        selection[name] = {"regressor_parameters": selected["regressor"], "classifier_parameters": selected["classifier"],
                           "regression_selection": "minimum tuning validation RMSE", "classification_selection": "minimum raw tuning validation Brier",
                           "candidate_min_samples_leaf": [2, 5], "one_class_fallback": selected["classifier"] is None,
                           "refit_on_validation": False}
    return models, selection


def _fit_catboost_models(X_train, duration_train, labels_train, X_validation, duration_validation, labels_validation, config):
    """Opt-in CPU candidate; tuning never sees calibration/test records."""
    config.validate()
    try:
        from catboost import __version__ as catboost_version
        from .models.catboost_compat import CTICatBoostClassifier as CatBoostClassifier, CTICatBoostRegressor as CatBoostRegressor
    except ImportError as exc:
        raise ValueError("CatBoost was requested but is not installed. Install the release requirements first.") from exc
    # Keep the original two candidates and their implicit native defaults exact.
    grid = ([{"depth": depth} for depth in (4, 6)] if config.catboost_search == 'basic' else
            [{"depth": depth, "l2_leaf_reg": l2, "iterations": iterations}
             for depth in (4, 6) for l2 in (3, 10) for iterations in (120, 300)])
    pair, parameters, trials, selected_trials = {}, {}, {}, {}
    for task, estimator, target in (("regressor", CatBoostRegressor, duration_train), ("classifier", CatBoostClassifier, labels_train)):
        trials[task] = []
        selected_trials[task] = None
        if task == "classifier" and len(np.unique(labels_train)) < 2:
            pair[task] = DummyClassifier(strategy="prior").fit(X_train, target)
            parameters[task] = None
            continue
        best, best_score, selected = None, float("inf"), None
        for candidate_parameters in grid:
            params = {"iterations": 120, **candidate_parameters, "learning_rate": .05,
                      "random_seed": config.random_seed, "thread_count": 1,
                      "task_type": "CPU", "verbose": False, "allow_writing_files": False,
                      "loss_function": "RMSE" if task == "regressor" else "Logloss"}
            model = Pipeline([("preprocess", _preprocessor("structured", config, dense=True)),
                              ("model", estimator(**params))])
            model.fit(X_train, target)
            score = (float(mean_squared_error(duration_validation, np.maximum(0, model.predict(X_validation))))
                     if task == "regressor" else float(brier_score_loss(labels_validation, _positive_probability(model, X_validation))))
            trials[task].append({"parameters": params, "effective_parameters": model.named_steps['model'].get_all_params(),
                                 "metric": "rmse" if task == "regressor" else "brier",
                                 "score": float(np.sqrt(score)) if task == "regressor" else score})
            if score < best_score:
                best, best_score, selected = model, score, params
                selected_trials[task] = len(trials[task]) - 1
        pair[task], parameters[task] = best, selected
    return {"structured_catboost": pair}, {"structured_catboost": {
        "regressor_parameters": parameters["regressor"], "classifier_parameters": parameters["classifier"],
        "search_mode": config.catboost_search, "candidate_configurations": grid, "trials": trials,
        "selected_trial_indices": selected_trials, "selection_split": "validation",
        "selection_rows": len(X_validation), "training_rows": len(X_train),
        "tie_breaker": "first candidate in declared order", "catboost_version": catboost_version,
        "candidate_depths": [4, 6], "regression_selection": "minimum tuning validation RMSE",
        "classification_selection": "minimum raw tuning validation Brier", "refit_on_validation": False,
        "native_task": "CPU", "one_class_fallback": parameters["classifier"] is None,
        "preprocessing": "Training-fitted numeric imputation/scaling and categorical one-hot encoding; no test fitting.",
    }}


def _fit_pci(X: pd.DataFrame) -> dict:
    medians = X[NUMERIC_FEATURES].median().fillna(0)
    imputed = X[NUMERIC_FEATURES].fillna(medians)
    return {"method": "equal-weight training-fitted min-max complexity index", "features": NUMERIC_FEATURES,
            "median": medians.to_dict(), "minimum": imputed.min().to_dict(), "maximum": imputed.max().to_dict(),
            "weights": {name: 1 / len(NUMERIC_FEATURES) for name in NUMERIC_FEATURES},
            "constant_component_value": 0.0, "clip_to_training_range": True,
            "interpretation": "Descriptive cohort-relative index, not a validated probability or clinical score. Missing values use training medians; constant training components contribute zero."}


def _pci_values(X: pd.DataFrame, fitted: dict) -> list[dict]:
    values = []
    for _, row in X.iterrows():
        components = {}
        for key in NUMERIC_FEATURES:
            value = fitted["median"][key] if pd.isna(row[key]) else float(row[key])
            span = fitted["maximum"][key] - fitted["minimum"][key]
            components[key] = float(np.clip((value - fitted["minimum"][key]) / span, 0, 1)) if span > 0 else 0.0
        values.append({"score": float(100 * sum(components[k] * fitted["weights"][k] for k in components)), "components": components, "method": fitted["method"]})
    return values


@threadpool_limits.wrap(limits=1)
def train_experiment(df: pd.DataFrame, output_dir: str | Path, source_metadata: dict | None = None, *, config: ExperimentConfig | None = None) -> dict:
    """Train comparable models and write an auditable experiment directory.

    Raises ValueError for insufficient/invalid cohorts. No artifact is written
    before fitting succeeds. A failed attempt produces an explicit error.json.
    """
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / "manifest.json").exists() or (directory / "models.joblib").exists():
        raise ValueError("Experiment directory already contains an artifact; use a new output directory.")
    config, metadata = config or ExperimentConfig(), dict(source_metadata or {})
    run_id = str(uuid.uuid4())
    try:
        config.validate()
        cohort, exclusions = prepare_cohort(df, metadata)
        exclusions.to_csv(directory / "cohort_exclusions.csv", index=False)
        if len(cohort) < 30:
            raise ValueError(f"At least 30 eligible completed trials with known ACTUAL outcomes are required; found {len(cohort)}. Bundled samples are software fixtures and cannot support research training.")
        splits = temporal_split(cohort, config)
        splits["purged"].to_csv(directory / "temporal_exclusions.csv", index=False)
        if len(splits["train"]) < 12 or min(len(splits[s]) for s in ("validation", "test")) < 3:
            raise ValueError("Temporal splitting and outcome-availability purging require at least 12 training and 3 validation/test trials; use a larger cohort with sufficient follow-up.")
        splits["validation"], splits["calibration"], validation_partition = partition_validation(splits["validation"])
        threshold = float(splits["train"]["duration_days"].quantile(config.prolonged_quantile))
        X = {name: _features(splits[name]) for name in ("train", "validation", "calibration", "test")}
        duration = {name: splits[name].duration_days.to_numpy(float) for name in X}
        labels = {name: (values > threshold).astype(int) for name, values in duration.items()}
        models, selection = {}, {}
        baseline_reg = DummyRegressor(strategy="median").fit(X["train"], duration["train"])
        baseline_cls = DummyClassifier(strategy="prior", random_state=config.random_seed).fit(X["train"], labels["train"])
        models["median_baseline"] = {"regressor": baseline_reg, "classifier": baseline_cls}
        selection["median_baseline"] = {"regression": "training duration median", "classification": "training prolonged prevalence"}
        for kind in ("structured", "text", "multimodal"):
            best_reg, reg_score, best_alpha = None, float("inf"), None
            for alpha in (1.0, 10.0, 100.0):
                reg = Pipeline([("preprocess", _preprocessor(kind, config)), ("model", Ridge(alpha=alpha, solver="lsqr"))])
                reg.fit(X["train"], duration["train"])
                score = float(mean_squared_error(duration["validation"], np.maximum(0, reg.predict(X["validation"]))))
                if score < reg_score:
                    best_reg, reg_score, best_alpha = reg, score, alpha
            best_cls, cls_score, best_c = None, float("inf"), None
            if len(np.unique(labels["train"])) < 2:
                best_cls = DummyClassifier(strategy="prior").fit(X["train"], labels["train"])
            else:
                for c in (0.1, 1.0, 10.0):
                    cls = Pipeline([("preprocess", _preprocessor(kind, config)), ("model", LogisticRegression(C=c, max_iter=2000, solver="liblinear", random_state=config.random_seed))])
                    cls.fit(X["train"], labels["train"])
                    score = float(brier_score_loss(labels["validation"], _positive_probability(cls, X["validation"])))
                    if score < cls_score:
                        best_cls, cls_score, best_c = cls, score, c
            models[kind] = {"regressor": best_reg, "classifier": best_cls}
            selection[kind] = {"ridge_alpha": best_alpha, "logistic_C": best_c, "regression_selection": "minimum tuning validation RMSE", "classification_selection": "minimum raw tuning validation Brier", "one_class_fallback": best_c is None}
        if config.enable_advanced_models:
            advanced, advanced_selection = _fit_advanced_models(X["train"], duration["train"], labels["train"],
                X["validation"], duration["validation"], labels["validation"], config)
            models.update(advanced)
            selection.update(advanced_selection)
            models["multimodal_late_fusion"], selection["multimodal_late_fusion"] = _fit_late_fusion(
                models, X["validation"], duration["validation"], labels["validation"])
        if config.enable_catboost:
            catboost_models, catboost_selection = _fit_catboost_models(
                X["train"], duration["train"], labels["train"],
                X["validation"], duration["validation"], labels["validation"], config)
            models.update(catboost_models)
            selection.update(catboost_selection)
        # Select before any test predictions/metrics exist. Ties use model name.
        validation_brier = {name: float(brier_score_loss(labels["validation"], _positive_probability(model["classifier"], X["validation"])))
                            for name, model in models.items()}
        recommended_model = min(validation_brier, key=lambda name: (validation_brier[name], name))
        recommendation = {"model_name": recommended_model, "metric": "brier", "split": "validation", "value": validation_brier[recommended_model],
                          "split_role": "tuning", "probability_semantics": "raw",
                          "reason": "Lowest raw tuning validation Brier score among enabled fitted models; exact ties use model name. Calibration/test data are not used. This risk recommendation does not establish the best duration regressor or prospective clinical validity."}
        validation_rmse = {name: float(np.sqrt(mean_squared_error(duration["validation"], np.maximum(0, model["regressor"].predict(X["validation"])))))
                           for name, model in models.items()}
        duration_model = min(validation_rmse, key=lambda name: (validation_rmse[name], name))
        duration_recommendation = {"model_name": duration_model, "metric": "rmse", "split": "validation", "split_role": "tuning",
                                   "value": validation_rmse[duration_model],
                                   "reason": "Lowest tuning validation RMSE; ties use model name. Duration and prolonged-risk recommendations are independent; no calibration or test selection."}
        pci = _fit_pci(X["train"])
        training_support = _fit_training_support(X["train"])
        uncertainty, calibration = {}, {}
        for name, model in models.items():
            if len(X["calibration"]):
                calibration_estimates = np.maximum(0, model["regressor"].predict(X["calibration"]))
                uncertainty[name] = {"status": "available", "method": "split conformal absolute duration residuals",
                    "split": "calibration", **split_conformal_quantile(np.abs(duration["calibration"] - calibration_estimates), config.uncertainty_alpha),
                    "interpretation": "Nominal marginal coverage relies on exchangeability; chronological distribution shift can invalidate it. Calibration is not test evidence."}
                calibration_probability = _positive_probability(model["classifier"], X["calibration"])
            else:
                uncertainty[name] = {"status": "unavailable", "method": "split conformal absolute duration residuals", "split": "calibration",
                    "n": 0, "alpha": config.uncertainty_alpha, "nominal_coverage": 1 - config.uncertainty_alpha,
                    "rank": None, "residual_quantile_days": None, "bounded": False, "reason": validation_partition["reason"]}
                calibration_probability = np.array([], dtype=float)
            calibration[name] = _fit_probability_calibration(calibration_probability, labels["calibration"], config)
        metrics, diagnostics, prediction_frames = {}, {}, []
        for name, model in models.items():
            metrics[name], diagnostics[name] = {}, {}
            for split in ("validation", "calibration", "test"):
                if not len(X[split]):
                    continue
                estimates = np.maximum(0, model["regressor"].predict(X[split]))
                probability = _positive_probability(model["classifier"], X[split])
                metrics[name][split] = evaluate_predictions(duration[split], estimates, labels[split], probability, config.bootstrap_samples, config.random_seed)
                metrics[name][split]["probability_semantics"] = "raw"
                metrics[name][split]["split_role"] = "tuning" if split == "validation" else split
                calibrated = _calibrated_probability(probability, calibration[name]) if split != "validation" else None
                if calibrated is not None:
                    calibrated_metrics = evaluate_predictions(duration[split], estimates, labels[split], calibrated, 0, config.random_seed)
                    metrics[name][split]["calibrated_classification"] = calibrated_metrics["classification"]
                    metrics[name][split]["calibrated_reliability"] = {**calibrated_metrics["calibration"],
                        "method": "10 equal-width reliability bins of sigmoid-calibrated probabilities",
                        "interpretation": "Calibration-fitting cohort diagnostics; in-sample for the sigmoid." if split == "calibration" else "Untouched test cohort; calibration fitted only on reserved validation groups."}
                metrics[name][split]["confidence_intervals"]["interpretation"] = (
                    "Descriptive resampling intervals on tuning data; selection optimism is not corrected and coverage is not guaranteed."
                    if split == "validation" else "Calibration-fitting cohort, not an untouched test; no calibration-selection correction."
                    if split == "calibration" else "Conditional on the fitted model and independent-trial resampling; excludes model-fitting uncertainty.")
                diagnostics[name][split] = _prediction_diagnostics(splits[split].nct_id.to_numpy(), duration[split], estimates, metrics[name][split])
                if split == "test":
                    metrics[name][split]["comparison_to_baseline"] = paired_baseline_comparison(
                        duration[split], estimates, np.maximum(0, baseline_reg.predict(X[split])),
                        labels[split], probability, _positive_probability(baseline_cls, X[split]), config.bootstrap_samples, config.random_seed)
                    metrics[name][split]["by_phase"] = _phase_metrics(X[split]["phase"].to_numpy(), duration[split], estimates, labels[split], probability)
                    state = uncertainty[name]
                    if state["status"] == "available":
                        quantile = state["residual_quantile_days"]
                        covered = np.ones(len(estimates), dtype=bool) if quantile is None else np.abs(duration[split] - estimates) <= quantile
                        state["test_diagnostics"] = {"n": len(estimates), "covered_count": int(covered.sum()),
                            "observed_coverage": float(covered.mean()), "mean_interval_width_days": None if quantile is None else float((estimates + quantile - np.maximum(0, estimates - quantile)).mean()),
                            "interpretation": "Descriptive observed held-out coverage; does not guarantee future coverage. Infinite intervals trivially cover every finite outcome."}
                        metrics[name][split]["duration_uncertainty"] = state["test_diagnostics"]
                prediction_frames.append(pd.DataFrame({"nct_id": splits[split].nct_id.to_numpy(), "split": split, "model_name": name,
                    "actual_duration_days": duration[split], "predicted_duration_days": estimates, "actual_prolonged": labels[split],
                    "prolonged_probability": probability, "calibrated_prolonged_probability": calibrated if calibrated is not None else np.nan,
                    "probability_semantics": "raw", "prolonged_threshold_days": threshold, "pci": [p["score"] for p in _pci_values(X[split], pci)]}))
        input_digest = hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()
        warning = "Research decision support only. Completed-only cohort creates follow-up/selection bias; minimum sample guard is not evidence of scientific validity."
        if metadata.get("is_fixture") or metadata.get("fixture"):
            warning += " SOFTWARE TEST FIXTURE: these generated or bundled records and metrics are not scientific evidence."
        if not metadata.get("baseline_provenance"):
            warning += " RETROSPECTIVE SNAPSHOT: baseline feature availability is unverified; post-start registry updates and narrative text may leak outcome information. Do not claim prospective validation."
        manifest = {
            "run_id": run_id, "status": "completed", "artifact_version": ARTIFACT_VERSION, "task": "duration",
            "created_at": datetime.now(timezone.utc).isoformat(), "source_metadata": metadata,
            "dataset_id": metadata.get("dataset_id"), "input_sha256": input_digest,
            "config": asdict(config), "pipeline_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__, "scikit_learn": sklearn.__version__, "joblib": joblib.__version__},
            "cohort": {"input_rows": len(df), "eligible_rows": len(cohort), "excluded_rows": len(exclusions), "temporally_purged_rows": len(splits["purged"]), "outcomes": "completed actual completion minus start date in days"},
            "splits": {name: {"rows": len(splits[name]), "role": "tuning" if name == "validation" else name,
                "start_date_min": splits[name].start_date.min().isoformat() if len(splits[name]) else None,
                "start_date_max": splits[name].start_date.max().isoformat() if len(splits[name]) else None,
                "positive_count": int(labels[name].sum()), "nct_ids": splits[name].nct_id.tolist()} for name in X},
            "validation_partition": validation_partition,
            "temporal_cutoffs": {"validation": splits["validation_cutoff"].isoformat(), "calibration": validation_partition["calibration_cutoff"],
                "test": splits["test_cutoff"].isoformat(), "policy": "Whole start-date groups. Training outcomes precede original validation cutoff; all original validation outcomes precede test cutoff. Earlier retained validation tunes; later groups calibrate when sufficient. No refit on validation or calibration. Tuning outcomes are available at the test cutoff, not necessarily the calibration start date."},
            "target": {"duration_unit": "days", "prolonged_quantile": config.prolonged_quantile, "prolonged_threshold_days": threshold, "positive_rule": "duration_days > training quantile; ties are non-prolonged"},
            "features": {"numeric": NUMERIC_FEATURES, "categorical": CATEGORICAL_FEATURES, "text": TEXT_FIELDS, "excluded": ["nct_id", "status", "start_date", "completion_date", "duration_days", "prolonged"]},
            "models": {name: {**MODEL_METADATA[name], "selection": selection[name], "metrics": metrics[name], "diagnostics": diagnostics[name],
                "uncertainty": uncertainty[name], "calibration": calibration[name]["metadata"]} for name in models},
            "uncertainty": {"method": "split conformal absolute duration residuals", "alpha": config.uncertainty_alpha,
                "nominal_coverage": 1 - config.uncertainty_alpha, "minimum_calibration_rows": MIN_CALIBRATION_ROWS,
                "available": validation_partition["calibration_available"], "models": uncertainty,
                "interpretation": "Exchangeability is required for nominal marginal coverage; chronological distribution shift can invalidate coverage. Null bounds indicate unavailable or mathematically unbounded intervals; inspect status and bounded."},
            "training_support": training_support,
            "recommended_model": recommended_model, "recommendation": recommendation,
            "recommended_duration_model": duration_model, "duration_recommendation": duration_recommendation,
            "pci": pci, "warning": warning,
            "limitations": ["Tuning validation metrics are optimistic after hyperparameter and raw model selection; test metrics are held out. Calibration diagnostics are in-sample for the calibration transform.", "Bootstrap intervals are conditional on the fitted models and assume independent trials; they exclude model-fitting uncertainty and sponsor/site clustering.", "Primary probabilities and classification metrics remain raw. Separate sigmoid-calibrated probabilities/metrics exist only with at least 10 calibration rows and two labels of each class; calibration never selects models.", "Split-conformal nominal marginal coverage assumes exchangeability, which chronological shift may violate. Finite-sample ranks beyond calibration size produce unbounded intervals; descriptive test coverage is not a future guarantee.", "Training range/category indicators describe extrapolation and cannot estimate an OOD probability or guarantee validity.", "Nonlinear structured branches and linear modalities share retained cohorts, but have different capacities. Additional complexity does not guarantee improved performance.", "Tree impurity importances summarize global behavior, may favor high-cardinality features, and are neither trial-specific SHAP values nor causal evidence.", "Text uses TF-IDF; BioBERT, survival, and SHAP are optional separate capabilities and are not claimed as executed.", "Completed-only analysis cannot estimate censored/ongoing trial outcomes without a separate survival cohort.", "Per-phase test metrics are exploratory; small or one-class subgroups may be unstable or undefined. Scatter plots retain at most 200 chronological rows; metrics and reliability bins use every retained row."],
            "files": {"artifact": "models.joblib", "metrics": "metrics.json", "predictions": "held_out_predictions.csv", "cohort_exclusions": "cohort_exclusions.csv", "temporal_exclusions": "temporal_exclusions.csv"},
        }
        pd.concat(prediction_frames, ignore_index=True).to_csv(directory / "held_out_predictions.csv", index=False)
        _json_write(directory / "metrics.json", metrics)
        joblib.dump({"artifact_version": ARTIFACT_VERSION, "task": "duration", "run_id": run_id, "models": models, "pci": pci,
                    "threshold_days": threshold, "source_metadata": metadata, "input_sha256": input_digest,
                    "pipeline_source_sha256": manifest["pipeline_source_sha256"], "training_support": training_support,
                    "uncertainty": uncertainty, "calibration": calibration, "warning": warning}, directory / "models.joblib")
        _json_write(directory / "manifest.json", manifest)
        if (directory / "error.json").exists():
            (directory / "error.json").unlink()
        return manifest
    except Exception as exc:
        _json_write(directory / "error.json", {"run_id": run_id, "status": "failed", "error_type": type(exc).__name__, "error": str(exc), "source_metadata": metadata})
        raise


def _linear_explanation(model, X: pd.DataFrame, units: str) -> dict:
    if not isinstance(model, Pipeline) or not hasattr(model.named_steps["model"], "coef_"):
        return {"method": "constant training baseline", "units": units, "features": [], "note": "No feature-specific attribution is defined for this constant predictor."}
    transformer, fitted = model.named_steps["preprocess"], model.named_steps["model"]
    transformed = transformer.transform(X)
    vector = transformed.toarray()[0] if hasattr(transformed, "toarray") else np.asarray(transformed)[0]
    coef = np.asarray(fitted.coef_).reshape(-1)
    contribution = vector * coef
    names = transformer.get_feature_names_out()
    order = np.argsort(-np.abs(contribution))[:12]
    return {"method": "linear feature contributions", "units": units,
            "intercept": float(np.asarray(fitted.intercept_).reshape(-1)[0]), "sum_all_contributions": float(contribution.sum()),
            "features": [{"feature": str(names[i]), "contribution": float(contribution[i])} for i in order if contribution[i] != 0],
            "note": "Contribution = transformed feature value × fitted coefficient. Top 12 shown; not SHAP and not causal evidence. Classification contributions are log-odds, not probability percentage points."}


def _model_explanation(model, X: pd.DataFrame, units: str) -> dict:
    if isinstance(model, Pipeline) and type(model.named_steps["model"]).__module__ in {"catboost.core", "src.clinical_trial_intelligence.models.catboost_compat"}:
        from catboost import Pool
        transformer, fitted = model.named_steps["preprocess"], model.named_steps["model"]
        transformed = transformer.transform(X)
        values = transformed.toarray() if hasattr(transformed, "toarray") else np.asarray(transformed)
        shap = np.asarray(fitted.get_feature_importance(Pool(values), type="ShapValues"))[0]
        names = transformer.get_feature_names_out()
        contributions, intercept = shap[:-1], float(shap[-1])
        order = np.argsort(-np.abs(contributions), kind="stable")
        return {"method": "TreeSHAP", "scope": "local", "units": units,
                "intercept": intercept, "sum_all_contributions": float(contributions.sum()),
                "features": [{"feature": str(names[i]), "contribution": float(contributions[i])} for i in order],
                "note": "Native CatBoost TreeSHAP on the actual fitted pipeline. All contributions shown. Classification units are raw log-odds; duration units precede nonnegative clipping. Attribution is not causal evidence."}
    if isinstance(model, FittedLateFusion):
        return {"method": "weighted late fusion", "scope": "model", "units": "days" if model.task == "regressor" else "probability",
                "features": [], "components": [
                    {"model_name": "structured_hist_gradient_boosting", "weight": model.structured_weight,
                     "prediction": float(np.maximum(0, model.structured.predict(X))[0]) if model.task == "regressor" else float(_positive_probability(model.structured, X)[0])},
                    {"model_name": "text", "weight": 1 - model.structured_weight,
                     "prediction": float(np.maximum(0, model.text.predict(X))[0]) if model.task == "regressor" else float(_positive_probability(model.text, X)[0])}],
                "note": "Weighted predictions of independently training-fitted branches. Weights selected on tuning only. Component outputs are not feature attributions, SHAP or causal evidence."}
    if isinstance(model, Pipeline) and isinstance(model.named_steps["model"], (HistGradientBoostingRegressor, HistGradientBoostingClassifier)):
        return {"method": "histogram gradient boosting; local attribution unavailable", "scope": "model", "units": units, "features": [],
                "note": "No native impurity or local feature attribution is provided for this branch. No substitute SHAP values or causal explanations are fabricated."}
    if isinstance(model, Pipeline) and hasattr(model.named_steps["model"], "feature_importances_"):
        importance = model.named_steps["model"].feature_importances_
        names = model.named_steps["preprocess"].get_feature_names_out()
        order = np.argsort(-importance, kind="stable")[:12]
        return {"method": "global impurity feature importance", "scope": "global", "units": "normalized impurity decrease",
                "features": [{"feature": str(names[i]), "importance": float(importance[i])} for i in order],
                "note": "Top 12 training-fitted tree impurity importances. Global model summary, not a local trial explanation, not SHAP, and not causal evidence. Importances may favor high-cardinality features; they do not add to this trial's probability or duration."}
    explanation = _linear_explanation(model, X, units)
    return {**explanation, "scope": "local" if explanation["method"] == "linear feature contributions" else "global"}


@threadpool_limits.wrap(limits=1)
def predict_trial(row: dict, artifact_dir: str | Path, model_name: str = "multimodal") -> dict:
    unavailable = {"status": "unavailable", "probability": None, "raw_probability": None, "calibrated_probability": None,
                   "probability_semantics": "raw", "duration_days": None, "predicted_duration_days": None,
                   "model_name": model_name, "explanation": None, "uncertainty": {"status": "unavailable", "lower_days": None, "upper_days": None},
                   "calibration": {"status": "unavailable"}, "extrapolation": None}
    directory = Path(artifact_dir)
    if not (directory / "models.joblib").is_file() or not (directory / "manifest.json").is_file():
        return {**unavailable, "reason": "No completed compatible trained artifact is available."}
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        artifact = joblib.load(directory / "models.joblib")
        if artifact.get("artifact_version") != ARTIFACT_VERSION or artifact.get("task") != "duration" or model_name not in artifact["models"]:
            return {**unavailable, "reason": "Artifact version or requested model is incompatible."}
        if (manifest.get("status") != "completed" or manifest.get("artifact_version") != ARTIFACT_VERSION
                or manifest.get("task") != "duration"
                or manifest.get("run_id") != artifact.get("run_id")
                or manifest.get("source_metadata") != artifact.get("source_metadata")
                or manifest.get("input_sha256") != artifact.get("input_sha256")
                or manifest.get("pipeline_source_sha256") != artifact.get("pipeline_source_sha256")):
            return {**unavailable, "reason": "Artifact and manifest do not match; rerun the experiment."}
        X = _features(pd.DataFrame([row]))
        model = artifact["models"][model_name]
        duration = max(0.0, float(model["regressor"].predict(X)[0]))
        probability = float(_positive_probability(model["classifier"], X)[0])
        calibrated = _calibrated_probability(np.array([probability]), artifact["calibration"][model_name])
        calibrated_probability = float(calibrated[0]) if calibrated is not None else None
        if not np.isfinite(duration) or not np.isfinite(probability) or (calibrated_probability is not None and not np.isfinite(calibrated_probability)):
            return {**unavailable, "reason": "Artifact produced a non-finite prediction."}
        identifier = str(row.get("nct_id", "")).strip()
        membership = next((split for split in ("train", "validation", "calibration", "test")
                           if identifier in manifest.get("splits", {}).get(split, {}).get("nct_ids", [])),
                          "not_in_retained_splits")
        scope = {
            "train": "In-sample estimate for a trial used to fit the model; not held-out evidence.",
            "validation": "Validation estimate for a trial used in hyperparameter selection; not an untouched test result.",
            "calibration": "Calibration cohort estimate; this outcome fitted duration uncertainty and, when supported, probability calibration. Not an untouched test result.",
            "test": "Held-out test estimate; the source-provenance and completed-only cohort limitations still apply.",
            "not_in_retained_splits": "Trial is outside retained training/tuning/calibration/test splits; no validation claim is established for this record.",
        }[membership]
        uncertainty = dict(artifact["uncertainty"][model_name])
        quantile = uncertainty["residual_quantile_days"]
        uncertainty.update({"lower_days": max(0.0, duration - quantile) if quantile is not None else None,
                            "upper_days": duration + quantile if quantile is not None else None,
                            "prediction_scope": scope})
        return {"status": "available", "run_id": artifact["run_id"], "model_name": model_name, "probability": probability,
                "raw_probability": probability, "calibrated_probability": calibrated_probability, "probability_semantics": "raw",
                "uncertainty": uncertainty, "calibration": artifact["calibration"][model_name]["metadata"],
                "extrapolation": _extrapolation(X, artifact["training_support"]),
                "duration_days": duration, "predicted_duration_days": duration, "prolonged_threshold_days": artifact["threshold_days"],
                "cohort_membership": membership, "prediction_scope": scope,
                "explanation": _model_explanation(model["classifier"], X, "log-odds"),
                "duration_explanation": _model_explanation(model["regressor"], X, "days (before nonnegative clipping)"),
                "pci": _pci_values(X, artifact["pci"])[0], "warning": artifact["warning"]}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, EOFError, ImportError, pickle.UnpicklingError) as exc:
        return {**unavailable, "reason": f"Artifact could not be used: {type(exc).__name__}: {exc}"}


def list_experiments(root: str | Path) -> list[dict]:
    """Read manifests without deserializing executable model files."""
    records = []
    for path in Path(root).glob("*/manifest.json"):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)
