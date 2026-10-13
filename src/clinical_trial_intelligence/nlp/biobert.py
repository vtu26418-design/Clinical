"""Optional frozen BioBERT encoder; never silently substitutes another method."""
import numpy as np
import re
from sklearn.base import BaseEstimator, TransformerMixin


class BioBERTEncoder(TransformerMixin, BaseEstimator):
    """Attention-mask mean pooling with an explicit model revision and no fine-tuning.

    Supply downloaded weights or explicitly set local_files_only=False. Record
    the exact model commit hash for reproducibility. Install torch+transformers.
    """
    def __init__(self, model_name="dmis-lab/biobert-base-cased-v1.2", revision=None, local_files_only=True, batch_size=8, max_length=256, device="cpu"):
        self.model_name, self.revision = model_name, revision
        self.local_files_only, self.batch_size = local_files_only, batch_size
        self.max_length, self.device = max_length, device

    def fit(self, X, y=None):
        if not isinstance(self.revision, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", self.revision):
            raise ValueError("Supply an exact model revision (commit hash) to make BioBERT reproducible.")
        try:
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("BioBERT requires the optional torch and transformers dependencies.") from exc
        if self.batch_size < 1 or not 1 <= self.max_length <= 512:
            raise ValueError("batch_size must be positive and max_length must be 1–512.")
        self.tokenizer_ = AutoTokenizer.from_pretrained(self.model_name, revision=self.revision, local_files_only=self.local_files_only)
        self.model_ = AutoModel.from_pretrained(self.model_name, revision=self.revision, local_files_only=self.local_files_only).to(self.device)
        self.model_.eval()
        self.n_features_out_ = self.model_.config.hidden_size
        return self

    def transform(self, X):
        if not hasattr(self, "model_"):
            raise ValueError("Call fit before transform.")
        import torch
        texts = ["" if value is None else str(value) for value in X]
        output = []
        with torch.inference_mode():
            for start in range(0, len(texts), self.batch_size):
                tokens = self.tokenizer_(texts[start:start + self.batch_size], padding=True, truncation=True, max_length=self.max_length, return_tensors="pt")
                tokens = {key: value.to(self.device) for key, value in tokens.items()}
                states = self.model_(**tokens).last_hidden_state
                mask = tokens["attention_mask"].unsqueeze(-1).to(states.dtype)
                output.append(((states * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)).cpu().numpy())
        return np.concatenate(output, axis=0) if output else np.empty((0, self.n_features_out_), dtype=np.float32)

    def get_feature_names_out(self, input_features=None):
        return np.array([f"biobert_{i}" for i in range(self.n_features_out_)], dtype=object)
