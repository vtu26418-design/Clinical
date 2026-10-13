"""Compatibility export for shap_adapter."""
from .services.shap_adapter import explain_prediction, get_demo_shap_values

__all__ = ["explain_prediction", "get_demo_shap_values"]
