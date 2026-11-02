"""Past-only features and fixed-origin, recursive daily forecasts."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
from .data import validate_sales, read_sales, source_info

FEATURES = ['store', 'item', 'lag_1', 'lag_7', 'lag_14', 'mean_7', 'mean_28',
            'std_28', 'weekday', 'month', 'year_day_sin', 'year_day_cos', 'time_index']
BASELINES = ['naive', 'seasonal_naive']


def feature_row(values, date, store, item):
    if len(values) < 28:
        raise ValueError('At least 28 historical daily observations are required per series.')
    date = pd.Timestamp(date)
    tail = np.asarray(values[-28:], dtype=float)
    return {'store': str(store), 'item': str(item), 'lag_1': values[-1], 'lag_7': values[-7],
            'lag_14': values[-14], 'mean_7': float(tail[-7:].mean()), 'mean_28': float(tail.mean()),
            'std_28': float(tail.std(ddof=0)), 'weekday': date.dayofweek, 'month': date.month,
            'year_day_sin': np.sin(2*np.pi*date.dayofyear/365.25),
            'year_day_cos': np.cos(2*np.pi*date.dayofyear/365.25),
            'time_index': (date-pd.Timestamp('2000-01-01')).days}


def make_training(frame):
    data = validate_sales(frame)
    rows = []
    for (store, item), group in data.groupby(['store', 'item'], sort=True):
        values = group.sales.to_list()
        dates = group.date.to_list()
        for index in range(28, len(group)):
            rows.append({**feature_row(values[:index], dates[index], store, item),
                         'date': dates[index], 'sales': values[index]})
    if not rows:
        raise ValueError('Need more than 28 days of history to train.')
    return pd.DataFrame(rows)


def forecast_frame(frame, horizon, kind, predictor=None):
    if not isinstance(horizon, int) or isinstance(horizon, bool) or not 1 <= horizon <= 28:
        raise ValueError('Forecast horizon must be an integer from 1 to 28 days.')
    data = validate_sales(frame)
    ends = data.groupby(['store', 'item']).date.max()
    if ends.nunique() != 1:
        raise ValueError('All selected series must have the same last date.')
    states = {(store, item): group.sales.to_list() for (store, item), group in data.groupby(['store', 'item'], sort=True)}
    minimum = 7 if kind == 'seasonal_naive' else (1 if kind == 'naive' else 28)
    if any(len(values) < minimum for values in states.values()):
        raise ValueError(f'{kind} needs at least {minimum} daily observations per series.')
    if kind not in BASELINES and predictor is None:
        raise ValueError('A fitted predictor is required for this model.')
    rows = []
    for step in range(1, horizon+1):
        date = data.date.max()+pd.Timedelta(days=step)
        if kind in BASELINES:
            predictions = [values[-1] if kind == 'naive' else values[-7] for values in states.values()]
        else:
            features = pd.DataFrame([feature_row(values, date, *key) for key, values in states.items()])
            predictions = predictor.predict(features[FEATURES])
        if len(predictions) != len(states) or not np.isfinite(predictions).all():
            raise ValueError('Model produced invalid predictions.')
        for (key, values), prediction in zip(states.items(), predictions):
            prediction = max(0., float(prediction))
            values.append(prediction)
            rows.append({'date': date, 'store': key[0], 'item': key[1], 'prediction': prediction, 'model': kind})
    return pd.DataFrame(rows)


def metrics(actual, predicted):
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if actual.shape != predicted.shape or actual.size == 0 or not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError('Metrics require matching, nonempty finite arrays.')
    error = predicted-actual
    denominator = float(np.abs(actual).sum())
    return {'mae': float(np.abs(error).mean()), 'rmse': float(np.sqrt(np.square(error).mean())),
            'bias': float(error.mean()), 'wape_percent': float(100*np.abs(error).sum()/denominator) if denominator else None,
            'n': int(actual.size)}


def split_windows(frame, horizon=7, block_days=28):
    data = validate_sales(frame)
    if block_days < horizon or block_days % horizon:
        raise ValueError('Evaluation block must be a positive multiple of the horizon.')
    if data.groupby(['store', 'item']).date.max().nunique() != 1:
        raise ValueError('All selected series must have the same last date.')
    end = data.date.max()
    test_start = end-pd.Timedelta(days=block_days-1)
    validation_start = test_start-pd.Timedelta(days=block_days)
    train_end = validation_start-pd.Timedelta(days=1)
    counts = data[data.date <= train_end].groupby(['store', 'item']).size()
    if len(counts) != data.groupby(['store', 'item']).ngroups or counts.min() < 42:
        raise ValueError('Need at least 42 training days plus 28 validation and 28 test days for every series.')
    return {'train_end': train_end, 'validation_start': validation_start,
            'validation_end': test_start-pd.Timedelta(days=1), 'test_start': test_start, 'test_end': end,
            'validation_origins': [train_end+pd.Timedelta(days=i) for i in range(0, block_days, horizon)],
            'test_origins': [test_start-pd.Timedelta(days=1)+pd.Timedelta(days=i) for i in range(0, block_days, horizon)]}


def evaluate_origins(frame, kind, origins, horizon=7, predictor=None):
    data = validate_sales(frame)
    results = []
    for origin in origins:
        origin = pd.Timestamp(origin)
        predictions = forecast_frame(data[data.date <= origin], horizon, kind, predictor)
        joined = predictions.merge(data.rename(columns={'sales': 'actual'}), on=['date', 'store', 'item'], how='left', validate='one_to_one')
        if joined.actual.isna().any():
            raise ValueError('Missing actual values for the full fixed-origin evaluation horizon.')
        joined['origin'] = origin
        results.append(joined)
    if not results:
        raise ValueError('At least one forecast origin is required.')
    return pd.concat(results, ignore_index=True)


def baseline_report(source, output):
    data = read_sales(source)
    windows = split_windows(data)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {'source': source_info(source), 'horizon_days': 7,
              'windows': {key: str(value) if not isinstance(value, list) else [str(v) for v in value] for key, value in windows.items()},
              'validation_metrics': {}, 'note': 'Week 2 uses validation only. The final test period remains reserved.'}
    tables = []
    for kind in BASELINES:
        table = evaluate_origins(data, kind, windows['validation_origins'])
        report['validation_metrics'][kind] = metrics(table.actual, table.prediction)
        tables.append(table)
    pd.concat(tables).to_csv(output / 'baseline_validation_predictions.csv', index=False)
    (output / 'baseline_report.json').write_text(json.dumps(report, indent=2))
    return report
