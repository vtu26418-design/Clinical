# v4 delivery against the supplied roadmaps

The two supplied upgrade PDFs were read in full: Clinical_Trial_Intelligence_Advanced_Visual_Upgrade_Roadmap(1).pdf and Clinical_Trial_Intelligence_Updates_Only_V4_V5(2).pdf. Their illustrative values and future provider names are not treated as observed results or available model IDs. This release upgrades the existing v3 implementation, retaining its data and workflows.

| Requested area | v4 delivery | Evidence / further work |
|---|---|---|
| Unified risk/research hub | Implemented Research Hub with source, PCI, duration and phase evidence, same-phase cohort context and retrieval | Recruitment and amendment probabilities explicitly unavailable without curated outcomes |
| Digital Twin | Implemented protocol overrides, immutable scenario history, source/model provenance and bounded JSON evidence export | Hypothetical model queries are not causal or prospectively validated forecasts |
| More useful animation | Implemented planning journey, validation roles and PCI term accumulation; retained Phase Academy | Keyboard/manual controls, playback/speed/reset and reduced-motion behavior |
| Clinical phase understanding | Retained separate multiclass classifier, reported-vs-predicted comparison and animated Phase0-IV academy | Phase class scores remain uncalibrated; combined phases are excluded from single-phase classifier training |
| More models | Seven duration/risk branches including deterministic Gradient Boosting, Extra Trees and Random Forest | More complex models are compared against median/prior and linear baselines; no guarantee of superiority |
| Uncertainty and calibration | Reserved calibration rows, split-conformal intervals and guarded sigmoid probability calibration | Chronological shift can violate coverage assumptions; unavailable support stays null |
| Similar trials | Bounded TF-IDF cosine retrieval with self exclusion and exact normalized phase filter | Dense biomedical embeddings and validation of clinical similarity are future work |
| Formula/values audit | Shared weights/caps/rounding specification; known-answer tests, 805-row Python/JS comparison, exact conformal ranks | Descriptive PCI assumptions are not validated clinical thresholds |
| Data and reproducibility | 800 frozen authentic registry records, raw responses, checksums, actual fitted artifacts, manifests and held-out predictions | Snapshot is convenience sampled, latest-state and retrospective; prospective baseline curation remains necessary |
| Full instructions | Included PDF and editable Markdown: setup, every screen, testing, keys, errors, updates and backups | Operating-system/provider limitations are recorded in VERIFICATION.md |
| Browser preview | Fixture-only Sites demo with working animation, formulas and scenarios | Python fitting, imports, persistent history and AI providers run in the full local app |
| V5 foundations | Versioned task artifacts, source/model hashes, evidence packets, bounded provider context, separate model branches | External/prospective validation, drift monitoring, curated amendment/recruitment tasks, durable queues, multiuser RBAC and governed model registry are planned |
| Provider flexibility (v4.0.1) | OpenAI, Gemini, Claude and optional OpenAI-compatible adapter, configurable auto routing/fallback and manual selection | Key presence is not live access or a measured quality ranking; live provider accounts remain unverified |

No clinical validity, regulatory approval, guaranteed prediction accuracy or production enterprise governance is claimed. Mathematical checks and software validation are distinct from validating a clinical model.
