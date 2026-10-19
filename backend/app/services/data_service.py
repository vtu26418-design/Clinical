"""Immutable project uploads and a trusted packaged public registry reference.

PostgreSQL stores project metadata; private files remain under STORAGE_DIR.
The public reference uses fixed, checksum-pinned files shared across projects.
"""
from __future__ import annotations

import hashlib
import csv
from calendar import monthrange
import io
import json
import math
import re
import shutil
import tempfile
import threading
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ..config import PROJECT_ROOT, Settings
from .bundled_reference import REFERENCE, REFERENCE_ID

NUMERIC_FIELDS = ('enrollment', 'number_of_arms', 'primary_outcomes', 'secondary_outcomes', 'criteria_count', 'text_complexity')
TEXT_DEFAULTS = {'study_type': 'Unknown', 'phase': 'Not reported', 'status': 'Unknown', 'brief_summary': '', 'eligibility_criteria': '', 'completion_date_type': 'Not reported'}
DATE_FIELDS = ('start_date', 'completion_date')
SAMPLE_ID = 'sample-fixture'
csv.field_size_limit(100 * 1024 * 1024)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_clean(value):
    if isinstance(value, dict):
        return {str(k): json_clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_clean(v) for v in value]
    if value is None:
        return None
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        return value if math.isfinite(value) else None
    if hasattr(value, 'item'):
        return json_clean(value.item())
    if pd.isna(value):
        return None
    return value


class DatasetValidationError(ValueError):
    def __init__(self, errors: list[dict]):
        self.errors = errors[:100]
        super().__init__('Dataset validation failed. No records were imported.')


def validate_frame(df: pd.DataFrame, max_rows: int) -> tuple[pd.DataFrame, dict]:
    errors = []
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    if df.columns.duplicated().any():
        errors.append({'field': 'columns', 'message': 'Duplicate column names are not allowed.'})
    for required in ('nct_id', 'title'):
        if required not in df.columns:
            errors.append({'field': required, 'message': 'Required column is missing.'})
    if not len(df) or len(df) > max_rows:
        errors.append({'field': 'rows', 'message': f'Provide between 1 and {max_rows} records.'})
    if len(df.columns) > 100:
        errors.append({'field': 'columns', 'message': 'At most 100 columns are supported.'})
    if errors:
        raise DatasetValidationError(errors)
    for column in df.columns:
        # Canonical tabular fields are scalar; nested values are never silently stringified.
        bad = df[column].map(lambda v: not pd.api.types.is_scalar(v) or isinstance(v, bytes))
        for index in df.index[bad][:10]:
            errors.append({'row': int(index) + 2, 'field': column, 'message': 'Expected a scalar value.'})
    if errors:
        raise DatasetValidationError(errors)
    for column in ('nct_id', 'title'):
        df[column] = df[column].fillna('').astype(str).str.strip()
        for index in df.index[df[column].eq('')][:10]:
            errors.append({'row': int(index) + 2, 'field': column, 'message': 'Value must not be empty.'})
    for index in df.index[df['nct_id'].duplicated(keep=False)][:20]:
        errors.append({'row': int(index) + 2, 'field': 'nct_id', 'message': 'Duplicate study identifier.'})
    for column in NUMERIC_FIELDS:
        if column not in df:
            df[column] = None
        present = df[column].notna() & df[column].astype(str).str.strip().ne('')
        numeric = pd.to_numeric(df[column], errors='coerce')
        invalid = present & (numeric.isna() | numeric.lt(0) | numeric.map(lambda v: pd.notna(v) and not math.isfinite(v)))
        for index in df.index[invalid][:10]:
            errors.append({'row': int(index) + 2, 'field': column, 'message': 'Expected a finite non-negative number.'})
        df[column] = numeric
    partial_dates = 0
    for column in DATE_FIELDS:
        if column not in df:
            df[column] = None
        def date_text(value):
            if pd.isna(value) or str(value).strip() == '':
                return None
            # Parquet date/timestamp fields are accepted only at day precision.
            if isinstance(value, (date, datetime)):
                timestamp = pd.Timestamp(value)
                if timestamp == timestamp.normalize():
                    return timestamp.date().isoformat()
            return str(value).strip()
        df[column] = df[column].map(date_text)
        for index, value in df[column].items():
            if value is None:
                continue
            try:
                if not re.fullmatch(r'\d{4}(-\d{2}){0,2}', value):
                    raise ValueError('format')
                pd.Timestamp(value)
                partial_dates += len(value) < 10
            except (ValueError, TypeError, OverflowError):
                errors.append({'row': int(index) + 2, 'field': column, 'message': 'Expected a valid ISO date (YYYY-MM-DD, YYYY-MM, or YYYY).'})
                if len(errors) >= 100:
                    break
    if errors:
        raise DatasetValidationError(errors)
    for index, row in df.iterrows():
        start, completion = row['start_date'], row['completion_date']
        if not start or not completion:
            continue
        # A partial date denotes an interval. Reject only a definitely inverted
        # order; duration training separately requires exact day precision.
        start_lower = start + ('-01-01' if len(start) == 4 else '-01' if len(start) == 7 else '')
        if len(completion) == 4:
            completion_upper = completion + '-12-31'
        elif len(completion) == 7:
            completion_upper = completion + f'-{monthrange(int(completion[:4]), int(completion[5:]))[1]:02d}'
        else:
            completion_upper = completion
        if completion_upper < start_lower:
            errors.append({'row': int(index) + 2, 'field': 'completion_date', 'message': 'Completion precedes start date.'})
            if len(errors) >= 100:
                break
    if errors:
        raise DatasetValidationError(errors)
    for column in TEXT_DEFAULTS:
        if column not in df:
            df[column] = None
    missingness = {c: int((df[c].isna() | df[c].astype(str).str.strip().eq('')).sum()) for c in df.columns}
    for column, default in TEXT_DEFAULTS.items():
        df[column] = df[column].fillna(default).astype(str).str.strip().replace('', default)
    warnings = ['Registry snapshots are retrospective unless baseline feature provenance is established.']
    if partial_dates:
        warnings.append(f'{partial_dates} date values have month/year precision; preserve that uncertainty when interpreting durations.')
    if df['completion_date_type'].str.upper().ne('ACTUAL').any():
        warnings.append('Records without an explicitly ACTUAL completion date are excluded from duration training.')
    if any(missingness[c] for c in NUMERIC_FIELDS):
        warnings.append('PCI displays missing components as zero burden; inspect missingness before comparing scores.')
    return df, {'missingness': missingness, 'duplicate_ids': 0, 'validation_errors': [], 'warnings': warnings, 'partial_date_values': partial_dates}


class DatasetRegistry:
    def __init__(self, config: Settings):
        url = config.postgres_url
        self.config = config
        self.root = config.store_path
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / 'datasets').mkdir(exist_ok=True)
        (self.root / 'experiments').mkdir(exist_ok=True)
        self.lock = threading.RLock()
        from sqlalchemy import create_engine, text
        schema = config.database_schema or 'cti_research'
        if not re.fullmatch(r'cti_[a-z0-9_]{1,59}', schema):
            raise ValueError('Invalid database schema.')
        args = {'connect_timeout': 10}
        admin_engine = create_engine(url, pool_pre_ping=True, connect_args=args)
        try:
            with admin_engine.begin() as conn:
                conn.execute(text('CREATE SCHEMA IF NOT EXISTS ' + schema))
                conn.execute(text('REVOKE ALL ON SCHEMA ' + schema + ' FROM PUBLIC'))
        finally:
            admin_engine.dispose()
        self.engine = create_engine(url, pool_pre_ping=True,
                                    connect_args={**args, 'options': '-csearch_path=' + schema})
        self._execute('CREATE TABLE IF NOT EXISTS datasets (id VARCHAR(80) PRIMARY KEY, payload TEXT NOT NULL)')
        self._execute('CREATE TABLE IF NOT EXISTS experiments (id VARCHAR(80) PRIMARY KEY, payload TEXT NOT NULL)')
        if self.get_dataset(SAMPLE_ID) is None:
            sample = (PROJECT_ROOT / 'data/sample/trials.csv').read_bytes()
            self.register_bytes(sample, 'bundled-sample.csv', name='Bundled software-test fixtures (5 studies)', source='bundled software-test fixtures', is_fixture=True, dataset_id=SAMPLE_ID)
        # Only a small metadata payload is registered per project. The public
        # 100k-record table remains lazy and is never copied into project storage.
        reference = REFERENCE.metadata()
        self._execute('INSERT INTO datasets (id,payload) VALUES (:id,:payload) ON CONFLICT(id) DO NOTHING',
                      {'id': REFERENCE_ID, 'payload': json.dumps(reference, allow_nan=False)})

    def _execute(self, sql: str, params: dict | None = None, fetch=False):
        with self.lock:
            from sqlalchemy import text
            with self.engine.begin() as conn:
                result = conn.execute(text(sql), params or {})
                return result.fetchall() if fetch else None

    def _list(self, table: str) -> list[dict]:
        return [json.loads(row[0]) for row in self._execute(f'SELECT payload FROM {table}', fetch=True)]

    def list_datasets(self) -> list[dict]:
        rows = [REFERENCE.metadata() if row.get('id') == REFERENCE_ID else row for row in self._list('datasets')]
        return sorted(rows, key=lambda row: (not row['is_fixture'], row['created_at']))

    def get_dataset(self, dataset_id: str) -> dict | None:
        rows = self._execute('SELECT payload FROM datasets WHERE id=:id', {'id': dataset_id}, fetch=True)
        if rows and dataset_id == REFERENCE_ID:
            # DB metadata cannot replace the code-pinned reference identity.
            return REFERENCE.metadata()
        return json.loads(rows[0][0]) if rows else None

    @property
    def preferred_dataset_id(self) -> str:
        return REFERENCE_ID

    def reference_overview(self, dataset_id: str) -> dict | None:
        if dataset_id == REFERENCE_ID and self.get_dataset(dataset_id) is not None:
            return REFERENCE.overview()
        return None

    def dataset_path(self, dataset_id: str) -> Path:
        # Callers cannot smuggle paths through dataset IDs, even if the DB is edited.
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', dataset_id) or self.get_dataset(dataset_id) is None:
            raise KeyError(dataset_id)
        if dataset_id == REFERENCE_ID:
            REFERENCE.metadata()
            return REFERENCE.root
        return self.root / 'datasets' / dataset_id

    def raw_path(self, dataset_id: str) -> Path:
        if dataset_id == REFERENCE_ID:
            self.dataset_path(dataset_id)
            # The public source is multi-file; this pinned manifest identifies
            # every preserved raw response instead of inventing a combined file.
            return REFERENCE.source_manifest_path()
        return self.dataset_path(dataset_id) / 'raw.bin'

    def canonical_fingerprint(self, dataset_id: str) -> str:
        if dataset_id == REFERENCE_ID:
            self.dataset_path(dataset_id)
            return REFERENCE.fingerprint()
        path = self._private_canonical_path(dataset_id)
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        return digest.hexdigest()

    def _private_canonical_path(self, dataset_id: str) -> Path:
        folder = self.dataset_path(dataset_id)
        path = folder / 'canonical.csv'
        if (folder.parent.is_symlink() or folder.is_symlink() or path.is_symlink()
                or path.resolve().parent != folder.resolve()):
            raise OSError('Unsafe dataset path.')
        return path

    def frame(self, dataset_id: str) -> pd.DataFrame:
        if dataset_id == REFERENCE_ID:
            self.dataset_path(dataset_id)
            return REFERENCE.frame()
        return pd.read_csv(self._private_canonical_path(dataset_id), keep_default_na=False, na_values=[''],
                           dtype={field: str for field in ('nct_id', 'title', *TEXT_DEFAULTS, *DATE_FIELDS)})

    def register_bytes(self, raw: bytes, filename: str, *, name: str | None = None, source: str = 'user upload', is_fixture=False, dataset_id: str | None = None, provenance: dict | None = None, canonical_frame: pd.DataFrame | None = None) -> dict:
        if len(raw) > self.config.max_upload_bytes:
            raise DatasetValidationError([{'field': 'file', 'message': f'File exceeds {self.config.max_upload_bytes} bytes.'}])
        if canonical_frame is None:
            suffix = Path(filename).suffix.lower()
            try:
                if suffix == '.csv':
                    # Disable broad NA tokens: e.g. phase NA is a legitimate registry value.
                    reader = csv.reader(io.StringIO(raw.decode('utf-8-sig')), strict=True)
                    header = next(reader, [])
                    cleaned_header = [field.strip() for field in header]
                    if len(set(cleaned_header)) != len(cleaned_header) or any(not field for field in cleaned_header):
                        raise DatasetValidationError([{'field': 'columns', 'message': 'Column names must be unique and non-empty.'}])
                    for row_number, values in enumerate(reader, start=2):
                        if values and len(values) != len(header):
                            raise DatasetValidationError([{'row': row_number, 'field': 'columns', 'message': 'Every CSV record must have the same number of fields as the header.'}])
                    canonical_frame = pd.read_csv(io.BytesIO(raw), keep_default_na=False, na_values=[''], dtype=str)
                elif suffix == '.json':
                    from .tabular_import import json_frame
                    canonical_frame = json_frame(raw)
                elif suffix == '.xlsx':
                    from .tabular_import import xlsx_frame
                    canonical_frame = xlsx_frame(raw, self.config)
                elif suffix in ('.parquet', '.pq'):
                    canonical_frame = pd.read_parquet(io.BytesIO(raw))
                else:
                    raise DatasetValidationError([{'field': 'file', 'message': 'Only CSV, JSON record arrays, XLSX and Parquet files are accepted.'}])
            except DatasetValidationError:
                raise
            except Exception as exc:
                raise DatasetValidationError([{'field': 'file', 'message': 'Could not parse the supplied file. Use valid CSV, flat JSON records, a bounded XLSX first worksheet, or Parquet.'}]) from exc
        frame, quality = validate_frame(canonical_frame.reset_index(drop=True), self.config.max_dataset_rows)
        identifier = dataset_id or uuid.uuid4().hex
        metadata = {'id': identifier, 'name': (name or Path(filename).name)[:120], 'row_count': len(frame), 'source': source, 'created_at': now(), 'sha256': hashlib.sha256(raw).hexdigest(), 'is_fixture': bool(is_fixture), 'quality': quality, 'columns': list(frame.columns), 'original_filename': Path(filename).name[:160], 'provenance': provenance or {}}
        staging = Path(tempfile.mkdtemp(prefix='upload-', dir=self.root))
        destination = self.root / 'datasets' / identifier
        moved = False
        try:
            (staging / 'raw.bin').write_bytes(raw)
            frame.to_csv(staging / 'canonical.csv', index=False)
            with self.lock:
                if self.get_dataset(identifier) is not None:
                    raise ValueError('Dataset already exists.')
                staging.replace(destination)
                moved = True
                self._execute('INSERT INTO datasets (id,payload) VALUES (:id,:payload)', {'id': identifier, 'payload': json.dumps(metadata)})
        except Exception as exc:
            shutil.rmtree(destination if moved else staging, ignore_errors=True)
            raise RuntimeError('Dataset files and metadata could not be saved atomically.') from exc
        return metadata

    def list_experiments(self, dataset_id: str | None = None) -> list[dict]:
        records = self._list('experiments')
        if dataset_id:
            records = [record for record in records if record['dataset_id'] == dataset_id]
        return sorted(records, key=lambda record: record['created_at'], reverse=True)

    def get_experiment(self, experiment_id: str) -> dict | None:
        rows = self._execute('SELECT payload FROM experiments WHERE id=:id', {'id': experiment_id}, fetch=True)
        return json.loads(rows[0][0]) if rows else None

    def save_experiment(self, record: dict):
        payload = json.dumps(json_clean(record), allow_nan=False)
        self._execute('INSERT INTO experiments (id,payload) VALUES (:id,:payload) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', {'id': record['id'], 'payload': payload})

    def artifact_path(self, experiment_id: str) -> Path:
        if not re.fullmatch(r'[a-f0-9]{32}', experiment_id):
            raise ValueError('Invalid experiment identifier.')
        return self.root / 'experiments' / experiment_id
