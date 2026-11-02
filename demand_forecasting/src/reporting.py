"""Small SQL exercise over the actual measured evaluation/forecast outputs."""
from pathlib import Path
import sqlite3
import pandas as pd


def export_database(run_directory):
    directory = Path(run_directory)
    predictions = pd.read_csv(directory/'test_predictions.csv', dtype={'store': str, 'item': str})
    forecasts = pd.read_csv(directory/'forecast.csv', dtype={'store': str, 'item': str})
    with sqlite3.connect(directory/'results.sqlite') as connection:
        predictions.to_sql('test_predictions', connection, if_exists='replace', index=False)
        forecasts.to_sql('forecasts', connection, if_exists='replace', index=False)
        summary = pd.read_sql_query('SELECT model, AVG(ABS(prediction-actual)) AS mae, COUNT(*) AS observations FROM test_predictions GROUP BY model ORDER BY mae', connection)
    return {'database': str(directory/'results.sqlite'), 'test_mae_by_model': summary.to_dict(orient='records'),
            'note': 'Descriptive SQL summary after evaluation; does not choose the model.'}
