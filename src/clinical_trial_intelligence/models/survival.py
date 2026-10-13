"""Optional cause-specific Cox analysis with explicit analyst-curated follow-up.

No completion/event values are inferred from estimated registry dates. The caller
must establish observed follow-up and endpoint ascertainment for every record.
"""
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ..research import NUMERIC_FEATURES, _features


def temporal_survival_cohort(frame: pd.DataFrame, *, cutoff: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {"nct_id", "start_date", "followup_date", "event_observed"}
    if not required.issubset(frame):
        raise ValueError("Survival cohort requires nct_id, start_date, followup_date, event_observed.")
    data = frame.copy()
    if data.nct_id.isna().any() or data.nct_id.astype(str).str.strip().eq("").any() or data.nct_id.duplicated().any():
        raise ValueError("Survival cohort requires nonempty unique nct_id values.")
    for field in ("start_date", "followup_date"):
        if not data[field].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}(?:$|[T ])").all():
            raise ValueError("Survival dates require known day precision.")
        data[field] = pd.to_datetime(data[field], errors="coerce", utc=True, format="mixed").dt.tz_convert(None)
        if data[field].isna().any():
            raise ValueError("Survival dates must be valid and observed, not estimated.")
    event = pd.to_numeric(data.event_observed, errors="coerce")
    if not event.isin([0, 1]).all():
        raise ValueError("event_observed must be binary 0 or 1 with no missing values.")
    data["event_observed"] = event.astype(int)
    boundary = pd.to_datetime(cutoff, utc=True).tz_convert(None)
    if pd.isna(boundary):
        raise ValueError("A valid temporal cutoff is required.")
    if (data.followup_date <= data.start_date).any():
        raise ValueError("Observed follow-up must be after trial start.")
    train, test = data.loc[data.start_date < boundary].copy(), data.loc[data.start_date >= boundary].copy()
    # Strictly pre-cutoff events are knowable; later events are administratively censored.
    future = train.followup_date >= boundary
    train.loc[future, "event_observed"] = 0
    train.loc[future, "followup_date"] = boundary
    for cohort in (train, test):
        cohort["duration_days"] = (cohort.followup_date - cohort.start_date).dt.total_seconds() / 86400
    return train, test


def fit_cox_model(train: pd.DataFrame, *, penalizer: float = 0.1) -> dict:
    """Fit numeric baseline covariates with training-only imputation/scaling."""
    if len(train) < 30 or "event_observed" not in train or train.event_observed.sum() < 5:
        raise ValueError("Cox fitting requires at least 30 training trials and 5 observed events; these guards do not establish adequacy.")
    if not np.isfinite(penalizer) or penalizer <= 0:
        raise ValueError("penalizer must be positive.")
    try:
        from lifelines import CoxPHFitter
    except ImportError as exc:
        raise RuntimeError("Cox survival analysis requires optional lifelines dependencies; no substitute model was run.") from exc
    values = _features(train)[NUMERIC_FEATURES]
    columns = [column for column in values if values[column].dropna().nunique() > 1]
    if not columns:
        raise ValueError("No varying observed numeric baseline covariates are available for Cox fitting.")
    preprocessor = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    design = pd.DataFrame(preprocessor.fit_transform(values[columns]), columns=columns, index=train.index)
    design["duration_days"] = train.duration_days
    design["event_observed"] = train.event_observed
    model = CoxPHFitter(penalizer=penalizer).fit(design, duration_col="duration_days", event_col="event_observed")
    return {"model": model, "preprocess": preprocessor, "features": columns, "penalizer": penalizer,
            "method": "Penalized Cox proportional hazards, numeric covariates", "training_n": len(train),
            "training_events": int(train.event_observed.sum())}


def evaluate_cox(artifact: dict, test: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    try:
        from lifelines.utils import concordance_index
    except ImportError as exc:
        raise RuntimeError("Survival evaluation requires optional lifelines dependencies.") from exc
    if test.empty:
        raise ValueError("A held-out survival test cohort is required.")
    design = pd.DataFrame(artifact["preprocess"].transform(_features(test)[artifact["features"]]), columns=artifact["features"], index=test.index)
    hazard = np.asarray(artifact["model"].predict_partial_hazard(design)).reshape(-1)
    # Cox hazard predicts earlier completion. Concordance expects longer-survival scores.
    try:
        cindex = float(concordance_index(test.duration_days, -hazard, test.event_observed))
    except ZeroDivisionError:
        cindex = None
    predictions = test[["nct_id", "duration_days", "event_observed"]].copy()
    predictions["relative_completion_hazard"] = hazard
    metrics = {"n": len(test), "observed_events": int(test.event_observed.sum()), "harrell_c_index": cindex,
               "interpretation": "Higher relative completion hazard means earlier completion; this is not prolonged-duration probability.",
               "limitations": "Requires non-informative censoring, consistent endpoint ascertainment and proportional-hazards assessment. Termination is a competing event; do not automatically treat it as independent censoring."}
    return metrics, predictions
