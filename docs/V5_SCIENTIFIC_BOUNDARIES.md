# V5 scientific and operational boundaries

Audit date: 2026-10-09. This is the intended-use and interpretation contract for the v5 workbench. Requirements references use physical pages and source keys defined in `V5_REQUIREMENTS_TRACEABILITY.md`.

## Intended use and evidence levels

The system supports human-reviewed research into protocol complexity, duration, operational risk and hypothetical design scenarios. It does not diagnose patients, prescribe treatment, approve protocol changes, replace a statistician/clinical expert or submit regulatory decisions autonomously (B p25).

Keep these evidence levels distinct in the UI, API and reports:

| Level | What it establishes | What it does not establish |
|---|---|---|
| Software fixture/test | Arithmetic, validation, API/UI behavior and security assertions for the tested inputs | Scientific accuracy or clinical benefit |
| Authentic latest-state registry data | Real public records with preserved acquisition/source provenance | Information available at original protocol-finalization time |
| Retrospective temporal evaluation | Performance on later retained completed trials under the documented cohort/splits | Prospective validation or absence of feature leakage |
| Curated point-in-time benchmark | Features were demonstrably available at the stated prediction time | Transfer to other sponsors/registries or clinical utility |
| External/prospective validation | Performance under a prespecified independent context and protocol | Universal applicability, regulatory approval or guaranteed benefit |

The number of downloaded records is not the number of eligible training trials. Report input, exclusion, temporal purge, training, tuning, calibration and test counts separately. A model family is implemented only when executable; it is verified only to the extent shown by actual tests/runs; it is scientifically validated only with fit-for-purpose evidence. Model names in requirements PDFs are not runtime access tests.

## Point-in-time and leakage

R pp6–7 and B pp12–13,27 require `feature_available_at <= prediction_timestamp`. This applies to text, derived counts, embeddings, ontology mappings and extracted clauses as well as structured variables. A current registry row with an old start date is not a historical baseline snapshot. Neither the acquisition timestamp nor a global `baseline_provenance=true` flag proves individual feature availability.

At protocol-design time, actual enrollment, actual completion, final status, results, future amendments, future site activation and future recruitment trajectories are label/post-index information. Store them separately. Even innocently named `enrollment`, `criteria_count` or `eligibility_criteria` can contain post-start revisions. Feature-name exclusion and chronological splitting alone cannot eliminate this risk.

Unknown or later feature timestamps must fail a strict pretrial eligibility gate. The same data can remain available in a clearly labeled retrospective exploration mode. Label observation time must also precede the relevant training/tuning cutoff; source dates, event dates and label-known dates are different concepts. Related protocol versions, sponsors, drug programs and near-duplicates need grouping controls where possible (B p17).

An approved model may serve a new compatible dataset without retraining. That does not remove point-in-time or domain checks. Record training snapshot/hash/cutoff separately from the incoming inference snapshot/hash and its availability audit. Dataset identity is not scientific model applicability; schema compatibility alone is also insufficient.

## Duration, censoring and estimands

Define the endpoint and time origin before modeling: e.g. start to observed study completion, or a separately defined operational milestone. Do not mix primary completion and study completion without a documented target. Preserve partial date precision; imputing a month/year to a day can manufacture duration precision.

The inherited core duration experiment uses completed trials with known ACTUAL completion dates. It predicts retrospective completed-trial duration and carries selection/follow-up bias. Ongoing trials are not negative outcomes or completed at current elapsed time. Survival models require observed follow-up/censoring dates and explicitly adjudicated event indicators. Estimated completion is not an observed event. Termination/withdrawal may be competing events rather than independent censoring. The optional Cox module requires analyst-curated follow-up and documents these assumptions.

Administrative censoring should use the analysis cutoff. Consistent endpoint ascertainment, non-informative censoring assumptions and, for Cox, proportional hazards assessment remain necessary. Adding ongoing rows without reliable follow-up does not create a valid survival cohort. A completed-only acquisition cannot validate censoring-aware prediction (R pp10–12; B pp7,13–16).

A regression estimate with a residual interval is not a survival curve. P25/P50/P75/P90 should be derived from an actual time-to-event distribution; if the estimated curve does not reach a quantile within supported follow-up, return null/unreached rather than extrapolating a convenient number. Do not fit a decorative exponential distribution around a point estimate and call it validated survival prediction.

## Separate long duration, delay, recruitment and amendment

Public long-duration risk can be defined as the probability of exceeding a training-only historical matched-cohort Q75, with matching variables, reference era and minimum support recorded (B p8). The existing completed-trial pipeline uses a global training-cohort quantile; it must not be labeled phase/indication-matched unless matching is actually implemented.

Delay-vs-plan needs a design-time planned completion and a prespecified approved tolerance. An intrinsically long study need not be delayed. Current revised planned dates do not establish the original plan. Without labels and a fitted/validated task model, delay risk is unavailable (R pp3,11).

Recruitment feasibility requires defined accrual outcomes and appropriate operational data. `target / (sites × rate)` is an assumption-driven estimate under constant rate, simultaneous activation and no attrition; it is not a learned recruitment-risk probability.

Amendment probabilities require dated version histories, a materiality definition, prediction horizon, adequate negatives/follow-up and adjudicated dimension labels. Text complexity, a difference between two snapshots or an LLM judgment alone is not calibrated amendment risk. Display unsupported recruitment/amendment outputs as unknown/unavailable, never as 0%, a made-up percentage or a burden score formatted like a probability (B p8; U p5).

## Complexity and extraction

PCI is a descriptive index, not a disease-risk or clinical-outcome probability. The seven domains in B pp6–7 are study design, eligibility, patient burden, site/operational burden, endpoint/data burden, geographic/regulatory burden and intervention/safety burden. The PDF proposes a weighted sum but does not prescribe validated weights/caps. Initial transparent expert or equal weights are research assumptions. Outcome association and agreement with blinded expert ratings are separate validation tasks.

Unavailable patient visit, procedure, site, geographic or safety fields cannot be invented from public registry proxies. A missing source field is unknown, not evidence of no burden. If a legacy formula imputes missing components as zero, keep that policy visible and do not treat its result as fully observed. A partial score needs its coverage/denominator and cannot silently be compared with a complete score.

Document extraction should preserve source hash/version and exact page/section/span. Text counts and regular-expression rules are parser outputs, not validated semantic understanding. Display original evidence, method, extraction confidence/limitations and review state; retain corrections and original values. No claim of schedule-of-activities, rare-disease or genomic restriction extraction should be made unless that feature is actually implemented and assessed (R pp7–8,23; B pp16–17,19).

## Calibration, uncertainty and applicability

Raw classifier scores and separately calibrated probabilities must remain distinct. The inherited sigmoid method requires adequate reserved calibration rows and both classes; unsupported calibration stays unavailable. Metrics on the same calibration cohort are in-sample for that transform. Model/hyperparameter selection uses tuning data; final test data must not select the champion.

The inherited duration intervals use split-conformal absolute residuals. Their nominal marginal coverage depends on exchangeability; chronological drift, clustering and selection can violate it. Individual, conditional, sponsor-specific or prospective coverage is not guaranteed. Report empirical held-out coverage and width. When the finite-sample rank exceeds available calibration residuals, the valid interval is unbounded, not an invented finite range.

Range/category and numeric/text-length distribution checks are descriptive support warnings. In-range inputs may still be unfamiliar in correlated, textual or clinical features. These checks are not a calibrated OOD probability. A supported-domain label needs measured evidence, not absence of a simple flag. Abstention requires documented thresholds and a safe human-review path (R pp12,14; B p10).

Bootstrap confidence intervals on fixed-model held-out predictions reflect the stated resampling scheme. They normally omit model-fitting uncertainty, sponsor/site clustering, cohort construction uncertainty and hyperparameter selection effects. Paired difference intervals compare models on the same cases; they do not establish superiority across future cohorts.

## Explanations, similar trials and scenarios

Linear coefficients, global tree impurity importance, local SHAP and probability-scale effects are different objects. State the method, units and target. Do not show an uncalibrated model attribution as a contribution to calibrated probability without an appropriate transformation/explanation method. Attention weights are not definitive explanations (B p20).

TF-IDF cosine measures text overlap. It is neither clinical equivalence nor an outcome probability. Dense biomedical embeddings also need empirical clinical-relevance validation. Explain filters, pool size, exclusions and why a trial matched. Similarity to training cases cannot substitute for validation.

Protocol Twin changes are hypothetical model queries. Display baseline, changed feature values, assumptions, deltas, model identity, interval/applicability and unchanged source evidence. An input not consumed by the fitted model can affect only the explicitly separate planning arithmetic. Scenario outputs are predictive associations, not proof that an intervention will shorten a study or reduce amendments. Changing multiple correlated fields can create implausible/out-of-domain cases; source cohort membership does not validate a new hypothetical protocol (R pp22–23,30; B pp8–10,19).

## Generative AI and persistent chat

Generative AI may explain model outputs and retrieve/extract bounded protocol evidence; it must not invent numerical forecasts, citations, evidence or missing facts. Numerical outputs originate in identifiable fitted model artifacts. Treat imported documents, registry narratives and prior chat text as data, not instructions that override server safeguards (B pp10–11).

Chat history must be scoped to authenticated project/user access, persist across reload/restart, preserve failed-call states, and record actual provider/model/source references. Bounded history means older turns may be omitted; the assistant must not imply unlimited memory. Configuration/key presence does not verify model access or quality. Provider fallback can send the same bounded context to another configured provider, so the UI/data policy must disclose and govern it. Public mode supports public/synthetic data only.

FAST/BALANCED/DEEP profiles describe routing policy, not an established quality ranking. Provider/model examples in V p12 and U p8 were printed as date-sensitive examples and require official verification before use. No LLM should silently overwrite source facts, retrain, approve a candidate or promote a model.

## Governance and deployment claims

Approved persisted inference, privileged independent retraining, candidate approval and rollback are separate lifecycle states. Promotion must preserve model validation evidence, actor/time/reason and previous champion. Earlier reports keep the model version that produced them. A newly uploaded source never silently replaces the champion.

Authentication, permissions, project isolation and quotas belong on the server for every API path, export and job. Browser-only role buttons do not enforce access. Account/session authentication is not SSO/MFA. PostgreSQL configuration is not a live remote persistence test, and PostgreSQL metadata does not make local raw/model files durable across hosts. Back up both registry and artifacts and verify restoration.

An in-process background task is not a durable distributed worker. A model registry list is not a validated approval gate. A database hash chain can provide tamper evidence but is not immutable against privileged administrators without external retention/anchoring controls. A reviewer acknowledgement is not automatically a qualified electronic signature.

This project does not claim GxP, HIPAA, GDPR or Part 11 compliance. Applicability, organizational SOPs, intended use, deployment controls, contracts and qualified review determine those obligations. The PDFs propose controls and reference legal/regulatory material; this document does not independently confirm those changing requirements or provide legal advice (R pp19–20; B pp24–25).

A static preview can demonstrate UI/fixture calculations; it does not prove live Python training, provider requests, remote persistence, authentication security or clinical validity. Use explicit fixture/demo statuses. Reports and README must distinguish implemented software, configured/live-tested integrations, optional dependencies, pending research and production operations.

## Release claim checklist

Before claiming a result, require its exact source: real acquisition manifest; eligible split counts; fitted artifact and held-out prediction file; model/calibration version; relevant test output; live integration check; review/audit record; or actual deployment artifact. If evidence is absent, say unavailable, unverified, conditional or deferred.

Do not infer novelty from the absence of a public identical architecture. Both R and B identify substantial commercial/academic overlap. No first-of-its-kind claim, guaranteed accuracy, implied training sample size, assumed clinical benefit or unsupported regulatory approval should appear in v5.
