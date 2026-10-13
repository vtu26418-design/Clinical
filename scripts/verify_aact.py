"""Validate frozen AACT protocol-table schemas and checksums without modifying them."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.clinical_trial_intelligence.ingestion.aact import verify_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, help="Directory of extracted AACT .txt or .csv tables")
    parser.add_argument("--expected", help="Previous verification/source metadata JSON; compare frozen SHA-256 fingerprints")
    parser.add_argument("--output", help="Save a verification manifest outside the raw directory")
    args = parser.parse_args()
    expected = json.loads(Path(args.expected).read_text(encoding="utf-8")) if args.expected else None
    if args.output and (Path(args.output).resolve() == Path(args.path).resolve() or Path(args.path).resolve() in Path(args.output).resolve().parents):
        parser.error("Write the verification manifest outside the immutable raw directory.")
    try:
        manifest = verify_snapshot(args.path, expected=expected)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Verification failed: {exc}\n")
    encoded = json.dumps(manifest, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
