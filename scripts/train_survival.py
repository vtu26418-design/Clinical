"""Fit optional Cox analysis to an explicit, curated censored follow-up cohort."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import joblib
import pandas as pd
from src.clinical_trial_intelligence.ingestion.aact import sha256_file
from src.clinical_trial_intelligence.models.survival import temporal_survival_cohort, fit_cox_model, evaluate_cox


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Curated CSV: nct_id/start_date/followup_date/event_observed + baseline numeric features")
    parser.add_argument("--output", required=True, help="New directory for separate Cox artifacts")
    parser.add_argument("--cutoff", required=True, help="YYYY-MM-DD temporal train/test boundary")
    parser.add_argument("--metadata", required=True, help="JSON explaining event definition, censoring, follow-up ascertainment and baseline provenance")
    parser.add_argument("--penalizer", type=float, default=0.1)
    args = parser.parse_args()
    directory = Path(args.output)
    if directory.exists() and any(directory.iterdir()):
        parser.error("Use a new, empty output directory.")
    metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8"))
    required = {"event_definition", "censoring_definition", "followup_ascertainment"}
    if any(not metadata.get(key) for key in required):
        parser.error("Survival metadata must state event_definition, censoring_definition and followup_ascertainment.")
    train, test = temporal_survival_cohort(pd.read_csv(args.input), cutoff=args.cutoff)
    try:
        artifact = fit_cox_model(train, penalizer=args.penalizer)
        metrics, predictions = evaluate_cox(artifact, test)
    except (ValueError, RuntimeError) as exc:
        parser.exit(2, f"Survival fit unavailable: {exc}\n")
    import lifelines
    directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, directory / "cox.joblib")
    predictions.to_csv(directory / "survival_test_predictions.csv", index=False)
    artifact["model"].summary.to_csv(directory / "cox_coefficients.csv")
    manifest = {"status": "completed", "method": artifact["method"], "penalizer": args.penalizer, "source_metadata": metadata,
                "source_sha256": sha256_file(args.input), "lifelines_version": lifelines.__version__, "cutoff": args.cutoff,
                "training_rows": len(train), "test_rows": len(test), "training_ids": train.nct_id.tolist(), "test_ids": test.nct_id.tolist(),
                "features": artifact["features"], "metrics": metrics,
                "warning": "Separate censored-cohort analysis, not directly comparable to completed-only classifier metrics. Proportional hazards and endpoint ascertainment require expert review. No hyperparameter selection or confidence intervals are claimed."}
    (directory / "survival_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
