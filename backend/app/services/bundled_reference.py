"""The one packaged public registry reference, pinned independently of the DB.

Project metadata never chooses a filesystem path. Canonical shards and preserved
compressed source responses are verified once per unchanged file identity; the
private table cache is never returned to a consumer. No private uploads enter it.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import re
import threading
from pathlib import Path

import pandas as pd

from ..config import PROJECT_ROOT

REFERENCE_ID = 'registry-v5205'
_MANIFEST_SHA256 = '8d603e03147faaeb166358230d23a4c7cea59cddf20c6af207263c26d42ed0c1'


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _signature(path: Path) -> tuple:
    info = path.stat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


class _BundledReference:
    def __init__(self, root: Path, manifest_sha256: str):
        self.root = root.absolute()
        self._manifest_sha256 = manifest_sha256
        self._lock = threading.RLock()
        self._verified = {}
        self._manifest_key = None
        self._manifest = None
        self._source = None
        self._frame_key = None
        self._frame = None

    def _safe_file(self, name: str) -> Path:
        if not isinstance(name, str) or not re.fullmatch(
                r'(metadata\.json|runtime-reference\.json|raw/page-\d{6}\.json\.gz|shards/part-\d{6}\.parquet)', name):
            raise ValueError('Unsafe bundled reference file.')
        path = self.root / name
        # Check every component in the bundle, including its root. Neither a
        # symlinked file nor a symlinked raw/shards directory is trusted.
        for part in (self.root.parent, self.root, *path.relative_to(self.root).parents):
            candidate = part if part.is_absolute() else self.root / part
            if candidate.is_symlink():
                raise OSError('Unsafe bundled reference path.')
        if path.is_symlink() or not path.is_file() or self.root.resolve() not in path.resolve().parents:
            raise OSError('Bundled reference file is unavailable or unsafe.')
        return path

    def _verify(self, name: str, expected: str) -> tuple:
        path = self._safe_file(name)
        before = _signature(path)
        key = (name, expected)
        if self._verified.get(key) != before:
            if _file_sha256(path) != expected or _signature(path) != before:
                raise ValueError('Bundled reference checksum mismatch.')
            self._verified[key] = before
        return before

    def _load_manifests(self):
        runtime_key = self._verify('runtime-reference.json', self._manifest_sha256)
        if self._manifest_key is None or self._manifest_key[0] != runtime_key:
            manifest = self._read_json('runtime-reference.json', self._manifest_sha256)
        else:
            manifest = self._manifest
        source_key = self._verify('metadata.json', manifest['source_manifest_sha256'])
        key = (runtime_key, source_key)
        if self._manifest_key != key:
            source = self._read_json('metadata.json', manifest['source_manifest_sha256'])
            descriptors = [{'file': page['canonical_file'], 'sha256': page['canonical_sha256'],
                            'rows': page['canonical_rows']} for page in source['pages']]
            fingerprint = hashlib.sha256(json.dumps(descriptors, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            if (manifest['schema_version'] != 1 or not source['acquisition_complete']
                    or source['duplicate_ids'] != 0 or source['rows'] != manifest['dataset']['row_count']
                    or manifest['dataset']['id'] != REFERENCE_ID
                    or fingerprint != manifest['canonical_sha256']
                    or sum(page['canonical_rows'] for page in source['pages']) != source['rows']
                    or len({page['canonical_file'] for page in source['pages']}) != len(source['pages'])
                    or self._verify('runtime-reference.json', self._manifest_sha256) != runtime_key
                    or self._verify('metadata.json', manifest['source_manifest_sha256']) != source_key):
                raise ValueError('Bundled reference manifest reconciliation failed.')
            self._manifest, self._source, self._manifest_key = manifest, source, key
        return self._manifest, self._source

    def _read_json(self, name: str, expected: str) -> dict:
        # Verify the exact bytes that are parsed, including a replacement racing
        # with the initial stat/checksum check. Metadata is small and read once.
        payload = self._safe_file(name).read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected:
            raise ValueError('Bundled reference checksum mismatch.')
        return json.loads(payload)

    def metadata(self) -> dict:
        with self._lock:
            manifest, _ = self._load_manifests()
            return copy.deepcopy(manifest['dataset'])

    def overview(self) -> dict:
        with self._lock:
            manifest, _ = self._load_manifests()
            return copy.deepcopy(manifest['overview'])

    def _verified_source_key(self) -> tuple:
        _, source = self._load_manifests()
        identities = []
        for page in source['pages']:
            identities.append(self._verify(page['file'], page['gzip_sha256']))
            identities.append(self._verify(page['canonical_file'], page['canonical_sha256']))
        return (self._manifest_key, *identities)

    def fingerprint(self) -> str:
        with self._lock:
            self._verified_source_key()
            return self._manifest['canonical_sha256']

    def source_manifest_path(self) -> Path:
        with self._lock:
            self._load_manifests()
            return self._safe_file('metadata.json')

    def frame(self) -> pd.DataFrame:
        with self._lock:
            key = self._verified_source_key()
            if self._frame is None or self._frame_key != key:
                # Arrow promotes all-null source shards without changing source
                # values or relying on pandas' deprecated concat inference.
                import pyarrow as pa
                tables = []
                for page in self._source['pages']:
                    payload = self._safe_file(page['canonical_file']).read_bytes()
                    if hashlib.sha256(payload).hexdigest() != page['canonical_sha256']:
                        raise ValueError('Bundled reference checksum mismatch.')
                    part = pd.read_parquet(io.BytesIO(payload))
                    if len(part) != page['canonical_rows']:
                        raise ValueError('Bundled reference shard row count differs.')
                    tables.append(pa.Table.from_pandas(part, preserve_index=False))
                frame = pa.concat_tables(tables, promote_options='permissive').to_pandas()
                if (len(frame) != self._source['rows'] or frame.nct_id.isna().any()
                        or frame.nct_id.duplicated().any() or list(frame) != self._manifest['dataset']['columns']
                        or self._verified_source_key() != key):
                    raise ValueError('Bundled reference data reconciliation failed.')
                self._frame, self._frame_key = frame, key
            return self._frame.copy(deep=True)


# This fixed code-owned path is the only public bundle recognized at runtime.
REFERENCE = _BundledReference(PROJECT_ROOT / 'data/registry-v5205', _MANIFEST_SHA256)
