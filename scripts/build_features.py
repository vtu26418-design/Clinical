"""Extract canonical protocol features from frozen AACT pipe files or canonical CSV."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.clinical_trial_intelligence.features.structured import build_structured_features
from src.clinical_trial_intelligence.ingestion.aact import extract_aact, sha256_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Extracted AACT table directory or canonical CSV/Parquet")
    parser.add_argument("--output", required=True, help="New processed-data directory")
    parser.add_argument("--snapshot-date", help="Required YYYY-MM-DD frozen AACT snapshot date")
    parser.add_argument("--source-url", help="Optional public acquisition URL (never a signed URL or credential)")
    args = parser.parse_args()
    source, directory = Path(args.input), Path(args.output)
    if (directory / "trials.csv").exists() or (directory / "source_metadata.json").exists():
        parser.error("Output already contains processed data; choose a new directory.")
    if source.is_dir():
        if not args.snapshot_date:
            parser.error("--snapshot-date is required for a frozen AACT snapshot.")
        frame, metadata = extract_aact(source, snapshot_date=args.snapshot_date, source_url=args.source_url)
    else:
        frame = pd.read_parquet(source) if source.suffix.lower() == ".parquet" else pd.read_csv(source)
        if "nct_id" not in frame:
            parser.error("Canonical input requires nct_id; raw AACT tables must be supplied as a directory.")
        frame = build_structured_features(frame)
        metadata = {"source": source.name, "input_sha256": sha256_file(source), "snapshot_date": args.snapshot_date,
                    "baseline_provenance": False, "mapping_version": "canonical-type-coercion-v1"}
    directory.mkdir(parents=True, exist_ok=True)
    frame.to_csv(directory / "trials.csv", index=False)
    metadata["canonical_sha256"] = sha256_file(directory / "trials.csv")
    (directory / "source_metadata.json").write_text(json.dumps(metadata, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Wrote {len(frame)} canonical rows to {directory / 'trials.csv'}; source files unchanged.")


if __name__ == "__main__":
    main()
