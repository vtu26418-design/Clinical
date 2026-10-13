"""Run the reproducible temporal experiment on a canonical real-data cohort."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.clinical_trial_intelligence.research import ExperimentConfig, train_experiment
from src.clinical_trial_intelligence.ingestion.aact import sha256_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Canonical CSV or Parquet")
    parser.add_argument("--output", required=True, help="New experiment directory")
    parser.add_argument("--config", default=None, help="ExperimentConfig JSON; see configs/research.json")
    parser.add_argument("--metadata", default=None, help="Source provenance JSON")
    args = parser.parse_args()
    path = Path(args.input)
    frame = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)
    config = ExperimentConfig(**json.loads(Path(args.config).read_text(encoding="utf-8"))) if args.config else ExperimentConfig()
    metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8")) if args.metadata else {}
    metadata.update({"source_file": path.name, "source_sha256": sha256_file(path)})
    try:
        result = train_experiment(frame, args.output, metadata, config=config)
    except ValueError as exc:
        parser.exit(2, f"Training refused: {exc}\n")
    print(json.dumps({"run_id": result["run_id"], "status": result["status"], "cohort": result["cohort"], "warning": result["warning"], "manifest": str(Path(args.output) / "manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
