#!/usr/bin/env python3
"""Generate a reproducible accuracy report from a completed saved experiment."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.clinical_trial_intelligence.model_analysis import write_analysis_report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=ROOT / "examples" / "starter-duration-v5", help="Trusted completed duration or phase experiment folder")
    parser.add_argument("--output-dir", type=Path, help="New output directory outside saved experiment folders")
    parser.add_argument("--baseline-dir", type=Path, help="Optional baseline with identical held-out IDs and outcomes")
    parser.add_argument("--pdf", action="store_true", help="Also export a PDF summary (requires optional reportlab)")
    args = parser.parse_args(argv)
    output = args.output_dir or ROOT / "reports" / ("model-accuracy-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    try:
        paths = write_analysis_report(args.run_dir, output, args.baseline_dir, args.pdf)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Report generation failed: {error}\n")
    for kind, path in paths.items():
        print(f"{kind.upper()}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
