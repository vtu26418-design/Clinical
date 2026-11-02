import pytest


@pytest.fixture(autouse=True)
def isolate_dashboard_training_runs(tmp_path, monkeypatch):
    """UI tests must not change the demo weights shipped in the repository."""
    monkeypatch.setenv('DEMAND_RUN_ROOT', str(tmp_path/'dashboard'))
