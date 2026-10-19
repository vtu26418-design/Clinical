"""Rebuild the bounded public-workspace summary from verified registry evidence.

Run with --check to reproduce and compare the bundled runtime-reference.json.
Every raw compressed response, decompressed response and canonical shard is
verified by the acquisition replay loader before deriving any summary. A changed
snapshot requires a deliberate new runtime manifest SHA-256 pin in
backend/app/services/bundled_reference.py; this script never changes that pin.
No acquired source file or acquisition metadata is rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.acquire_registry_cohort import load_cohort
from backend.app.services.data_service import NUMERIC_FIELDS, json_clean
from backend.app.services.pci_service import calculate_pci


def build_manifest(folder: Path) -> bytes:
    metadata_bytes = (folder / 'metadata.json').read_bytes()
    source = json.loads(metadata_bytes)
    frame = load_cohort(folder, verify=True)
    if source['duplicate_ids'] or len(frame) != 101135:
        raise ValueError('The bundled v5.2.0.5 scope must reconcile to 101135 unique records.')
    missingness = {column: int((frame[column].isna() | frame[column].astype(str).str.strip().eq('')).sum())
                   for column in frame}
    partial = sum(int(frame[column].dropna().astype(str).str.fullmatch(r'\d{4}(-\d{2})?').sum())
                  for column in ('start_date', 'completion_date'))
    quality = {'missingness': missingness, 'duplicate_ids': int(frame.nct_id.duplicated().sum()),
               'validation_errors': [], 'partial_date_values': partial, 'warnings': [
        'Registry snapshots are retrospective unless baseline feature provenance is established.',
        f'{partial} date values have month/year precision; preserve that uncertainty when interpreting durations.',
        'Records without exact day-precision ACTUAL start/completion dates, valid ordering, and required outcomes are not duration-training labels.',
        'PCI displays missing components as zero burden; inspect missingness before comparing scores.',
        'Acquired record counts are not model training or evaluation counts; use each model report for eligible records and split support.'
    ]}
    source_sha = hashlib.sha256(metadata_bytes).hexdigest()
    descriptors = [{'file': page['canonical_file'], 'sha256': page['canonical_sha256'],
                    'rows': page['canonical_rows']} for page in source['pages']]
    canonical_sha = hashlib.sha256(json.dumps(descriptors, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    provenance = {key: value for key, value in source.items()
                  if key not in {'pages', 'events', 'next_page_token', 'duplicate_nct_ids'}}
    provenance.update({'source_manifest_sha256': source_sha, 'canonical_sha256': canonical_sha,
        'source_identity_method': 'SHA-256 of the immutable acquisition metadata, which contains raw response and canonical shard checksums.',
        'canonical_identity_method': 'SHA-256 of ordered canonical shard file/hash/row-count descriptors in sorted-key compact JSON.'})
    dataset = {'id': 'registry-v5205',
        'name': 'ClinicalTrials.gov completed drug trials · 101,135 source records',
        'row_count': len(frame),
        'source': 'ClinicalTrials.gov API v2 · complete frozen completed interventional DRUG / Phase I–IV scope',
        'created_at': source['retrieved_at'], 'sha256': source_sha, 'is_fixture': False,
        'quality': quality, 'columns': list(frame), 'original_filename': 'metadata.json',
        'provenance': provenance, 'storage_kind': 'bundled-public-reference', 'canonical_sha256': canonical_sha}
    scores = [calculate_pci(row)[0] for row in frame[list(NUMERIC_FIELDS)].to_dict('records')]
    overview = {'total_studies': len(frame), 'median_pci': round(float(pd.Series(scores).median()), 2),
        'phase_counts': frame.phase.fillna('Not reported').value_counts().to_dict(),
        'status_counts': frame.status.fillna('Unknown').value_counts().to_dict(),
        'enrollment_total': float(pd.to_numeric(frame.enrollment, errors='coerce').sum()),
        'pci_distribution': [{'nct_id': row.nct_id, 'title': row.title, 'pci': score}
                             for row, score in zip(frame.head(100).itertuples(), scores[:100])]}
    result = json_clean({'schema_version': 1, 'source_manifest_sha256': source_sha,
                        'canonical_sha256': canonical_sha, 'dataset': dataset, 'overview': overview})
    if (folder / 'metadata.json').read_bytes() != metadata_bytes:
        raise ValueError('Acquisition metadata changed while deriving the summary.')
    return (json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=ROOT / 'data/registry-v5205')
    parser.add_argument('--check', action='store_true', help='Compare the derived bytes without writing.')
    args = parser.parse_args()
    payload = build_manifest(args.dataset)
    destination = args.dataset / 'runtime-reference.json'
    if args.check:
        if destination.read_bytes() != payload:
            raise ValueError('Bundled runtime summary differs from verified source-derived bytes.')
    else:
        temporary = destination.with_suffix('.json.tmp')
        temporary.write_bytes(payload)
        temporary.replace(destination)
    print(json.dumps({'rows': 101135, 'runtime_manifest_sha256': hashlib.sha256(payload).hexdigest(),
                      'bytes': len(payload), 'verified_existing': args.check}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
