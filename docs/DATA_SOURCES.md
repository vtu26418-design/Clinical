# Data sources and canonical records

## Sources

The bundled `data/sample/trials.csv` contains **five software fixtures**, not a scientific dataset. Real cohorts come from an imported CSV/Parquet, frozen AACT protocol flat files, or ClinicalTrials.gov API v2.

- AACT: https://aact.ctti-clinicaltrials.org/download
- ClinicalTrials.gov API: https://clinicaltrials.gov/data-api/api

The app's registry importer makes real API requests and preserves the retrieved JSON and query provenance. No external registry snapshot or pretrained research result is silently substituted when a request fails.

## Canonical fields

| Field | Purpose / expected representation |
|---|---|
| `nct_id` | Required unique nonempty study identifier |
| `title` | Required nonempty study title |
| `phase`, `status`, `study_type` | Categorical protocol fields; normalized uppercase status |
| `enrollment`, `number_of_arms` | Nonnegative numeric counts when known |
| `primary_outcomes`, `secondary_outcomes` | Counts of planned design outcomes, not posted results |
| `criteria_count` | Eligibility-burden proxy; enumerated lines for AACT/registry mapping |
| `text_complexity` | Optional explicit numeric proxy; missing if no defined derivation supplied |
| `brief_summary`, `detailed_description`, `eligibility_criteria` | Protocol text used by the text branch |
| `start_date`, `completion_date` | ISO dates; partial YYYY or YYYY-MM may be preserved but are excluded from duration training |
| `start_date_type`, `completion_date_type` | Date provenance; completed training requires ACTUAL outcomes |
| `enrollment_type` | ACTUAL or ESTIMATED when reported |
| `conditions`, `sponsor` | Optional descriptive metadata |

Validation rejects duplicates, malformed CSV records, invalid dates and invalid negative/non-finite numeric fields. Unknown columns are retained within documented bounds. Missing components can understate descriptive PCI and must be reviewed.

## Frozen AACT extraction

`verify_aact.py` validates headers/record width, required columns, unique study IDs and hashes. `build_features.py` aggregates one-to-many protocol tables before joining, avoiding row multiplication. Selected tables: studies, design_outcomes, design_groups, eligibilities, brief_summaries, detailed_descriptions, conditions and sponsors. Posted-results outcome and results-group tables are excluded.

Store raw source files unchanged. Keep a snapshot date, acquisition URL without credentials, trusted checksums when available and a separate verification manifest. The default extractor operates on UTF-8 headered pipe `.txt` or comma `.csv` tables; it does not restore PostgreSQL dump archives.

## Interpretation limits

A snapshot taken after trial completion may contain updated enrollment, eligibility or summaries. Merely removing outcome columns does not establish prospective validation. `baseline_provenance` is false by default and UI/manifests expose that limitation. Establish a documented baseline-as-of extraction before making prospective claims.
