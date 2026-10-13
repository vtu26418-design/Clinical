# Protocol Complexity Index

PCI is a research-defined descriptive index, not an established clinical score and not a probability.

## Interface reference index

For each field, clamp `value / ceiling` to [0, 1], multiply by its weight and sum. Missing or non-finite values contribute zero, which can understate complexity.

| Component | Field | Ceiling | Weight |
|---|---|---:|---:|
| Eligibility burden | criteria_count | 40 | 25% |
| Primary outcomes | primary_outcomes | 10 | 20% |
| Secondary outcomes | secondary_outcomes | 20 | 20% |
| Arms | number_of_arms | 8 | 15% |
| Enrollment | enrollment | 1000 | 10% |
| Text complexity | text_complexity | 20 | 10% |

Scores below 40 are labeled Low, 40 through 70 Medium, above 70 High. These fixed ceilings, weights and labels are explicit project assumptions, not validated clinical thresholds. Complexity Lab lets users compare reference/equal/custom normalized weights and enrollment changes without mutating source data. Exported scenarios are labeled exploratory.

## Experiment index

Research experiments fit their PCI normalization and imputations on training records only, then freeze them for validation and test. The experiment manifest records the fitted specification. This is intentionally distinct from the fixed reference UI index. See RESEARCH_METHODS for the exact algorithm. Neither index proves a causal relationship with duration.
