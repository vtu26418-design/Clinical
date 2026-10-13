# Plugin and deployment handoff

The following describes actual work in this build session. A plugin account is not automatically a runtime dependency of the project.

| Requested tool | Actual use and status |
|---|---|
| Build Web Apps | Frontend builder, React guidance and testing workflow used for the eight-screen React/Vite implementation |
| Superpowers | Planning, implementation/review and fresh verification; review defects fixed |
| OpenAI Developers | Dedicated connector was not available; official OpenAI API documentation was used and server-side Responses integration implemented |
| Context7 | FastAPI documentation resolved and queried for upload/lifecycle patterns |
| Figma | Created and populated an editable implementation handoff; visual screenshot inspected |
| MagicPath | Created a private architecture project and ten native canvas shapes |
| Vercel | Hosted the explicitly fixture-only static demo; deployment reached READY |
| GitHub | Connected identity checked; no accessible repository selected. Source and GitHub Actions CI included, no push claimed |
| Neon | Connection documentation consulted; optional PostgreSQL registry adapter included. No live database provisioned or tested |
| Notion | Created a private launch/research handoff draft; not shared or moved |
| tldraw | Workflow board created, but the live board view did not connect, so drawing could not be committed. Editable Mermaid source is included locally |

## Verified hosted preview

https://clinical-trial-intelligence-preview.vercel.app/

This runs the compiled React app with an explicitly labeled five-record fixture adapter. Search, comparisons, PCI scenarios, animated Phase Academy and its quiz are interactive. Uploads, registry import, model training and OpenAI require the full backend in the ZIP. No credentials or private datasets were deployed. The deployed single-file HTML has no API calls in demo mode.

Project ID: `prj_xqXGyFwbSzjFpNkR5y9ydLHFX3Np`. Release deployment: `dpl_2NuKzggG9jbU7V4eEFkBAaHUTipg`. The v3 update uses the production alias of the existing standalone **demo** project. This is not deployment of the full research backend or a real clinical service.

The local browser target was initially blocked by URL policy; no local-browser workaround was attempted. The separately hosted public fixture demo was then opened and checked with the supported browser tool.

## Design and operating references

These remote design/operating handoffs were created during v2; the ZIP documentation and live preview are the v3 source of truth.

- Figma: https://www.figma.com/design/bOyjdTtSvzsiQestTOaAoE — editable screen map and design tokens, not an imported browser screenshot.
- MagicPath private project ID: `458455087107428352` — architecture canvas.
- Notion private draft: https://app.notion.com/p/3f29f33d73ad819a9ae4dfa8a8add42b?pvs=204 — launch and research guide. It can be moved after you choose a destination.
- tldraw board: https://www.tldraw.com/f/ntpAspORHZODRjEPkszIE — currently empty because no open live board was available to the edit tool. tldraw's default board setting is link-editable; no trial data was added.
- `docs/design/implementation-handoff.svg` is included for offline use.
- `docs/design/research-workflow.mmd` contains the editable workflow source.

## Later GitHub/Vercel deployment

Create your own repository and push the source after reviewing `.gitignore`. Use `frontend` as the Vercel root directory, `npm run build` as build command and `dist` as output. Set `VITE_DEMO_MODE=true` for a fixture demo. For the real frontend, leave demo mode unset and configure `VITE_API_BASE_URL` with an HTTPS backend URL including `/api/v1`; add the frontend origin to backend CORS.

Do not host this version's in-process Python training and local file registry as ephemeral functions. Use a persistent host/container or implement the queue/object-store architecture first. API keys belong only in the backend environment.
