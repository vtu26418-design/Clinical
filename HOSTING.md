# Hosting and live deployment

The complete app needs the React web build, the Node campus API, one private Python academic worker, MongoDB and persistent media. Deploying only the React folder to Vercel/Netlify does not run AMS synchronization, authentication, events or SMTP.

## Recommended zero-hosting-fee path

Use a **college-provided server or your own Windows computer running Docker Desktop**, MongoDB Atlas Free and a free Cloudflare Tunnel. The tunnel provides the public HTTPS edge without opening an incoming router port. A stable address needs a domain/DNS zone you or the college control; an existing college subdomain can avoid a new domain purchase. Hardware, electricity, Internet access and domain ownership are separate costs. Speed depends on the host and its uplink, and the host must remain powered on and awake.

This path fits the delivered application's single academic worker and persistent Docker media volume. No Oracle account or separate Ubuntu installation is required on Windows.

### 1. Start the app locally

Extract the full source ZIP. Open PowerShell in the `veltech-ams-mini` folder, start Docker Desktop in Linux-container mode and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1
npm run setup
```

Supply your Atlas Drivers URI and provision the first administrator when asked. Setup retains existing private keys and accounts. Check local health at `http://localhost:4100/api/campus/health`.

### 2. Create a Cloudflare Tunnel

In Cloudflare's dashboard, create a remotely managed Cloudflare Tunnel and choose Docker as its connector. Create a published application route/public hostname such as `campus.your-domain.edu` with service type **HTTP** and service URL **`campus:4100`**. The hostname should serve the app publicly; the app's own login protects private records.

Copy only the connector token into a file named **`.private/cloudflare-tunnel-token`**. Do not put it in GitHub, screenshots or terminal command history. The supplied Compose file reads it from a Docker secret file. The token is private; the hostname is public.

Copy `.env.tunnel.example` to `.env.tunnel` and edit it:

```dotenv
CAMPUS_PUBLIC_URL=https://campus.your-domain.edu
```

Use the exact origin, without a path. Add the SMTP settings from [EMAIL-SMTP.md](EMAIL-SMTP.md) to `.private/campus.env`. Keep Atlas and encryption values unchanged.

### 3. Start public HTTPS

```powershell
docker compose --env-file .env.tunnel -f compose.yaml -f compose.tunnel.yaml config --quiet
docker compose --env-file .env.tunnel -f compose.yaml -f compose.tunnel.yaml up -d --build
docker compose --env-file .env.tunnel -f compose.yaml -f compose.tunnel.yaml ps
```

`compose.tunnel.yaml` enables Secure cookies, the exact public browser origin, shared MongoDB rate limits and a fixed trusted tunnel address. The academic worker remains private and runs one process. Port 4100 remains bound to localhost, not a public host interface. Do not combine this stack with the development Mailpit override or the separate Nginx production stack.

The tunnel makes encrypted outbound connections; Cloudflare normally requires outbound TCP/UDP port 7844 for its connector. SMTP leaves from the Docker host itself, so the provider's SMTP port must also be allowed. If the fixed Docker subnet `172.30.241.0/24` conflicts with an existing network, choose an unused private subnet and change both the tunnel IP and campus `CAMPUS_TRUST_PROXY` together.

### 4. Verify before sharing with students

```powershell
Invoke-RestMethod https://campus.your-domain.edu/api/campus/health
docker compose --env-file .env.tunnel -f compose.yaml -f compose.tunnel.yaml exec -T campus node campus/scripts/mail-check.js --verify
docker compose --env-file .env.tunnel -f compose.yaml -f compose.tunnel.yaml exec -T campus node campus/scripts/mail-check.js --send-to=YOUR_OWN_REAL_EMAIL
```

The health result should say `status: ok` and `database: connected`. Confirm that `https://campus.your-domain.edu/api/v1/health` returns **404**, and that app sign-in, refresh, sign-out, one real authorized AMS sync, an event registration and a received email work on your deployed URL. Test both phone and desktop. A configuration check is not proof of live provider operation.

Keep `.private`, Atlas credentials, encryption keys and Docker media volumes across updates. Back up database and media. Copy updated source into the existing project folder without deleting `.private`, then rebuild the campus image; avoid restarting the academic worker when only mail/UI changes. `docker compose down -v` destroys volumes and is not an update command.

The existing `scripts/production-check.mjs` checks the **separate Nginx/TLS topology** in `compose.production.yaml`; it is not the validator for this tunnel overlay. Use the tunnel commands above. For a public server with its own reverse proxy/certificates, follow [deployment.md](deployment.md) instead.

## Managed free hosting comparison

| Option | Published free constraints | Fit for this full application |
| --- | --- | --- |
| College/own Docker host + Cloudflare Tunnel | No hosting-plan fee; existing hardware, Internet and stable DNS required; host must stay on | Recommended no-hosting-fee path for the delivered stateful topology. Real capacity depends on your host. |
| Render Free | Sleeps after 15 idle minutes; restart can take about a minute; ephemeral filesystem; ports 25/465/587 blocked | Not suitable for fast, persistent student deployment with Gmail SMTP. Brevo HTTPS avoids SMTP-port blocking, but does not solve media/session/sleep limitations. |
| Koyeb Free | One free instance, 512 MB RAM, 0.1 vCPU, restricted regions; provider describes it as non-production | Too constrained to promise fast campus-wide Node + Python service operation. |
| Google Cloud Run | Monthly usage-based free allowance, then billing; cold starts and external storage/network/build costs can apply | A future deployment option, not a drop-in host for the current local-media/process-session topology. Requires storage/session/background-job planning and a billing account. Not guaranteed permanently free. |
| Vercel/Cloudflare Pages static frontend | Fast CDN delivery within plan limits | Frontend only. The campus API, private worker and storage still need hosting; keep the app/API same-origin or deliberately configure secure cookies/proxying. |

There is no verified offer here for unlimited, always-fast, college-wide backend traffic at zero cost. Do not use uptime-ping workarounds to evade a provider's sleep rules. For predictable student access, use an adequately provisioned college server or budget for a persistent managed host.

## Database and media

Atlas Free currently provides **0.5 GB total data/index storage** and a published connection limit of 500. It is a useful demonstration tier, not massive free storage. Keep videos/photos out of MongoDB documents, monitor the quota, and retain the app's persistent media volume. Ephemeral server files are not durable storage. Moving to serverless hosting requires a compatible private media/object-storage design, not just an environment-variable change.

## What goes to GitHub

Push application source, lockfiles, Docker/Compose files, `scripts`, `shared`, `docs`, Android configuration examples and non-secret env examples. Exclude `.private`, `.env.tunnel`, real `.env` values, SMTP/Atlas/Cloudflare credentials, uploads, database dumps, signing keys, logs and `node_modules`. The supplied `.gitignore` covers these. See [GITHUB.md](GITHUB.md).

Official sources checked 21 October 2026: [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/), [Cloudflared release](https://github.com/cloudflare/cloudflared/releases/tag/2026.10.2), [Render Free](https://render.com/docs/free), [Koyeb instances](https://www.koyeb.com/docs/reference/instances), [Cloud Run pricing](https://cloud.google.com/run/pricing), [Atlas Free limits](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/). Provider plans can change.
