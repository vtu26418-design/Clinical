"""Portable, inference-only adapter for the separately evaluated phase probe.

Accepts the established ``_phase_features(..., include_design=True)`` frame.
No fitting, source labels, IDs, dates or outcomes enter this adapter. Current
reported enrollment remains a retrospective input, not planned enrollment.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.base import BaseEstimator, ClassifierMixin


def refinement_features(features):
    """Recreate the probe's deterministic text cleanup from redacted features."""
    if not isinstance(features, pd.DataFrame) or "protocol_text" not in features:
        raise ValueError("Phase refinement requires the established phase feature frame.")
    output = features.copy()
    output["protocol_text"] = (output.protocol_text.fillna("").astype(str)
        .str.replace(r"(?i)\bNCT\s*\d{8}\b", " ", regex=True)
        .str.replace(r"\b(?:19|20)\d{2}(?:[-/]\d{1,2}(?:[-/]\d{1,2})?)?\b", " ", regex=True)
        .str.slice(0, 12000).str.replace(r"\s+", " ", regex=True).str.strip())
    output.loc[~output.protocol_text.str.contains(r"\w", regex=True), "protocol_text"] = "missingprotocol"
    return output


class PhaseRefinementClassifier(ClassifierMixin, BaseEstimator):
    """Wrap already fitted transforms and estimator without a training method."""

    def __init__(self, preprocessor, estimator, svd=None, text_columns=None):
        self.preprocessor = preprocessor
        self.estimator = estimator
        self.svd = svd
        self.text_columns = text_columns

    @property
    def classes_(self):
        return self.estimator.classes_

    def _matrix(self, features):
        transformed = self.preprocessor.transform(refinement_features(features))
        if self.svd is None:
            return transformed
        if not isinstance(self.text_columns, int) or not 0 < self.text_columns < transformed.shape[1]:
            raise ValueError("Phase refinement text-component contract is invalid.")
        transformed = sparse.csr_matrix(transformed)
        return np.hstack([self.svd.transform(transformed[:, :self.text_columns]),
                          transformed[:, self.text_columns:].toarray()])

    def predict(self, features):
        return np.asarray(self.estimator.predict(self._matrix(features))).reshape(-1)

    def predict_proba(self, features):
        return self.estimator.predict_proba(self._matrix(features))
