# OpenAI setup within the multi-provider assistant

v4.0.1 supports OpenAI, Gemini, Claude and an optional OpenAI-compatible service. See **AI_PROVIDERS.md** for the full setup, preference order, fallback and tests.

For OpenAI, set OPENAI_API_KEY in root .env. OPENAI_MODEL defaults to gpt-5.4-mini and can be changed to a compatible Responses model available to your account. AI_PROVIDER=auto uses configured providers in order; AI_PROVIDER=openai pins OpenAI. Restart after changes. Create a key at https://platform.openai.com/api-keys. No key is included.

The shared assistant_service.py uses the OpenAI Responses SDK with store=False, 20-second transport timeout, no SDK retries and a 700-token output cap. A bounded question/context is sent only on Send. Store=False is not a blanket retention guarantee. Key presence is not account verification. Previous chat turns are not sent.

The legacy openai_service.assist helper remains an OpenAI-only string-returning wrapper for source compatibility; the HTTP assistant route uses the multi-provider service and returns provider/model/fallback metadata.
