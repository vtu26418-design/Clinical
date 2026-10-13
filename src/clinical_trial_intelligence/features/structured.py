import pandas as pd

def build_structured_features(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce types only; imputation must be fitted inside training pipelines."""
    out = df.copy()
    for c in ["enrollment","number_of_arms","primary_outcomes","secondary_outcomes","criteria_count"]:
        if c in out:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out
