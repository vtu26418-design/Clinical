"""Recover an explicitly incomplete dataset from preserved official API response pages.

Never fills missing strata, fabricates rows or changes saved source bytes. Recovery
is a new provenance event, not a claim that the original acquisition completed.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re
import shutil

from download_starter_data import PERIODS, ENDPOINT, canonical_record, coverage, sha256, utc_now


def recover(source: Path, output: Path, requested_per_period: int) -> dict:
    if not 1 <= requested_per_period <= 10000:
        raise ValueError('Requested maximum per period must be between 1 and 10000.')
    if output.exists():
        raise FileExistsError('Recovery output must be a new directory.')
    rows, pages, ids, observed_pages = [], [], set(), {}
    for path in sorted((source / 'raw').glob('*.json.gz')):
        match = re.fullmatch(r'(\d{4})-(\d{4})-page-(\d{3})\.json\.gz', path.name)
        if not match:
            raise ValueError('Unexpected raw source filename.')
        first, last, page_number = map(int, match.groups())
        if (first, last) not in PERIODS:
            raise ValueError('Unexpected source stratum.')
        expected_page = observed_pages.get((first, last), 0) + 1
        if page_number != expected_page:
            raise ValueError('Recovery requires contiguous source pages beginning at page 1 in every observed stratum.')
        observed_pages[(first, last)] = page_number
        compressed = path.read_bytes()
        payload = gzip.decompress(compressed)
        parsed = json.loads(payload)
        studies = parsed.get('studies')
        if not isinstance(studies, list) or not studies:
            raise ValueError('Saved response must contain a nonempty studies array.')
        for study in studies:
            row = canonical_record(study, first, last)
            if row['nct_id'] in ids:
                raise ValueError('Duplicate source identifier; recovery stopped without silently deduplicating.')
            ids.add(row['nct_id'])
            rows.append(row)
        pages.append({'file': 'raw/' + path.name, 'rows': len(studies),
                      'retrieved_at': None, 'http_date': None,
                      'uncompressed_bytes': len(payload), 'response_sha256': sha256(payload),
                      'gzip_sha256': sha256(compressed),
                      'provenance_note': 'Recovered preserved response; original HTTP headers and retrieval timestamp unavailable.'})
    if not rows:
        raise ValueError('No preserved source rows were found.')
    import pandas as pd
    canonical = pd.DataFrame(rows).to_csv(index=False, lineterminator='\n').encode('utf-8')
    metadata = {
        'dataset_name': 'Recovered partial ClinicalTrials.gov completed drug-trial acquisition',
        'schema_version': 1, 'is_fixture': False, 'source': 'ClinicalTrials.gov API v2',
        'endpoint': ENDPOINT, 'source_documentation': 'https://clinicaltrials.gov/data-api/api',
        'recovered_at': utc_now(), 'retrieved_at': None, 'acquisition_complete': False,
        'recovery_source_directory': source.name,
        'requested_maximum_per_period': requested_per_period,
        'requested_maximum_total': len(PERIODS) * requested_per_period,
        'rows': len(rows), 'duplicate_ids': 0, 'raw_response_pages': pages,
        'coverage': coverage(rows), 'canonical_file': 'trials.csv',
        'canonical_sha256': sha256(canonical), 'canonical_bytes': len(canonical),
        'baseline_provenance': False, 'snapshot_type': 'latest registry state at original requests',
        'not_population_representative': True,
        'sampling_method': 'Interrupted convenience acquisition; only available consecutive raw pages are recovered. Missing strata are not filled.',
        'limitations': ['The original requested acquisition did not complete; this file is a recovered partial dataset.',
                       'Original retrieval times and HTTP headers are not reconstructed or inferred.',
                       'Observed start-period distribution is unbalanced; not population-representative.',
                       'No historical baseline provenance; completed-only selection and retrospective narrative leakage remain.',
                       'Recovery does not certify suitability for training. Raw response hashes enable exact replay.'],
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / 'raw').mkdir()
    for page in pages:
        shutil.copyfile(source / page['file'], output / page['file'])
    (output / 'trials.csv').write_bytes(canonical)
    (output / 'metadata.json').write_text(json.dumps(metadata, indent=2, allow_nan=False) + '\n')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--requested-per-period', type=int, required=True)
    args = parser.parse_args()
    try:
        result = recover(args.source, args.output, args.requested_per_period)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f'Recovery refused: {exc}\n')
    print(json.dumps({'rows': result['rows'], 'acquisition_complete': False,
                      'canonical_sha256': result['canonical_sha256']}, indent=2))


if __name__ == '__main__':
    main()
