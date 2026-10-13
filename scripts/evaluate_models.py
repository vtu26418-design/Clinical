"""Recompute saved held-out metrics without fitting or changing model artifacts."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.clinical_trial_intelligence.research import evaluate_predictions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--output", help="Optional separate JSON report; defaults to console")
    args = parser.parse_args()
    directory = Path(args.experiment)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    predictions = pd.read_csv(directory / manifest["files"]["predictions"])
    metrics = {}
    for (name, split), group in predictions.groupby(["model_name", "split"]):
        metrics.setdefault(name, {})[split] = evaluate_predictions(group.actual_duration_days, group.predicted_duration_days, group.actual_prolonged, group.prolonged_probability, manifest["config"]["bootstrap_samples"], manifest["config"]["random_seed"])
    report = {"run_id": manifest["run_id"], "warning": manifest["warning"], "metrics": metrics}
    encoded = json.dumps(report, indent=2, allow_nan=False)
    if args.output:
        Path(args.output).write_text(encoded, encoding="utf-8")
    else:
        print(encoded)


if __name__ == "__main__":
    main()
