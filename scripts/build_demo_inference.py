"""Freeze genuine research API responses for the static v5 browser preview.

Uses the first three chronological identifiers shared by the two test splits.
The exported records are independent of the UI's five software fixtures.
No fitting, fictional trials, synthetic metrics or live-browser claims occur.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from backend.app.config import Settings
from backend.app.main import create_app


def forbid_fit(*args, **kwargs):
    raise AssertionError('Frozen preview generation must only apply saved models.')


def build() -> dict:
    source_dir = ROOT / 'data/starter'
    source_metadata = json.loads((source_dir / 'metadata.json').read_text())
    source_bytes = (source_dir / 'trials.csv').read_bytes()
    assert hashlib.sha256(source_bytes).hexdigest() == source_metadata['canonical_sha256']
    assert source_metadata['is_fixture'] is False
    manifests, prediction_files = {}, {}
    for task in ('duration', 'phase'):
        folder = ROOT / f'examples/starter-{task}-v5'
        prefix = '' if task == 'duration' else 'phase_'
        manifests[task] = json.loads((folder / f'{prefix}manifest.json').read_text())
        prediction_files[task] = pd.read_csv(folder / f'{prefix}held_out_predictions.csv')
    phase_test = set(manifests['phase']['splits']['test']['nct_ids'])
    identifiers = [identifier for identifier in manifests['duration']['splits']['test']['nct_ids'] if identifier in phase_test][:3]
    assert len(identifiers) == 3
    frame = pd.read_csv(source_dir / 'trials.csv').set_index('nct_id', drop=False).loc[identifiers].reset_index(drop=True)
    raw = frame.to_csv(index=False).encode()
    with tempfile.TemporaryDirectory(prefix='cti-v5-real-preview-') as folder:
        app = create_app(Settings(storage_dir=folder, database_url='', auth_mode='local', _env_file=None))
        with patch.object(Pipeline, 'fit', forbid_fit), patch.object(ColumnTransformer, 'fit_transform', forbid_fit), TestClient(app) as client:
            registry = app.state.project_registry('local')
            dataset = registry.register_bytes(raw, 'clinicaltrials-heldout-preview.csv',
                name='Frozen ClinicalTrials.gov held-out research records',
                source='ClinicalTrials.gov API v2; frozen starter snapshot',
                provenance={'source_dataset_sha256': source_metadata['canonical_sha256'],
                            'source_retrieved_at': source_metadata['retrieved_at'],
                            'selection': 'First three chronological IDs common to both untouched test splits.'})
            catalog_response = client.get('/api/v5/models')
            assert catalog_response.status_code == 200, catalog_response.text
            catalog = catalog_response.json()
            assert {model['id'] for model in catalog['items'] if model['status'] == 'approved'} == {'bundled-duration-v5', 'bundled-phase-v5'}
            batches = {}
            for task in ('duration', 'phase'):
                response = client.post('/api/v5/inference/batch', json={'dataset_id': dataset['id'], 'task': task,
                    'model_id': 'active', 'mode': 'retrospective', 'limit': 3})
                assert response.status_code == 201, response.text
                batch = response.json()
                assert batch['summary'] == {'requested': 3, 'available': 3, 'blocked': 0, 'unavailable': 0}
                saved = prediction_files[task]
                saved = saved[(saved.split == 'test') & (saved.model_name == batch['model']['branch'])].set_index('nct_id')
                for item in batch['items']:
                    prediction = item['prediction']
                    assert prediction['cohort_membership'] == 'test'
                    expected = saved.loc[item['nct_id']]
                    if task == 'duration':
                        np.testing.assert_allclose([prediction['duration_days'], prediction['probability']],
                            [expected.predicted_duration_days, expected.prolonged_probability], rtol=1e-10, atol=1e-10)
                    else:
                        assert prediction['predicted_phase'] == expected.predicted_phase
                        for label, probability in prediction['class_probabilities'].items():
                            np.testing.assert_allclose(probability, expected['probability_' + label], rtol=1e-10, atol=1e-10)
                persisted = client.get('/api/v5/inference/' + batch['id'])
                assert persisted.status_code == 200 and persisted.json() == batch
                batches[task] = batch
            assert registry.list_experiments() == []
    return {'preview_kind': 'frozen_real_research_api_outputs',
            'source': {'name': source_metadata['dataset_name'], 'source': source_metadata['source'],
                'retrieved_at': source_metadata['retrieved_at'], 'canonical_sha256': source_metadata['canonical_sha256'],
                'source_record_count': source_metadata['rows'], 'preview_record_count': len(identifiers),
                'record_ids': identifiers, 'subset_sha256': hashlib.sha256(raw).hexdigest(),
                'selection': 'First three chronological IDs common to both untouched test splits; no performance-based selection.',
                'warning': 'Frozen retrospective research outputs from real public records. These are separate from interface fixtures. No browser model inference, prospective validation, recruitment-risk or amendment-risk prediction is provided.'},
            'models': catalog['items'], 'active': catalog['active'], 'batch': batches['duration'], 'batches': batches}


if __name__ == '__main__':
    result = build()
    output = ROOT / 'frontend/src/v5/demoInference.json'
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps({'output': str(output.relative_to(ROOT)), 'records': result['source']['record_ids'],
                      'models': {task: batch['model']['branch'] for task, batch in result['batches'].items()},
                      'status': 'Saved predictions reproduced and persisted API responses verified; no fitting.'}, indent=2))
