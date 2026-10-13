# v4.0.1 · multiple assistant providers

Requested change: allow the available OpenAI, Gemini or Claude key, choose automatically among configured services, and deliver the full updated v4 ZIP. This supersedes the earlier OpenAI-only constraint for the assistant.

Added native Gemini/Claude adapters, an optional OpenAI-compatible Chat Completions adapter, editable priority, bounded sequential fallback, a request-local provider selector, actual reply attribution, secret-safe status/errors, updated setup template, and revised operating PDF. Default Auto order is OpenAI, Claude, Gemini, compatible; it is a preference and not a measured best-model benchmark. No other research feature or formula was changed.

Existing OpenAI-only .env files continue to work. Setup preserves your .env; append new settings from .env.example to configure additional services. Stop and back up your existing store, extract the update into a separate folder, install/start as usual and point STORAGE_DIR at your backed-up store if needed. No duration/phase retraining is required solely for this assistant patch. Never overwrite or share your private .env.

244 tests pass, one optional SHAP test is skipped. See VERIFICATION.md for evidence and limitations.
