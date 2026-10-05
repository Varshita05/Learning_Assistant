import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from learning_assistant import auth
from learning_assistant.config import settings


def test_development_uses_local_identity_without_credentials(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "SINGLE_USER_USERNAME", "")
    monkeypatch.setattr(settings, "SINGLE_USER_PASSWORD", "")

    assert auth.get_current_principal(None).subject == "local-development"


def test_configured_single_user_authenticates(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SINGLE_USER_USERNAME", "owner")
    monkeypatch.setattr(settings, "SINGLE_USER_PASSWORD", "correct horse battery")

    principal = auth.get_current_principal(
        HTTPBasicCredentials(username="owner", password="correct horse battery")
    )

    assert principal.subject == "single-user"


def test_missing_credentials_are_allowed_as_guest_for_optional_auth(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SINGLE_USER_USERNAME", "owner")
    monkeypatch.setattr(settings, "SINGLE_USER_PASSWORD", "secret")

    assert auth.get_optional_principal(None) is None


def test_invalid_optional_credentials_are_rejected(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SINGLE_USER_USERNAME", "owner")
    monkeypatch.setattr(settings, "SINGLE_USER_PASSWORD", "secret")

    with pytest.raises(HTTPException) as error:
        auth.get_optional_principal(
            HTTPBasicCredentials(username="owner", password="wrong")
        )

    assert error.value.status_code == 401


def test_wrong_single_user_password_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SINGLE_USER_USERNAME", "owner")
    monkeypatch.setattr(settings, "SINGLE_USER_PASSWORD", "correct horse battery")

    with pytest.raises(HTTPException) as error:
        auth.get_current_principal(
            HTTPBasicCredentials(username="owner", password="wrong")
        )

    assert error.value.status_code == 401


def test_required_auth_rejects_missing_credentials(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SINGLE_USER_USERNAME", "owner")
    monkeypatch.setattr(settings, "SINGLE_USER_PASSWORD", "secret")

    with pytest.raises(HTTPException) as error:
        auth.get_current_principal(None)

    assert error.value.status_code == 401


def test_production_requires_credentials(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SINGLE_USER_USERNAME", "")
    monkeypatch.setattr(settings, "SINGLE_USER_PASSWORD", "")

    with pytest.raises(RuntimeError, match="SINGLE_USER_USERNAME"):
        auth.validate_auth_configuration()