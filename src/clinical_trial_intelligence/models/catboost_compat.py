"""Native CatBoost estimators with the scikit-learn 1.8 estimator protocol.

CatBoost 1.2.8 supplies legacy tags but not __sklearn_tags__. Inheriting the
standard mixins preserves native fitting, prediction and serialization while
providing the supported BaseEstimator tag implementation. No global patching.
"""
from catboost import CatBoostClassifier, CatBoostRegressor
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin


class CTICatBoostRegressor(CatBoostRegressor, RegressorMixin, BaseEstimator):
    pass


class CTICatBoostClassifier(CatBoostClassifier, ClassifierMixin, BaseEstimator):
    pass
