"""Daily sales validation, immutable source provenance and explicit practice data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = 'synthetic practice; not observed retail sales'


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_sales(path):
    return validate_sales(pd.read_csv(path, dtype={'store': 'string', 'item': 'string'}))


def normalize_identifiers(frame):
    """Check IDs before any selection can silently exclude malformed rows."""
    data = frame.copy()
    for key in ['store', 'item']:
        if data[key].isna().any():
            raise ValueError('Missing store/item identifiers. Resolve them before selecting a subset.')
        data[key] = data[key].astype(str).str.strip()
        if data[key].eq('').any():
            raise ValueError('Empty store/item identifiers.')
    return data


def validate_sales(frame):
    required = ['date', 'store', 'item', 'sales']
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f'Missing columns: {sorted(missing)}. Expected date,store,item,sales.')
    data = frame[required].copy()
    if data.empty:
        raise ValueError('The sales dataset is empty.')
    dates = pd.to_datetime(data['date'], errors='coerce')
    if dates.isna().any():
        raise ValueError('Invalid or missing date. Use YYYY-MM-DD.')
    if not pd.api.types.is_datetime64_ns_dtype(dates.dtype):
        raise ValueError('Dates must be timezone-free daily dates.')
    if not dates.eq(dates.dt.normalize()).all():
        raise ValueError('Dates must be daily dates without time-of-day values.')
    data['date'] = dates
    data = normalize_identifiers(data)
    data['sales'] = pd.to_numeric(data['sales'], errors='coerce')
    if not np.isfinite(data['sales'].to_numpy(dtype=float)).all() or (data.sales < 0).any():
        raise ValueError('sales must be finite, nonnegative numbers; investigate missing values/returns first.')
    if data.duplicated(['date', 'store', 'item']).any():
        raise ValueError('Duplicate date/store/item observations. Resolve their meaning before aggregating.')
    data = data.sort_values(['store', 'item', 'date']).reset_index(drop=True)
    differences = data.groupby(['store', 'item'])['date'].diff().dropna()
    if not differences.eq(pd.Timedelta(days=1)).all():
        raise ValueError('Missing daily observations within a series. Do not silently replace them with zero sales.')
    return data


def source_info(path):
    digest = file_hash(path)
    meta = Path(path).with_suffix('.metadata.json')
    if meta.exists():
        info = json.loads(meta.read_text())
        if info.get('source_sha256') == digest:
            return {**info, 'source_file': Path(path).name}
    return {'data_kind': 'user supplied; provenance must be documented by operator',
            'source_file': Path(path).name, 'source_sha256': digest}


def generate_demo(path, days=730, seed=42):
    if days < 1:
        raise ValueError('days must be positive.')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    dates = pd.date_range('2022-01-01', periods=days)
    rows = []
    for store in ['1', '2']:
        for item in ['1', '2', '3', '4']:
            for i, date in enumerate(dates):
                weekly = [0.8, 0.85, 0.95, 1.0, 1.2, 1.45, 1.15][date.dayofweek]
                mean = (12 + int(item) * 4 + int(store) * 3) * weekly * (1 + 0.0005 * i)
                rows.append((date.strftime('%Y-%m-%d'), store, item, int(rng.poisson(mean))))
    pd.DataFrame(rows, columns=['date', 'store', 'item', 'sales']).to_csv(path, index=False)
    info = {'data_kind': SYNTHETIC, 'seed': seed, 'days_per_series': days,
            'generator': 'Poisson counts with assumed weekday effect and trend; generated for software learning only',
            'source_sha256': file_hash(path)}
    path.with_suffix('.metadata.json').write_text(json.dumps(info, indent=2))
    return info


def prepare(source, output):
    source, output = Path(source), Path(output)
    if source.resolve() == (output / 'cleaned.csv').resolve():
        raise ValueError('Output must not overwrite the raw source.')
    data = read_sales(source)
    output.mkdir(parents=True, exist_ok=True)
    report = {**source_info(source), 'rows': len(data), 'series': data.groupby(['store', 'item']).ngroups,
              'start': str(data.date.min().date()), 'end': str(data.date.max().date()),
              'zero_sales_rows': int(data.sales.eq(0).sum()), 'total_units': float(data.sales.sum()),
              'missing_values': int(data.isna().sum().sum()), 'duplicate_keys': 0,
              'notes': 'Validated observed daily sales. Missing periods are rejected, not filled. Sales may understate demand during unobserved stockouts.'}
    data.to_csv(output / 'cleaned.csv', index=False)
    data.groupby(['store', 'item']).sales.agg(['count', 'mean', 'std', 'min', 'max']).to_csv(output / 'series_summary.csv')
    data.assign(weekday=data.date.dt.day_name()).groupby('weekday').sales.mean().to_csv(output / 'weekday_sales.csv')
    (output / 'audit.json').write_text(json.dumps(report, indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), constrained_layout=True)
    data.groupby('date').sales.sum().plot(ax=axes[0], title=f'Daily sales — {report["data_kind"]}', ylabel='Units sold')
    data.groupby('item').sales.sum().plot.bar(ax=axes[1], title='Sales by item', ylabel='Units sold')
    fig.savefig(output / 'sales_overview.png', dpi=130)
    plt.close(fig)
    return report
