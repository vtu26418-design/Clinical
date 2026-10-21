# Deployment and upgrades

For a college/own Windows Docker host with a free Cloudflare HTTPS tunnel, use [HOSTING.md](HOSTING.md). This document below describes the separate Nginx/TLS topology. Configure real email using [EMAIL-SMTP.md](EMAIL-SMTP.md).

V1.8 includes an optional HTTPS deployment for **multiple campus containers on one Docker host**, one private academic worker, shared MongoDB and a shared media volume. This is a configuration and functional-test package, not a measured student-capacity guarantee. Choose capacity from measurements using authorized test accounts. AMS login, camera access, actual email delivery and production load require your own validation.

There is no unlimited free database or hosting service here. Atlas remains supported. The optional MongoDB Community configuration has no database license charge for this self-hosted use, but your server, finite disk, backups, network, monitoring and administration still cost resources. Review MongoDB's SSPL terms for your use, particularly if offering database services to others. See [storage.md](storage.md).

## Keep the Windows / Atlas workflow

`Setup.ps1`, `Start.ps1`, `Stop.ps1`, Docker Desktop and the localhost `compose.yaml` still work as before. `Setup.ps1` accepts an Atlas SRV URI, generates persistent private keys and starts a localhost HTTP deployment. Keep Atlas TLS and certificate verification enabled; allow only your deployment's egress IPs in Atlas network access. Keep both database names unchanged when upgrading: `unieve_campus_v1` and `unieve_campus_attendance_v1`.

Do not expose the localhost HTTP service by changing its bind address. Use the standalone production file below for hosted HTTPS. Do not combine `compose.yaml` with `compose.production.yaml`: merging would preserve the development published app port. After moving to production, use the production Compose commands for that stack; the existing PowerShell start/stop scripts manage the development stack.

## Prepare hosted HTTPS

Install current Docker Engine with Compose v2 (Docker Desktop for Windows). Use an operator account with access to the Docker host. Put private files on encrypted storage with access restricted to the operator and required runtime accounts. Linux private directories should have mode `700` and env files `600`; on Windows use NTFS ACLs and protect the Docker Desktop disk as well. A Docker administrator can read container environment values, so limit Docker access.

1. Preserve your existing `.private/campus.env` and `.private/academic.env`, including their keys. Set `CAMPUS_ORIGINS` to your exact HTTPS origin, for example `https://campus.your-college.edu`, and `CAMPUS_COOKIE_SECURE=true` in `campus.env`. Keep `ACADEMIC_API_URL=http://academic:8000/api/v1`, `CAMPUS_HOST=0.0.0.0` and `CAMPUS_MEDIA_DIR=/app/media`. Atlas URIs stay in the private files. Campus and academic services must use their respective original database names.
2. Configure an actual sender (`CAMPUS_MAIL_FROM`) and either SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_REQUIRE_TLS=true`, or implicit TLS on 465) or `BREVO_API_KEY`. Recovery-email verification requires deliverable mail. Mailpit is for local tests only. Do not disable mail certificate verification.
3. Copy `.env.production.example` to `.env.production`. Set `CAMPUS_SERVER_NAME` to the DNS hostname alone and `CAMPUS_TLS_DIR` to the absolute directory on the Docker host containing your own valid `fullchain.pem` and `privkey.pem`. On Docker Desktop use a shared drive and a forward-slash path such as `C:/campus/tls`. Obtain and renew your certificate through your chosen certificate authority; this package does not issue certificates. Only TCP 80/443 should be publicly reachable. Keep SSH or remote administration restricted separately.
4. Check for Docker subnet conflicts. The example proxy has `172.29.240.2` on `172.29.240.0/24`; only `172.29.240.2/32` is trusted by Express. If you change that network, change the proxy address and `CAMPUS_TRUST_PROXY` together in the production file. Never trust every proxy or accept user-controlled forwarded headers. This example assumes Nginx directly receives the client's connection; putting another load balancer/CDN before it requires an explicit trusted-client-IP configuration and retesting.
5. Run the configuration check, then start the stack. These commands work in PowerShell and Bash from the project directory:

```sh
node scripts/production-check.mjs
docker compose --env-file .env.production -f compose.production.yaml config --quiet
docker compose --env-file .env.production -f compose.production.yaml up -d --build --scale campus=3
docker compose --env-file .env.production -f compose.production.yaml ps
node scripts/production-check.mjs --url=https://campus.your-college.edu
```

The first check is expected to fail until you have configured real TLS, origins, mail and secrets. It resolves Compose in memory and reports checks without printing environment values. Avoid sharing `docker compose config` output without `--quiet`: it includes resolved secrets. With `--url`, the checker verifies the public campus/database health response and checks that the academic health route returns 404. It does not send mail or validate AMS credentials. An optional `--storage-path=/your/data/filesystem` checks at least 1 GiB of available space on that filesystem; that is only a low-space threshold, not a capacity estimate. Run capacity checks on the actual Docker data/media filesystem. Docker Desktop's VM disk may differ from the filesystem visible to Node on Windows.

Provision staff/admin accounts using your existing private provisioning procedure; no administrator password is distributed in the source. A fresh self-hosted setup is described in [storage.md](storage.md). Make one end-to-end test for login, rolling session renewal, explicit logout/revocation, password recovery, owned upload access and a supported AMS sync before allowing real students. Never publish the private academic API or MongoDB ports.

## What is shared, and what is bounded

Nginx 1.28 resolves Docker's campus service address list and balances campus requests. Campus containers use the same database, persistent encryption/bridge keys and `campus-media` volume. Campus login sessions and revocations live in MongoDB, so campus requests do not require sticky sessions. All replicas must run the same release. The production Compose file enables shared MongoDB request counters, including portal/login/identity/form write controls. A store failure stops guarded requests with 503 rather than falling back to an independent per-process allowance. Fixed windows can permit a burst across a window boundary. Counters use hashed client keys and expire through a TTL index. This adds database writes; measure that cost.

Authenticated API allowances are per student account, so students behind a campus NAT have separate API limits. Public unauthenticated allowances use the trusted proxy client IP. Login and portal attempt keys combine client IP and the bounded account identifier; their counters are hashed in MongoDB. Start conservatively and adjust `CAMPUS_API_RATE_LIMIT`, `CAMPUS_PORTAL_RATE_LIMIT`, `CAMPUS_LOGIN_RATE_LIMIT`, `CAMPUS_IDENTITY_RATE_LIMIT` and `CAMPUS_FORM_RATE_LIMIT` only after reviewing legitimate traffic and abuse. The defaults are 120/minute, 30/15 minutes, 15/15 minutes, 35/15 minutes and 30/user/minute, respectively. More replicas do not multiply these allowances. Health pings skip the general request counter and check the database directly.

Keep **one academic container with one Uvicorn worker**. Pending verification and retained AMS refresh sessions include an in-memory HTTP client. Retained sessions have a hard 30-minute lifetime, a 100-owner capacity and per-owner refresh lock; no passwords or CAPTCHA answers are retained. Restarting loses these upstream sessions; campus sessions and synced records remain in MongoDB. A student can request a fresh challenge. MongoDB persistence of academic records does not make that in-memory state distributed. Do not scale this service or increase its worker count until the portal session/challenge architecture supports routing and concurrency across workers. This remains a throughput and availability limit for large student sign-in bursts. Respect AMS availability and university permission; more campus replicas do not increase the upstream's capacity.

Local media and private form-proof files are protected by the campus API, not served as a public Nginx directory. A single named volume is shared only by containers on the **same Docker host**. This example is not a multi-host orchestrator or a highly available database. Several hosts need a separately implemented shared object-store adapter or a carefully secured shared filesystem mounted consistently, plus shared MongoDB and keys, private networking, academic-session routing, job coordination and tested failure handling. The shipped local-media adapter has no S3/Cloudinary deployment switch. Copying files asynchronously or setting the same volume name on two machines does not provide consistent shared storage. See [storage.md](storage.md) before changing topology.

## Back up, upgrade and verify

Back up both databases, both private env files and uploaded media/private proofs to encrypted storage outside the host. Recover the original `CAMPUS_LINK_KEY`, `CAMPUS_SERVICE_KEY`, `JWT_SECRET` and `PORTAL_CREDENTIAL_ENCRYPTION_KEY`; replacing them can make existing encrypted records unreadable. Keep the bridge key equal in both service files. Include MongoDB credentials for self-hosted deployments and protect backup access. Test a restore into an isolated stack before trusting backups.

Pin reviewed image digests for your deployment, record release/image versions, and keep an application rollback and database restore plan. The provided Nginx/MongoDB tags choose maintained release lines, not immutable artifacts. Inspect changes before pulling upgrades. Certificate renewal requires an Nginx reload (`docker compose --env-file .env.production -f compose.production.yaml exec proxy nginx -s reload`) after replacing the files. Restarting or rebuilding may briefly interrupt service; this example does not promise zero downtime. Never run `down --volumes` unless you intend to delete all stack data.

Monitor database connections/query latency, rate-limit failures, disk and backup age, certificate expiry, memory, API errors and the private academic service. Each campus replica creates its own database pool and may run scheduled work; current delivery records use database claims, but SMTP retry after an ambiguous network result can still duplicate mail. Load and failover tests must include these jobs and AMS sign-in bottlenecks. The supplied synthetic parser tests and shared-counter tests are not a production load test.

For event payments, complete merchant test-mode validation, webhooks, pending-order handling, reconciliation and refund procedures before collecting money. A browser message alone does not verify a payment.

## Building inside the managed Codex cloud environment

The deployment commands above are for your own machine. In a managed Codex session, check the intended local daemon with:

```sh
env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH docker --host=unix:///var/run/docker.sock info
```

Preserve the session proxy configuration and mount its CA as a BuildKit secret for networked npm/pip stages. The Dockerfiles accept `proxy_ca`; pass `--secret id=proxy_ca,src="$CODEX_PROXY_CERT"` to a direct `docker build`, or supply equivalent Compose build secrets in a session-only override. Keep TLS verification enabled and do not copy the session CA into image layers. Do not run a full Docker build when the environment lacks enough disk; local syntax checks and source tests do not establish that a new production image has built or started.


## Concurrent student access

Keep one private academic worker while AMS clients are process-local. Campus containers can scale on one Docker host using the supplied production proxy, shared Mongo sessions/rate limits and persistent shared media. Start with `--scale campus=3`, monitor your actual workload, then size the service from measurements. Do not expose the academic API or run unrelated per-replica copies of upstream sessions. A genuinely multi-host deployment also needs shared media/object storage and an owner-routed academic session design; the default package does not claim those capabilities.

Source login permits4 active and8 waiting attempts per academic process, with a5-second queue deadline. Record fetching uses3 shared slots. Busy503 responses include Retry-After3; the app preserves unused upstream challenges. Do not automatically hammer AMS or remove limits to hide congestion. Browser sessions remain separate from the short upstream lifetime. Source-provider slowdowns and CAPTCHA still affect sign-in.

The included synthetic checks exercised100 attempted source-login owners and36 record-sync owners without making live AMS calls. A local Docker workload also used24 fictional campus accounts,8 simultaneous student flows and144 HTTP requests. These are regression checks, not a guarantee for a specified production student count. Configure monitoring, backups, resource limits, Mongo capacity and operator alerts before inviting the college.

Use [GITHUB.md](GITHUB.md) for the repository file list and [ANDROID.md](ANDROID.md) for the later HTTPS address, signing certificate and domain-association setup. Windows Docker Desktop, real Atlas, Internet push/email, physical phones and production load must be verified on your deployment.
