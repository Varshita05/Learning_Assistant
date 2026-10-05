import pytest

from learning_assistant.retrieval_services import embeddings


@pytest.fixture(autouse=True)
def reset_embedder(monkeypatch):
    monkeypatch.setattr(embeddings, "active_model", None)
    monkeypatch.setattr(embeddings, "model_type", None)


def test_local_embedder_remains_primary(monkeypatch):
    local_model = object()
    monkeypatch.setattr(embeddings, "load_fallback", lambda: local_model)
    monkeypatch.setattr(embeddings, "probe_gemini", lambda: pytest.fail("Gemini should not be probed"))

    embeddings.init()

    assert embeddings.active_model is local_model
    assert embeddings.model_type == "fallback"


def test_gemini_is_selected_when_local_initialization_fails(monkeypatch):
    gemini_model = object()

    def fail_local():
        raise RuntimeError("local model unavailable")

    monkeypatch.setattr(embeddings, "load_fallback", fail_local)
    monkeypatch.setattr(embeddings, "probe_gemini", lambda: gemini_model)

    embeddings.init()

    assert embeddings.active_model is gemini_model
    assert embeddings.model_type == "gemini"


def test_startup_fails_when_no_embedder_is_available(monkeypatch):
    def fail_local():
        raise RuntimeError("local model unavailable")

    monkeypatch.setattr(embeddings, "load_fallback", fail_local)
    monkeypatch.setattr(embeddings, "probe_gemini", lambda: None)

    with pytest.raises(RuntimeError, match="providers are unavailable"):
        embeddings.init()