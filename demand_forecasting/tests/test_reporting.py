import sqlite3
import pandas as pd
from src.reporting import export_database


def test_sql_summary_matches_hand_checked_errors(tmp_path):
    pd.DataFrame({'model': ['naive', 'naive'], 'actual': [10, 20], 'prediction': [12, 16],
                  'store': ['1', '1'], 'item': ['1', '1'], 'date': ['2024-01-01', '2024-01-02']}).to_csv(tmp_path/'test_predictions.csv', index=False)
    pd.DataFrame({'store': ['1'], 'item': ['1'], 'prediction': [15], 'date': ['2024-01-03']}).to_csv(tmp_path/'forecast.csv', index=False)
    result = export_database(tmp_path)
    assert result['test_mae_by_model'][0]['mae'] == 3
    with sqlite3.connect(tmp_path/'results.sqlite') as connection:
        assert connection.execute('SELECT SUM(prediction) FROM forecasts').fetchone()[0] == 15


def test_sql_preserves_distinct_leading_zero_identifiers(tmp_path):
    data = pd.DataFrame({'model': ['naive', 'naive'], 'actual': [10, 20], 'prediction': [12, 16],
                         'store': ['001', '1'], 'item': ['01', '01'], 'date': ['2024-01-01']*2})
    data.to_csv(tmp_path/'test_predictions.csv', index=False)
    data.to_csv(tmp_path/'forecast.csv', index=False)
    export_database(tmp_path)
    with sqlite3.connect(tmp_path/'results.sqlite') as connection:
        assert connection.execute('SELECT COUNT(DISTINCT store) FROM forecasts').fetchone()[0] == 2
