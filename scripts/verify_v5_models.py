"""Verify the pinned v5 research release against its source and saved predictions.

This loads trusted, checksum-pinned local artifacts only. It never fits a model.
Numerical equality is checked with rtol=atol=1e-10 to allow CSV round trips.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from src.clinical_trial_intelligence import phase_model, research
from download_starter_data import canonical_record


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_numeric(actual, expected):
    np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-10, equal_nan=True)


def source_checks(folder: Path) -> dict:
    metadata = json.loads((folder / 'metadata.json').read_text())
    assert not metadata['is_fixture']
    assert sha256(folder / 'trials.csv') == metadata['canonical_sha256']
    records = pd.read_csv(folder / 'trials.csv')
    assert len(records) == metadata['rows']
    assert records.nct_id.is_unique
    page_ids, replayed = [], []
    for page in metadata['raw_response_pages']:
        compressed = (folder / page['file']).read_bytes()
        payload = gzip.decompress(compressed)
        assert hashlib.sha256(compressed).hexdigest() == page['gzip_sha256']
        assert hashlib.sha256(payload).hexdigest() == page['response_sha256']
        studies = json.loads(payload)['studies']
        assert len(studies) == page['rows']
        page_ids.extend(study['protocolSection']['identificationModule']['nctId'] for study in studies)
        first, last = map(int, Path(page['file']).name.split('-')[:2])
        replayed.extend(canonical_record(study, first, last) for study in studies)
    assert len(page_ids) == len(records)
    assert set(page_ids) == set(records.nct_id)
    assert pd.DataFrame(replayed).to_csv(index=False, lineterminator='\n').encode() == (folder / 'trials.csv').read_bytes()
    return {'rows': len(records), 'unique_identifiers': records.nct_id.nunique(),
            'raw_pages': len(metadata['raw_response_pages']),
            'canonical_sha256': metadata['canonical_sha256'],
            'canonical_bytes_replayed_from_raw_pages': True,
            'acquisition_complete': metadata.get('acquisition_complete', True)}


@threadpool_limits.wrap(limits=1)
def verify() -> dict:
    source = source_checks(ROOT / 'data/starter')
    recovered = source_checks(ROOT / 'data/clinicaltrials-v5-recovered')
    frame = pd.read_csv(ROOT / 'data/starter/trials.csv')
    indexed = frame.set_index('nct_id', drop=False)
    report = {'created_at': datetime.now(timezone.utc).isoformat(),
              'procedure': 'Checksum validation, source-page identifier reconciliation, saved-artifact prediction replay and point-metric recomputation; no model fitting.',
              'numerical_tolerance': {'rtol': 1e-10, 'atol': 1e-10},
              'starter_source': source, 'recovered_partial_source': recovered,
              'recovered_used_to_fit_bundled_models': False, 'models': {}}
    for entry in json.loads((ROOT / 'examples/approved-models-v5.json').read_text())['models']:
        task = entry['task']
        folder = ROOT / entry['directory']
        prefix = '' if task == 'duration' else 'phase_'
        manifest_path = folder / f'{prefix}manifest.json'
        artifact_path = folder / f'{prefix}models.joblib'
        assert sha256(manifest_path) == entry['manifest_sha256']
        assert sha256(artifact_path) == entry['artifact_sha256']
        manifest = json.loads(manifest_path.read_text())
        assert manifest['source_metadata']['canonical_sha256'] == source['canonical_sha256']
        assert manifest['input_sha256'] == hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()
        artifact = joblib.load(artifact_path)
        assert artifact['run_id'] == manifest['run_id']
        assert artifact['source_metadata'] == manifest['source_metadata']
        saved = pd.read_csv(folder / f'{prefix}held_out_predictions.csv')
        metrics = json.loads((folder / f'{prefix}metrics.json').read_text())
        assert metrics == {name: details['metrics'] for name, details in manifest['models'].items()}
        split_ids = [set(value['nct_ids']) for value in manifest['splits'].values()]
        assert sum(map(len, split_ids)) == len(set.union(*split_ids))
        comparison_count = 0
        max_prediction_error = 0.0
        for (name, split), predictions in saved.groupby(['model_name', 'split'], sort=False):
            assert set(predictions.nct_id) == set(manifest['splits'][split]['nct_ids'])
            rows = indexed.loc[predictions.nct_id].reset_index(drop=True)
            model = artifact['models'][name]
            if task == 'duration':
                features = research._features(rows)
                estimate = np.maximum(0, model['regressor'].predict(features))
                probability = research._positive_probability(model['classifier'], features)
                assert_numeric(estimate, predictions.predicted_duration_days)
                assert_numeric(probability, predictions.prolonged_probability)
                actual = (pd.to_datetime(rows.completion_date) - pd.to_datetime(rows.start_date)).dt.days
                assert_numeric(actual, predictions.actual_duration_days)
                assert_numeric(actual > artifact['threshold_days'], predictions.actual_prolonged)
                computed = research.evaluate_predictions(actual, estimate, predictions.actual_prolonged, probability, 0)
                for category in ('regression', 'classification'):
                    for metric, value in computed[category].items():
                        expected = metrics[name][split][category][metric]
                        assert value is None if expected is None else np.isclose(value, expected, rtol=1e-10, atol=1e-10)
                max_prediction_error = max(max_prediction_error, float(np.abs(estimate - predictions.predicted_duration_days).max()),
                                           float(np.abs(probability - predictions.prolonged_probability).max()))
                calibrated = research._calibrated_probability(probability, artifact['calibration'][name]) if split != 'validation' else None
                if calibrated is None:
                    assert predictions.calibrated_prolonged_probability.isna().all()
                else:
                    assert_numeric(calibrated, predictions.calibrated_prolonged_probability)
            else:
                features = phase_model._phase_features(rows)
                estimate = model.predict(features)
                probability = phase_model._probabilities(model, features)
                assert np.array_equal(estimate, predictions.predicted_phase)
                assert list(rows.phase.map(phase_model.normalize_phase)) == list(predictions.actual_phase)
                saved_probability = predictions[['probability_' + label for label in phase_model.PHASE_LABELS]].to_numpy()
                assert_numeric(probability, saved_probability)
                computed = phase_model.evaluate_phase_predictions(predictions.actual_phase, estimate, manifest['training_classes'])
                assert computed == metrics[name][split]
                max_prediction_error = max(max_prediction_error, float(np.abs(probability - saved_probability).max()))
            comparison_count += len(predictions)
        report['models'][task] = {'run_id': manifest['run_id'], 'artifact_sha256': entry['artifact_sha256'],
            'manifest_sha256': entry['manifest_sha256'], 'cohort': manifest['cohort'],
            'splits': {key: value['rows'] for key, value in manifest['splits'].items()},
            'branches': len(artifact['models']), 'saved_prediction_rows_reproduced': comparison_count,
            'max_absolute_prediction_error': max_prediction_error,
            'all_saved_point_metrics_reproduced': True}
    report['status'] = 'passed'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Optional JSON evidence output')
    args = parser.parse_args()
    result = verify()
    payload = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    print(payload)


if __name__ == '__main__':
    main()
