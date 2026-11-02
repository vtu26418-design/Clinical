"""Compatibility launcher. Prefer: python -m streamlit run app/dashboard.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("dashboard.py")), run_name="__main__")
