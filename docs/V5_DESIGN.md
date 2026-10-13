# Clinical Trial Intelligence v5 design

## User brief
Upgrade v4 without modifying the original folder. Preserve all twelve existing research screens, formulas, real starter data and provider adapters. Add a usable project platform, role-limited access, saved contextual conversations, more import methods, protocol evidence, improved model evaluation and meaningful prediction animation. Deliver a separate preview, full ZIP and complete operating/training guide. Production deployment is a later user task.

## Architecture
Keep React/Vite and Python/FastAPI. PostgreSQL is the production metadata store; use server-side DATABASE_URL with psycopg and TLS. SQLite remains an explicitly labelled offline development fallback. Never pretend a remote database is connected when no credentials are supplied. Store raw datasets/model artifacts in private storage; describe persistent volume/object storage requirements clearly.

The v5 platform exposes /api/v5 for sessions, projects, project settings, members, audit and saved chat. Existing /api/v1 research endpoints execute in a project-isolated registry selected by X-Project-ID. Platform login uses a server-generated, expiring session, secure password hashing and no public admin registration. Roles: owner, researcher, reviewer, viewer. All API access checks must be enforced server-side; hiding buttons is insufficient. Anonymous local mode uses one explicit local workspace and is forbidden in production mode.

## Frontend/backend contract
- GET /api/v5/bootstrap -> {auth_required, setup_required, user, projects, database, capabilities}
- POST /api/v5/auth/setup {email,password,name,setup_token}; POST /api/v5/auth/login {email,password}; POST /api/v5/auth/logout; GET /api/v5/auth/me.
- GET/POST /api/v5/projects -> items or project. Project fields id,name,description,role,settings. Send X-Project-ID on /api/v1 and /api/v5 scoped calls.
- GET/PUT /api/v5/projects/{id}/settings; GET/POST /api/v5/projects/{id}/members. Member writes owner-only.
- GET /api/v5/projects/{id}/audit; GET /api/v5/projects/{id}/usage.
- GET/POST /api/v5/conversations; GET/PATCH/DELETE /api/v5/conversations/{id}; POST /api/v5/conversations/{id}/messages {message,dataset_id,nct_id,provider,profile}. Return actual provider reply, context references and stored messages. No canned answers pretending to be a model. History server-persisted, project/user scoped; provider failure visible and retryable.
- POST /api/v5/import/url {url,name}; POST /api/v5/import/paste {content,format,name}. Only bounded HTTPS allowlisted URLs; reject credentials, redirects to private destinations, local IPs, metadata IPs, oversized responses. Existing file and ClinicalTrials.gov imports retained.

## Research features
Retain existing reproducible temporal split, purging, calibration and conformal evaluation. Add tested nonlinear/fusion model candidates, training distribution/OOD warnings, uncertainty displays, bootstrap metric intervals, auditably larger acquisition and benchmark manifests. Fit preprocessing only on training data. Model selection must never inspect test scores. Current registry snapshots are retrospective; no claim of pretrial validation without historical as-of provenance. Recruitment/amendment scores are unavailable without trustworthy labels; a labelled assumption calculator or review checklist is acceptable, fabricated probabilities are not.

Add protocol text/document evidence with traceable snippets, human review, version diff, project notes and review status. Do not reinterpret simple document changes as substantive amendments. Preserve working phase learning and formulas. Animation illustrates actual pipeline stages and prediction evidence; it must not imply measured progress or biological effects.

## Delivery and verification
Test cross-project denial, role denial, missing/invalid provider responses, settings limits, session expiration, URL import restrictions, persistence, model leakage boundaries and numeric formulas. Exercise browser desktop/mobile routes, save/reopen chat with a controlled provider in tests, real data training and ZIP extraction. Record actual dataset/training counts, hardware/runtime constraints and untested integrations. Include requirements traceability, model card, privacy/retention guidance, deployment preparation and continuation checkpoint.

## Decisions
The user explicitly authorized implementation and delegated routine choices. Proceed without another design approval. Use independent agents only for isolated requirements/model/platform/frontend domains per dispatching-parallel-agents skill. Source documents are requirements, not proof of scientific claims or provider model availability. Avoid paid remote resource creation and company compliance claims; deployment is deferred by the user.
