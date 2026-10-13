# Formula specification and numerical audit

The authoritative shared configuration is `configs/formulas.json`, schema version 1. Python reads this file at service import; the browser imports the same file. Its formulas and known answers are software verification contracts. They do not validate PCI as a clinical instrument, establish causal effects, or establish model performance on new populations.

## Fixed-reference descriptive PCI

Formula identifier: `fixed_reference_pci_v1`.

For component value \(x_i\), ceiling \(c_i\) and weight \(w_i\), the unrounded score is

\[
S=\sum_i w_i\operatorname{clip}(x_i/c_i,0,1).
\]

Weights total 100; each ceiling is positive. Clipping keeps the score in [0,100] and each contribution in [0, its weight]. Ceilings and weights are explicit research assumptions, not empirically validated clinical thresholds.

| Source key | Display label | Fixed ceiling | Weight / maximum contribution |
| --- | --- | ---: | ---: |
| `criteria_count` | Eligibility burden | 40 | 25 |
| `primary_outcomes` | Primary outcome burden | 10 | 20 |
| `secondary_outcomes` | Secondary outcome burden | 20 | 20 |
| `number_of_arms` | Arm complexity | 8 | 15 |
| `enrollment` | Enrollment burden | 1,000 | 10 |
| `text_complexity` | Text complexity | 20 | 10 |

`text_complexity` is the supplied numeric feature; the score does not infer a validated reading level. PCI ignores study status, outcomes and fitted-model probabilities. A large enrollment does not alone imply high risk or long duration.

### Missingness and accepted scalars

Accept a finite numeric scalar or a trimmed decimal/scientific numeric string matching the JSON `decimal_pattern`. Preserve numeric strings during exact arithmetic. Interpret numeric scalars by their decimal text representation. Booleans, arrays, objects, null, absent values, blank strings, malformed strings (including hexadecimal and underscore formats), NaN and either infinity are invalid. To bound exact integer arithmetic, the shared input policy rejects mantissas longer than 340 digits and absolute decimal scale greater than 320 (scientific exponent minus fractional-digit count). These out-of-contract scalar representations are also disclosed as invalid; the guard is applied before allocating a large integer.

Missing, invalid and non-finite components contribute zero. `missing_fields` lists their source keys in component order. Zero contribution is a scoring convention, not evidence that a burden is absent. Incomplete records can therefore have understated scores and should be compared only after inspecting completeness. Finite negative values clip to zero and are not counted as missing; inspect source quality separately.

Python exposes `calculate_pci_details(row)` with `score`, `category`, unrounded weighted `components`, `methodology`, `missing_fields` and `formula_id`. `calculate_pci(row)` preserves the v3 three-item tuple `(score, category, components)` for existing callers.

### Rounding and category boundaries

Convert decimal text to exact rational values before division and summation. Python uses `Decimal` to parse decimal text and `Fraction` to keep exact ratios. A compatible browser implementation uses decimal parsing and integer arithmetic. Round the total once, to two decimals, with half-up rounding: an exact nonnegative half-cent rounds upward. Components are not rounded before summation.

For exact total \(S=n/d\), with \(n\geq0,d>0\), the reported cents are

\[
\left\lfloor\frac{200n+d}{2d}\right\rfloor,
\]

and the reported score is cents / 100. Classify the reported rounded score:

| Category | Rule |
| --- | --- |
| Low | score < 40 |
| Medium | 40 ≤ score ≤ 70 |
| High | score > 70 |

This rule deliberately fixes binary floating-point and ties-to-even disagreements at half-cent boundaries. It preserves the five bundled v3 fixture scores; an exact half-cent elsewhere can differ from the older binary-rounding result by 0.01.

| Independently computed unrounded total | Reported total | Category |
| ---: | ---: | --- |
| 0.005 | 0.01 | Low |
| 39.9949 | 39.99 | Low |
| 39.995 | 40.00 | Medium |
| 70 | 70.00 | Medium |
| 70.0049 | 70.00 | Medium |
| 70.005 | 70.01 | High |

The shared `parity_cases` include these boundary cases, decimal strings just below a half-cent, zero/missing/invalid/non-finite inputs, negative and upper clipping, and all five v3 fixtures. Fixtures are software-test records, not clinical evidence.

| Bundled fixture | Exact reported PCI | Category |
| --- | ---: | --- |
| NCT-SAMPLE-001 | 25.50 | Low |
| NCT-SAMPLE-002 | 55.40 | Medium |
| NCT-SAMPLE-003 | 12.60 | Low |
| NCT-SAMPLE-004 | 41.05 | Medium |
| NCT-SAMPLE-005 | 52.90 | Medium |

Custom browser weights are exploratory assumptions. Require six finite weights, each in [0,100], totaling 100 after explicit normalization (floating-point sum tolerance 1e-8). Reject an invalid vector rather than letting a score exceed 100. Label this result as custom/exploratory and retain the reference result for comparison; it is not `fixed_reference_pci_v1`.

## Separate training-relative PCI

Duration research artifacts use an equal-weight, training-fitted min–max descriptive index. They fit medians, minima and maxima using retained training records only. For each numeric feature, impute missing values with its training median, normalize to the training minimum/maximum, clip to [0,1], and assign zero if the training range is constant. Multiply the mean normalized contribution by 100.

This method has different normalization, weights and missing-value behavior from fixed-reference PCI. Its fitted feature names, medians, ranges and weights live in the artifact/manifest. Two experiments with different training cohorts can produce different relative PCI values for the same study. Do not equate this artifact value with the workspace reference score or compare it across differently fitted cohorts without examining the fitted parameters.

## Evaluation metrics

Let \(y_i\) be the actual outcome, \(\hat y_i\) its estimate, \(\bar y\) the mean actual outcome, \(b_i\in\{0,1\}\) a binary label, and \(p_i\in[0,1]\) a probability. Use matched, finite, nonempty vectors of equal length.

| Metric | Definition | Interpretation and undefined cases |
| --- | --- | --- |
| MAE | \(n^{-1}\sum_i\lvert y_i-\hat y_i\rvert\) | Mean absolute error; duration units are days. Undefined for an empty set. |
| RMSE | \(\sqrt{n^{-1}\sum_i(y_i-\hat y_i)^2}\) | Error in days; larger errors receive more weight. Undefined for an empty set. |
| R² | \(1-\sum_i(y_i-\hat y_i)^2/\sum_i(y_i-\bar y)^2\) | Unitless and can be negative. Return null for fewer than two outcomes or constant actual outcomes. |
| Binary Brier | \(n^{-1}\sum_i(p_i-b_i)^2\) | Unitless, [0,1], lower is better; checks probability error for the defined binary outcome. Not the doubled two-class convention. Undefined for an empty set. |
| Cosine similarity | \(a\cdot b/(\lVert a\rVert_2\lVert b\rVert_2)\) | Unitless. For nonnegative TF-IDF vectors it is in [0,1]. A zero norm is mathematically undefined; retrieval uses zero overlap and omits zero-score results. |

Metric input validation rejects non-finite values, non-binary labels and probabilities outside [0,1]. Backend evaluation rejects empty input rather than fabricating a zero metric. Frontend formula displays use null for undefined mathematical quantities. Per-phase metrics with too little variation retain null R². Do not replace an unavailable metric with zero.

MAE, RMSE and R² measure estimates for the same retained outcome population. Brier refers to the declared positive-label definition and the probability variant reported in the artifact. Raw probabilities and probabilities calibrated on reserved calibration data must be identified consistently in predictions, recommendation and test metrics. A low Brier score alone does not establish clinical validity.

Known-answer fixture: actual `[10,20,30]`, estimated `[12,18,33]`, binary labels `[0,1,1]`, probabilities `[0.2,0.8,0.6]`:

| Quantity | Hand computation | Expected result |
| --- | --- | ---: |
| Absolute-error sum | 2 + 2 + 3 | 7 |
| Squared-error sum | 4 + 4 + 9 | 17 |
| Actual squared variation | 100 + 0 + 100 | 200 |
| MAE | 7/3 | 2.3333333333333335 |
| RMSE | √(17/3) | 2.3804761428476167 |
| R² | 1 − 17/200 | 0.915 |
| Binary Brier | (0.04 + 0.04 + 0.16)/3 | 0.08 |

Cosine known answer: `[1,1,0]` and `[1,0,1]` have dot product 1 and norms √2, so similarity is 0.5. Orthogonal nonzero vectors have similarity 0. Retrieval excludes the source study itself and discloses source/cohort scope; this is descriptive text overlap, not a clinical-equivalence score.

## Deterministic recruitment planning

Given target enrollment \(T\), sites \(s\), monthly recruitment rate per site \(r\), startup months \(u\), and follow-up months \(f\):

\[
\text{recruitment months}=T/(s r),\qquad
\text{planned total months}=u+T/(s r)+f.
\]

Inputs must be finite; sites and rate must be positive; target, startup and follow-up must be nonnegative. A scenario's enrollment override supplies the target, otherwise use source enrollment. Refuse a missing target rather than silently treating it as zero. Preserve source fields and scenario assumptions so the arithmetic is reproducible.

Known answer: target 240, four sites, five participants per site per month, three startup months and six follow-up months give 12 recruitment months and 21 total months. Zero sites or zero rate cannot produce a defined planning duration.

This calculation assumes a constant recruitment rate and sequential startup, recruitment and follow-up periods. It does not model site activation delays, attrition, uneven recruitment, overlapping participant follow-up or amendments. The months are user assumptions and arithmetic, not fitted recruitment risk, causal counterfactuals or validated duration forecasts. No recruitment/amendment probabilities are inferred without curated labels and trained evidence.

## Reproduction

Run `python -m pytest tests/test_pci.py -q` for Python fixed-PCI and metric known answers. The shared JSON cases let the frontend verifier exercise the same inputs and expected scores/categories/missingness. Research-workspace tests independently verify planning arithmetic, source immutability and retrieval behavior. Run the complete repository test suite and frontend build before release; finite-score checks and a successful build do not establish scientific validity.
