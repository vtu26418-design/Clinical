"""Read frozen AACT protocol flat files without modifying raw source bytes.

Supported: headered UTF-8 pipe-delimited .txt and comma-delimited .csv tables.
Posted-results tables are deliberately excluded from protocol feature extraction.
"""
from datetime import date
import csv
import hashlib
from pathlib import Path
import re

import numpy as np
import pandas as pd

MAPPING_VERSION = "aact-protocol-flatfiles-v1"
TABLE_COLUMNS = {
    "studies": {"nct_id", "brief_title", "official_title", "overall_status", "start_date", "start_date_type", "completion_date", "completion_date_type", "study_type", "phase", "enrollment", "enrollment_type", "number_of_arms"},
    "design_outcomes": {"nct_id", "id", "outcome_type"},
    "design_groups": {"nct_id", "id"},
    "eligibilities": {"nct_id", "criteria"},
    "brief_summaries": {"nct_id", "description"},
    "detailed_descriptions": {"nct_id", "description"},
    "conditions": {"nct_id", "name"},
    "sponsors": {"nct_id", "name", "lead_or_collaborator"},
}
REQUIRED_COLUMNS = {
    "studies": {"nct_id", "overall_status", "start_date", "completion_date", "completion_date_type"},
    "design_outcomes": {"nct_id", "outcome_type"}, "design_groups": {"nct_id"},
    "eligibilities": {"nct_id", "criteria"}, "brief_summaries": {"nct_id", "description"},
    "detailed_descriptions": {"nct_id", "description"}, "conditions": {"nct_id", "name"},
    "sponsors": {"nct_id", "name", "lead_or_collaborator"},
}


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _files(directory: str | Path) -> dict:
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError("AACT input must be a directory of extracted .txt or .csv flat files.")
    files = {}
    for name in TABLE_COLUMNS:
        matches = [p for p in directory.iterdir() if p.is_file() and p.stem.lower() == name and p.suffix.lower() in (".csv", ".txt")]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous AACT table {name}: leave one frozen table file per name.")
        if matches:
            files[name] = matches[0]
    if "studies" not in files:
        raise ValueError("Missing required AACT studies.txt or studies.csv table.")
    return files


def _read(path: Path, **kwargs):
    return pd.read_csv(path, sep="|" if path.suffix.lower() == ".txt" else ",", dtype=str,
                       encoding="utf-8-sig", keep_default_na=False, na_values=["", r"\N"], **kwargs)


def _scan_table(path: Path, name: str) -> tuple[list[str], int]:
    """Validate raw records before pandas can rename headers or infer an index."""
    # Long protocol narratives are valid fields; bound an individual field to
    # the same generous limit used by canonical CSV imports.
    csv.field_size_limit(100 * 1024 * 1024)
    try:
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source, delimiter="|" if path.suffix.lower() == ".txt" else ",", strict=True)
            columns = next(reader, [])
            cleaned = [column.strip() for column in columns]
            if not columns or any(not column for column in cleaned) or len(set(cleaned)) != len(cleaned):
                raise ValueError(f"AACT {name} column names must be unique and non-empty.")
            missing = REQUIRED_COLUMNS[name] - set(columns)
            if missing:
                raise ValueError(f"AACT {name} missing columns: {', '.join(sorted(missing))}")
            identifier_column = columns.index("nct_id")
            row_count, ids = 0, set()
            for record in reader:
                if not record:  # Empty physical lines are not data records.
                    continue
                if len(record) != len(columns):
                    raise ValueError(f"AACT {name} record ending at line {reader.line_num} has {len(record)} fields; expected {len(columns)}.")
                identifier = record[identifier_column].strip()
                if identifier in ("", r"\N"):
                    raise ValueError(f"AACT {name} contains missing nct_id values.")
                if name == "studies":
                    if identifier in ids:
                        raise ValueError("Duplicate nct_id values in AACT studies table.")
                    ids.add(identifier)
                row_count += 1
            return columns, row_count
    except (csv.Error, UnicodeError) as exc:
        raise ValueError(f"AACT {name} is not a valid UTF-8 delimited table: {exc}") from exc


def verify_snapshot(directory: str | Path, expected: dict | None = None) -> dict:
    """Validate selected table schemas, parse rows and fingerprint frozen bytes.

    Expected is a previous verification manifest. It verifies local integrity,
    not publisher authenticity unless its hashes were obtained independently.
    """
    files, tables = _files(directory), {}
    for name, path in files.items():
        columns, row_count = _scan_table(path, name)
        tables[name] = {"file": path.name, "rows": row_count, "bytes": path.stat().st_size,
                        "sha256": sha256_file(path), "columns": columns}
    if expected:
        expected_tables = expected.get("tables", expected.get("source_files", {}))
        if not expected_tables or set(expected_tables) != set(tables):
            raise ValueError("Snapshot checksum manifest table set differs from supplied files.")
        for name, entry in expected_tables.items():
            if entry.get("sha256") != tables[name]["sha256"]:
                raise ValueError(f"Snapshot checksum mismatch for {name}; raw files changed.")
    return {"mapping_version": MAPPING_VERSION, "tables": tables,
            "missing_optional_tables": sorted(set(TABLE_COLUMNS) - set(files)),
            "verification": "Selected protocol table schema, parseability, row count, unique study IDs, SHA-256; no raw files modified."}


def _criteria_count(text):
    if pd.isna(text) or not str(text).strip():
        return np.nan
    # Count visibly enumerated criteria, not sentences or an invented clinical NLP result.
    lines = str(text).replace(r"\n", "\n").splitlines()
    count = sum(bool(re.match(r"^\s*(?:[-*•]|\d+[.)])\s+\S", line)) for line in lines)
    return float(count) if count else np.nan


def extract_aact(directory: str | Path, *, snapshot_date: str, source_url: str | None = None) -> tuple[pd.DataFrame, dict]:
    """Aggregate one-to-many protocol tables into one canonical row per study."""
    date.fromisoformat(snapshot_date)
    verification = verify_snapshot(directory)
    files = _files(directory)
    tables = {name: _read(path, usecols=lambda c: c in TABLE_COLUMNS[name]) for name, path in files.items()}
    for table in tables.values():
        table["nct_id"] = table.nct_id.str.strip()
    data = tables["studies"].rename(columns={"brief_title": "title", "overall_status": "status"}).set_index("nct_id")
    if "title" not in data:
        data["title"] = data.get("official_title", "")
    for name in ("status", "completion_date_type", "start_date_type", "study_type", "phase", "enrollment_type"):
        if name in data:
            data[name] = data[name].str.strip().str.upper().str.replace(" ", "_", regex=False)
    for source, dest, text_column in (("brief_summaries", "brief_summary", "description"), ("detailed_descriptions", "detailed_description", "description"), ("eligibilities", "eligibility_criteria", "criteria"), ("conditions", "conditions", "name")):
        if source in tables:
            # Stable de-duplication avoids duplicate joined narratives.
            grouped = tables[source].dropna(subset=[text_column]).groupby("nct_id", sort=False)[text_column].agg(lambda values: "\n".join(dict.fromkeys(values)))
            data[dest] = grouped.reindex(data.index)
        else:
            data[dest] = None
    data["criteria_count"] = data["eligibility_criteria"].map(_criteria_count)
    data["number_of_arms"] = pd.to_numeric(data.get("number_of_arms", pd.Series(np.nan, index=data.index)), errors="coerce")
    if "design_groups" in tables:
        group_counts = tables["design_groups"].groupby("nct_id").size().reindex(data.index)
        data["number_of_arms"] = data["number_of_arms"].fillna(group_counts)
    for kind in ("primary", "secondary"):
        if "design_outcomes" in tables:
            outcomes = tables["design_outcomes"]
            counts = outcomes.loc[outcomes.outcome_type.str.strip().str.lower().eq(kind)].groupby("nct_id").size()
            data[f"{kind}_outcomes"] = counts.reindex(data.index, fill_value=0)
        else:
            data[f"{kind}_outcomes"] = np.nan
    if "sponsors" in tables:
        sponsors = tables["sponsors"]
        leads = sponsors.loc[sponsors.lead_or_collaborator.str.strip().str.lower().eq("lead")].dropna(subset=["name"])
        data["sponsor"] = leads.groupby("nct_id")["name"].agg(lambda v: "; ".join(dict.fromkeys(v))).reindex(data.index)
    if "enrollment" in data:
        data["enrollment"] = pd.to_numeric(data["enrollment"], errors="coerce")
    data = data.reset_index()
    metadata = {"source": "AACT frozen protocol flat files", "snapshot_date": snapshot_date, "source_url": source_url,
                "mapping_version": MAPPING_VERSION, "source_files": verification["tables"], "rows": len(data),
                "missing_optional_tables": verification["missing_optional_tables"], "baseline_provenance": False,
                "criteria_count_method": "Count bullet or numbered eligibility lines; missing when no enumerated lines. Proxy requires manual audit.",
                "feature_time_warning": "Retrospective registry snapshot; even protocol fields and enrollment can be updated after trial start. No prospective validation is established.",
                "outcomes_table": "design_outcomes only; posted-results outcomes and result_groups are never input features",
                "missingness": {name: int(data[name].isna().sum()) for name in data}}
    return data, metadata
