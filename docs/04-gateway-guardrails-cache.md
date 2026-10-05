# Gateway, Guardrails, and Limits

## Current Behavior

- `gateway/client.py` uses Portkey only when both `PORTKEY_API_KEY` and a non-empty JSON-object `PORTKEY_CONFIG` are set. Otherwise it calls Groq directly with `GROQ_API_KEY`. If Portkey rejects the config with `Invalid config passed`, the request retries directly through Groq without logging the config value.
- The NeMo input guardrail currently creates a direct `ChatGroq` client, so not every model call passes through Portkey. The output guardrail is a local check.
- The query cache and rate limiter in `limits.py` are in-process. The cache uses a normalized-query hash and configured TTL; query cache keys include the caller-provided thread identifier. Rate limiting allows 20 requests per minute per thread by default.
- Query guardrails execute before the cache lookup, so cache hits still incur input-guardrail work.
- Production routes accept one configured HTTP Basic account. Rate limits use a fixed single-user identity, and graph thread IDs cannot cross account boundaries.
- `/ingest` and `/graph` require valid credentials. Local development without credentials uses a local-development identity; never use that mode on a public deployment.
- Basic credentials are sent on API requests and held in browser memory only. Terminate HTTPS at the deployment edge; do not expose Basic auth over plain HTTP.

## Production Requirements

Before public deployment, configure the single account, trusted CORS origins, and HTTPS. Verify Portkey routing/retry settings, route guardrail model calls through the approved policy or document a tested exception, and replace or bound process-local state for the chosen worker topology. Never log credentials or full sensitive prompts.
