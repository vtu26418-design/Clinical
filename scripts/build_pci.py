"""Export descriptive PCI; optionally apply the training-fitted research index."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import joblib
import pandas as pd
from backend.app.services.pci_service import calculate_pci, METHODOLOGY
from src.clinical_trial_intelligence.research import _features, _pci_values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--experiment", help="Optional trusted local experiment directory; uses its training-fitted PCI")
    args = parser.parse_args()
    source, output = Path(args.input), Path(args.output)
    if output.resolve() == source.resolve():
        parser.error("Do not overwrite the source dataset.")
    frame = pd.read_parquet(source) if source.suffix.lower() == ".parquet" else pd.read_csv(source)
    if "nct_id" not in frame:
        parser.error("Input requires nct_id.")
    rows = []
    if args.experiment:
        directory = Path(args.experiment)
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        artifact = joblib.load(directory / "models.joblib")
        if manifest.get("run_id") != artifact.get("run_id") or manifest.get("source_metadata") != artifact.get("source_metadata"):
            parser.error("Trusted artifact and manifest do not match.")
        for nct_id, value in zip(frame.nct_id, _pci_values(_features(frame), artifact["pci"])):
            rows.append({"nct_id": nct_id, "pci": value["score"], **value["components"]})
        metadata = {"run_id": artifact["run_id"], "methodology": artifact["pci"], "warning": "Cohort-relative descriptive index, not a probability. Components are normalized 0–1; weights produce the 0–100 score."}
    else:
        for row in frame.to_dict(orient="records"):
            score, category, components = calculate_pci(row)
            rows.append({"nct_id": row["nct_id"], "pci": score, "category": category, **components})
        metadata = {"methodology": METHODOLOGY, "warning": "Fixed-assumption exploratory PCI used by the UI; distinct from the training-fitted research index. Components are weighted score points, not probabilities."}
    output.parent.mkdir(parents=True, exist_ok=True)
    result = pd.DataFrame(rows)
    result.to_parquet(output, index=False) if output.suffix.lower() == ".parquet" else result.to_csv(output, index=False)
    output.with_suffix(output.suffix + ".methodology.json").write_text(json.dumps(metadata, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Wrote {len(rows)} descriptive PCI records and explicit methodology.")


if __name__ == "__main__":
    main()
