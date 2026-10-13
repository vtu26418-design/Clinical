# Research Hub, Digital Twin and Research Journey

These v4 screens extend the existing source-data workbench. They are research decision support, not clinical or regulatory advice. Scientific output comes from the current dataset, the documented fixed-reference PCI, compatible fitted artifacts, descriptive text retrieval and explicit planning assumptions. Fixture preview records remain software-test examples.

## Research Hub

Select an **Active study** from loaded workspace records. The selector includes records loaded by the application and records opened through Study Explorer. The workspace fetches the selected study, PCI components, compatible duration and phase predictions, related protocols, dataset provenance and evidence-dependent risk availability.

The four primary outputs are:

| Output | Meaning | Availability |
| --- | --- | --- |
| Protocol complexity | Fixed-reference, descriptive PCI on a 0–100 point scale | Calculated from source protocol features; missing fields are disclosed |
| Fitted duration | Duration in days from a compatible fitted duration artifact | Unavailable when no compatible artifact exists |
| Prolonged-duration risk | Duration-model probability/score relative to the training threshold | Displayed only for a supported fitted output; inspect evidence for calibration semantics |
| Phase consistency | Predicted phase compared with the recorded registry label | Requires a compatible phase classifier; the registry label remains authoritative |

The complexity bars all use a 0–100 point scale. They show each term's contribution to the final PCI, not a separate risk percentage. Missing numeric source fields contribute zero according to the shared PCI specification and are listed visibly. The PCI details expose the methodology and full component object.

**Explain the model evidence** exposes prediction scope, warnings, complete duration/phase objects, explanation, uncertainty and model/source metadata supplied by the API. Attribution is evidence about the fitted model, not a causal explanation. The phase-classifier scores do not assign a regulatory phase.

**Find protocols with related text** shows the actual TF-IDF cosine similarity as a decimal value. The API excludes the selected study and returns retrieval scope and phase-context evidence. Similarity is descriptive text retrieval, not clinical equivalence, treatment suitability or an outcome probability. Empty retrieval remains empty.

**Evidence-dependent risks** keeps recruitment and amendment risk unavailable without their required curated outcome labels and validated task-specific models. Deterministic recruitment planning does not unlock either probability.

**Source record** opens the preserved study. **Formula Studio**, **Inspect cohort validation**, and **Explore a scenario** navigate to the related workbench sections. **Evidence JSON** downloads the API-generated workspace and scenario packet with source scope, generation time and evidence checksum. The complete workspace evidence can also be inspected on screen. An unavailable API produces an explicit error and a Refresh action.

## Digital Twin

Choose a **Source study**. Permitted design inputs begin with that study's actual reported values. Enrollment, arms, primary/secondary outcome counts, eligibility-criteria count, text complexity and phase can be overridden. No IDs, recorded outcomes, dates or source text can be edited through this form. An empty optional field preserves its source value. An enrollment target missing from the source must be explicitly supplied before planning or saving; it never silently becomes zero. An explicitly reported or entered zero target is allowed and yields zero recruitment months.

The form matches API numeric bounds:

| Input | Bounds | Requirement |
| --- | --- | --- |
| Enrollment target | 0–10,000,000 | Finite number; source value or explicit scenario target required |
| Study arms | 0–1,000 | Whole number when supplied |
| Primary outcomes | 0–10,000 | Whole number when supplied |
| Secondary outcomes | 0–10,000 | Whole number when supplied |
| Eligibility-criteria count | 0–100,000 | Whole number when supplied |
| Text complexity | 0–10,000 | Finite number when supplied |
| Sites | 1–100,000 | Positive whole number |
| Monthly recruitment rate per site | 0.000000001–1,000,000 | Positive finite participants/site/month |
| Startup months | 0–1,200 | Finite nonnegative number |
| Follow-up months | 0–1,200 | Finite nonnegative number |

The initial planning values—10 sites, 2 participants per site per month, 3 startup months, and 6 follow-up months—are explicitly labeled editable assumptions. They are not imported source facts, measured recruitment rates or model estimates.

The live plan uses the shared frontend formula helper:

```
recruitment_months = target_enrollment / (sites × monthly_rate_per_site)
total_months = startup_months + recruitment_months + followup_months
```

For a target of 100, 10 sites, rate 2, startup 3 and follow-up 6, recruitment is 5 months and the planned total is 14 months. The model's duration prediction remains a separate output in days. Planning assumes a constant recruitment rate, simultaneous site activation, sequential stages, and no attrition, pauses, ramp-up or overlap. None of these arithmetic results is a recruitment-risk or clinical forecast.

**Compute & save scenario** sends only permitted changed design fields and the four planning assumptions to the API. The API recalculates PCI and obtains any compatible fitted duration output for the original and hypothetical feature sets. It stores a separate immutable scenario record; the source record is preserved. New scenarios appear in **Scenario history**, scoped to the current dataset and study. **Restore inputs** restores source design values and the explicitly labeled initial planning assumptions.

The saved comparison exposes source versus hypothetical PCI, fitted duration, prolonged-duration score, changes, assumption-based planning, warnings, preserved protocol data, model explanation, provenance and evidence SHA-256. An unavailable duration/probability remains unavailable. A changed feature's modeled difference is not a causal effect. Editing form inputs does not mutate a previously saved result. Select a scenario name in history to inspect that saved result; download its exact JSON with **Scenario JSON** or its row's download control. **Evidence JSON** downloads the full selected-study packet.

Local API scenario history is backed by the workbench registry. Browser preview scenarios follow the preview API implementation and do not imply that fitting or remote storage occurred.

## Research Journey

The native SVG journey explains six stages: Protocol, Startup, Recruitment, Follow-up, Analysis and Closeout. The first, fifth and sixth are explicitly conceptual and unmeasured. Only startup, recruitment and follow-up appear in the quantitative duration bar. Their widths are proportional to the actual entered/calculated month values; the displayed total and recruitment equation come from the same live planning calculation. Zero-length assumptions have zero width, and a total of zero draws no duration bar. Missing/invalid planning inputs show no timed forecast while preserving conceptual stage exploration.

Playback highlights workflow stages; it does not claim elapsed study time or completion percentage. No simulated participants, decorative research progress values or invented outcomes are used. Manual stage buttons expose the active stage and its explanatory text.

| Control | Behavior |
| --- | --- |
| Play/Pause | Starts or pauses stage highlighting; playback stops after Closeout |
| Step | Advances one stage and pauses automatic playback |
| Reset | Returns to Protocol and pauses |
| Speed | Selects 0.5×, 1× or 2× illustrative playback speed |
| Numbered stage button | Selects that stage and pauses |
| Focused-panel Space | Toggles playback |
| Focused-panel Right/Left arrow | Changes the active stage manually |
| Focused-panel Home | Resets to Protocol |

Native buttons and fields remain keyboard-operable. SVG titles describe the active stage and the numeric timeline. Manual-stage explanatory text is announced politely; playback suppresses repeated announcements. With `prefers-reduced-motion: reduce`, automatic playback and speed are disabled, transitions are removed, and Step, Reset and stage selection remain available.

## Section acceptance checks

1. Select two different source studies. Confirm title, phase, PCI, retrieval and source checksum are scoped to the selected dataset/study and no previous-study prediction remains visible while loading.
2. Open a record without a compatible fitted model. Confirm duration, prolonged risk and phase-classifier outputs say Unavailable rather than invented values. Recruitment and amendment risk remain explicitly unavailable without labels.
3. Inspect PCI inputs with missing values. Confirm the missing-field warning and exact component evidence remain visible. Compare the methodology with the shared formula specification.
4. Open a related protocol and inspect the downloaded evidence JSON. Confirm the selected study is excluded from its own retrieval and the packet includes provenance and retrieval scope.
5. In Digital Twin, use a 100-person target, 10 sites, rate 2, startup 3, follow-up 6. Confirm recruitment 5 months and total 14 months in the live summary and journey, then save and inspect the exact saved result.
6. Change one permitted source design feature and save. Confirm the original source object is preserved and the scenario object contains the hypothetical value. Confirm unsupported fitted outputs remain unavailable.
7. Inspect a source with missing enrollment. Confirm the form requires an explicit target and does not save a zero-target plan. Try negative, nonfinite, out-of-range and fractional site/count values; confirm the relevant validation prevents submission.
8. Save two named scenarios, change the form again, and select an older history entry. Confirm its saved result and evidence checksum remain unchanged. Download both scenario JSON and complete Evidence JSON.
9. Use Play/Pause, Step, Reset, every speed and every numbered stage. Verify automatic playback stops at Closeout. Focus the panel and test Space, arrows and Home.
10. Enable reduced motion. Confirm automatic playback is disabled while manual controls still work. Verify desktop and mobile views retain readable values, labels, source evidence and accessible scrolling for wide tables/diagrams.

Backend endpoints are under authenticated `/api/v1/research`: workspace, scenarios, similar and evidence. Review `docs/API_CONTRACT.md`, `docs/FORMULA_SPECIFICATION.md`, `docs/V4_MODELS.md` and the full v4 operating guide for their integration and scientific contract.
