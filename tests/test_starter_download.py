"""Starter-source integrity and safe acquisition failures; no network calls."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("starter_downloader", ROOT / "scripts/download_starter_data.py")
downloader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(downloader)


def test_acquisition_never_overwrites_existing_directory(tmp_path, monkeypatch):
    marker = tmp_path / "keep.txt"
    marker.write_text("untouched")
    monkeypatch.setattr(downloader, "fetch_response", lambda *_: pytest.fail("Existing output must fail before network access"))
    with pytest.raises(FileExistsError):
        downloader.acquire(tmp_path)
    assert marker.read_text() == "untouched"


def test_acquisition_failure_has_no_canonical_or_fixture_fallback(tmp_path, monkeypatch):
    def fail(*_):
        raise OSError("Network unavailable")
    monkeypatch.setattr(downloader, "fetch_response", fail)
    target = tmp_path / "new-acquisition"
    with pytest.raises(OSError, match="Network unavailable"):
        downloader.acquire(target)
    assert not (target / "trials.csv").exists()
    assert not (target / "metadata.json").exists()
    assert json.loads((target / "DOWNLOAD_FAILED.json").read_text())["usable_dataset"] is False


def test_bundled_source_bytes_reproduce_canonical_without_date_imputation():
    target = ROOT / "data/starter"
    metadata = json.loads((target / "metadata.json").read_text())
    rows = []
    for page in metadata["raw_response_pages"]:
        compressed = (target / page["file"]).read_bytes()
        assert hashlib.sha256(compressed).hexdigest() == page["gzip_sha256"]
        payload = gzip.decompress(compressed)
        assert hashlib.sha256(payload).hexdigest() == page["response_sha256"]
        first, last = map(int, Path(page["file"]).name.split("-")[:2])
        studies = json.loads(payload)["studies"]
        assert len(studies) == page["rows"]
        for study in studies:
            row = downloader.canonical_record(study, first, last)
            status = study["protocolSection"]["statusModule"]
            assert row["start_date"] == status.get("startDateStruct", {}).get("date")
            assert row["completion_date"] == status.get("completionDateStruct", {}).get("date")
            rows.append(row)
    regenerated = pd.DataFrame(rows).to_csv(index=False, lineterminator="\n").encode("utf-8")
    assert regenerated == (target / "trials.csv").read_bytes()
    assert hashlib.sha256(regenerated).hexdigest() == metadata["canonical_sha256"]
    assert len(rows) == metadata["rows"]
    assert len({row["nct_id"] for row in rows}) == len(rows)
    assert metadata["is_fixture"] is False
    assert metadata["baseline_provenance"] is False
    assert metadata["not_population_representative"] is True
