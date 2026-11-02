"""Shared artifact locations. Data, learned weights and reports have separate homes."""
from .data import ROOT

DEMO_MODELS = ROOT/'models/demo'
DEMO_REPORTS = ROOT/'reports/evaluation/demo'
