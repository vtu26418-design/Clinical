from pathlib import Path
import pandas as pd

REQUIRED = {"nct_id", "title", "study_type", "phase", "enrollment", "start_date", "completion_date"}

def validate_csv(path: str) -> dict:
    p = Path(path)
    df = pd.read_csv(p)
    missing = sorted(REQUIRED - set(df.columns))
    return {
        "path": str(p),
        "rows": len(df),
        "columns": list(df.columns),
        "missing_required_columns": missing,
        "duplicates": int(df["nct_id"].duplicated().sum()) if "nct_id" in df else None,
        "valid": not missing,
    }
