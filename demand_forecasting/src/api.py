"""Compatibility entrypoint. Prefer: python -m uvicorn api.main:app."""
from api.main import app

__all__ = ["app"]
