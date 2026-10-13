"""Recovery checks use authentic bundled source bytes, never generated trial records."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_interrupted_download_recovers_only_verified_preserved_rows(tmp_path):
    source = tmp_path / 'partial'
    (source / 'raw').mkdir(parents=True)
    original = ROOT / 'data/starter/raw/2000-2005-page-001.json.gz'
    shutil.copyfile(original, source / 'raw' / original.name)
    output = tmp_path / 'recovered'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/recover_registry_acquisition.py'),
        '--source', str(source), '--output', str(output), '--requested-per-period', '1000'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    metadata = json.loads((output / 'metadata.json').read_text())
    assert metadata['rows'] == 100
    assert metadata['requested_maximum_total'] == 4000
    assert metadata['acquisition_complete'] is False
    assert metadata['is_fixture'] is False
    assert metadata['retrieved_at'] is None
    assert metadata['coverage']['start_period_counts'] == {'2000-2005': 100}
    assert metadata['canonical_sha256'] == hashlib.sha256((output / 'trials.csv').read_bytes()).hexdigest()
    assert (output / 'raw' / original.name).read_bytes() == original.read_bytes()
    assert (source / 'raw' / original.name).read_bytes() == original.read_bytes()
    replay = subprocess.run([sys.executable, str(ROOT / 'scripts/download_starter_data.py'), '--replay-from', str(output),
        '--output-dir', str(tmp_path / 'replay')], capture_output=True, text=True)
    assert replay.returncode == 0, replay.stderr
    assert (tmp_path / 'replay/trials.csv').read_bytes() == (output / 'trials.csv').read_bytes()
