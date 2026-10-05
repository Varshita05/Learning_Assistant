import hmac
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from learning_assistant.config import settings

_basic = HTTPBasic(auto_error=False, realm="Learning Assistant")


@dataclass(frozen=True)
class Principal:
    subject: str


def validate_auth_configuration() -> None:
    if settings.APP_ENV == "production" and not (
        settings.SINGLE_USER_USERNAME and settings.SINGLE_USER_PASSWORD
    ):
        raise RuntimeError(
            "Production requires SINGLE_USER_USERNAME and SINGLE_USER_PASSWORD"
        )


def authentication_required() -> bool:
    return not (
        settings.APP_ENV == "development"
        and not settings.SINGLE_USER_USERNAME
        and not settings.SINGLE_USER_PASSWORD
    )


def get_current_principal(
    credentials: HTTPBasicCredentials | None = Depends(_basic),
) -> Principal:
    principal = get_optional_principal(credentials)
    if principal is not None:
        return principal

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Username and password required",
        headers={"WWW-Authenticate": 'Basic realm="Learning Assistant"'},
    )


def get_optional_principal(
    credentials: HTTPBasicCredentials | None = Depends(_basic),
) -> Principal | None:
    configured_username = settings.SINGLE_USER_USERNAME
    configured_password = settings.SINGLE_USER_PASSWORD
    if (
        settings.APP_ENV == "development"
        and not configured_username
        and not configured_password
    ):
        return Principal("local-development")

    if not configured_username or not configured_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Single-user credentials are not configured",
        )
    if credentials is None:
        return None

    valid_username = hmac.compare_digest(
        credentials.username, configured_username
    )
    valid_password = hmac.compare_digest(
        credentials.password, configured_password
    )
    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": 'Basic realm="Learning Assistant"'},
        )
    return Principal("single-user")


def require_admin(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    return principal