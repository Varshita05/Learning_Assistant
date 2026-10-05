import pytest
from types import SimpleNamespace

from learning_assistant.gateway import client
from learning_assistant.gateway.configuration import parse_portkey_config


def test_empty_portkey_config_uses_account_default():
    assert parse_portkey_config("  ") is None


def test_json_portkey_config_is_parsed():
    assert parse_portkey_config('{"strategy":{"mode":"fallback"}}') == {
        "strategy": {"mode": "fallback"}
    }


def test_invalid_portkey_config_is_ignored_for_direct_provider_fallback():
    assert parse_portkey_config("{'strategy': 'fallback'}") is None


def test_non_object_json_portkey_config_is_ignored():
    assert parse_portkey_config('["not", "an", "object"]') is None


def test_complete_uses_groq_when_portkey_is_unconfigured(monkeypatch):
    monkeypatch.setattr(client, "portkey_client", None)
    monkeypatch.setattr(
        client,
        "_complete_with_groq",
        lambda prompt, max_tokens: "direct response",
    )

    assert client.complete("question") == "direct response"


def test_invalid_portkey_response_retries_directly(monkeypatch):
    def reject_config(**kwargs):
        raise RuntimeError("Invalid config passed. You need to pass a valid json")

    monkeypatch.setattr(
        client,
        "portkey_client",
        SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=reject_config)
            )
        ),
    )
    monkeypatch.setattr(
        client,
        "_complete_with_groq",
        lambda prompt, max_tokens: "direct retry",
    )

    assert client.complete("question") == "direct retry"