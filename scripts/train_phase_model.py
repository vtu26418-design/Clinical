"""Train the separate temporal registry-phase classifier from a canonical cohort."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.clinical_trial_intelligence.ingestion.aact import sha256_file
from src.clinical_trial_intelligence.phase_model import PhaseConfig, train_phase_experiment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Canonical CSV or Parquet")
    parser.add_argument("--output", required=True, help="New phase experiment directory")
    parser.add_argument("--config", help="Optional PhaseConfig JSON; see docs/PHASE_MODEL.md")
    parser.add_argument("--metadata", help="Optional source-provenance JSON")
    args = parser.parse_args()
    try:
        path = Path(args.input)
        frame = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)
        config = PhaseConfig(**json.loads(Path(args.config).read_text(encoding="utf-8"))) if args.config else PhaseConfig()
        metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8")) if args.metadata else {}
        if not isinstance(metadata, dict):
            raise ValueError("Source metadata must be a JSON object.")
        metadata.update({"source_file": path.name, "source_sha256": sha256_file(path)})
        result = train_phase_experiment(frame, args.output, metadata, config=config)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"Phase training refused: {exc}\n")
    print(json.dumps({"run_id": result["run_id"], "task": result["task"], "status": result["status"], "cohort": result["cohort"], "warning": result["warning"], "manifest": str(Path(args.output) / "phase_manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
