# AI providers · v4.0.1

The assistant supports **OpenAI**, **Google Gemini**, **Anthropic Claude**, and an optional service implementing the **OpenAI Chat Completions** protocol. A key must be entered under its matching provider; arbitrary services do not all share the same API. Clinical models, formulas, data, and animations still run without a provider key.

## Add whichever key you have

1. Run setup, then open the project root `.env` locally in a text editor. If upgrading, append the new settings from `.env.example`; setup deliberately preserves your existing file.
2. Keep `AI_PROVIDER=auto`. Fill one or more matching key fields and leave unused fields empty.
3. Save `.env`, stop the backend with Ctrl+C, restart START_WINDOWS.bat (or `bash start.sh`), and refresh the app.
4. Open AI Assistant. Choose Server default or Auto. Send a question using public registry context.
5. Read the actual provider and model shown above the response. Configuration status alone does not verify credentials, model access, account quota or billing.

```dotenv
AI_PROVIDER=auto
AI_PROVIDER_PRIORITY=openai,anthropic,gemini,compatible
AI_AUTO_FALLBACK=true
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6
COMPATIBLE_API_KEY=
COMPATIBLE_BASE_URL=
COMPATIBLE_MODEL=
```

| Your key | Field to fill | Create/manage your own key |
|---|---|---|
| OpenAI | OPENAI_API_KEY | https://platform.openai.com/api-keys |
| Google Gemini | GEMINI_API_KEY | https://aistudio.google.com/api-keys |
| Anthropic Claude | ANTHROPIC_API_KEY | https://platform.claude.com/ |
| Another compatible provider | COMPATIBLE_API_KEY, COMPATIBLE_BASE_URL, COMPATIBLE_MODEL | That provider's own developer console |

Only one configured key: Auto selects it. Multiple configured keys: Auto takes the first available configuration in the declared order. A provider with a blank model is skipped; the compatible provider also needs its base URL. Omitted provider IDs are appended in the default order, so a sole configured provider is still usable. Each provider is attempted at most once per question. No provider is called during health checks or key discovery.

## What “best available” means

No universal best model can be inferred from an API key. This release uses an explicit, editable preference order, not fabricated quality scores or a benchmark performed on your data. The default order preserves OpenAI preference from the previous release, then Claude, Gemini and the custom compatible service. Model defaults are configurable starting points, not claims to be the newest or most accurate models.

To prefer Gemini: `AI_PROVIDER_PRIORITY=gemini,anthropic,openai,compatible`. To pin Claude globally: `AI_PROVIDER=anthropic` (the server also accepts `claude` as an alias). Use the screen's provider dropdown for a single-session override. An explicitly selected provider never silently switches to another. Set `AI_AUTO_FALLBACK=false` to keep Auto on its first configured choice.

## Automatic fallback

In Auto mode with fallback enabled, authentication/access/model-availability failures (HTTP 401/403/404), timeout (408), quota/rate limiting (429), service errors (5xx), and network/timeout failures can advance to the next configured provider. The same bounded question/context may therefore reach more than one provider and incur multiple charges. The response identifies the provider that answered and whether fallback occurred. Failed providers are tried again on the next question; there is no hidden persistent routing history.

A refusal/safety block, empty response, malformed response or ordinary bad-request response does not trigger automatic rerouting. No parallel model fan-out, answer scoring, external web search or hidden model benchmark runs. Failed provider bodies, headers, credentials and prompts are not returned as error details.

## Other OpenAI-compatible services

Set all three COMPATIBLE settings using that service's own documentation. `COMPATIBLE_BASE_URL` is the exact HTTPS API root, often ending `/v1`, with no query, fragment, embedded username/password, or `/chat/completions` suffix. The adapter appends `/chat/completions`; it sends a Bearer key, model, system/user messages and `max_tokens=700`. The service must accept this contract and return `choices[0].message.content` as text. A key alone cannot establish compatibility with every vendor, Azure-specific API, AWS Bedrock, Google Vertex service account, or non-chat API.

Native provider keys are sent only to their fixed official endpoints. The custom endpoint receives only COMPATIBLE_API_KEY. Cross-provider key reuse is never automatic. Requests do not follow redirects; custom/native HTTP adapters do not implicitly use environment proxy settings. Corporate networks requiring a proxy need a reviewed transport change. API settings are server configuration, not frontend input.

## Request and privacy contract

All providers receive the same research instructions and at most 4,000 question characters plus 18,000 context characters. Earlier visible chat turns are not sent. No files or full cohorts are uploaded. OpenAI uses Responses with `store=False`, 700 output tokens; Claude Messages and compatible Chat Completions use 700; Gemini generateContent allows 2,048 including its reasoning/output budget. Provider-reported thought content is excluded from the visible reply. Transport timeouts are 20 seconds per operation, no SDK retries; browser assistant requests allow 120 seconds for sequential fallback. Very long requests can still time out.

OpenAI `store=False` is not a guarantee about every provider's retention. Review the terms of each configured service before sending nonpublic data. Keys must not appear in VITE variables, screenshots, exports, source control or chat. Browser Connection settings takes only the app's optional API_BEARER_TOKEN. Never put a provider key there.

## Test and troubleshoot

```bash
python -m pytest -q tests/test_assistant_providers.py tests/test_api.py
python scripts/doctor.py
```

These contract tests use mock transports, not live paid accounts. For your own optional live check, use public fixture context, supply exactly one real provider key and send a short question. Repeat only for providers you intend to use. To test fallback without deliberate failed billable requests, use the automated suite.

- Setup required: check matching key/model fields, select Auto, restart and refresh.
- Access/key error: verify provider account and model permission privately; a chatbot subscription is not an API key.
- Quota/rate limit: review the provider's account limits/billing or use another configured provider.
- 404: model retired, unavailable to your account, or incorrect custom API root; update the matching MODEL setting from that provider's docs.
- No text/declined: revise the question or verify model/output support; the app does not route around refusals.
- Unknown settings: use the exact names from `.env.example`. The doctor never verifies a paid account and does not print credentials.

Official API contracts consulted 8 October 2026:
- https://developers.openai.com/api/reference/python/resources/responses/methods/create
- https://ai.google.dev/api/generate-content
- https://ai.google.dev/api
- https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash
- https://platform.claude.com/docs/en/api/messages/create
- https://platform.claude.com/docs/en/api/overview
- https://platform.claude.com/docs/en/about-claude/model-deprecations
