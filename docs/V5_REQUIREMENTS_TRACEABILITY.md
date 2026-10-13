# V5 requirements and evidence traceability

Audit date: 2026-10-09. This document records the requested scope and the implementation evidence actually inspected. A pending requirement is not a delivered capability. The separate v4 directory is the preservation baseline and was read only during this audit.

## Final release implementation overlay

The earlier audit table below is retained as the requirements baseline. Final integrated evidence is in RELEASE_V5_VERIFICATION.md. Delivered: session auth and project roles, persisted chat, CSV/XLSX/JSON/Parquet/paste/allowlisted URL imports, approved pretrained inference and separate owner candidate lifecycle, protocol evidence/human review/version comparison, nullable seven-domain rubric, feature-availability audit, model cards, animated learning, full guide and packaged UI. 299 Python tests pass; one optional SHAP test is skipped.

Conditional: live AI providers and remote PostgreSQL require account credentials and have not been exercised against paid/live accounts. Deferred: external/prospective validation, clinical PDF models, recruitment/amendment risk, advanced survival serving and the longer production/clinical program. Web builds pass; rendered browser interaction QA remains manual because supported automation was unavailable.

The additional five-page supplied document was **Clinical_Trial_Intelligence_V5_Pretrained_Model_Update_Prompt(1).pdf**. Its central no-training-on-normal-upload requirements are implemented and covered by test_v5_inference.py.

## Source documents and page convention

All four supplied PDFs were read completely from their extracted text. References below use **physical PDF page numbers**, including cover pages. In U, physical page 2 carries printed slide number 06; use the physical page when locating references.

| Key | Supplied document | Pages read |
|---|---|---|
| R | **CLINICAL TRIAL INTELLIGENCE — Explainable Multimodal AI System for Clinical Trial Protocol Complexity and Prolonged-Duration Risk Prediction**, Production-Ready V5 Deep Research Report | 1–37 |
| B | **Clinical Trial Intelligence V5 — Deep Research, Differentiation, Production and Publication Blueprint** | 1–31 |
| V | **Clinical_Trial_Intelligence_Advanced_Visual_Upgrade_Roadmap(3)** | 1–18 |
| U | **Clinical_Trial_Intelligence_Updates_Only_V4_V5(4)** | 1–13 |
| USER | User delivery requirements relayed with the task | Separate v5; preserve v4; advanced verified models; persistent project chat; auth/role limits; remote PostgreSQL; multiple imports; useful animation; preview, ZIP and full guide |
| APPROVED | Additional approved-model requirement relayed by the integration lead after the four-document audit | Persisted approved models serve ordinary uploads; retraining is independent, owner/admin controlled, followed by candidate approval and rollback. This audit did not receive that additional document's title/pages and does not invent them. |

The PDFs are requirements sources, not independent proof of current provider availability, legal compliance, training sample size or achieved model performance. Their market claims, example probabilities, example quantiles, screenshots and ratings are not application results. R and B explicitly say the earlier shared conversation/source was unavailable to their authors (R p35; B p2); V's inspected baseline is v2 (V pp1–5), so this audit uses actual v4 source to establish the starting point.

## Status meanings

- **Retained:** present in inspected v4 source and carried into the v5 copy; release regression verification still applies.
- **V5 verification pending:** allocated or being implemented during this audit; do not describe as delivered until executable source, relevant tests and release evidence exist.
- **Conditional:** runnable adapter/module requires additional curated data, installed dependencies, secrets or infrastructure. Configuration is not a successful live test.
- **Deferred/data dependent:** no demonstrated implementation or required scientific evidence; expose unavailable status rather than a fabricated result.

`V5_MODEL_CARD.md` and the release verification report, when present, should record completed runs and final integration results. Their evidence may advance a status; a feature name or UI mockup cannot.

## Starting point confirmed from v4 source

`backend/app/main.py`, `services/data_service.py`, `services/assistant_service.py`, `services/research_workspace.py`, `src/clinical_trial_intelligence/research.py`, `models/survival.py`, `nlp/biobert.py` and the v4 frontend were inspected read only.

V4 has twelve research screens, CSV/Parquet and ClinicalTrials.gov imports, a local SQLite registry with an optional PostgreSQL metadata adapter, a frozen 800-record authentic latest-state registry cohort, seven completed-trial duration/risk branches, a separate phase classifier/academy, train-only preprocessing, chronological outcome purging, reserved probability calibration and conformal residual intervals, TF-IDF retrieval, immutable scenario packets, and a multi-provider assistant. V4 chat is React component state; it sends no prior turns. V4 authentication is an optional shared bearer token, not user identity or RBAC. Training uses an in-process worker; a restart marks work failed. Bulk datasets and model files remain on disk even when metadata uses PostgreSQL. Optional Cox, BioBERT and SHAP modules are present but are outside the verified core. Recruitment/amendment probabilities are explicitly unavailable.

## Preservation, inference lifecycle and delivery

| ID | Exact requirement and acceptance evidence | Source | V4 baseline / v5 status at audit |
|---|---|---|---|
| D01 | Work only in a separate v5 directory; verify original v4 content hashes and existing delivery remain unchanged. | USER; analogous freeze/inventory R p32 | Separate v5 copy exists; final hash verification pending. |
| D02 | Preserve existing workflows while adding a study-centered workspace rather than replacing research tools. | V p4; U pp3,9 | Retained; frontend integration verification pending. |
| D03 | Default inference uses an approved persisted model artifact; an ordinary upload must not start fitting or force a new training run. | APPROVED | V4 models are tightly dataset/source bound; cross-dataset approved inference is a v5 change requiring schema/domain compatibility gates. Verification pending. |
| D04 | Separate ingestion, inference and retraining. Owner/admin starts a candidate run; a reviewer/authorized owner approves a version; record promotion, prior champion and rollback. | APPROVED; R pp16–18; B pp24,27–28 | V4 experiment history exists; governed cross-dataset champion lifecycle verification pending. |
| D05 | A model artifact must be compatible with feature schema, units, task, preprocessing, calibration and source/run hashes before inference. Unknown or incompatible artifacts fail closed. | R pp16–17; U p12 | V4 hash/task/version checks retained; approved-artifact generalization requires new evidence. |
| D06 | Supply runnable source ZIP, setup/update/backup instructions, full PDF guide and a reviewable preview whose runtime limitations are explicit. | USER; R pp26–27,35 | V4 has packaging and guide tooling; v5 deliverables/release verification pending. |
| D07 | Report actual cohort counts and test metrics; no world-first, guaranteed accuracy, arbitrary training-size or production-readiness claims. | R pp1–5,13,31–35; B pp1–5,27–30 | Required communication boundary throughout. |

## Data, imports and protocol evidence

| ID | Exact requirement and acceptance evidence | Source | V4 baseline / v5 status at audit |
|---|---|---|---|
| I01 | Ingest ClinicalTrials.gov/NCT and dated AACT extracts; retain raw response, acquisition time, schema/mapping version, source hash and data license/privacy metadata. | R pp6,15; B pp11–13; U p3 | CT.gov API and AACT flat-file scripts retained; AACT is not the same as a live managed database connector. |
| I02 | Support multiple deliberate imports: upload, registry, pasted structured data and safe supported URLs; validate type, size, required fields, duplicate IDs and dates before commit. | USER; B pp22–24; U pp3,11 | CSV/Parquet/registry retained; extra formats/paste/URL v5 verification pending. Arbitrary network fetches must not expose internal services or credentials. |
| I03 | Keep immutable source and canonical versions; record schema evolution, missingness and feature lineage. Separate source facts from reviewer corrections. | R pp15–17,32; U p11 | Raw/canonical hashes retained; per-feature/document history and controlled correction pending. |
| I04 | For every prediction store study ID, source, snapshot timestamp, prediction timestamp, protocol version, document hash and feature-availability timestamps. | B pp12–13; R pp6–7,17 | V4 snapshot provenance exists; row/feature point-in-time enforcement pending. |
| I05 | Enforce feature availability at or before prediction time; exclude actual enrollment, actual completion, final status, results, future amendments/sites/recruitment from design-time inputs. Unknown provenance cannot pass the pretrial gate. | B pp12–13,27; R pp7,32 | V4 excludes named outcome columns but latest-state enrollment/text may still leak; **not fulfilled by temporal split alone**. |
| I06 | Track original planned versus actual dates/enrollment; retain censored ongoing trials in a separate valid survival cohort. | R pp10–12,32; B pp7,12–15 | Core v4 cohort is completed-only. Curated Cox script retained; new survival dataset needed. |
| I07 | Parse protocol versions into reviewable evidence: inclusion/exclusion, endpoints/objectives, visits, procedures, assessments, laboratory/imaging/invasive burden, PROs, hospitalization, washout/run-in/follow-up, temporal/biomarker restrictions, site/travel burden and schedule density. | R pp7–8,33; B pp10–11,15–17 | Document-native extraction and schedule parsing pending; simplistic text counts cannot claim all these fields. |
| I08 | Every extracted feature links to document hash/version, page/section/paragraph or exact span; record confidence, extraction method and accepted/corrected/rejected review. | R pp14,23; B pp19–20 | Registry evidence retained; document-level Evidence Trace pending. |
| I09 | Quantify field-level extraction accuracy/precision/recall/F1, source grounding, error rate and schedule extraction accuracy using adjudicated examples. | B pp16–17,28 | Deferred/data dependent. Parsing software success is not extraction validity. |
| I10 | Add controlled disease terminology, optional drug/molecule descriptors and a modality mask; missing molecular structure must not break non-drug trials. | R pp6,9–10; B pp11,14–15 | Deferred/data dependent. No claim of ontology, molecular, graph or neural fusion simply from structured+text inputs. |
| I11 | Map toward USDM; define harmonized CTIS/WHO/external-registry adapters and held-out evaluation cohorts. | R pp6,15–16,32; B p11 | Deferred/configuration and licensed-access dependent; no untested live connector claims. |
| I12 | Sponsor CTMS/EDC/eTMF, recruitment funnels, site operations and amendment histories use separate authorized adapters and privacy controls. | B pp6,11,24; U p11 | Deferred/private-data dependent. Public registries do not supply all operational labels. |

## Numerical models, targets and validation

| ID | Exact requirement and acceptance evidence | Source | V4 baseline / v5 status at audit |
|---|---|---|---|
| M01 | Maintain naive median/prevalence, Ridge/ElasticNet, logistic and TF-IDF baselines; compare added nonlinear models on identical locked cohorts. | R pp8–13,31; B pp13,28; U p4 | Seven v4 branches retained. Histogram boosting and tuned structured/text late fusion are v5 work; metrics must come from actual runs. |
| M02 | Compare XGBoost/CatBoost/LightGBM as appropriate; added complexity is accepted only with useful held-out evidence, calibration or operational benefit. | R pp8–10; B pp13–15; V p8; U p4 | Named third-party boosting libraries are not fulfilled by sklearn Gradient/Histogram Boosting. Deferred unless installed, executed and reported. |
| M03 | Fit censoring-aware duration baselines: Kaplan–Meier cohort, Cox, AFT and nonlinear survival; DeepSurv is a candidate, not an assumed winner. | R pp8–12; B pp7,13–16; U p4 | Optional curated Cox retained. KM/AFT/RSF/DeepSurv benchmark and production inference deferred/data dependent. |
| M04 | Return valid duration distribution S(t), P25/P50/P75/P90, point prediction where defined and intervals; unsupported quantiles remain null with reason. | R pp10–14; B pp6–8,19 | V4 point prediction + residual interval retained; these are not a survival distribution. Quantile serving pending. |
| M05 | Define public long-duration target using a training-only matched phase/indication/type/era Q75; retain target definition/version/threshold. | B p8; R p11 | V4 uses one training-cohort Q75, **not matched-cohort Q75**. Conditional subgroup target work required. |
| M06 | Compute delay-vs-plan only from a genuine design-time planned completion date and prespecified tolerance, with separate labels/model. | R pp3,11,29; B p8 | Deferred/data dependent; never relabel long duration as delay. |
| M07 | Decompose PCI into seven transparent domains; disclose weights, caps, missingness and evidence. Validate against blinded expert ratings/outcomes before clinical claims. | B pp6–7,16,18; R pp7–8 | V4 descriptive feature PCI retained; seven-domain PCI pending; no weights/caps supplied by the PDFs. |
| M08 | Amendment risk uses adjudicated material changes/version-history labels; separate eligibility/endpoint/schedule/site/design outcomes where supported; calibrate real outputs. | B pp6,8,15–16; R pp3,29 | Unavailable. Heuristic burden scores or chat percentages must not be presented as learned amendment probability. |
| M09 | Recruitment feasibility/slow-accrual models require actual outcome/operational labels; deterministic target/sites/rate is a labeled planning calculation. | U pp5–6; V pp9–10 | V4 planning retained; calibrated recruitment probability unavailable. |
| M10 | Biomedical text encoder uses pinned revisions, section-aware chunking and hierarchy; compare text-only, structured+text, disease/molecule and modality ablations. | R pp9–10,13,33; B pp14–15,28 | Optional frozen BioBERT retained; core verified model text is TF-IDF. Hierarchical transformer/gated fusion deferred. |
| M11 | GNN/graph transformer is experimental, added only after graph correctness and locked-test incremental benefit. | R pp9–10,33 | Deferred; explicitly conditional in source. |
| M12 | Temporal train/tune/calibrate/locked-test separation; train-only transforms, outcome maturity purging, protocol-family/sponsor/program grouping where feasible. | R pp12–13; B p17; U pp4,7,12 | Temporal/train-only/purging retained; separate calibration retained. Grouped leakage controls and external test not established. |
| M13 | Probability calibration, reliability, Brier, AUROC/AUPRC; distinguish raw and calibrated outputs, unsupported classes and in-sample calibration metrics. | R p12; B p16; U pp7,12 | V4 guarded sigmoid/calibrated fields retained; calibration slope/intercept, decision curve and broader validation deferred. |
| M14 | Regression MAE/RMSE/median AE, survival Harrell/Uno C-index, integrated/time-specific Brier, dynamic AUC and horizon calibration, plus subgroup results. | R pp11–12; B p16 | V4 MAE/RMSE/R² and classification metrics retained; optional Cox Harrell C-index. Remaining metrics conditional/deferred. |
| M15 | Report 80/90% interval coverage, width and phase/therapeutic/OOD subgroups, with assumptions and limitations. | R pp12,14,33; B p16 | V4 nominal configurable conformal coverage/test coverage retained; comprehensive subgroup/80%+90% analysis pending. |
| M16 | Show input support/shift signals and explicit unknown/low confidence/out-of-domain/abstain states. Do not call range checks a validated OOD probability. | R pp14,18,33; B p10; U p7 | Training range/category checks retained; numeric/text-length distribution warnings are v5 work. Validated OOD detector/abstention thresholds deferred. |
| M17 | Present global/local attributions and protocol evidence in their actual scale. Attention weights and impurity importance are not local SHAP or causal proof. | R pp13–14,23; B p20; U p7 | Linear contributions/global tree importances retained; SHAP optional. Clause-linked attribution pending. |
| M18 | Preserve exact model/config/seed/environment/data/code/feature hashes and held-out predictions; record software, statistical and clinical validation separately. | R pp16–17,24,31; B pp23–28; U p12 | Core manifests retained; release/model registry and approved inference evidence pending. |
| M19 | External registry, therapeutic-area and prospective shadow validation precede clinical/enterprise performance claims. | R pp12,32,35; B pp17,27–30; U p12 | Deferred; unit/integration tests and larger latest-state training do not satisfy this requirement. |

## Researcher experience, AI and animation

| ID | Exact requirement and acceptance evidence | Source | V4 baseline / v5 status at audit |
|---|---|---|---|
| X01 | Study-centered portfolio, unified Risk Hub, phase intelligence, protocol evidence, comparable trials, twin, validation and reports share active project/study context. | V pp4,7,14; U pp3,10; B pp17–20 | V4 Research Hub/navigation retained; project scope/portfolio integration pending. |
| X02 | Phase I–IV objectives, endpoints, enrollment/monitoring expectations, combined/unknown phases, confidence and controlled overrides. | V p6; U p2 | Phase academy and classifier retained. Class scores uncalibrated; manual override must not overwrite source fact. |
| X03 | Similar-trial retrieval excludes self, applies phase/condition/design/enrollment/geography/intervention filters, explains matches and shows benchmark support. | B pp9–10; U p4 | TF-IDF + exact phase retained; dense/ontology clinical matching and validated equivalence deferred. |
| X04 | Save baseline and multiple scenarios with allowed design variables, bounds, explicit assumptions, deltas, interval/applicability/evidence, immutable original and noncausal language. | R pp22–23,30; B pp8–10,19; U p6 | Existing bounded scenarios retained; new document/visit/geography fields conditional on model support. A slider must not claim the model uses that variable unless it does. |
| X05 | Evidence report includes snapshot, source hash, model/calibration version, training cutoff, uncertainty, OOD, limitations, review state and packet/report hash. | B pp6–7,23–24; R pp14,17; U pp5,7,12 | JSON evidence packets retained; unified protocol/review report and PDF generation pending. |
| X06 | LLM/RAG extracts/explains source-grounded facts; numerical predictions come from versioned statistical models. Treat source documents as untrusted data. | B pp10–11; R pp2,9; U pp8–9 | Server assistant guardrails retained; document RAG/extraction verification pending. |
| X07 | Save conversations and messages durably per project/user, reload history, include bounded relevant prior context, record real provider/model/reference/failed-call state. | USER; supporting U pp8–11 | V4 chat state is ephemeral. V5 session/project conversations and persistence verification pending. |
| X08 | Provider-neutral OpenAI/Gemini/Claude routing with FAST/BALANCED/DEEP/approved profiles, budget/data policy and server-only secrets; access verified separately from key presence. | U p8; V pp12,18 | Multi-provider preference/fallback retained; profiles/quotas v5 verification pending. PDF model names are examples, not verified API identifiers. |
| X09 | Useful one-shot prediction/evidence/scenario animations, controlled journey playback and OS reduced motion; no decorative continuous clinical progress. | R pp24–25; V p6; U p2 | V4 keyboard-controlled journey/academy/reduced motion retained; new evidence transition verification pending. |
| X10 | Accessible labeled charts/statuses and UNKNOWN/INSUFFICIENT states; not color alone; responsive layout and WCAG 2.2 AA target. | B pp20–21; R p34 | Existing accessible controls retained; full conformance requires audit, not just a CSS media query. |
| X11 | Research view exposes cohort config, split years/counts, seed, hashes, configs, metrics/CIs, calibration, ablations, subgroup and model card. | R p24; B pp26–28 | Experiments/Validation Lab retained; ablation/publication package conditional on actual experiments. |

## Identity, governance, operations and settings

| ID | Exact requirement and acceptance evidence | Source | V4 baseline / v5 status at audit |
|---|---|---|---|
| P01 | Authenticated accounts, project/tenant isolation and server-enforced role permissions on every read/mutation/export/background operation; no UI-only enforcement. | USER; U p11; B p24; R pp20,34 | Shared optional bearer token replaced/extended by v5 identity; verification pending. |
| P02 | Owner/admin/researcher/reviewer/viewer boundaries, invitations, session expiry/revocation and least privilege; SSO/OIDC/SAML/MFA are separate enterprise integrations. | R pp25–26,34; B p24 | Local/session roles v5 work. Enterprise federation/MFA deferred unless explicitly tested. |
| P03 | Project-scoped request/import/training/chat limits enforced transactionally by server; meaningful failure messages and actual usage. | USER; U p11 | V4 global size/train limits retained; role/project quotas verification pending. |
| P04 | Durable remote PostgreSQL for users/projects/settings/chat/audit/registry; restart persistence and actual remote roundtrip test; no secret printed or put in frontend. | USER; B pp21–22 | Optional adapter retained; remote provisioning/connectivity conditional and must be reported separately. |
| P05 | Durable jobs with states, attempts, retry/restart recovery and artifact references; do not describe in-process threads as a durable queue. | U p11; V p15; B pp21–22 | V4 in-process worker retained until new queue verified. External broker/worker remains deployment-dependent. |
| P06 | Model registry supports candidate/champion, validation gates, approval/rollback and drift/change history; approved inference independent of uploads. | APPROVED; B p24; R pp16–18 | V5 verification pending. A list of experiments alone is not model governance. |
| P07 | Human review stores actor/time/outcome/comment/corrected values and report version; accepted/corrected/rejected records remain auditable. | B p4,24; R pp17,20,26 | V5 workflow pending. Review acknowledgement is not a legally qualified electronic signature. |
| P08 | Append-only audit events cover access, exports, model/data/config/permission changes, overrides and approvals; export inspection history with tamper evidence. | R pp18–20; B p24; U p11 | V5 pending. Database hash chains are not independently immutable against administrators. |
| P09 | Public mode allows public/synthetic data only; enterprise privacy/retention/deletion/residency controls require deployment-specific review. | B pp6,24; R pp19–20,25–26 | Public research boundary retained; enterprise PHI workflows deferred. No HIPAA/GxP/Part 11 certification claim. |
| P10 | Production TLS, encryption at rest, secret manager, file type/size/malware checks, network controls, security scans and incident handling. | B p24; R pp17,20,27,34 | Code-level file limits/secret separation retained; managed infrastructure and security validation conditional/deferred. |
| P11 | Versioned APIs, migrations, containers/CI, backup/restore/disaster recovery, staging/canary, rollback and load/SLO verification. | R pp17,27,34; B pp21–27 | V4 API/container/CI assets retained; production recovery/load/gates need operational execution. |
| P12 | Monitor data schema/missingness/text drift, prediction/calibration/coverage drift after labels mature, OOD/abstention, application failures and governance events. | R pp18–19; B pp22,24–25 | Health/data-quality screens retained; real monitoring collectors/alerts and mature-outcome drift deferred. |
| P13 | Settings cover organization/users, permissions, sources/parser, champion/calibration/thresholds/coverage/OOD, benchmark/retrieval, scenario bounds, review, audit/retention/privacy, API/webhooks/notifications, monitoring/accessibility/research. | R pp25–26 | Project settings v5 work. Only implemented settings should be editable; future options must not imply operational enforcement. |
| P14 | Measure review time, correction/acceptance rates, validated findings, scenarios, upload-to-review time and confidence coverage without inventing savings. | B p25; R p27 | Deferred until recorded events/cohorts support actual calculations. |
| P15 | Publication package includes intended use/limitations, model/data cards, cohort flow, leakage rules, ablations, calibration/subgroups, reproducible config and TRIPOD+AI mapping. | R pp19,24,31–35; B pp25–28 | This traceability/boundaries work is included; actual research/paper/external validation deferred. |

## Seven-domain PCI contract

B pp6–7 proposes the following weighted decomposition, but supplies **no validated numeric weights or normalization caps**:

`PCI = w1·D_design + w2·D_eligibility + w3·D_patient + w4·D_site + w5·D_endpoint + w6·D_geo/reg + w7·D_intervention`

| Domain | Evidence needed before a meaningful domain score |
|---|---|
| Study Design Complexity | Allocation, masking, arms, design/adaptive elements and intervention structure |
| Eligibility Complexity | Adjudicated constraints, inclusion/exclusion, temporal/biomarker restrictions and supporting clauses |
| Patient Burden | Visit/procedure schedule, invasive assessments, PROs, travel and follow-up |
| Site / Operational Burden | Site activities, staffing/procedures, planned network and execution assumptions |
| Endpoint / Data Burden | Primary/secondary/exploratory endpoints and schedule/assessment density |
| Geographic / Regulatory Burden | Planned countries/regions and documented cross-jurisdiction requirements |
| Intervention / Safety Burden | Intervention modality, dosing/administration and documented monitoring burden |

An equal-weight or expert-chosen first version is a transparent research heuristic. Unknown domains stay unknown and total coverage must be shown. Do not silently fill unavailable patient/site/geographic/safety values from enrollment or assign them zero burden. Any partial aggregate must state its denominator and cannot be compared to a fully observed score as if identical. Keep legacy PCI visible under its original name/formula until the new specification is explicitly versioned and verified.

## Approved-model lifecycle: ten release acceptance checks

The integration lead relayed a requirement for ten tests. These are concrete acceptance checks for that requirement, not a claim that the tests have already passed:

1. Importing a new valid dataset creates source records and **does not** create a training run or mutate the approved champion.
2. Ordinary analysis loads the approved persisted artifact after process restart and returns its exact version/hash/calibration identity.
3. A new dataset compatible with the model schema receives inference without requiring a dataset-identical training artifact; output records both training-source provenance and inference-source provenance.
4. Missing or incompatible approved artifacts return explicit unavailable/conflict status; the server does not fit silently or substitute an unapproved candidate.
5. A non-owner/non-admin cannot start retraining through either UI or direct API; the request creates no run or artifact.
6. An owner/admin can launch an independent candidate run with fixed snapshot/config/seed; existing approved inference remains available.
7. Candidate completion does not automatically promote the model; failed validation gates prevent promotion and record the reason.
8. Authorized promotion records actor/time/comment, candidate identity, prior champion and validation evidence, and affects subsequent inference atomically.
9. Authorized rollback restores the prior approved version; earlier reports/predictions retain their original immutable model references.
10. Project isolation, restart persistence, quotas and audit behavior hold across ingestion, inference, training, promotion and rollback; cross-project identifiers cannot access private artifacts.

## Release prioritization

P0: preserve v4; correct source/provenance/availability semantics; approved default inference; independent privileged training; server identity/project isolation/quotas; persisted chat/settings; actual PostgreSQL verification; meaningful model comparison and honest unavailable outputs.

P1: document-native evidence/review, seven-domain nullable PCI, explainable matched retrieval, governed scenario/report workflow, censoring-aware serving with curated data, useful accessible motion.

P2/data gates: validated amendment/recruitment models, biomedical/hierarchical/ontology/molecular branches and ablations, advanced survival benchmark, external/prospective validation, SSO/MFA, object storage/durable distributed workers, security/load/backup drills, production monitoring and qualified compliance/publication work.

A release that implements P0 plus selected P1 remains an advanced research workbench; it must not be described as the entire 28-week, multi-disciplinary production program proposed by R p28.
