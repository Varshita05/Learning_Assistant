import logfire
from langchain_groq import ChatGroq
from portkey_ai import Portkey

from learning_assistant.config import settings
from learning_assistant.gateway.configuration import parse_portkey_config


portkey_config = parse_portkey_config(settings.PORTKEY_CONFIG)
portkey_client = (
    Portkey(api_key=settings.PORTKEY_API_KEY, config=portkey_config)
    if settings.PORTKEY_API_KEY and portkey_config
    else None
)


def _complete_with_groq(prompt: str, max_tokens: int | None) -> str:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("Configure GROQ_API_KEY to generate responses")
    response = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL,
        temperature=0,
        max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
    ).invoke(prompt)
    return str(response.content or "").strip()


def complete(prompt: str, feature: str = "rag", max_tokens: int | None = None) -> str:
    if portkey_client is None:
        return _complete_with_groq(prompt, max_tokens)

    try:
        response = portkey_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
            temperature=0,
            metadata={
                "feature": feature,
                "_user": "learning-assistant",
            },
        )
    except Exception as exc:
        if "Invalid config passed" not in str(exc):
            raise
        logfire.warning("Portkey rejected its config; retrying through Groq directly.")
        return _complete_with_groq(prompt, max_tokens)

    cache_status = extract_cache_status(response)

    if cache_status != "MISS":
        logfire.info(f"Portkey cache {cache_status}")

    return (response.choices[0].message.content or "").strip()


def extract_cache_status(response) -> str:
    for attr in ("_raw_response", "_response", "_http_response"):
        raw = getattr(response, attr, None)

        if raw is not None:
            status = getattr(raw, "headers", {}).get(
                "x-portkey-cache-status", ""
            )

            if status:
                return str(status).upper()

    return "MISS"