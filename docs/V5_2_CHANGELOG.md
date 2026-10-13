# v5.2.0 changes and request coverage

This is an implemented development release based on the selected v5 repository. The supplied v5.1 archive could not be downloaded because it exceeds the 32 MiB tool limit; a v5.1 merge is not claimed.

## Delivered additions

- Responsive Research home and navy/teal workspace; guided import → saved prediction → scenario → evidence workflow.
- Interactive decorative molecular helix, selectable/playable model pipeline and actual model-explanation bars when numeric attribution evidence exists. Reduced-motion support.
- Live ClinicalTrials.gov, PubMed and openFDA drug-label search with source links, timestamps, response limits and safe error handling.
- Server-persisted project evidence library, CSV export and owner/researcher write enforcement. New saves use a 24-hour server search cache so invented client titles or citations cannot replace source results.
- Resend email-verification integration with configured HTTPS origin, explicit confirmation, hashed single-use one-hour tokens, revocation/rate limits and optional account-access gate. No actual email was sent during verification.
- Genuine provider SSE chat streaming with a selected configured provider, Markdown/table rendering, safe links, stop/partial-error states, existing project context and references. Live paid requests require credentials and were not tested.
- Cohort-monitoring command for numeric/categorical shift, missingness, trial overlap and input hashes. It requests human review rather than automatically promoting a model.
- Self-contained preview, rendered desktop/mobile screenshots, 19-page operating guide, source ZIP packaging fix and reproducible verification receipts.

## Retained and verified

Saved duration/phase inference, model registry approvals/activation/rollback, temporal training, structured/text/multimodal comparisons, uncertainty, protocol extraction/review, four project roles, saved conversations, descriptive study comparison/reporting, Digital Twin and phase education.

Approved artifacts remain unchanged. Saved predictions and metrics replayed successfully on the existing frozen cohort. A release upgrade does not establish improved scientific accuracy.

## Full prompt coverage

| Request | Status in this release |
| --- | --- |
| Upgraded downloadable v5.2.0 project, preview and guide | Included |
| Modernized UI | Implemented with desktop/mobile browser checks |
| Streaming research assistant with citations | Implemented provider streaming and supplied context reference cards; each generated claim still needs human verification |
| Inline assistant charts | Markdown tables supported; no arbitrary model-generated scientific charts are treated as evidence |
| Provider choice | Existing OpenAI/Anthropic/Gemini/compatible configuration preserved; no universal best model or free provider key claimed |
| ClinicalTrials.gov + PubMed + openFDA | Live tested; PubMed metadata and openFDA labels are the implemented endpoints |
| Login and role-based access | Existing session/password/project roles retained; new email-verification support added |
| Google login/SSO | Deferred; requires external identity provider and deployment design |
| Email verification link | Implemented; actual delivery requires a verified sender and server credential |
| Saved workspaces/bookmarks | Existing projects/history plus new server-side citation bookmarks |
| Comparison/export | Existing descriptive comparison, CSV, evidence JSON and printable HTML/PDF workflow |
| Prediction pipeline and multimodal fusion visual | Implemented illustrative pipeline; actual fusion components shown when model evidence exists |
| Phase timeline and recruitment journey | Existing educational/assumption-based interactive journeys retained |
| XAI animation | Actual contribution/importance bars; no fabricated SHAP values for unsupported models |
| What-if simulation | Existing backend calculation and saved scenario preserved and browser-tested |
| 3D-style molecular homepage | Interactive decorative SVG helix with perspective response; not a molecular/physiological simulator |
| Trial success, recruitment or amendment predictor | No validated target/model provided; remains explicitly unavailable |
| Massive-cohort training and automatic daily improvement | Monitoring and reproducible candidate workflow provided; no massive training or automatic promotion performed |
| Durable distributed jobs/cloud production platform | Existing local worker and Docker sources retained; production orchestration/deployment is not claimed |
| HIPAA/Part 11 compliance or mistake-free models | Not claimed; requires external validation and organizational controls |
| Supplied v5.1 ZIP integration | Blocked by uploaded archive transfer size; base is the v5 Git checkout |

## External configuration

Live public search was tested after saving exact network hostnames. Paid AI, Resend delivery, remote PostgreSQL and hosting were not exercised. Model names must be selected from the operator's actual provider account. Secrets belong in server configuration; none are shipped in the archive.
