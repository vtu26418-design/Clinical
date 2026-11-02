"""Validation-selected models, untouched test evaluation, and separate serving refit."""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
from pathlib import Path
from importlib.metadata import version
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from .data import validate_sales, file_hash
from .forecasting import FEATURES, BASELINES, make_training, forecast_frame, split_windows, evaluate_origins, metrics


def estimator_for(name):
    numeric = [name for name in FEATURES if name not in ['store', 'item']]
    transform = ColumnTransformer([('ids', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['store', 'item']),
                                   ('numeric', StandardScaler(), numeric)])
    estimator = LinearRegression() if name == 'linear_regression' else RandomForestRegressor(
        n_estimators=60, max_depth=10, min_samples_leaf=3, random_state=42, n_jobs=1)
    return Pipeline([('features', transform), ('regressor', estimator)])


def fit_model(data, name):
    training = make_training(data)
    predictor = estimator_for(name)
    predictor.fit(training[FEATURES], training.sales)
    return predictor


def train(frame, output, source_metadata=None, model_directory=None):
    data = validate_sales(frame)
    windows = split_windows(data)
    training = data[data.date <= windows['train_end']]
    names = BASELINES + ['linear_regression', 'random_forest']
    predictors = {name: fit_model(training, name) for name in names if name not in BASELINES}
    validation_metrics, validation_tables = {}, []
    for name in names:
        table = evaluate_origins(data, name, windows['validation_origins'], predictor=predictors.get(name))
        validation_metrics[name] = metrics(table.actual, table.prediction)
        validation_tables.append(table)
    selected = min(names, key=lambda name: validation_metrics[name]['mae'])
    # The decision is fixed above. Test values are read only after selection.
    test_metrics, test_tables = {}, []
    for name in names:
        table = evaluate_origins(data, name, windows['test_origins'], predictor=predictors.get(name))
        test_metrics[name] = metrics(table.actual, table.prediction)
        test_tables.append(table)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    model_directory = Path(model_directory) if model_directory is not None else output
    model_directory.mkdir(parents=True, exist_ok=True)
    pd.concat(validation_tables).to_csv(output / 'validation_predictions.csv', index=False)
    pd.concat(test_tables).to_csv(output / 'test_predictions.csv', index=False)
    digest = hashlib.sha256(data.to_csv(index=False).encode()).hexdigest()
    packages = {name: version(name) for name in ['numpy', 'pandas', 'scikit-learn', 'joblib']}
    source = source_metadata or {'data_kind': 'user supplied; provenance not verified'}
    common = {'version': 1, 'horizon_limit': 7,
              'training_end': str(data.date.max().date()), 'data_sha256': digest, 'packages': packages,
              'series': [list(key) for key in data.groupby(['store', 'item']).groups], 'source': source}
    # Serving refits are distinct from the earlier training-only evaluation fits.
    bundles, entries, hashes = {}, [], {}
    for name in names:
        estimator = fit_model(data, name) if name not in BASELINES else None
        candidate = {**common, 'model_name': name, 'estimator': estimator}
        bundles[name] = candidate
        if name in BASELINES:
            filename = f'{name}.json'
            specification = {**common, 'model_name': name,
                'rule': 'Repeat latest observed value' if name == 'naive' else 'Recursively repeat corresponding value from seven days ago',
                'last_seven_observations': [{'store': key[0], 'item': key[1], 'sales': group.sales.tail(7).tolist()}
                                            for key, group in data.groupby(['store', 'item'])]}
            (model_directory/filename).write_text(json.dumps(specification, indent=2))
        else:
            filename = f'{name}.joblib'
            joblib.dump(candidate, model_directory/filename, compress=3)
        hashes[filename] = file_hash(model_directory/filename)
        entries.append({'name': name, 'file': filename, 'sha256': hashes[filename], 'selected': name == selected,
                        'type': 'baseline specification' if name in BASELINES else 'fitted scikit-learn pipeline',
                        'validation_metrics': validation_metrics[name], 'test_metrics': test_metrics[name]})
    bundle = bundles[selected]
    selected_path = model_directory/'selected_model.joblib'
    joblib.dump(bundle, selected_path, compress=3)
    hashes['selected_model.joblib'] = file_hash(selected_path)
    # Existing programmatic clients and old commands can still use output/model.joblib.
    shutil.copyfile(selected_path, output/'model.joblib')
    if model_directory.resolve() == output.resolve():
        hashes['model.joblib'] = hashes['selected_model.joblib']
    registry = {'version': 1, 'selected_model': selected, 'selected_file': 'selected_model.joblib',
                'source': source, 'training_end': common['training_end'], 'canonical_data_sha256': digest,
                'features': FEATURES, 'packages': packages, 'models': entries, 'artifacts': hashes,
                'artifact_scope': 'Serving refits on all known history AFTER evaluation; metrics belong to the separate evaluation fits.'}
    (model_directory/'registry.json').write_text(json.dumps(registry, indent=2))
    card = {'forecast_horizon_days': 7, 'independent_business_validation': False, 'source': source,
            'selected_model': selected, 'selection': 'Lowest validation MAE; test does not select the model.',
            'training_end': common['training_end'], 'canonical_data_sha256': digest,
            'limitations': ['Synthetic practice models are not real retail evidence.',
                            'Observed sales may be constrained by unobserved stockouts.',
                            'Seven-day recursive forecasts; no calibrated prediction interval supplied.',
                            'Inventory inputs are explicit scenarios, not observed stock or guaranteed service levels.'],
            'packages': packages, 'trusted_load': 'Only deserialize artifacts generated by your own trusted installation.'}
    (model_directory/'model_card.json').write_text(json.dumps(card, indent=2))
    forecast_saved(data, bundle).to_csv(output / 'forecast.csv', index=False)
    report_hashes = {name: file_hash(output/name) for name in
                     ['validation_predictions.csv', 'test_predictions.csv', 'forecast.csv']}
    manifest = {'selected_model': selected, 'selection_rule': 'Minimum validation MAE only; test values cannot choose the model.',
                'horizon_days': 7, 'source': source,
                'canonical_data_sha256': digest, 'model_sha256': file_hash(output / 'model.joblib'),
                'rows': len(data), 'series': len(bundle['series']), 'model_artifacts': entries,
                'report_hashes': report_hashes,
                'windows': {key: [str(v) for v in value] if isinstance(value, list) else str(value) for key, value in windows.items()},
                'validation_metrics': validation_metrics, 'test_metrics': test_metrics,
                'serving_model': 'Selected method refitted on all observed history AFTER evaluation; reported held-out metrics belong to evaluation fits, not an independent evaluation of this refit.',
                'backtesting': 'Four seven-day origins per block. Actual history becomes available between origins; within each horizon predictions feed subsequent lags. Learned models stay fitted to the initial training partition during evaluation.',
                'inventory': 'No observed inventory supplied. Replenishment outputs are explicit what-if scenarios.',
                'python': platform.python_version(), 'packages': packages}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    if model_directory.resolve() != output.resolve():
        (model_directory/'manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


def load_bundle(path):
    # Only load artifacts generated by your own installation. joblib/pickle is executable.
    path = Path(path)
    registry_path = path.parent/'registry.json'
    manifest_path = path.parent / 'manifest.json'
    if registry_path.exists():
        registry = json.loads(registry_path.read_text())
        expected = registry.get('artifacts', {}).get(path.name)
        if expected is None or expected != file_hash(path):
            raise ValueError('Model checksum mismatch or unregistered artifact. Retrain from trusted CSV input.')
    elif manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest.get('model_sha256') != file_hash(path):
            raise ValueError('Model checksum mismatch. Retrain from trusted CSV input.')
    bundle = joblib.load(path)
    if not isinstance(bundle, dict) or bundle.get('version') != 1:
        raise ValueError('Unsupported model artifact.')
    return bundle


def forecast_saved(frame, bundle, horizon=7):
    data = validate_sales(frame)
    if not isinstance(horizon, int) or isinstance(horizon, bool) or not 1 <= horizon <= bundle['horizon_limit']:
        raise ValueError('This evaluated workflow supports horizons from 1 through 7 days.')
    known = {tuple(pair) for pair in bundle['series']}
    if not set(data.groupby(['store', 'item']).groups).issubset(known):
        raise ValueError('Input contains unseen store/item series. Train a new candidate first.')
    if data.date.max() < pd.Timestamp(bundle['training_end']):
        raise ValueError('History ends before the serving model training cutoff; this would leak future training data.')
    return forecast_frame(data, horizon, bundle['model_name'], bundle['estimator'])
