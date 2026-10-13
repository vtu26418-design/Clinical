"""Acquire a real, auditable ClinicalTrials.gov convenience subset into a new directory.

No generated records, date imputation, model fitting, or silent data fallback.
The API is a live registry: exact replay uses the bundled raw response bytes;
running this downloader again is a new acquisition and may return changed data.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from backend.app.services.clinicaltrials_service import ENDPOINT, _record

PERIODS = ((2000, 2005), (2006, 2011), (2012, 2017), (2018, 2023))
PHASES = {"PHASE1", "PHASE2", "PHASE3", "PHASE4"}


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def query_for_period(first: int, last: int) -> str:
    return (
        "AREA[StudyType]INTERVENTIONAL AND AREA[OverallStatus]COMPLETED "
        "AND AREA[InterventionType]DRUG "
        "AND (AREA[Phase]PHASE1 OR AREA[Phase]PHASE2 OR AREA[Phase]PHASE3 OR AREA[Phase]PHASE4) "
        f"AND AREA[StartDate]RANGE[{first}-01-01,{last}-12-31]"
    )


def canonical_record(study: dict, first: int, last: int) -> dict:
    """Check registry scope without selecting records by observed duration."""
    protocol = study.get("protocolSection") or {}
    design = protocol.get("designModule") or {}
    arms = protocol.get("armsInterventionsModule") or {}
    row = _record(study)
    intervention_types = sorted({v.get("type", "") for v in arms.get("interventions", [])})
    if (
        row["study_type"] != "INTERVENTIONAL"
        or row["status"] != "COMPLETED"
        or "DRUG" not in intervention_types
        or not PHASES.intersection(design.get("phases", []))
        or not row.get("start_date")
        or not first <= int(row["start_date"][:4]) <= last
        or not row.get("nct_id")
    ):
        raise ValueError("Registry returned a record outside the requested scope; acquisition stopped.")
    row["detailed_description"] = (protocol.get("descriptionModule") or {}).get("detailedDescription", "")
    row["intervention_types"] = "|".join(intervention_types)
    row["starter_start_period"] = f"{first}-{last}"
    return row


def fetch_response(params: dict, remaining_bytes: int) -> tuple[bytes, str]:
    """Use only the official HTTPS endpoint; bound memory and retry transient errors."""
    url = ENDPOINT + "?" + urlencode(params)
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "CTI-Research-Starter/3"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=45) as response:
                if not response.url.startswith(ENDPOINT + "?"):
                    raise ValueError("Unexpected registry redirect; acquisition stopped.")
                payload = response.read(remaining_bytes + 1)
                if len(payload) > remaining_bytes:
                    raise ValueError("Registry responses exceeded --max-bytes; acquisition stopped.")
                return payload, response.headers.get("Date", "")
        except HTTPError as exc:
            if attempt == 2 or exc.code not in (429, 500, 502, 503, 504):
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)
    raise RuntimeError("Registry acquisition failed.")


def coverage(rows: list[dict]) -> dict:
    counts = lambda key: dict(sorted(Counter(str(row.get(key) or "Not reported") for row in rows).items()))
    exact_pairs = sum(
        len(row.get("start_date") or "") == 10
        and len(row.get("completion_date") or "") == 10
        and row.get("completion_date_type") == "ACTUAL"
        for row in rows
    )
    return {
        "start_period_counts": counts("starter_start_period"),
        "start_year_counts": dict(sorted(Counter(row["start_date"][:4] for row in rows).items())),
        "phase_counts": counts("phase"),
        "status_counts": counts("status"),
        "study_type_counts": counts("study_type"),
        "start_date_min": min(row["start_date"] for row in rows),
        "start_date_max": max(row["start_date"] for row in rows),
        "completion_date_type_counts": counts("completion_date_type"),
        "exact_start_and_actual_completion_date_rows": exact_pairs,
        "partial_start_date_rows": sum(0 < len(row.get("start_date") or "") < 10 for row in rows),
        "partial_completion_date_rows": sum(0 < len(row.get("completion_date") or "") < 10 for row in rows),
    }


def acquire(output_dir: Path, per_period: int = 200, max_bytes: int = 256 * 1024 * 1024) -> dict:
    if not 1 <= per_period <= 10000:
        raise ValueError("--per-period must be between 1 and 10000.")
    if max_bytes < 1024:
        raise ValueError("--max-bytes must be at least 1024.")
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "raw").mkdir()
    started_at = utc_now()
    rows, pages, strata, seen_ids = [], [], [], set()
    total_bytes = 0
    try:
        for first, last in PERIODS:
            query = query_for_period(first, last)
            token, seen_tokens, collected, page_number = None, set(), 0, 0
            while collected < per_period:
                params = {"query.term": query, "format": "json", "pageSize": min(100, per_period - collected), "countTotal": "true"}
                if token:
                    params["pageToken"] = token
                payload, server_date = fetch_response(params, max_bytes - total_bytes)
                total_bytes += len(payload)
                retrieved_at = utc_now()
                parsed = json.loads(payload)
                if not isinstance(parsed, dict) or not isinstance(parsed.get("studies"), list):
                    raise ValueError("Registry returned an unexpected response format.")
                studies = parsed["studies"]
                if len(studies) > params["pageSize"]:
                    raise ValueError("Registry returned more records than requested.")
                page_number += 1
                filename = f"raw/{first}-{last}-page-{page_number:03d}.json.gz"
                compressed = gzip.compress(payload, mtime=0)
                with (output_dir / filename).open("xb") as raw_file:
                    raw_file.write(compressed)
                pages.append({"file": filename, "request_parameters": params, "retrieved_at": retrieved_at,
                              "http_date": server_date, "rows": len(studies), "uncompressed_bytes": len(payload),
                              "response_sha256": sha256(payload), "gzip_sha256": sha256(compressed)})
                for study in studies:
                    row = canonical_record(study, first, last)
                    if row["nct_id"] in seen_ids:
                        raise ValueError("Registry returned a duplicate study identifier; acquisition stopped.")
                    seen_ids.add(row["nct_id"])
                    rows.append(row)
                collected += len(studies)
                print(f"{first}-{last}: {collected}/{per_period} records acquired", flush=True)
                token = parsed.get("nextPageToken")
                if not token:
                    break
                if not studies or token in seen_tokens:
                    raise ValueError("Registry pagination did not advance; acquisition stopped.")
                seen_tokens.add(token)
            strata.append({"start_year_min": first, "start_year_max": last, "query": query,
                           "requested_maximum": per_period, "rows": collected, "last_reported_total_count": parsed.get("totalCount")})
        if not rows:
            raise ValueError("Registry returned no records; no canonical dataset was written.")
        canonical = pd.DataFrame(rows).to_csv(index=False, lineterminator="\n").encode("utf-8")
        metadata = {
            "dataset_name": "ClinicalTrials.gov completed drug-trial starter cohort",
            "schema_version": 1, "is_fixture": False, "source": "ClinicalTrials.gov API v2",
            "endpoint": ENDPOINT, "source_documentation": "https://clinicaltrials.gov/data-api/api",
            "acquisition_started_at": started_at, "retrieved_at": utc_now(),
            "snapshot_type": "latest registry state", "baseline_provenance": False,
            "sampling_method": "Convenience subset: first API-returned records in each fixed start-date stratum; default API order, no outcome-duration or model-performance selection.",
            "not_population_representative": True, "requested_maximum_per_period": per_period,
            "rows": len(rows), "duplicate_ids": 0, "strata": strata,
            "canonical_file": "trials.csv", "canonical_sha256": sha256(canonical),
            "canonical_bytes": len(canonical), "raw_response_pages": pages,
            "coverage": coverage(rows),
            "date_policy": "Preserve original registry date strings and ACTUAL/ESTIMATED labels; no day/month/year imputation. Training excludes partial dates.",
            "missingness_policy": "Source-missing values remain missing. criteria_count and text_complexity are not invented.",
            "limitations": ["Not a frozen historical baseline snapshot.", "Not a population-representative or exhaustive registry export.",
                            "Completed-trial restriction creates selection bias; no censored trials are represented.",
                            "Results support a reproducible retrospective workflow demonstration, not validated prospective or clinical claims.",
                            "The live API may change. Exact bundled-data reproduction uses the preserved raw responses and checksums."],
        }
        with (output_dir / "trials.csv").open("xb") as canonical_file:
            canonical_file.write(canonical)
        with (output_dir / "metadata.json").open("x", encoding="utf-8") as metadata_file:
            json.dump(metadata, metadata_file, indent=2, ensure_ascii=False)
            metadata_file.write("\n")
        return metadata
    except Exception as exc:
        # Preserve fetched source bytes for inspection; never substitute fixtures.
        with (output_dir / "DOWNLOAD_FAILED.json").open("x", encoding="utf-8") as failure:
            json.dump({"failed_at": utc_now(), "error": str(exc), "completed_raw_pages": len(pages),
                       "usable_dataset": False}, failure, indent=2)
        raise


def replay(source_dir: Path, output_dir: Path) -> dict:
    """Rebuild identical canonical bytes from preserved pages without network access."""
    if output_dir.exists():
        raise FileExistsError("Output directory already exists; choose a new path.")
    metadata_bytes = (source_dir / "metadata.json").read_bytes()
    metadata = json.loads(metadata_bytes)
    rows, source_files = [], []
    for page in metadata["raw_response_pages"]:
        match = re.fullmatch(r"raw/(\d{4})-(\d{4})-page-\d{3}\.json\.gz", page["file"])
        if not match:
            raise ValueError("Unexpected raw response path in metadata.")
        first, last = map(int, match.groups())
        if (first, last) not in PERIODS:
            raise ValueError("Unexpected source stratum in metadata.")
        compressed = (source_dir / page["file"]).read_bytes()
        if sha256(compressed) != page["gzip_sha256"]:
            raise ValueError("Raw compressed response checksum mismatch.")
        payload = gzip.decompress(compressed)
        if sha256(payload) != page["response_sha256"]:
            raise ValueError("Raw response checksum mismatch.")
        studies = json.loads(payload)["studies"]
        if len(studies) != page["rows"]:
            raise ValueError("Raw response row count mismatch.")
        rows.extend(canonical_record(study, first, last) for study in studies)
        source_files.append((page["file"], compressed))
    canonical = pd.DataFrame(rows).to_csv(index=False, lineterminator="\n").encode("utf-8")
    if len(rows) != metadata["rows"] or len({row["nct_id"] for row in rows}) != len(rows):
        raise ValueError("Source row count or identifier uniqueness check failed.")
    if sha256(canonical) != metadata["canonical_sha256"]:
        raise ValueError("Canonical replay checksum mismatch; inspect the pinned environment and source files.")
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "raw").mkdir()
    for filename, payload in source_files + [("trials.csv", canonical), ("metadata.json", metadata_bytes)]:
        with (output_dir / filename).open("xb") as output:
            output.write(payload)
    receipt = {"reproduced_at": utc_now(), "metadata_sha256": sha256(metadata_bytes),
               "canonical_sha256": sha256(canonical), "rows": len(rows), "network_used": False}
    with (output_dir / "replay_receipt.json").open("x", encoding="utf-8") as output:
        json.dump(receipt, output, indent=2)
        output.write("\n")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path, help="New output directory; existing directories are never overwritten")
    parser.add_argument("--per-period", type=int, default=200, help="Maximum records for each of four fixed start periods (default: 200)")
    parser.add_argument("--max-bytes", type=int, default=256 * 1024 * 1024, help="Maximum total uncompressed API response bytes")
    parser.add_argument("--replay-from", type=Path, help="Reproduce canonical data from this saved acquisition without network access")
    args = parser.parse_args()
    try:
        metadata = replay(args.replay_from, args.output_dir) if args.replay_from else acquire(args.output_dir, args.per_period, args.max_bytes)
    except Exception as exc:
        parser.exit(1, f"Starter acquisition failed: {exc}\nNo fabricated fallback was used. Choose a new output directory to retry.\n")
    print(f"Saved {metadata['rows']} authentic registry records to {args.output_dir}; SHA-256 {metadata['canonical_sha256']}")


if __name__ == "__main__":
    main()
