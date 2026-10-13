# Real public starter data

The release includes **800 authentic ClinicalTrials.gov records** downloaded from the official public [API v2](https://clinicaltrials.gov/data-api/api) on **2026-10-07 UTC**. These are completed, interventional studies with a drug intervention and a reported phase I–IV, including combined phases. They have start dates in every year from 2000 through 2023.

This is a **convenience subset for a reproducible retrospective research workflow**, not the entire registry and not a population-representative sample. It is distinct from the five synthetic software-test fixtures in `data/sample/`. No trial records, missing values, outcomes, or model metrics were fabricated. No model was fitted to choose this subset.

## Included files

| Path | Contents |
| --- | --- |
| `data/starter/trials.csv` | Canonical UTF-8 table, 800 unique NCT IDs |
| `data/starter/metadata.json` | Queries, acquisition timestamps, per-page request parameters, row coverage, raw and canonical SHA-256 checksums, limitations |
| `data/starter/raw/*.json.gz` | Eight gzip-compressed, original API response bodies, 100 records per page |
| `data/starter/cohort_check.json` | Outcome eligibility and temporal-split audit; no fitted models or performance metrics |
| `scripts/download_starter_data.py` | Immutable acquisition and offline replay commands |

Canonical SHA-256:

```text
d096795e303b5a103e0aba8bd79ffe7e85609827ea810d1c08e8e0811b5496d2
```

The canonical table is 2,976,872 bytes. Decompressing a raw page reproduces its original API response body byte for byte. Metadata separately records the checksum of the compressed file and original uncompressed response. The raw responses contain the full returned registry records, including fields not mapped to the table.

## Selection and coverage

Four queries each request the first 200 records in the API's default return order. The start-date strata are fixed before acquisition. There is no random-sample claim, no duration filter, no selection for model scores, and no filtering to improve label balance.

| Start period | Records |
| --- | ---: |
| 2000–2005 | 200 |
| 2006–2011 | 200 |
| 2012–2017 | 200 |
| 2018–2023 | 200 |

| Registry phase | Records |
| --- | ---: |
| PHASE1 | 197 |
| PHASE1\|PHASE2 | 41 |
| PHASE2 | 233 |
| PHASE2\|PHASE3 | 21 |
| PHASE3 | 153 |
| PHASE4 | 155 |

Each query uses this structure, with the corresponding start-date range:

```text
AREA[StudyType]INTERVENTIONAL AND AREA[OverallStatus]COMPLETED
AND AREA[InterventionType]DRUG
AND (AREA[Phase]PHASE1 OR AREA[Phase]PHASE2 OR AREA[Phase]PHASE3 OR AREA[Phase]PHASE4)
AND AREA[StartDate]RANGE[2000-01-01,2005-12-31]
```

The downloader verifies every returned record against this scope and rejects duplicate NCT IDs. The completed-only condition is part of the requested cohort and creates selection bias; this dataset does not represent censored or ongoing studies.

## Date precision and training eligibility

Registry date strings are preserved exactly: `YYYY`, `YYYY-MM`, and `YYYY-MM-DD` remain distinct. Neither missing days nor missing ACTUAL/ESTIMATED labels are inferred. There are 482 partial start dates and 428 partial completion dates. Completion dates are labelled ACTUAL for 744 records; 56 have no reported completion type.

`prepare_cohort` requires completed status, a positive observed duration, exact day-precision start and completion dates, and an ACTUAL completion label. It retains **312 records** and excludes **488**. Of the eligible records, 307 start dates are explicitly ACTUAL and five have no reported start-date type; the current eligibility rule requires completion actuality and does not infer start actuality.

The default temporal split groups whole start dates and purges outcomes unavailable at the next evaluation cutoff:

| Split | Rows after purging | Prolonged outcomes |
| --- | ---: | ---: |
| Training | 105 | 26 |
| Validation | 20 | 0 |
| Test | 64 | 6 |

The validation cutoff is **2019-10-10**, the test cutoff is **2021-09-14**, and **123** otherwise eligible records are purged. The prolonged-duration threshold is the training-only 75th percentile, **1,101 days**, with durations strictly above the threshold labelled prolonged. Validation AUROC and average precision are undefined because the validation subset contains one class; they must remain unavailable. The subset was not changed to obtain more favorable labels. These checks establish workflow feasibility, not model accuracy.

## Reproduction

Run commands from the repository root after installing `requirements.txt` in the supported Python environment. Always supply a **new output directory**; the script refuses to overwrite any existing directory.

Reconstruct the identical canonical table from the bundled raw response bytes, without network access:

```bash
python scripts/download_starter_data.py --replay-from data/starter --output-dir data/replayed-starter
```

This verifies all raw-response checksums and the regenerated canonical checksum before writing. It retains the original acquisition metadata and writes a separate replay receipt. `cohort_check.json` is an analysis audit, not a source record, and is not copied by the replay command.

Acquire a fresh subset using the same selection policy:

```bash
python scripts/download_starter_data.py --output-dir data/new-starter --per-period 200
```

ClinicalTrials.gov is a live registry, so fresh acquisition can return revised records and a different default ordering. The fresh download is a new dataset with its own timestamps and checksums. The script does not silently substitute fixtures on a network or registry error. Failed downloads retain fetched raw pages and a `DOWNLOAD_FAILED.json` receipt; retry into a new directory.

Run offline source-integrity and safe-failure checks:

```bash
PYTHONPATH=src:. python -m pytest tests/test_starter_download.py -q
```

To reproduce the core cohort/split counts without fitting models:

```python
import json
import pandas as pd
from clinical_trial_intelligence.research import prepare_cohort, temporal_split

metadata = json.load(open("data/starter/metadata.json", encoding="utf-8"))
trials = pd.read_csv("data/starter/trials.csv")
cohort, exclusions = prepare_cohort(trials, metadata)
splits = temporal_split(cohort)
print(len(cohort), len(exclusions))
print({name: len(splits[name]) for name in ("train", "validation", "test", "purged")})
```

Set `PYTHONPATH=src:.` for this example. For an exhaustive, frozen registry analysis, use the documented AACT acquisition/verification pipeline and retain the independently verified snapshot; the starter subset does not replace that workflow.

## Interpretation limits

These are latest-state registry records, not proven baseline protocol snapshots. Later revisions to enrollment, outcomes, or text may contain information unavailable at trial start. Temporal outcome purging does not establish baseline feature provenance. Incomplete dates disproportionately exclude older records. `criteria_count` and `text_complexity` remain missing because no validated extraction method is applied by the downloader. Any experiments on this subset must be described as retrospective demonstrations, not validated prospective, clinical, or regulatory predictions.
