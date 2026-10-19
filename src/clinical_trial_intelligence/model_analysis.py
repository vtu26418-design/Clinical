"""Recompute descriptive accuracy from saved predictions, without loading models.

Only trusted, operator-selected completed experiment directories are supported.
No estimator deserialization or training is performed. Outputs are deterministic.
"""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


def _read_json(path: Path) -> dict:
    def invalid(value):
        raise ValueError(f"Non-finite JSON constant in {path.name}: {value}")
    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            invalid(value)
        return parsed
    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=invalid, parse_float=finite_float)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _file(directory: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or Path(name).name != name or "\\" in name:
        raise ValueError("Artifact file names must be local basenames")
    result = directory / name
    if result.resolve().parent != directory.resolve():
        raise ValueError("Artifact file must stay inside the experiment directory")
    if not result.is_file():
        raise ValueError(f"Missing required file: {name}")
    return result


def _number(row: dict, column: str, low=None, high=None) -> float:
    try:
        value = float(row[column])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"Missing or invalid {column}") from None
    if not math.isfinite(value) or (low is not None and value < low) or (high is not None and value > high):
        raise ValueError(f"Out-of-range or non-finite {column}")
    return value


def _role(name: str, definition: dict) -> str:
    return str(definition.get("role") or {"validation": "tuning", "test": "test", "calibration": "calibration", "train": "train"}.get(name, name))


def _load(directory) -> tuple[dict, list[dict], dict]:
    directory = Path(directory)
    manifest_name = "manifest.json" if (directory / "manifest.json").is_file() else "phase_manifest.json"
    manifest_path = _file(directory, manifest_name)
    manifest = _read_json(manifest_path)
    if manifest.get("status") != "completed":
        raise ValueError("Only completed experiment manifests can be analyzed")
    task = manifest.get("task", "duration")
    if task not in {"duration", "phase"}:
        raise ValueError("Unsupported experiment task")
    prefix = "phase_" if task == "phase" else ""
    for name in ("files", "models", "target", "source_metadata", "cohort"):
        if not isinstance(manifest.get(name, {}), dict):
            raise ValueError(f"Manifest {name} must be an object")
    if not isinstance(manifest.get("limitations", []), list):
        raise ValueError("Manifest limitations must be a list")
    files = manifest.get("files", {})
    predictions_path = _file(directory, files.get("predictions", prefix + "held_out_predictions.csv"))
    metrics_path = _file(directory, files.get("metrics", prefix + "metrics.json"))
    _read_json(metrics_path)  # Parse for integrity; never use stored performance claims.
    splits = manifest.get("splits")
    if not isinstance(splits, dict) or not splits:
        raise ValueError("Manifest must declare split memberships")
    memberships = {}
    seen_ids = set()
    for split, definition in splits.items():
        if not isinstance(definition, dict):
            raise ValueError("Manifest split definition must be an object")
        ids = definition.get("nct_ids")
        if not isinstance(ids, list) or any(not isinstance(x, str) or not x.strip() for x in ids):
            raise ValueError("Manifest split must declare nonempty string nct_ids")
        if len(ids) != len(set(ids)) or seen_ids.intersection(ids):
            raise ValueError("Duplicated IDs within or across manifest splits")
        if definition.get("rows") != len(ids):
            raise ValueError("Manifest split count differs from membership")
        seen_ids.update(ids)
        memberships[split] = set(ids)
    labels = manifest.get("labels", [])
    if task == "phase" and (not isinstance(labels, list) or not labels or any(not isinstance(x, str) or not x for x in labels) or len(set(labels)) != len(labels)):
        raise ValueError("Phase manifest must declare unique string labels")
    with predictions_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Missing or duplicate prediction CSV columns")
        rows = list(reader)
    if not rows:
        raise ValueError("No held-out prediction rows available")
    groups = defaultdict(set)
    targets = {}
    parsed = []
    for row in rows:
        if None in row:
            raise ValueError("Malformed prediction CSV row")
        split, model, trial = (row.get(k, "") for k in ("split", "model_name", "nct_id"))
        if not model or not trial or split not in memberships:
            raise ValueError("Missing model/ID or unknown prediction split")
        if _role(split, splits[split]) == "train":
            raise ValueError("Training rows must not appear in held-out predictions")
        if trial not in memberships[split]:
            raise ValueError("Prediction ID is outside its manifest split membership")
        if trial in groups[(model, split)]:
            raise ValueError("Duplicated prediction ID for model/split")
        groups[(model, split)].add(trial)
        item = {"nct_id": trial, "split": split, "model_name": model}
        if task == "duration":
            item.update({key: _number(row, key, 0) for key in ("actual_duration_days", "predicted_duration_days")})
            actual = _number(row, "actual_prolonged", 0, 1)
            if actual not in {0, 1}:
                raise ValueError("actual_prolonged must be binary 0/1")
            item["actual_prolonged"] = int(actual)
            item["prolonged_probability"] = _number(row, "prolonged_probability", 0, 1)
            threshold = _number(row, "prolonged_threshold_days", 0)
            if int(item["actual_duration_days"] > threshold) != actual:
                raise ValueError("Duration label contradicts prolonged threshold")
            manifest_threshold = manifest.get("target", {}).get("prolonged_threshold_days")
            if manifest_threshold is not None and threshold != float(manifest_threshold):
                raise ValueError("Prediction threshold differs from manifest target")
            item["prolonged_threshold_days"] = threshold
            if row.get("probability_semantics", "raw") != "raw":
                raise ValueError("Primary prolonged_probability must declare raw semantics")
            calibrated = row.get("calibrated_prolonged_probability", "")
            item["calibrated_prolonged_probability"] = _number(row, "calibrated_prolonged_probability", 0, 1) if calibrated else None
            target = (item["actual_duration_days"], actual, threshold)
        else:
            actual, predicted = row.get("actual_phase"), row.get("predicted_phase")
            if actual not in labels or predicted not in labels:
                raise ValueError("Unknown actual or predicted phase label")
            probabilities = [_number(row, "probability_" + label, 0, 1) for label in labels]
            if not math.isclose(sum(probabilities), 1.0, abs_tol=1e-6):
                raise ValueError("Phase probabilities must sum to one")
            if probabilities[labels.index(predicted)] < max(probabilities) - 1e-10:
                raise ValueError("Predicted phase contradicts maximum class probability")
            item.update(actual_phase=actual, predicted_phase=predicted, probabilities=probabilities)
            target = actual
        key = (split, trial)
        if key in targets and targets[key] != target:
            raise ValueError("Inconsistent actual targets across models")
        targets[key] = target
        parsed.append(item)
    model_names = set(manifest.get("models", {})) or {model for model, _ in groups}
    if {model for model, _ in groups} != model_names:
        raise ValueError("Prediction models differ from manifest models")
    for model in model_names:
        for split, ids in memberships.items():
            if _role(split, splits[split]) != "train" and ids and groups.get((model, split), set()) != ids:
                raise ValueError("Incomplete prediction membership for model/split")
    for key, ids in groups.items():
        if ids != memberships[key[1]]:
            raise ValueError("Incomplete prediction membership for model/split")
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (manifest_path, predictions_path, metrics_path)}
    return manifest, sorted(parsed, key=lambda r: (r["model_name"], r["split"], r["nct_id"])), hashes


def _ratio(numerator, denominator):
    return float(numerator / denominator) if denominator else None


def _classification(actual: list, predicted: list, labels: list) -> dict:
    matrix = [[sum(a == left and p == right for a, p in zip(actual, predicted)) for right in labels] for left in labels]
    support = [sum(row) for row in matrix]
    precisions, recalls, f1s = [], [], []
    per_class = []
    for i, label in enumerate(labels):
        tp = matrix[i][i]
        predicted_n = sum(row[i] for row in matrix)
        precision, recall = _ratio(tp, predicted_n), _ratio(tp, support[i])
        f1 = _ratio(2 * tp, support[i] + predicted_n)
        per_class.append({"label": label, "support": support[i], "precision": precision, "recall": recall, "f1": f1})
        if support[i] or predicted_n:
            # Macro convention: union of actual/predicted labels, zero for undefined precision/recall.
            precisions.append(precision or 0.0)
            recalls.append(recall or 0.0)
            f1s.append(f1 or 0.0)
    supported_recalls = [matrix[i][i] / n for i, n in enumerate(support) if n]
    return {
        "accuracy": sum(a == p for a, p in zip(actual, predicted)) / len(actual),
        "balanced_accuracy": float(np.mean(supported_recalls)) if len(supported_recalls) > 1 else None,
        "macro_precision": float(np.mean(precisions)), "macro_recall": float(np.mean(recalls)),
        "macro_f1": float(np.mean(f1s)), "labels": labels, "confusion_matrix": matrix, "per_class": per_class,
    }


def _reliability(actual, probabilities) -> dict:
    bins = []
    for i in range(10):
        indexes = [j for j, p in enumerate(probabilities) if min(int(p * 10), 9) == i]
        if indexes:
            bins.append({"lower": i / 10, "upper": (i + 1) / 10, "count": len(indexes),
                         "mean_probability": float(np.mean([probabilities[j] for j in indexes])),
                         "observed_fraction": float(np.mean([actual[j] for j in indexes]))})
    return {"method": "10 equal-width bins; descriptive reliability, not calibration fitting",
            "bins": bins, "expected_calibration_error": sum(b["count"] * abs(b["mean_probability"] - b["observed_fraction"]) for b in bins) / len(actual)}


def _binary(actual, probabilities) -> dict:
    result = _classification(actual, [int(p >= 0.5) for p in probabilities], [0, 1])
    positive = result["per_class"][1]
    result.update(precision=positive["precision"], recall=positive["recall"], f1=positive["f1"], threshold=0.5,
                  positive_count=sum(actual), auroc=float(roc_auc_score(actual, probabilities)) if len(set(actual)) == 2 else None,
                  average_precision=float(average_precision_score(actual, probabilities)) if len(set(actual)) == 2 else None,
                  brier=float(np.mean([(p - a) ** 2 for a, p in zip(actual, probabilities)])),
                  log_loss=float(np.mean([-math.log(max(np.finfo(float).eps, min(1 - np.finfo(float).eps, p if a else 1 - p))) for a, p in zip(actual, probabilities)])),
                  calibration=_reliability(actual, probabilities))
    result["undefined_reasons"] = (["AUROC, average precision and balanced accuracy require both actual classes."] if len(set(actual)) < 2 else [])
    if positive["precision"] is None:
        result["undefined_reasons"].append("Positive precision is undefined because no positive predictions were made.")
    if positive["recall"] is None:
        result["undefined_reasons"].append("Positive recall is undefined because no positive outcomes were observed.")
    return result


def _summarize(manifest: dict, rows: list[dict], chart_point_limit=None) -> tuple[list[dict], list[dict]]:
    groups = defaultdict(list)
    for row in rows:
        groups[(row["model_name"], row["split"])].append(row)
    summaries, charts = [], []
    for (model, split), values in sorted(groups.items()):
        result = {"model_name": model, "split": split, "split_role": _role(split, manifest["splits"][split]), "n": len(values)}
        if manifest.get("task", "duration") == "duration":
            actual = np.array([row["actual_duration_days"] for row in values])
            predicted = np.array([row["predicted_duration_days"] for row in values])
            residual = predicted - actual
            variance = float(np.sum((actual - actual.mean()) ** 2))
            result["regression"] = {"mae_days": float(np.mean(abs(residual))), "rmse_days": float(np.sqrt(np.mean(residual ** 2))),
                                    "median_absolute_error_days": float(np.median(abs(residual))),
                                    "r2": 1 - float(np.sum(residual ** 2)) / variance if len(values) > 1 and variance else None,
                                    "mean_error_days": float(residual.mean()), "residual_definition": "predicted minus observed days"}
            result["classification"] = _binary([row["actual_prolonged"] for row in values], [row["prolonged_probability"] for row in values])
            calibrated = [row["calibrated_prolonged_probability"] for row in values]
            if any(value is not None for value in calibrated):
                if not all(value is not None for value in calibrated):
                    raise ValueError("Incomplete calibrated probabilities within model/split")
                result["calibrated_classification"] = _binary([row["actual_prolonged"] for row in values], calibrated)
            indexes = np.linspace(0, len(values) - 1, min(len(values), chart_point_limit), dtype=int) if chart_point_limit else np.arange(len(values))
            charts.extend([
                {"kind": "scatter", "title": f"{model} / {split}: observed vs predicted duration", "x_label": "Observed duration (days)", "y_label": "Predicted duration (days)", "points": list(map(list, zip(actual[indexes].tolist(), predicted[indexes].tolist())))},
                {"kind": "residual", "title": f"{model} / {split}: duration residuals", "x_label": "Predicted duration (days)", "y_label": "Predicted − observed (days)", "points": list(map(list, zip(predicted[indexes].tolist(), residual[indexes].tolist())))},
            ])
            for key, name in [("classification", "raw"), ("calibrated_classification", "calibrated")]:
                if key in result:
                    bins = result[key]["calibration"]["bins"]
                    charts.append({"kind": "reliability", "title": f"{model} / {split}: {name} prolonged-risk reliability", "x_label": "Mean predicted probability", "y_label": "Observed prolonged fraction", "points": [[b["mean_probability"], b["observed_fraction"]] for b in bins]})
        else:
            labels = manifest["labels"]
            actual = [row["actual_phase"] for row in values]
            result["classification"] = _classification(actual, [row["predicted_phase"] for row in values], labels)
            class_metrics = result["classification"]
            class_metrics["macro_convention"] = "Union of observed/predicted labels; undefined class precision/recall contributes zero. Balanced accuracy requires at least two supported actual classes."
            class_metrics["multiclass_brier"] = float(np.mean([sum((p - int(label == row["actual_phase"])) ** 2 for label, p in zip(labels, row["probabilities"])) for row in values]))
            class_metrics["log_loss"] = float(np.mean([-math.log(max(np.finfo(float).eps, row["probabilities"][labels.index(row["actual_phase"])])) for row in values]))
            class_metrics["one_vs_rest"] = {}
            for i, label in enumerate(labels):
                binary = _binary([int(row["actual_phase"] == label) for row in values], [row["probabilities"][i] for row in values])
                class_metrics["one_vs_rest"][label] = binary
                bins = binary["calibration"]["bins"]
                charts.append({"kind": "reliability", "title": f"{model} / {split}: {label} reliability", "x_label": "Mean predicted class probability", "y_label": "Observed class fraction", "points": [[b["mean_probability"], b["observed_fraction"]] for b in bins]})
        for chart in charts:
            if 'model_name' not in chart:
                chart.update(model_name=model, split=split, population_n=len(values))
        summaries.append(result)
    return summaries, charts


def analyze_experiment(path, baseline_dir=None, *, model_names=None, split=None, chart_point_limit=None) -> dict:
    """Return deterministic JSON-safe analysis of a trusted completed experiment.

    Raises ValueError for invalid/incomplete rows, overlapping membership, or an
    unpaired baseline. Absolute filesystem paths and model artifacts are omitted.
    """
    manifest, rows, hashes = _load(path)
    if chart_point_limit is not None and (type(chart_point_limit) is not int or chart_point_limit < 1 or chart_point_limit > 10000):
        raise ValueError('Chart point limit must be an integer from 1 to 10000')
    if model_names is not None and not set(model_names).issubset({row['model_name'] for row in rows}):
        raise ValueError('Selected model has no saved prediction evidence')
    if split is not None and split not in manifest['splits']:
        raise ValueError('Selected split is not declared in the manifest')
    selected_rows = [row for row in rows if (model_names is None or row['model_name'] in model_names) and (split is None or row['split'] == split)]
    if not selected_rows:
        raise ValueError('No held-out prediction rows for selected model/split')
    models, charts = _summarize(manifest, selected_rows, chart_point_limit)
    source = manifest.get("source_metadata", {})
    report = {
        "schema_version": 1, "task": manifest.get("task", "duration"),
        "run": {key: manifest.get(key) for key in ("run_id", "created_at", "artifact_version", "input_sha256", "pipeline_source_sha256", "additional_model_source_sha256")},
        "provenance": {key: source.get(key) for key in ("dataset_name", "source", "retrieved_at", "is_fixture", "snapshot_type", "baseline_provenance", "sampling_method", "not_population_representative", "canonical_sha256") if key in source},
        "provenance_scope": "The analyzed model training/evaluation cohort, not the currently selected application dataset.",
        "cohort": {key: value for key, value in manifest.get("cohort", {}).items() if key in {"input_rows", "eligible_rows", "excluded_rows", "temporally_purged_rows", "outcomes", "target"}}, "hashes": hashes,
        "split_counts": {name: {"n": definition["rows"], "role": _role(name, definition), "prediction_rows": sum(row["split"] == name for row in rows)} for name, definition in sorted(manifest["splits"].items())},
        "models": models, "charts": charts,
        "selection": {**{key: manifest.get(key) for key in ("recommended_model", "recommended_duration_model") if key in manifest},
                      "task_components": {name: {key: value.get("selection", {}).get(key) for key in ("regressor_component", "classifier_component", "method") if key in value.get("selection", {})} for name, value in manifest.get("models", {}).items() if name=="accuracy_task_selected"}},
        "chart_sampling": ('Deterministic evenly spaced sample in trial-ID order, bounded per chart; metrics and reliability bins include every selected prediction row.' if chart_point_limit else 'Charts show every stored prediction row.'),
        "limitations": [
            "Retrospective descriptive research decision support; no clinical validation or guaranteed future accuracy.",
            "Tuning data support model selection; calibration data fit transforms/intervals; only test data provide the untouched held-out estimate. Test inspection can influence subsequent experiments.",
            "Metrics are recomputed from every stored prediction. Saved aggregate metrics are parsed and hashed but are not treated as evidence of accuracy.",
            "Current registry snapshots may contain post-start updates and leakage. Completed-only and convenience samples can create selection bias; chronological splits do not establish prospective validity.",
            "No regression accuracy percentage is defined. Duration errors use days. Binary decisions use probability >= 0.5; confusion matrices have actual rows and predicted columns.",
            "Undefined values are null, displayed as unavailable. One-class splits do not identify class discrimination. Small held-out samples and imbalance can make estimates unstable; no uncertainty interval is invented.",
            "Reliability uses ten equal-width bins. Raw and post-hoc calibrated probabilities are analyzed separately; calibration-cohort diagnostics can be optimistic.",
            "Duration-by-phase subgroup metrics cannot be recomputed because saved duration prediction rows do not contain verified phase labels; stored subgroup aggregates are not substituted.",
            (f"Scatter and residual charts show at most {chart_point_limit} deterministic points each; metrics and bin counts include every selected row." if chart_point_limit else "Charts show all stored points (overlapping points can obscure sample counts); metrics and bin counts include every row."),
        ] + [str(value) for value in manifest.get("limitations", [])],
    }
    if manifest.get("warning"):
        report["limitations"].append(str(manifest["warning"]))
    if baseline_dir is not None:
        baseline_manifest, baseline_rows, baseline_hashes = _load(baseline_dir)
        if baseline_manifest.get("task", "duration") != report["task"]:
            raise ValueError("Baseline and candidate tasks must match")
        if report["task"] == "phase" and baseline_manifest["labels"] != manifest["labels"]:
            raise ValueError("Baseline and candidate phase labels must match")
        def targets(values):
            return {(r["split"], r["nct_id"]): (r["actual_duration_days"], r["actual_prolonged"], r["prolonged_threshold_days"]) if report["task"] == "duration" else r["actual_phase"] for r in values}
        if targets(rows) != targets(baseline_rows):
            raise ValueError("Paired comparison requires the same held-out IDs, splits and actual targets")
        for split in manifest["splits"]:
            if split in baseline_manifest["splits"] and _role(split, manifest["splits"][split]) != _role(split, baseline_manifest["splits"][split]):
                raise ValueError("Baseline and candidate split roles must match")
        base_models, _ = _summarize(baseline_manifest, baseline_rows)
        paired = []
        base_by_key = {(r["model_name"], r["split"]): r for r in base_models}
        for row in models:
            base = base_by_key.get((row["model_name"], row["split"]))
            if base:
                delta = {"model_name": row["model_name"], "split": row["split"], "n": row["n"]}
                for family in ("regression", "classification"):
                    for metric, value in row.get(family, {}).items():
                        before = base.get(family, {}).get(metric)
                        if type(value) in (int, float) and type(before) in (int, float):
                            delta[family + "." + metric + "_delta"] = value - before
                paired.append(delta)
        report["paired_comparison"] = {"baseline_run_id": baseline_manifest.get("run_id"), "baseline_hashes": baseline_hashes,
                                        "interpretation": "Candidate minus baseline on identical IDs and outcomes. Negative error/Brier deltas favor candidate; positive accuracy/F1/AUROC deltas favor candidate. Descriptive only; no significance or future guarantee.",
                                        "matched_model_deltas": paired, "baseline_models": base_models}
    # Enforce JSON finiteness here, not only when exporting files.
    json.dumps(report, allow_nan=False)
    return report


def _svg(chart: dict) -> str:
    """Render numeric plot data ourselves; never inject supplied SVG/HTML."""
    points = [(float(x), float(y)) for x, y in chart["points"] if math.isfinite(float(x)) and math.isfinite(float(y))]
    if not points:
        return "<p>No plot observations available.</p>"
    xs, ys = zip(*points)
    if chart["kind"] == "reliability":
        xmin = ymin = 0.0
        xmax = ymax = 1.0
    elif chart["kind"] == "scatter":
        xmin = ymin = min(0.0, min(xs), min(ys))
        xmax = ymax = max(1.0, max(xs), max(ys)) * 1.03
    else:
        xmin, xmax = min(0.0, min(xs)), max(1.0, max(xs)) * 1.03
        ymin, ymax = min(0.0, min(ys)), max(0.0, max(ys))
        padding = max((ymax - ymin) * 0.05, 1)
        ymin, ymax = ymin - padding, ymax + padding
    def xpixel(x):
        return 72 + 480 * (x - xmin) / (xmax - xmin)
    def ypixel(y):
        return 278 - 224 * (y - ymin) / (ymax - ymin)
    esc = lambda value: html.escape(str(value), quote=True)
    title = esc(chart["title"])
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 340" role="img" aria-label="{title}"><title>{title}</title>',
           '<rect width="600" height="340" fill="white"/><path d="M72 54V278H552" fill="none" stroke="#536070"/>']
    for i in range(6):
        xv, yv = xmin + (xmax - xmin) * i / 5, ymin + (ymax - ymin) * i / 5
        svg.append(f'<text x="{xpixel(xv):.2f}" y="296" text-anchor="middle" font-size="11">{xv:.3g}</text><text x="65" y="{ypixel(yv)+4:.2f}" text-anchor="end" font-size="11">{yv:.3g}</text>')
    if chart["kind"] in {"scatter", "reliability"}:
        svg.append('<path d="M72 278L552 54" stroke="#a0a7b3" stroke-dasharray="5 4"/>')
    else:
        svg.append(f'<path d="M72 {ypixel(0):.2f}H552" stroke="#a0a7b3" stroke-dasharray="5 4"/>')
    for x, y in points:
        svg.append(f'<circle cx="{xpixel(x):.2f}" cy="{ypixel(y):.2f}" r="3.5" fill="#2563a4" fill-opacity="0.6"><title>{x:.5g}, {y:.5g}</title></circle>')
    svg.extend([f'<text x="312" y="326" text-anchor="middle" font-size="13">{esc(chart["x_label"])}</text>',
                f'<text transform="translate(18 166) rotate(-90)" text-anchor="middle" font-size="13">{esc(chart["y_label"])}</text>', '</svg>'])
    return "".join(svg)


def _flatten(row: dict) -> dict:
    result = {key: row[key] for key in ("model_name", "split", "split_role", "n")}
    for family in ("regression", "classification", "calibrated_classification"):
        for key, value in row.get(family, {}).items():
            if value is None or type(value) in (int, float):
                result[family + "." + key] = value
    return result


def _display(value):
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _table(rows: list[dict], columns: list[str]) -> str:
    esc = lambda value: html.escape(_display(value), quote=True)
    return '<div class="table-wrap"><table><thead><tr>' + ''.join('<th>' + esc(key) + '</th>' for key in columns) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + esc(row.get(key)) + '</td>' for key in columns) + '</tr>' for row in rows) + '</tbody></table></div>'


def render_analysis_html(report: dict) -> str:
    """Render a self-contained report. All supplied text is HTML-escaped."""
    esc = lambda value: html.escape(str(value), quote=True)
    output = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Model accuracy analysis</title>',
              '<style>body{font:15px/1.5 system-ui,sans-serif;color:#183047;background:#f5f7fa;margin:0}main{max-width:1280px;margin:auto;padding:30px}h1,h2,h3{line-height:1.25}section,.notice,figure{background:white;padding:20px;border:1px solid #d7dfe8;border-radius:8px;margin:18px 0}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:9px;text-align:left;border-bottom:1px solid #d7dfe8}th{background:#eef3f8}.table-wrap{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.plots{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}figure{margin:0}svg{width:100%;height:auto}figcaption{font-weight:600}small{color:#536070}@media print{body{background:white}main{padding:0}.table-wrap{overflow:visible}figure{break-inside:avoid}}</style></head><body><main>',
              '<h1>Model accuracy analysis</h1>', f'<p>Task: <strong>{esc(report["task"])}</strong> · Run: {esc(report["run"].get("run_id"))}</p>',
              '<div class="notice">Recomputed from stored predictions. Research decision support only; retrospective performance does not establish clinical validation or future accuracy.</div>',
              '<section><h2>Split roles and counts</h2><p>Tuning supports selection. Calibration fits transforms or uncertainty intervals. Test is the held-out evaluation cohort. Training predictions are excluded.</p>',
              _table([{"split": name, **value} for name, value in report["split_counts"].items()], ["split", "role", "n", "prediction_rows"]),
              '<small>n counts unique manifest trials; prediction_rows counts all model rows.</small></section>',
              '<section><h2>Recomputed model metrics</h2><p>Duration MAE and RMSE are in days; R² is unitless and can be negative. Classification values are proportions, with binary threshold ≥ 0.5. Unavailable means undefined or not applicable.</p>']
    if 'quality_context' in report:
        output.append('<details><summary>Approved model identity, integrity, endpoint and uncertainty</summary><pre>' + esc(json.dumps(report['quality_context'], indent=2, ensure_ascii=False, allow_nan=False)) + '</pre></details>')
    flattened = [_flatten(row) for row in report["models"]]
    columns = list(dict.fromkeys(key for row in flattened for key in row))
    output.extend([_table(flattened, columns), '</section>'])
    for row in report["models"]:
        output.append(f'<section><h3>{esc(row["model_name"])} / {esc(row["split"])} — classification details</h3>')
        for key in ("classification", "calibrated_classification"):
            if key in row:
                output.append(f'<h4>{esc(key)}</h4><p>Confusion matrix: actual rows, predicted columns. Labels: {esc(row[key]["labels"])}</p>')
                output.append('<pre>' + esc(json.dumps(row[key], indent=2, ensure_ascii=False, allow_nan=False)) + '</pre>')
        output.append('</section>')
    output.append('<h2>Observed predictions and reliability</h2><p>Dashed lines indicate perfect predictions/reliability, or zero residual. Reliability shows occupied bins; metrics use all rows.</p><div class="plots">')
    for chart in report["charts"]:
        output.append('<figure><figcaption>' + esc(chart["title"]) + '</figcaption>' + _svg(chart) + '</figure>')
    output.append('</div>')
    if "paired_comparison" in report:
        comparison = report["paired_comparison"]
        output.extend(['<section><h2>Paired baseline comparison</h2><p>' + esc(comparison["interpretation"]) + '</p>',
                       '<pre>' + esc(json.dumps(comparison, indent=2, ensure_ascii=False, allow_nan=False)) + '</pre></section>'])
    output.extend(['<section><h2>Provenance and reproducibility</h2><p>SHA-256 hashes identify the exact analyzed input files. No model artifact was loaded.</p>',
                   '<pre>' + esc(json.dumps({key: report[key] for key in ("run", "provenance_scope", "provenance", "cohort", "selection", "hashes")}, indent=2, ensure_ascii=False, allow_nan=False)) + '</pre></section>',
                   '<section><h2>Limitations</h2><ul>'])
    output.extend('<li>' + esc(value) + '</li>' for value in report["limitations"])
    output.append('</ul></section></main></body></html>')
    return ''.join(output)


def render_analysis_csv(report: dict) -> str:
    """Return deterministic model/split metrics, including paired deltas if present."""
    flat = [_flatten(row) for row in report["models"]]
    if "paired_comparison" in report:
        comparisons = {(row["model_name"], row["split"]): row for row in report["paired_comparison"]["matched_model_deltas"]}
        for row in flat:
            row.update({key: value for key, value in comparisons.get((row["model_name"], row["split"]), {}).items() if key.endswith("_delta")})
    columns = list(dict.fromkeys(key for row in flat for key in row))
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    # Protect spreadsheet consumers from user-controlled model/split formulas.
    writer.writerows({key: ("'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")) else value) for key, value in row.items()} for row in flat)
    return buffer.getvalue()


def write_analysis_report(run_dir, output_dir, baseline_dir=None, pdf=False) -> dict:
    """Write HTML, JSON, CSV and optional PDF to a new output directory.

    Existing directories are rejected so saved artifacts and prior reports cannot
    be overwritten. PDF support is optional and requires reportlab.
    """
    output_dir = Path(output_dir).resolve()
    for protected in (run_dir, baseline_dir):
        if protected is not None and (output_dir == Path(protected).resolve() or Path(protected).resolve() in output_dir.parents):
            raise ValueError("Output directory must be outside saved experiment folders")
    if output_dir.exists():
        raise ValueError("Output directory already exists; choose a new report directory")
    if pdf:
        try:
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        except ImportError:
            raise ValueError("PDF output requires optional reportlab. Install it with: python -m pip install reportlab; HTML, JSON and CSV need no reportlab.") from None
    report = analyze_experiment(run_dir, baseline_dir)
    rendered = render_analysis_html(report)
    csv_content = render_analysis_csv(report)
    output_dir.mkdir(parents=True, exist_ok=False)
    paths = {}
    for filename, content in (("model_analysis.html", rendered), ("model_analysis.json", json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"), ("model_comparison.csv", csv_content)):
        path = output_dir / filename
        path.write_bytes(content.encode("utf-8"))
        paths[filename.rsplit(".", 1)[-1]] = str(path)
    if pdf:
        styles = getSampleStyleSheet()
        story = [Paragraph("Model accuracy analysis", styles["Title"]), Paragraph("Portable metric summary. Open model_analysis.html for all SVG charts and full details.", styles["BodyText"])]
        for row in [_flatten(row) for row in report["models"]]:
            story.append(Spacer(1, 12))
            for key, value in row.items():
                story.append(Paragraph(html.escape(f"{key}: {_display(value)}"), styles["BodyText"]))
        story.append(Spacer(1, 12))
        for limitation in report["limitations"]:
            story.append(Paragraph(html.escape(limitation), styles["BodyText"]))
        path = output_dir / "model_analysis.pdf"
        SimpleDocTemplate(str(path)).build(story)
        paths["pdf"] = str(path)
    return paths
