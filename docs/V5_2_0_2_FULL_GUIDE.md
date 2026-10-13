# Clinical Trial Intelligence Workbench v5.2.0.2

## 1. What to open first

The ZIP includes the built React interface, FastAPI source, PostgreSQL configuration, tests, the frozen 800-record public registry cohort, verified saved models and this operating guide. PostgreSQL holds accounts, sessions, projects, memberships, chat, feedback and research metadata. Source files and model artifacts remain on persistent disk. There is no SQLite fallback.

Start in this order: prepare the environment; start PostgreSQL and the workbench; create an owner account; create/open a project; load the starter cohort; inspect Overview; use Prediction Studio. Training is an independent owner workflow and is not required for the bundled predictions.

The main navigation is Overview, Studies, Prediction Studio, Protocol Evidence, Scenarios, Models, Assistant and Settings. More tools contains Data Manager, Experiments, Validation Lab, the evidence animation pages, Phase Academy, Research sources, Saved library and Access Control.

## 2. Windows Docker startup

Install Docker Desktop and Python 3.12 with its Windows launcher. Start Docker Desktop and use its Linux-container engine. Complete any requested WSL2 setup first.

1. Download the complete Workbench ZIP. Right-click it, choose Extract All and use a short folder such as `C:\CTI`.
2. Open the extracted folder containing `docker-compose.yml`.
3. Double-click `START_DOCKER_WINDOWS.bat`. It generates a private `.env`, builds the application and starts PostgreSQL and the workbench.
4. Open `http://localhost:8000` when startup completes.
5. Open your local `.env` in a text editor and copy only the `SETUP_TOKEN` value into the first-owner form. Enter your name, email and a unique password of at least 12 characters.
6. Create a project and open it. After later logins, the separate Projects launcher lets you open, search or create a workspace.

Equivalent PowerShell commands from the project root:

```powershell
py -3.12 scripts/initialize_env.py
 docker compose up -d --build workbench
 docker compose ps
 docker compose logs --tail 50 workbench
```

The first download/build can take several minutes. Keep Docker Desktop running. Stop containers with `docker compose down`; retain their named volumes to keep your work. Deleting volumes deletes stored data.

## 3. Linux, macOS and native Python

For Docker, install Docker with Compose and Python 3.12, then run:

```bash
python3.12 scripts/initialize_env.py
 docker compose up -d --build workbench
 docker compose ps
```

Open `http://localhost:8000`, use the generated setup token and create the first owner. `start-docker.sh` combines environment preparation and startup. The application container runs as an unprivileged user.

For native backend development, install Python 3.12 and start PostgreSQL locally or through Compose. Node is unnecessary when using the ZIP's prebuilt interface.

Windows:

```powershell
py -3.12 scripts/setup.py --dev
 docker compose up -d postgres
.venv\Scripts\python.exe scripts/doctor.py
.venv\Scripts\python.exe scripts/start.py
```

Linux/macOS:

```bash
python3.12 scripts/setup.py --dev
 docker compose up -d postgres
.venv/bin/python scripts/doctor.py
.venv/bin/python scripts/start.py
```

To use an existing PostgreSQL service, configure `DATABASE_URL` before native startup. Setup preserves existing operator values. For frontend development install Node.js 22, run `npm ci` and `npm run dev` inside `frontend/`, and keep the backend on port 8000. Run `npm run build` there after editing the interface.

## 4. Environment values

Initialization copies `.env.example` into a private `.env` and generates local database credentials and a setup token. Credentials are not printed and are excluded from release ZIPs.

| Variable | Purpose |
| --- | --- |
| `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PASSWORD` | Local Docker database credentials; the password is generated. |
| `POSTGRES_PORT` | Native database port, normally 5432. |
| `DATABASE_URL` | Native application's PostgreSQL connection. |
| `COMPOSE_DATABASE_URL` | Container PostgreSQL connection, normally using hostname `postgres`. |
| `TEST_DATABASE_URL` | Disposable test database, normally port 5433 and database `cti_test`. |
| `SETUP_TOKEN` | Generated first-owner setup secret. |
| `APP_ENV`, `AUTH_MODE` | Development/production environment; use authenticated `session` mode. |
| `AI_PROVIDER`, `AI_PROVIDER_PRIORITY` | Assistant provider preference. |
| Provider key and model fields | Server-side credentials and an API model ID your account can access. |
| `AI_MAX_OUTPUT_TOKENS`, `AI_CONTEXT_CHARS` | Server response/context ceilings. |
| `TRUSTED_PROXY_HOSTS` | Explicit trusted proxy IPs/CIDRs; empty ignores forwarding headers. |
| `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_TRAINING`, `RATE_LIMIT_ASSISTANT` | Abuse-control request limits. |
| `STORAGE_DIR` | Persistent source/model file location. |
| `MAIL_API_KEY`, `MAIL_FROM`, `PUBLIC_BASE_URL` | Optional email-verification configuration. |

Native URL format:

```text
postgresql+psycopg://USER:URL_ENCODED_PASSWORD@HOST:PORT/DATABASE
```

Generated passwords are URL-safe. URL-encode manually supplied passwords. Remote production PostgreSQL requires `sslmode=require`, `verify-ca` or `verify-full`; use certificate verification when your provider supplies its CA configuration. Configure `COMPOSE_DATABASE_URL` separately when Docker should use that remote database.

AI configuration examples use field names, not credentials:

```text
OPENAI_API_KEY=
OPENAI_MODEL=
GEMINI_API_KEY=
GEMINI_MODEL=
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=
```

Fill at least one provider's actual key and usable API model ID locally, then restart the server. A coding application's model labels are not guaranteed API identifiers. Keys stay on the server.

## 5. Projects, roles and invitations

A project keeps its datasets, evidence, models, scenarios, conversations and audit records separate. Use Projects in the header to return to the launcher. Choose a project according to its assigned role.

| Operation | Owner | Trial researcher | Clinical reviewer | Viewer |
| --- | --- | --- | --- | --- |
| Read data, graphs, predictions and exports | Yes | Yes | Yes | Yes |
| Import research data and protocol files | Yes | Yes | No | No |
| Run and save scenarios | Yes | Yes | No | No |
| Train, approve and activate models | Yes | No | No | No |
| Review protocol evidence | Yes | No | Yes | No |
| Use enabled assistant | Yes | Yes | Yes | No |
| Manage members/project settings | Yes | No | No | No |
| Inspect audit history | Yes | No | Yes | No |

The server enforces these capabilities. The interface reflects them. The last owner cannot be removed or demoted. Password change invalidates other sessions; Account settings can sign out all sessions.

To invite someone: Settings, Members, Invite member; enter email/name/role and save. Share the resulting invitation link privately. The member opens it and creates a password. Existing accounts can be added directly. The interface states when no invitation email was sent. Invitation links expire.

## 6. Import and review data

Open More tools, Data Manager and load the starter cohort. Its 800 public ClinicalTrials.gov records and original source hashes are preserved. The five software-test fixtures are a separate dataset and cannot support scientific prediction or training.

Canonical imports require `nct_id` and `title`. Useful model fields are `phase`, `study_type`, `enrollment`, `number_of_arms`, `primary_outcomes`, `secondary_outcomes`, `criteria_count`, `brief_summary` and `eligibility_criteria`. Existing CSV/JSON, Excel, Parquet and documented registry/import workflows remain available.

Review quality, missingness and source hashes before analysis. Invalid numeric/date fields and duplicate study IDs cause a validation error without a partial import. Preserve raw AACT files unchanged. Arbitrary uploaded model binaries are not trusted saved models.

Duration fitting requires completed studies with precise start/completion dates and established ACTUAL completion outcomes. Estimated, imprecise, inverted, missing or nonpositive outcomes are excluded. Strict pretrial inference additionally needs consumed-feature availability timestamps.

Recruitment graphs require actual supported screening, eligibility, enrollment, follow-up/completion or site fields. Planned enrollment does not establish screening, retention or dropout counts. Absent fields remain unknown.

## 7. Overview graphs and study comparison

Overview aggregates the entire dataset. Phase/status filters apply to graphs and the study table; text search narrows the table. Source & method explains that distinction.

Choose Customize graphs, select your plots and Apply. Selection and ordering persist on this device for each project/dataset. Use arrow controls or drag handles to reorder. Fullscreen enlarges a graph; CSV/JSON export includes source values and methodology.

| Graph | Meaning |
| --- | --- |
| Phase distribution | Counts across reported phase categories. |
| Status distribution | Counts across registry statuses. |
| Enrollment distribution | Reported enrollment in explicit bins, with missingness. |
| Protocol complexity | Fixed-reference PCI distribution and incomplete-input disclosure. |
| Enrollment vs complexity | Descriptive enrollment/PCI association. |
| Observed duration | Quartiles by phase from eligible ACTUAL exact-day outcomes. |
| Enrollment by phase | Reported enrollment totals and denominators. |
| PCI components | Weighted component summaries and missingness. |
| Observed trial dates | Registry dates with their original precision. |
| Missing data | Missing fractions/counts by field. |
| Start-year activity | Study counts by reported start year. |
| Model comparison | Saved held-out errors and complete metrics. |

Select two or three study rows and Compare studies for a field comparison. Unavailable source measurements remain unavailable. PCI can be calculated with its documented zero-burden missing-component policy; partial coverage is disclosed and is not an outcome probability.

## 8. Saved-model prediction

Open Prediction Studio, choose Duration or Phase consistency, choose an approved saved model, select an evidence mode and Predict now. Saved preprocessing/models run on up to 100 validated records. Prediction does not trigger training.

Select a returned study to inspect values, intervals, explanation, source/model hashes and provenance. The phase pathway and prediction journey appear after actual evidence returns. Previous prediction runs can be reopened. Export CSV/evidence JSON or print to PDF.

Retrospective mode supports historical screening with source limitations. Strict pretrial mode checks supplied feature timestamps against the prediction cutoff; missing or late timestamps block the record.

Prolonged-duration probability concerns the training-defined duration threshold, not clinical success or delay relative to an operational plan. Split-conformal intervals may be unbounded or unavailable. The phase classifier estimates a phase label, not advancement probability.

## 9. Seven visual explanations

1. AI Pipeline connects the selected protocol, features, saved model and returned result. Job states reflect queued/running/completed/failed records; progress percentages are not invented.
2. Trial Timeline preserves reported date precision. Overall model-estimated completion requires an available duration and exact start date. Individual stage durations are not estimated.
3. Explainability exposes actual trained branches. Local additive waterfalls reconcile the intercept, signed contributions, exact remaining feature contribution and raw output. Linear contributions, global importance and fusion weights keep their method labels. Approved CatBoost branches provide native TreeSHAP. Constant baselines have zero feature effects.
4. Recruitment uses actual supported source counts and clearly unknown stages. Observed enrollment is separate from planned targets.
5. What-If Lab compares genuine saved-model predictions, keeping assumption-based planning separate.
6. Data Fusion shows actual structured/text encoders and available combination weights. Select a fitted branch; a constant baseline applies no feature encoders.
7. Research home's pointer-responsive helix is decorative and produces no biological prediction.

Pause and reduced-motion controls apply. Phase buttons explain educational categories; highlighted reported/model phase values come from the selected record and actual classifier. One study does not traverse all four phases.

## 10. Scenarios and planning

Open What-If Lab from More tools and choose a study and available model branch. Blank overrides preserve source fields. Changed fields apply only to the hypothetical copy; the original dataset remains unchanged.

Supply all planning assumptions: sites, participants per site per month, startup months and follow-up months. Name and run the scenario. Compare base/model results, changed/model results, PCI differences and explicit planning totals. A constant baseline can legitimately produce no prediction change.

```text
Recruitment months = enrollment / (sites × monthly recruitment rate per site)
Planning total = startup + recruitment + follow-up months
```

This is arithmetic using your assumptions, not a trained recruitment-risk forecast. Protocol perturbations are not causal evidence. The Scenarios workspace retains saved comparisons and provenance. Network errors never trigger a substitute prediction.

## 11. Train, compare, approve and activate

Owners can open More tools, Experiments, review readiness, select Include CatBoost and Run experiment. Actual run states and completed manifests/held-out predictions are retained. Researchers/reviewers/viewers cannot train or activate.

The nine existing branches are median/prevalence baseline, structured/text/multimodal linear models, Extra Trees, Random Forest, Gradient Boosting, Histogram Boosting and weighted late fusion. Opt-in CatBoost adds a tenth candidate and native additive TreeSHAP.

Preprocessing fits training records only. Tuning, calibration and test splits retain distinct roles; date groups and outcome-availability purging protect direct split separation. Compare duration MAE/RMSE and classification Brier/AUROC/average precision. Undefined metrics remain unavailable.

The new frozen-cohort comparison used 800 inputs, 312 eligible precise ACTUAL outcomes, 123 temporal exclusions and retained splits of 105 training, 9 tuning, 11 calibration and 64 test records. The median baseline remains the duration validation winner. CatBoost is a candidate capability, not an activated accuracy claim. Detailed evaluation evidence is included in `docs/v5202-evidence/`.

After completion, open Models. Inspect source, metrics, hashes, eligibility and limitations. Owner approval is required before activation. Training alone does not replace the active model. Branch selectors list branches present in the approved artifact; CatBoost appears after a compatible candidate is approved/activated. Do not repeatedly tune on the test set.

## 12. Protocols, sources and formulas

Protocol Evidence imports supported PDF/text, extracts text and links fields to page/section evidence. Inspect excerpts before using extracted values. Owners/clinical reviewers can review or correct evidence; researchers can import documents. Scanned PDFs without extractable text need a supported separate text/OCR workflow.

Version comparison identifies added/removed text. Amendment-risk prediction is unavailable without suitable labels and validation. The advanced reviewed rubric is a separate user-defined calculation.

Research sources integrates ClinicalTrials.gov, PubMed and openFDA. Save useful results to the project evidence library. Live services need internet and can report availability errors. Complexity Lab and Formula Studio explain fixed PCI weights, ceilings, rounding and missing-data policy.

Phase Academy, Phase Model, Research Hub and Validation Lab retain their existing research/educational workflows and saved evaluation evidence.

## 13. Assistant configuration and feedback

Configure one usable provider key/model ID in the private server environment and restart. OpenAI, Gemini, Claude and compatible HTTPS services are supported. Use Settings, Assistant for provider/profile, enable switch and budgets. A daily quota of 0 means no daily application quota; request and provider limits still apply.

Open Assistant, choose a study or dataset context and send a question. Replies stream as readable Markdown, including lists/tables/code. Sources identify actually supplied references. Copy/export preserves answers. Errors do not create invented replies.

Context includes actual cohort quality, selected-study fields, saved predictions, active-model evaluation, protocol excerpts and relevant saved evidence. Verify answer claims against their sources. Commercial provider access needs your own usable credentials; automated provider and UI streaming checks use local test responders.

Useful/Needs review records feedback against a completed message owned by your account. An owner uses Settings, Feedback review to approve an evidence-backed correction. Approved guidance can inform later project prompts. Pending feedback is not an instruction and source measurements take precedence.

This is reviewed context improvement. Model weights change through evaluated training and owner approval; feedback does not prove increased accuracy or automatic retraining.

## 14. Settings and security

Appearance offers Light/Dark/System, reduced motion, chart labels and chart-grid preferences. Graph layouts persist per project/dataset on the current device. Texture stays on decorative/navigation surfaces; charts retain clear analytical backgrounds.

Project assistant settings include enablement, provider/profile, response/context ceilings, daily quota and retention. Members and audit use real server records. Account controls change passwords and sign out sessions. Reducing retention can remove old conversations. Refresh after a membership change.

PostgreSQL schemas isolate project metadata. Feedback IDs never become filenames. Request limiting covers research forwarding and uses configured trusted-proxy policy. Startup disables Uvicorn's automatic forwarding-header trust.

## 15. Automated and manual tests

Use a disposable PostgreSQL database. Compose's test profile runs separately on port 5433. Tests use temporary private schemas and remove them after the run.

```bash
docker compose --profile test up -d postgres-test
```

Windows:

```powershell
py -3.12 scripts/setup.py --dev
.venv\Scripts\python.exe scripts/run_tests.py
.venv\Scripts\python.exe scripts/run_smoke_test.py
.venv\Scripts\python.exe scripts/verify_v5_models.py
```

Linux/macOS:

```bash
python3.12 scripts/setup.py --dev
.venv/bin/python scripts/run_tests.py
.venv/bin/python scripts/run_smoke_test.py
.venv/bin/python scripts/verify_v5_models.py
```

Frontend:

```bash
cd frontend
npm ci
npm run build
node --test src/components/animations/evidence.test.mjs src/components/animations/components.test.mjs
```

The suite checks PostgreSQL, auth, roles, isolation, imports, inference, scenarios, actual explanations, cohort graphs, fitting, feedback, grounding and provider/stream error handling. An optional external SHAP-library test may skip if that dependency is absent; native CatBoost TreeSHAP has separate executed tests.

Manual acceptance: create/login/open a project; load data; select/filter/reorder/export charts; compare studies; predict and inspect phases; run a scenario; inspect explanations/fusion; import/review a protocol; verify each role; change appearance/account settings; test assistant feedback. Commercial provider/email/remote deployment checks need operator configuration.

## 16. CLI research and release builds

A standalone fitting example:

```bash
.venv/bin/python scripts/train_models.py --input data/starter/trials.csv --output results/my-comparison --config configs/research-catboost.json --metadata data/starter/metadata.json
```

On Windows use `.venv\Scripts\python.exe`. Output must be a new directory. The CLI exports hashes, manifests, exclusions, predictions and metrics; it does not create a project approval or activate a model. `configs/research.json` retains the original candidate set.

Optional BioBERT/survival methods require their separate dependencies and appropriate cohorts; they are not newly trained release models. Ongoing/censored outcomes require a separate survival analysis.

Rebuild a release:

```bash
npm --prefix frontend run build
.venv/bin/python scripts/package_release.py --version 5.2.0.2 --output ../Clinical-Trial-Intelligence-Workbench-v5.2.0.2.zip
```

The archive includes current built assets and portable paths/checksums. Secrets, runtime databases, dependency folders and nested release ZIPs are excluded.

## 17. Backup and deployment

Back up PostgreSQL and research-file volumes together. Database records do not contain all PDFs/CSVs/model binaries. Use your provider's backups or PostgreSQL `pg_dump`; keep your private environment secure.

Deployment requires HTTPS, authenticated session mode, production values, TLS PostgreSQL, persistent storage and explicitly trusted reverse proxies. The release validates a development/container workflow, not a certified production or clinical deployment.

For a previous SQLite development installation, export/import source datasets and retain hashes. This release does not automatically migrate SQLite or ship old runtime databases.

## 18. Troubleshooting and evidence limits

| Symptom | Check |
| --- | --- |
| Docker fails | Docker Desktop running, Linux engine, Compose available. |
| Port conflict | Change host port and relevant URL together. |
| Database failure | Database running; correct host/port/credentials/database/TLS. |
| Setup token rejected | Use local generated token; setup closes after an owner exists. |
| Invitation fails | Correct project/email and an unexpired invitation. |
| Prediction unavailable | Real compatible data and an approved intact artifact. |
| Pretrial blocked | Cutoff and consumed-feature availability timestamps. |
| Recruitment unknown | Actual supported source counts, not assumed retention rates. |
| No scenario model change | Constant model or unsupported input; select a fitted branch. |
| Assistant unavailable | Usable key/model ID, enabled assistant, permitted role. |
| Reply incomplete | Larger supported budget/profile or narrower question. |
| Request limited | Wait for the rate window; quota 0 does not disable abuse controls. |
| Old interface appears | Rebuild `frontend/dist` and restart/reload. |

The cohort is retrospective and becomes small after outcome/split filtering. Feature snapshots may include post-start updates; the nine-record tuning split does not support strong generalization claims. Clinical-success, treatment-effect, recruitment-risk and amendment-risk probabilities are not validated bundled tasks. Inspect source records, explicit assumptions and evaluation evidence before interpreting research outputs.


Local developer mode (`AUTH_MODE=local`) bypasses sign-in and therefore does not support attributed assistant feedback. Use the default `AUTH_MODE=session` for feedback, owner review and team access.
