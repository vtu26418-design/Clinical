"""Freeze real registry cohorts and chronological roles before any model fitting.

Raw acquisition files are read-only. Derived inputs remain bounded Parquet shards.
Current registry snapshots are retrospective, even when dates are ACTUAL.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import pandas as pd
from acquire_registry_cohort import _read_shards
from src.clinical_trial_intelligence.research import ExperimentConfig, prepare_cohort, temporal_split, partition_validation
from src.clinical_trial_intelligence.phase_model import prepare_phase_cohort, phase_temporal_split

NCT = re.compile(rb"\bNCT\d{8}\b")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def object_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def historical_sources(root, additional=()):
    """Conservative union across every retained old data projection/evidence file.

    Scan authentic raw pages as well as CSVs: previously exposed source rows may
    have failed an old training filter and still must be excluded now.
    """
    root = Path(root)
    directories = [root / "data" / "starter", *sorted((root / "data").glob("clinicaltrials-v5-*")), root / "examples", root / "docs", root / "models"]
    candidates = set()
    for directory in directories:
        if directory.is_dir():
            candidates.update(p for p in directory.rglob("*") if p.is_file() and (p.suffix.lower() in {".csv", ".json", ".jsonl"} or p.name.endswith(".json.gz")))
    candidates = {path for path in candidates if not any("v5205" in part.lower() or "5.2.0.5" in part for part in path.relative_to(root).parts)}
    candidates.update(Path(path).resolve() for path in additional)
    return sorted(candidates)


def historical_exposure(root, additional=()):
    inventory, origins = [], {}
    root = Path(root).resolve()
    for path in historical_sources(root, additional):
        if path.is_symlink():
            raise ValueError("Historical evidence must not be a symbolic link.")
        payload = gzip.decompress(path.read_bytes()) if path.name.endswith(".gz") else path.read_bytes()
        identifiers = sorted({match.decode("ascii") for match in NCT.findall(payload)})
        name = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        if identifiers:
            inventory.append({"file": name, "sha256": sha256_file(path), "unique_nct_ids": len(identifiers)})
        for identifier in identifiers:
            origins.setdefault(identifier, []).append(name)
    return origins, inventory


def eligibility(frame):
    """Task-specific prespecified eligibility; never trim duration outliers."""
    data = frame.copy()
    reasons = pd.Series("", index=data.index, dtype=object)
    parsed = {}
    for name in ("start_date", "completion_date"):
        raw = data[name].fillna("").astype(str).str.strip()
        precise = raw.str.fullmatch(r"\d{4}-\d{2}-\d{2}")
        parsed[name] = pd.to_datetime(raw.where(precise), format="%Y-%m-%d", errors="coerce")
        reasons.loc[~precise | parsed[name].isna()] += name + "_exact_valid_day_required;"
        actual = data.get(name + "_type", pd.Series("", index=data.index)).fillna("").astype(str).str.upper().eq("ACTUAL")
        reasons.loc[~actual] += name + "_actual_required;"
    observed = pd.to_datetime(data["source_retrieved_at"], utc=True, errors="coerce").dt.tz_convert(None).dt.normalize()
    if observed.isna().any():
        raise ValueError("Each source row requires a valid page retrieval time.")
    reasons.loc[parsed["completion_date"].gt(observed)] += "completion_after_source_retrieval_day;"
    reasons.loc[parsed["completion_date"].le(parsed["start_date"])] += "nonpositive_duration;"
    reasons.loc[~data.status.fillna("").astype(str).str.upper().eq("COMPLETED")] += "status_not_completed;"
    duration_excluded = pd.DataFrame({"nct_id": data.loc[reasons.ne(""), "nct_id"], "reason": reasons.loc[reasons.ne("")].str.rstrip(";")})
    duration = data.loc[reasons.eq("")].copy()
    # Phase is a recorded protocol label: completion eligibility is irrelevant.
    phase, phase_excluded = prepare_phase_cohort(data)
    return duration, duration_excluded, phase, phase_excluded


def _partition_report(splits, task, threshold=None):
    records, summaries = [], {}
    for role in ("train", "validation", "calibration", "test"):
        if role not in splits:
            continue
        frame = splits[role]
        support = {str(key): int(value) for key, value in frame.phase.fillna("MISSING").value_counts().items()}
        summaries[role] = {"rows": len(frame), "role": "tuning" if role == "validation" else role,
                           "start_date_min": str(frame.start_date.min()) if len(frame) else None,
                           "start_date_max": str(frame.start_date.max()) if len(frame) else None,
                           "phase_support": support}
        if threshold is not None:
            summaries[role]["risk_support"] = {"positive": int(frame.duration_days.gt(threshold).sum()), "negative": int(frame.duration_days.le(threshold).sum())}
        for row in frame[["nct_id", "start_date"]].itertuples(index=False):
            records.append({"nct_id": row.nct_id, "task": task, "split": role, "start_date": str(row.start_date)})
    return pd.DataFrame(records, columns=["nct_id", "task", "split", "start_date"]), summaries


def prepare(source, output, *, root=ROOT, protocol=None, duration_config=None, phase_config=None, additional_exposure=(), resume=False):
    source, output, root = Path(source).resolve(), Path(output).resolve(), Path(root).resolve()
    protocol = Path(protocol or ROOT / "configs/v5205-frozen-experiment.json").resolve()
    duration_config = Path(duration_config or ROOT / "configs/research-design.json").resolve()
    phase_config = Path(phase_config or ROOT / "configs/phase-design.json").resolve()
    if source == output or source in output.parents:
        raise ValueError("Prepared output must be separate from immutable acquisition.")
    state = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
    if not state.get("acquisition_complete") or state.get("is_fixture") or state.get("baseline_provenance"):
        raise ValueError("A complete genuine retrospective source acquisition is required.")
    exposed, inventory = historical_exposure(root, additional_exposure)
    contract = {"source_metadata_sha256": sha256_file(source / "metadata.json"), "historical_inventory_sha256": object_hash(inventory),
                "protocol_sha256": sha256_file(protocol), "duration_config_sha256": sha256_file(duration_config),
                "phase_config_sha256": sha256_file(phase_config), "preparation_source_sha256": sha256_file(__file__)}
    if output.exists():
        if not resume:
            raise ValueError("Prepared output exists; use --resume to verify and reuse it without overwrite.")
        _, manifest = load_prepared(output, verify=True, load_rows=False)
        if manifest["contract"] != contract:
            raise ValueError("Prepared cohort contract changed; choose a new output directory.")
        return manifest
    output.mkdir(parents=True, exist_ok=False)
    (output / "shards").mkdir()
    files, compact_frames, excluded_historical = [], [], []
    input_rows, seen = 0, set()
    for page in state["pages"]:
        # Independently verify raw responses and canonical shards before deriving.
        frame = _read_shards(source, {"pages": [page]}, True)
        identifiers = set(frame.nct_id.astype(str))
        if len(identifiers) != len(frame) or identifiers.intersection(seen):
            raise ValueError("Source contains repeated registry IDs.")
        seen.update(identifiers)
        input_rows += len(frame)
        historical = frame.nct_id.isin(exposed)
        excluded_historical.extend(frame.loc[historical, "nct_id"].tolist())
        frame = frame.loc[~historical].copy()
        frame["source_retrieved_at"] = page["retrieved_at"]
        frame["source_response_sha256"] = page["response_sha256"]
        name = f"shards/part-{len(files) + 1:06d}.parquet"
        frame.to_parquet(output / name, index=False, compression="zstd")
        files.append({"file": name, "sha256": sha256_file(output / name), "rows": len(frame)})
        fields = [name for name in ("nct_id", "start_date", "completion_date", "start_date_type", "completion_date_type", "status", "phase", "source_retrieved_at") if name in frame]
        compact_frames.append(frame[fields])
    if input_rows != state["rows"]:
        raise ValueError("Source row reconciliation failed.")
    compact = pd.concat(compact_frames, ignore_index=True)
    duration, duration_excluded, phase, phase_excluded = eligibility(compact)
    cfg = ExperimentConfig(**json.loads(duration_config.read_text(encoding="utf-8")))
    cfg.validate()
    duration, unexpected = prepare_cohort(duration, state)
    if len(unexpected):
        raise ValueError("Duration eligibility differs from the declared source filter.")
    duration_splits = temporal_split(duration, cfg)
    tuning, calibration, calibration_record = partition_validation(duration_splits["validation"])
    duration_splits["validation"], duration_splits["calibration"] = tuning, calibration
    threshold = float(duration_splits["train"].duration_days.quantile(cfg.prolonged_quantile))
    duration_roles, duration_counts = _partition_report(duration_splits, "duration", threshold)
    phase_splits = phase_temporal_split(phase)
    phase_roles, phase_counts = _partition_report(phase_splits, "phase")
    pd.DataFrame([{"nct_id": identifier, "source_files": "|".join(exposed[identifier]), "present_in_new_source": identifier in seen} for identifier in sorted(exposed)]).to_csv(output / "historical_exposed_ids.csv", index=False)
    pd.DataFrame({"nct_id": sorted(excluded_historical), "reason": "historical_development_exposure"}).to_csv(output / "historical_exclusions.csv", index=False)
    duration_excluded.to_csv(output / "duration_eligibility_exclusions.csv", index=False)
    phase_excluded.to_csv(output / "phase_eligibility_exclusions.csv", index=False)
    duration_splits["purged"].to_csv(output / "duration_temporal_exclusions.csv", index=False)
    duration_roles.to_csv(output / "duration_partitions.csv", index=False)
    phase_roles.to_csv(output / "phase_partitions.csv", index=False)
    write_json(output / "historical_source_inventory.json", {"files": inventory})
    artifacts = {path.name: sha256_file(path) for path in sorted(output.iterdir()) if path.is_file()}
    # Bind the data identity to ordered shard bytes and the prespecified contract.
    dataset_hash = object_hash({"shards": files, "contract": contract})
    manifest = {"schema_version": 1, "status": "prepared_not_fitted", "created_at": datetime.now(timezone.utc).isoformat(),
                "dataset_id": "registry-v5205-" + dataset_hash[:16], "dataset_sha256": dataset_hash,
                "contract": contract, "source_directory": str(source), "shards": files, "evidence_sha256": artifacts,
                "source_metadata": {**state, "baseline_provenance": False, "is_fixture": False},
                "counts": {"source_unique_rows": input_rows, "historical_union_ids": len(exposed), "historical_source_rows_excluded": len(excluded_historical),
                           "unexposed_source_rows": len(compact), "duration_eligible_rows": len(duration), "duration_eligibility_excluded": len(duration_excluded),
                           "duration_temporally_purged": len(duration_splits["purged"]), "phase_eligible_rows": len(phase), "phase_eligibility_excluded": len(phase_excluded)},
                "duration": {"splits": duration_counts, "threshold_days": threshold, "validation_cutoff": str(duration_splits["validation_cutoff"]), "test_cutoff": str(duration_splits["test_cutoff"]), "validation_partition": calibration_record},
                "phase": {"splits": phase_counts, "validation_cutoff": str(phase_splits["validation_cutoff"]), "test_cutoff": str(phase_splits["test_cutoff"])},
                "duration_exclusion_reasons": dict(Counter(reason for text in duration_excluded.reason for reason in text.split(";"))),
                "phase_exclusion_reasons": dict(Counter(reason for text in phase_excluded.reason for reason in text.split(";"))),
                "policy": {"historical": "Exclude union of retained old raw acquisitions, projections, examples, and JSON/CSV evidence before all task fitting.",
                           "duration": "Exact valid ACTUAL start/completion; COMPLETED; positive duration; completion no later than each page retrieval calendar day. No cutoff tuning or outlier removal.",
                           "phase": "Exact valid start and known single phase, independently of completion eligibility; current phase availability at trial start remains unverified.",
                           "date_groups": "Fixed 60/20/20 distinct whole start-date groups; duration outcome purging then later-half calibration reservation. Phase does not purge completion outcomes.",
                           "scale": "Finite official query around one hundred thousand trials, not millions.",
                           "provenance": "Current retrospective registry snapshot, not historical or pretrial validation.",
                           "related_protocols": "No linked-protocol deduplication or sponsor clustering is claimed; distinct IDs can be correlated."}}
    write_json(output / "preparation_manifest.json", manifest)
    return manifest


def load_prepared(directory, *, verify=True, load_rows=True, task=None):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / "preparation_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "prepared_not_fitted" or manifest.get("source_metadata", {}).get("baseline_provenance") or manifest.get("source_metadata", {}).get("is_fixture"):
        raise ValueError("Invalid prepared genuine retrospective cohort.")
    identity = object_hash({"shards": manifest["shards"], "contract": manifest["contract"]})
    if identity != manifest["dataset_sha256"]:
        raise ValueError("Prepared dataset identity differs from its manifest.")
    if task not in (None, "duration", "phase"):
        raise ValueError("Unknown training task.")
    frames = []
    for item in manifest["shards"]:
        if not re.fullmatch(r"shards/part-\d{6}\.parquet", item["file"]):
            raise ValueError("Unsafe prepared shard name.")
        path = directory / item["file"]
        if path.is_symlink() or (verify and sha256_file(path) != item["sha256"]):
            raise ValueError("Prepared shard checksum mismatch.")
        if load_rows:
            frame = pd.read_parquet(path)
            if len(frame) != item["rows"]:
                raise ValueError("Prepared shard row count mismatch.")
            frames.append(frame)
    if verify:
        for name, expected in manifest["evidence_sha256"].items():
            if Path(name).name != name or (directory / name).is_symlink() or sha256_file(directory / name) != expected:
                raise ValueError("Prepared cohort evidence checksum mismatch.")
    frame = pd.concat(frames, ignore_index=True) if load_rows else None
    if frame is not None:
        if len(frame) != manifest["counts"]["unexposed_source_rows"] or frame.nct_id.duplicated().any():
            raise ValueError("Prepared source count or ID reconciliation failed.")
        if task is not None:
            # Duration purged rows remain available to the training API so its
            # prespecified split cutoffs reproduce the full eligible cohort.
            exclusions = pd.read_csv(directory / f"{task}_eligibility_exclusions.csv")
            frame = frame.loc[~frame.nct_id.isin(exclusions.nct_id)].reset_index(drop=True)
    return frame, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/registry-v5205")
    parser.add_argument("--output", type=Path, default=ROOT / "data/registry-v5205-training")
    parser.add_argument("--additional-exposure", type=Path, action="append", default=[])
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    try:
        manifest = prepare(args.source, args.output, additional_exposure=args.additional_exposure, resume=args.resume)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Cohort preparation refused: {error}\n")
    print(json.dumps({"status": manifest["status"], "dataset_sha256": manifest["dataset_sha256"], "counts": manifest["counts"], "duration": manifest["duration"]["splits"], "phase": manifest["phase"]["splits"]}, indent=2))


if __name__ == "__main__":
    main()
