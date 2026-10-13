"""Verify fixture ingestion and descriptive PCI without inventing a model risk score."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.clinical_trial_intelligence.ingestion.validator import validate_csv
from src.clinical_trial_intelligence.research import predict_trial
from backend.app.services.pci_service import calculate_pci
import tempfile


def main():
    path = Path(__file__).resolve().parents[1] / "data/sample/trials.csv"
    print("SOFTWARE FIXTURES ONLY — not scientific validation")
    print(validate_csv(str(path)))
    with tempfile.TemporaryDirectory() as empty_artifacts:
        for row in pd.read_csv(path).to_dict(orient="records"):
            score, category, _ = calculate_pci(row)
            prediction = predict_trial(row, empty_artifacts)
            assert prediction["status"] == "unavailable" and prediction["probability"] is None
            print(f"{row['nct_id']}: descriptive PCI={score} ({category}); model prediction unavailable (no trained artifact)")
    print("Software smoke test completed.")


if __name__ == "__main__":
    main()
