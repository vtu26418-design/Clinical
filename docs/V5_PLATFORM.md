# v5 platform implementation and operation

The published application is `backend.app.main:app`, which constructs the v5 platform. `create_research_app` is an internal research worker factory used behind the gateway and by scientific regression tests. Do not deploy that factory separately.

## Identity and project boundaries

`AUTH_MODE=session` is the default. Set `SETUP_TOKEN` to a private random value of at least 24 characters, then use the one-time first-owner setup form. The setup claim is transactional. There is no public administrator registration. Project owners add existing accounts or generate an invitation token, valid for 24 hours and redeemable once; the operator shares that token out of band. The application does not send invitation email.

Passwords use salted scrypt (N=16384, r=8, p=1). Random 256-bit session tokens are stored only as SHA-256 digests in metadata. The session cookie is HttpOnly, SameSite=Lax, and Secure in production. `SESSION_HOURS` defaults to 12 and is bounded to 1–168 hours. Logout revokes the server session; expired sessions cannot authorize research requests. Authentication attempts have a database-backed per-client limit. A reverse proxy must not obscure all clients behind a single rate-limit identity without configuring trusted forwarding deliberately.

Every project-scoped research request sends `X-Project-ID`. Membership is checked on the server before reaching `/api/v1`, including scenario history, exports, reports, model files, and predictions. The gateway rejects a project/header mismatch. Project IDs are generated on the server and validated before they form storage/schema paths. Cookies and project IDs are the authorization inputs; the legacy shared bearer token is not an alternate v5 credential.

| Role | Read studies/predict | Import data | Train | Saved AI reply | Settings/members | Audit |
|---|---|---|---|---|---|---|
| Owner | Yes | Yes | Yes | Yes | Yes | Yes |
| Researcher | Yes | Yes | No | Yes | No | No |
| Reviewer | Yes | No | No | No | No | Yes |
| Viewer | Yes | No | No | No | No | No |

Owners and researchers may create, rename, delete, and send messages in their own conversations. Reviewers and viewers retain read-only access to their existing history and cannot call an AI provider. Conversations are both project scoped and user scoped; another project owner cannot read a user's private conversation through these APIs. The legacy `/api/v1/assistant` endpoint returns 410 so it cannot bypass saved-chat quotas. Model promotion and protocol review permissions are supplied by their dedicated v5 modules.

Unsafe request origins are rejected for mutations; CORS allows only configured origins and supports credentialed development requests. API responses carry `Cache-Control: no-store`. Both declared and streamed request bodies are bounded before processing.

`AUTH_MODE=local` is an explicit development-only option, exposing one local workspace without identity security. It cannot start with `APP_ENV=production`; it must not be used as an internet-facing deployment mode.

## Metadata, datasets, and durability

A real `DATABASE_URL=postgresql+psycopg://…?sslmode=require` uses SQLAlchemy and psycopg. Production rejects missing PostgreSQL and missing TLS configuration. The platform creates `v5_*` metadata tables in its private `cti_platform` schema and revokes public schema access; each project research registry uses a separate generated PostgreSQL schema (`cti_<project_id>`). The database credential therefore needs schema/table creation privileges during initialization. Application authorization is enforced by the gateway; this is not a claim of PostgreSQL row-level security or independent database credentials per tenant.

With no database URL in development, `STORAGE_DIR/platform.sqlite3` is the labelled offline metadata fallback. Each project has a separate SQLite research registry beneath `STORAGE_DIR/projects/<project_id>`. Bootstrap reports the actual database kind; it never labels SQLite as PostgreSQL.

Raw files, canonical datasets, protocol source files, and fitted model artifacts remain private files under the configured persistent storage root. PostgreSQL alone does not make those files durable. Back up the database and storage volume together. Remote object storage, external key management, independently immutable audit storage, disaster-recovery exercises, and production deployment are operator work, not completed integrations in this build.

Run one server process (`workers=1`). Training is bounded to one job across projects in that process. Queued/running research jobs encountered after a server restart are marked failed; the operator can start a new run. This is not a durable distributed job queue.

## Saved contextual conversations

`GET/POST /api/v5/conversations`, `GET/PATCH/DELETE /api/v5/conversations/{id}`, and `POST /api/v5/conversations/{id}/messages` persist conversations and messages. A message request accepts `message`, `dataset_id`, optional `nct_id`, `provider`, and `profile`.

Grounding includes the selected project's dataset provenance, the selected study and PCI details when selected, retained conversation history, and bounded evidence from the protocol module when installed. Source references contain dataset/document identifiers and hashes. References show supplied context; they are not fabricated external citations, proof that every sentence is supported, or a clinical approval. Study/document text is treated as untrusted evidence in provider instructions.

| Profile | Retained history messages | Context character cap | Requested output-token cap |
|---|---:|---:|---:|
| fast | 6 | 9,000 | 400 |
| balanced | 16 | 18,000 | 700 |
| deep | 30 | 30,000 | 1,600 |

Profiles vary bounded context/output, not a scientifically measured model ranking. Provider selection uses the configured provider or explicit request; auto follows the configured priority and only eligible error-based fallback. These profiles do not secretly retrain models or override the operator's model configuration.

The existing OpenAI, Anthropic, Gemini, and compatible provider adapters perform real requests. Model identifiers are server configuration; key presence does not verify account access or model quality. Missing keys return 503, persist the user message as failed, and create no pretend assistant response. Provider errors are retryable through another message request; invalid/refusal responses are not silently converted into answers. Returned metadata includes the actual provider/model response, profile, attempted providers, and context references. Live provider billing/account access must be checked separately in the deployment environment.

Project settings expose `default_provider`, `default_profile`, `chat_daily_limit` (0–500), and `chat_retention_days` (1–3650). The default quota is 50 assistant requests per UTC day per project. Quota reservation is transactional; unavailable, unconfigured providers do not consume quota. Configured provider failures do consume a request. Automatic fallback can make several provider calls within one assistant request; the quota is not a currency or token-spend cap. A per-conversation lease prevents overlapping replies. Defaults cap conversations at 200 per user/project and messages at 200 per conversation.

Retention deletes idle conversations older than the configured period when that project accesses chat routes. This is lazy application retention, not an independent scheduled deletion service; backups have their own retention. Audit entries omit chat content and record action identifiers/provider metadata. They are application audit history, not externally immutable logs or regulated electronic signatures.

## Bounded import methods

File upload and ClinicalTrials.gov cohort import continue through the isolated v1 gateway. File upload accepts CSV, flat JSON record arrays, `.xlsx` Excel workbooks, and Parquet. Excel imports the first worksheet with unique nonempty column headers; formulas are never executed and only cached values are read. Legacy `.xls`, macros, encrypted workbooks, XML DTD/entities, and oversized expanded archives are not supported. XLSX processing requires openpyxl and defusedxml, bounds archive entries/uncompressed bytes, and limits columns, rows, and cells. Paste import accepts canonical CSV or a nonempty JSON array of flat study records; required fields remain `nct_id` and `title`. Paste content is limited to two million UTF-8 bytes or the configured upload maximum, whichever is smaller.

URL import permits exact HTTPS hosts from `IMPORT_ALLOWED_HOSTS` (defaults: `clinicaltrials.gov,raw.githubusercontent.com`). It rejects userinfo, nonstandard ports, IP literals, query strings, fragments, internal/private/metadata destinations, and redirects. DNS answers must all be public and the HTTPS connection is pinned to the validated IP while certificate verification retains the hostname. No second DNS lookup is used for the actual socket. The importer does not follow redirects, send credentials, honor environment proxy settings, or accept compressed HTTP responses. Time and streamed byte limits apply even when the source omits Content-Length. Accepted content is CSV or a flat JSON record array; use the dedicated registry importer for the nested ClinicalTrials.gov API schema.

## Verification and limits

`tests/test_v5_platform.py` exercises one-time setup, invalid tokens, session expiry/logout, persisted password/session hashing, origin rejection, streamed body limits, project isolation across research/export/scenario endpoints, user-private chats, role-denied imports and training, settings validation, failed-provider persistence, successful controlled-provider chat/reopen/history/metadata, finite quota behavior, pasted records, private DNS answers, redirects, response limits, and credentialed research CORS. Provider-adapter and legacy research tests remain separate regression coverage.

SQLite and controlled-provider behavior can be tested without external credentials. A real remote PostgreSQL connection, production reverse proxy/TLS, hosted persistent volume, and live paid AI response have not been established merely by these tests. The build does not claim HIPAA/GxP compliance, electronic signature validation, externally immutable audit, or clinical/regulatory validation. Additional deployment work includes a reviewed migration process, backup/restore, password recovery and account administration, independent audit retention, and measured operational load/security testing.
