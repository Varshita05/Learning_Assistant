import logfire
from langchain_groq import ChatGroq
from nemoguardrails import RailsConfig, LLMRails
from nemoguardrails.rails.llm.options import RailStatus

from learning_assistant.config import settings
from learning_assistant.guardrails.colang_rules import COLANG_CONTENT, YAML_CONTENT

_rails: LLMRails | None = None


def _clean_response(text: str) -> str:
    if "<think>" in text and "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()


def initialize_rails() -> None:
    global _rails

    guard_llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL,
        temperature=0,
    )

    config = RailsConfig.from_content(
        colang_content=COLANG_CONTENT,
        yaml_content=YAML_CONTENT,
    )

    _rails = LLMRails(config, llm=guard_llm)

    logfire.info("NeMo Guardrails initialised.")


def guard(message: str) -> tuple[bool, str | None]:
    if _rails is None:
        logfire.warning("Guardrails not initialised — skipping gate.")
        return False, None

    with logfire.span("Guardrails Check"):
        result = _rails.check(
            messages=[{"role": "user", "content": message}]
        )

        print("\nRAW NEMO CHECK RESULT:")
        print(result)
        print("-" * 70)

        if result.status == RailStatus.BLOCKED:
            return True, _clean_response(result.content)

        return False, None


def guard_output(text: str) -> str:
    if not (text or "").strip():
        return "I could not produce an answer from the study materials."

    if "ignore all previous" in text.lower():
        return "I can only help with questions about your study materials."

    return text