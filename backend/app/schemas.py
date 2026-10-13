from typing import Literal
from pydantic import BaseModel, Field


class ClinicalTrialsImportRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    max_studies: int = Field(default=100, ge=1, le=1000)
    name: str | None = Field(default=None, max_length=120)


class ExperimentRequest(BaseModel):
    dataset_id: str = Field(default='sample-fixture', min_length=1, max_length=80)
    enable_catboost: bool = False


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    dataset_id: str = Field(default='sample-fixture', max_length=80)
    nct_id: str | None = Field(default=None, max_length=100)
    provider: Literal['auto', 'openai', 'anthropic', 'gemini', 'compatible'] | None = None


class PredictionRequest(BaseModel):
    nct_id: str = Field(min_length=1, max_length=100)
    dataset_id: str = Field(default='sample-fixture', max_length=80)
    model_name: Literal['recommended', 'median_baseline', 'multimodal', 'structured', 'text', 'structured_extra_trees', 'structured_random_forest', 'structured_gradient_boosting', 'structured_hist_gradient_boosting', 'multimodal_late_fusion', 'structured_catboost'] = 'recommended'


class PhasePredictionRequest(BaseModel):
    nct_id: str = Field(min_length=1, max_length=100)
    dataset_id: str = Field(default='sample-fixture', min_length=1, max_length=80)
