"""Optional real SHAP for fitted linear sklearn pipelines with train-only background."""
import numpy as np
from sklearn.pipeline import Pipeline


def explain(model, X, background=None, *, max_background=100):
    """Return serialized SHAP values, or an explicit unavailable reason.

    X and background must already use the pipeline's canonical feature columns.
    Caller must supply records from the original training split as background.
    """
    if background is None or len(background) == 0:
        return {"status": "unavailable", "reason": "An explicit nonempty training-only background is required for SHAP."}
    if not isinstance(model, Pipeline) or not {"preprocess", "model"}.issubset(model.named_steps):
        return {"status": "unavailable", "reason": "SHAP adapter supports a fitted linear pipeline; constant baselines have no feature attribution."}
    fitted = model.named_steps["model"]
    if not hasattr(fitted, "coef_"):
        return {"status": "unavailable", "reason": "The model has no fitted linear coefficients."}
    if not isinstance(max_background, int) or max_background < 1:
        raise ValueError("max_background must be a positive integer.")
    try:
        import shap
    except ImportError:
        return {"status": "unavailable", "reason": "Install the optional shap dependency to compute SHAP; no attribution was fabricated."}
    transform = model.named_steps["preprocess"]
    train = transform.transform(background.iloc[:max_background])
    values = transform.transform(X)
    result = shap.LinearExplainer(fitted, train)(values)
    return {"status": "available", "method": "SHAP LinearExplainer", "shap_version": shap.__version__,
            "units": "log-odds" if hasattr(fitted, "predict_proba") else "days before nonnegative clipping",
            "background_rows": min(max_background, len(background)),
            "feature_names": transform.get_feature_names_out().tolist(),
            "values": np.asarray(result.values).tolist(), "base_values": np.asarray(result.base_values).tolist(),
            "warning": "Attribution depends on the training background and feature dependence assumptions; it is not causal evidence."}
