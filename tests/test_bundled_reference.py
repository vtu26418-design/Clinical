"""Public registry integration; generated rows below are security fixtures only."""
import gzip
import hashlib
import json

import pandas as pd
import pytest

from backend.app.config import Settings
from backend.app.services.data_service import DatasetRegistry


REFERENCE_ID = 'registry-v5205'


def registry_at(path):
    return DatasetRegistry(Settings(storage_dir=str(path), _env_file=None))


def test_new_projects_register_real_reference_without_copying_or_reading_table(tmp_path, monkeypatch):
    def no_table_read(*args, **kwargs):
        pytest.fail('Project creation must not read the public table.')
    monkeypatch.setattr(pd, 'read_parquet', no_table_read)
    first, second = registry_at(tmp_path / 'first'), registry_at(tmp_path / 'second')
    reference = first.get_dataset(REFERENCE_ID)
    assert reference is not None
    assert reference['row_count'] == 101135
    assert reference['is_fixture'] is False
    assert reference['provenance']['acquisition_complete'] is True
    assert reference['quality']['partial_date_values'] > 0
    assert reference['quality']['missingness']['planned_enrollment'] > 0
    assert first.preferred_dataset_id == REFERENCE_ID
    assert first.get_dataset('sample-fixture')['is_fixture'] is True
    assert second.get_dataset(REFERENCE_ID) == reference
    assert not (first.root / 'datasets' / REFERENCE_ID).exists()
    assert not (second.root / 'datasets' / REFERENCE_ID).exists()
    assert len(json.dumps(reference)) < 20000


def test_real_reference_preserves_source_values_and_reuses_verified_cache(tmp_path, monkeypatch):
    registry = registry_at(tmp_path)
    frame = registry.frame(REFERENCE_ID)
    assert len(frame) == 101135 and frame.nct_id.is_unique
    assert frame.start_date.dropna().str.fullmatch(r'\d{4}-\d{2}').any()
    assert frame.phase.str.contains('|', regex=False).any()
    assert frame.planned_enrollment.isna().any()
    assert frame.loc[frame.enrollment_type.ne('ESTIMATED'), 'planned_enrollment'].isna().all()
    assert frame.criteria_count.isna().all() and frame.text_complexity.isna().all()
    source = frame.iloc[0].copy()
    frame.loc[0, ['title', 'enrollment']] = ['Changed consumer copy', 9999999]
    from backend.app.services import bundled_reference
    def no_reread(*args, **kwargs):
        pytest.fail('An unchanged verified public table must use the cache.')
    monkeypatch.setattr(pd, 'read_parquet', no_reread)
    monkeypatch.setattr(bundled_reference, '_file_sha256', no_reread)
    another = registry_at(tmp_path / 'second').frame(REFERENCE_ID)
    assert another.iloc[0].title == source.title
    assert another.iloc[0].enrollment == source.enrollment
    summary = registry.reference_overview(REFERENCE_ID)
    assert summary['total_studies'] == 101135
    assert len(summary['pci_distribution']) == 100
    assert sum(summary['phase_counts'].values()) == 101135


def test_research_snapshot_supports_reference_without_a_canonical_csv(tmp_path):
    registry = registry_at(tmp_path)
    from backend.app.services.research_workspace import ResearchWorkspace
    source = registry.frame(REFERENCE_ID).iloc[0]
    snapshot = ResearchWorkspace(registry).snapshot(REFERENCE_ID, source.nct_id)
    assert snapshot.study['title'] == source.title
    assert snapshot.canonical_sha256 == registry.get_dataset(REFERENCE_ID)['canonical_sha256']
    assert snapshot.provenance['is_fixture'] is False


def small_reference(tmp_path):
    """A small checksum-pinned bundle to exercise failures without changing real data."""
    from backend.app.services.bundled_reference import _BundledReference
    root = tmp_path / 'public'
    (root / 'shards').mkdir(parents=True)
    (root / 'raw').mkdir()
    shard = root / 'shards/part-000001.parquet'
    pd.DataFrame([{'nct_id': 'SOFTWARE-ONLY', 'title': 'Security fixture'}]).to_parquet(shard)
    raw = root / 'raw/page-000001.json.gz'
    raw.write_bytes(gzip.compress(b'{"studies": []}', mtime=0))
    page = {'file': 'raw/' + raw.name, 'gzip_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
            'canonical_file': 'shards/' + shard.name, 'canonical_sha256': hashlib.sha256(shard.read_bytes()).hexdigest(),
            'canonical_rows': 1}
    metadata = {'acquisition_complete': True, 'rows': 1, 'duplicate_ids': 0, 'pages': [page]}
    metadata_bytes = json.dumps(metadata).encode()
    (root / 'metadata.json').write_bytes(metadata_bytes)
    descriptors = [{'file': page['canonical_file'], 'sha256': page['canonical_sha256'], 'rows': 1}]
    fingerprint = hashlib.sha256(json.dumps(descriptors, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    manifest = {'schema_version': 1, 'source_manifest_sha256': hashlib.sha256(metadata_bytes).hexdigest(),
                'canonical_sha256': fingerprint,
                'dataset': {'id': REFERENCE_ID, 'row_count': 1, 'columns': ['nct_id', 'title']},
                'overview': {'total_studies': 1}}
    manifest_bytes = json.dumps(manifest).encode()
    (root / 'runtime-reference.json').write_bytes(manifest_bytes)
    return _BundledReference(root, hashlib.sha256(manifest_bytes).hexdigest()), root


@pytest.mark.parametrize('target', ['metadata.json', 'runtime-reference.json', 'raw/page-000001.json.gz', 'shards/part-000001.parquet'])
def test_public_reference_rejects_tampering_even_after_cache_fill(tmp_path, target):
    reference, root = small_reference(tmp_path)
    assert reference.frame().iloc[0].nct_id == 'SOFTWARE-ONLY'
    with (root / target).open('ab') as stream:
        stream.write(b'tamper')
    with pytest.raises((OSError, ValueError)):
        reference.frame()


@pytest.mark.parametrize('target', ['raw', 'shards', 'metadata.json', 'runtime-reference.json', 'shards/part-000001.parquet'])
def test_public_reference_rejects_symlinks(tmp_path, target):
    reference, root = small_reference(tmp_path)
    source = root / target
    moved = tmp_path / 'external'
    source.rename(moved)
    source.symlink_to(moved, target_is_directory=moved.is_dir())
    with pytest.raises((OSError, ValueError)):
        reference.frame()


def test_db_metadata_cannot_redirect_a_private_upload_to_public_files(tmp_path):
    registry = registry_at(tmp_path)
    dataset = registry.register_bytes(b'nct_id,title\nPRIVATE,Private upload\n', 'private.csv',
                                      provenance={'reference_path': '/etc/passwd', 'reference_id': REFERENCE_ID})
    fake = {**dataset, 'storage_kind': 'bundled-public-reference', 'path': '/etc/passwd'}
    registry._execute('UPDATE datasets SET payload=:payload WHERE id=:id',
                      {'id': dataset['id'], 'payload': json.dumps(fake)})
    assert registry.frame(dataset['id']).iloc[0].nct_id == 'PRIVATE'
    assert registry.dataset_path(dataset['id']).parent == registry.root / 'datasets'


def test_db_metadata_cannot_replace_public_reference_identity(tmp_path):
    registry = registry_at(tmp_path)
    original = registry.get_dataset(REFERENCE_ID)
    altered = {**original, 'row_count': 5, 'sha256': 'fake', 'is_fixture': True,
               'reference_path': '/etc/passwd'}
    registry._execute('UPDATE datasets SET payload=:payload WHERE id=:id',
                      {'id': REFERENCE_ID, 'payload': json.dumps(altered)})
    assert registry.get_dataset(REFERENCE_ID) == original
    assert next(row for row in registry.list_datasets() if row['id'] == REFERENCE_ID) == original
