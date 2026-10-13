"""Bounded protocol-only inputs for hypothetical research scenarios."""
from __future__ import annotations

from typing import Annotated, Literal
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

DatasetId = Annotated[str, Field(min_length=1, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')]
StudyId = Annotated[str, Field(min_length=1, max_length=100)]


class ProtocolOverrides(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enrollment: float | None = Field(default=None, strict=True, ge=0, le=10_000_000, allow_inf_nan=False)
    number_of_arms: int | None = Field(default=None, strict=True, ge=0, le=1000)
    primary_outcomes: int | None = Field(default=None, strict=True, ge=0, le=10_000)
    secondary_outcomes: int | None = Field(default=None, strict=True, ge=0, le=10_000)
    criteria_count: int | None = Field(default=None, strict=True, ge=0, le=100_000)
    text_complexity: float | None = Field(default=None, strict=True, ge=0, le=10_000, allow_inf_nan=False)
    phase: str | None = Field(default=None, strict=True, min_length=1, max_length=80)

    @field_validator('*', mode='before')
    @classmethod
    def explicit_null_is_not_an_override(cls, value):
        if value is None:
            raise ValueError('Omit unchanged fields; an explicit null is not a protocol override.')
        return value

    @field_validator('phase')
    @classmethod
    def known_phase(cls, value):
        from src.clinical_trial_intelligence.phase_model import normalize_phase
        value = value.strip()
        pieces = re.split(r'[|/]', value)
        normalized = [normalize_phase(piece) for piece in pieces]
        if normalized and all(normalized):
            result = '/'.join(normalized)
            if result in {'EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4', 'PHASE1/PHASE2', 'PHASE2/PHASE3'}:
                return result
        if value.upper() in {'NA', 'N/A', 'NOT REPORTED'}:
            return 'NA' if value.upper() != 'NOT REPORTED' else 'Not reported'
        raise ValueError('Use a recognized registry phase or Not reported.')


class PlanningInputs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sites: int = Field(strict=True, gt=0, le=100_000)
    monthly_rate_per_site: float = Field(strict=True, ge=1e-9, le=1_000_000, allow_inf_nan=False)
    startup_months: float = Field(strict=True, ge=0, le=1200, allow_inf_nan=False)
    followup_months: float = Field(strict=True, ge=0, le=1200, allow_inf_nan=False)


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset_id: DatasetId
    nct_id: StudyId
    model_name: Literal['recommended','median_baseline','structured','text','multimodal','structured_extra_trees','structured_random_forest','structured_gradient_boosting','structured_hist_gradient_boosting','multimodal_late_fusion','structured_catboost'] = 'recommended'
    overrides: ProtocolOverrides = Field(default_factory=ProtocolOverrides)
    planning: PlanningInputs
    name: str = Field(default='Research scenario', strict=True, min_length=1, max_length=120)

    @field_validator('name')
    @classmethod
    def nonempty_name(cls, value):
        if not value.strip():
            raise ValueError('Give the scenario a nonempty name.')
        return value.strip()
