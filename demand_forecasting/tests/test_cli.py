from pathlib import Path
import subprocess
import sys
import pandas as pd
import pytest


@pytest.mark.parametrize('dates', [['2024-01-01', '2024-01-03'], ['2024-01-01', '2024-01-01']])
def test_inventory_cli_rejects_gapped_or_duplicate_forecast_dates(tmp_path, dates):
    data = pd.DataFrame({'date': dates, 'store': ['1']*2, 'item': ['1']*2, 'prediction': [10, 20]})
    path = tmp_path/'forecast.csv'
    data.to_csv(path, index=False)
    run = subprocess.run([sys.executable, '-m', 'src.cli', 'inventory', '--forecast', str(path),
                           '--store', '1', '--item', '1', '--lead-days', '2', '--on-hand', '0', '--daily-std', '0'],
                          cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert run.returncode == 2
    assert 'Input error' in run.stderr


def test_custom_training_output_keeps_models_inside_custom_run(tmp_path,monkeypatch):
    import numpy as np
    from src import cli
    path=tmp_path/'sales.csv'
    pd.DataFrame({'date':pd.date_range('2024-01-01',periods=120),'store':'1','item':'1',
                  'sales':20+np.sin(np.arange(120)*2*np.pi/7)}).to_csv(path,index=False)
    protected=tmp_path/'bundled_demo_models'
    monkeypatch.setattr(cli,'DEMO_MODELS',protected)
    monkeypatch.setattr(cli,'DEMO_REPORTS',tmp_path/'default_reports')
    custom=tmp_path/'custom_run'
    monkeypatch.setattr(sys,'argv',['project','train','--input',str(path),'--output',str(custom)])
    cli.main()
    assert (custom/'models/selected_model.joblib').is_file()
    assert (custom/'model.joblib').is_file()
    assert not (protected/'registry.json').exists()
