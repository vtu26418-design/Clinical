"""Restore matching saved model/report runs without fitting anything on startup."""
import hashlib
import json
from pathlib import Path
import pandas as pd
from .data import validate_sales, file_hash
from .modeling import load_bundle, forecast_saved


def dataset_signature(frame):
    return hashlib.sha256(validate_sales(frame).to_csv(index=False).encode()).hexdigest()


def run_locations(signature, base):
    if len(signature) != 64 or any(character not in '0123456789abcdef' for character in signature):
        raise ValueError('Expected a SHA-256 dataset signature.')
    return Path(base)/'models/runs'/signature[:16], Path(base)/'reports/runs'/signature[:16]


def restore_run(frame, model_directory, report_directory):
    model_directory, report_directory = Path(model_directory), Path(report_directory)
    required = [model_directory/'selected_model.joblib', model_directory/'registry.json',
                report_directory/'manifest.json', report_directory/'test_predictions.csv',
                report_directory/'validation_predictions.csv', report_directory/'forecast.csv']
    if not all(path.is_file() for path in required):
        return None
    signature = dataset_signature(frame)
    registry = json.loads((model_directory/'registry.json').read_text())
    manifest = json.loads((report_directory/'manifest.json').read_text())
    if registry.get('canonical_data_sha256') != signature or manifest.get('canonical_data_sha256') != signature:
        return None
    bundle = load_bundle(model_directory/'selected_model.joblib')
    if bundle.get('data_sha256') != signature:
        return None
    if manifest.get('model_sha256') != file_hash(model_directory/'selected_model.joblib'):
        raise ValueError('Saved model and reports belong to a different model experiment. Regenerate the matching run.')
    if registry.get('selected_model') != bundle.get('model_name') or manifest.get('selected_model') != bundle.get('model_name'):
        raise ValueError('Saved model/report selection metadata does not match.')
    for name in ['validation_predictions.csv','test_predictions.csv','forecast.csv']:
        expected = manifest.get('report_hashes', {}).get(name)
        if not expected or expected != file_hash(report_directory/name):
            raise ValueError(f'Saved report checksum mismatch: {name}. Regenerate the matching run.')
    return {'signature': signature, 'manifest': manifest, 'registry': registry,
            'forecasts': forecast_saved(frame, bundle),
            'test': pd.read_csv(report_directory/'test_predictions.csv', dtype={'store': str, 'item': str}),
            'model_directory': str(model_directory), 'report_directory': str(report_directory)}
