from __future__ import annotations

import json
import secrets
from unittest.mock import Mock
from uuid import uuid4

import pytest
from redis.exceptions import RedisError
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.models import OAuthIdentity
from app.services.github_oauth import (
    GitHubOAuthService,
    InvalidOAuthState,
    OAuthConfigurationError,
    OAuthProviderError,
    RedisStateStore,
)
from app.services.identity import (
    EmailVerificationService,
    IdentityConflict,
    IdentityService,
    InvalidVerificationToken,
    PasswordResetService,
    RateLimitUnavailable,
    RedisRateLimiter,
    UnverifiedOAuthEmail,
    UserNotFound,
)
from tests.services.test_identity import _new_user, _request_with_query


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def test_identity_service_rejects_unsafe_bindings_and_reuses_existing_identity(
    session: Session,
) -> None:
    service = IdentityService(session)
    owner = _new_user(session, email_verified=True)
    other = _new_user(session, email_verified=True)

    with pytest.raises(UserNotFound):
        service.link_github(
            uuid4(), "missing-user", str(owner.email), email_verified=True
        )
    with pytest.raises(IdentityConflict):
        service.link_github(owner.id, "", str(owner.email), email_verified=True)
    with pytest.raises(UnverifiedOAuthEmail):
        service.link_github(owner.id, "invalid-email", "not-an-email", True)
    with pytest.raises(IdentityConflict):
        service.link_github(owner.id, "other-email", str(other.email), True)

    provider_subject = secrets.token_urlsafe(20)
    identity = service.link_github(
        owner.id, provider_subject, str(owner.email), email_verified=True
    )
    assert service.link_github(
        owner.id, provider_subject, str(owner.email), email_verified=True
    ) == identity

    unverified_owner = _new_user(session, email_verified=False)
    with pytest.raises(IdentityConflict):
        service.link_github(
            unverified_owner.id,
            secrets.token_urlsafe(20),
            f"{secrets.token_hex(8)}@example.com",
            email_verified=True,
        )


def test_resolve_github_login_handles_existing_or_unverified_accounts(
    session: Session,
) -> None:
    service = IdentityService(session)
    user = _new_user(session, email_verified=True)
    identity = service.link_github(
        user.id, "existing-subject", str(user.email), email_verified=True
    )

    resolved_user, resolved_identity = service.resolve_github_login(
        "existing-subject", str(user.email), email_verified=False
    )
    assert resolved_user.id == user.id
    assert resolved_identity.id == identity.id

    with pytest.raises(UnverifiedOAuthEmail):
        service.resolve_github_login(
            "new-subject", str(user.email), email_verified=False
        )

    unverified = _new_user(session, email_verified=False)
    with pytest.raises(IdentityConflict):
        service.resolve_github_login(
            "unverified-subject", str(unverified.email), email_verified=True
        )

    orphan = OAuthIdentity(
        user_id=uuid4(),
        provider="github",
        provider_subject="orphan-subject",
        email="orphan@example.com",
        email_verified=True,
    )
    session.add(orphan)
    session.commit()
    with pytest.raises(UserNotFound):
        service.resolve_github_login(
            "orphan-subject", "orphan@example.com", email_verified=True
        )


def test_identity_token_requests_fail_safely_for_missing_users_and_disabled_email(
    monkeypatch: pytest.MonkeyPatch, session: Session
) -> None:
    verification = EmailVerificationService(session=session)
    reset = PasswordResetService(session=session)

    with pytest.raises(UserNotFound):
        verification.issue_verification_token(uuid4())
    with pytest.raises(InvalidVerificationToken):
        verification.verify("")
    with pytest.raises(InvalidVerificationToken):
        reset.consume_token("")

    verification.request(uuid4())
    reset.request(uuid4())
    user = _new_user(session)
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    mailer = Mock()
    verification = EmailVerificationService(session=session, mailer=mailer)
    verification.request(user.id)
    reset = PasswordResetService(session=session, mailer=mailer)
    reset.request(user.id)
    mailer.assert_not_called()


def test_redis_rate_limiter_fails_closed_on_client_error() -> None:
    class BrokenRedis:
        def eval(self, *_args: object) -> int:
            raise RedisError("redis unavailable")

    with pytest.raises(RateLimitUnavailable):
        RedisRateLimiter(client=BrokenRedis()).check(
            scope="test", identifier="subject", limit=1, window_seconds=60
        )


def test_redis_state_store_handles_empty_invalid_and_provider_errors() -> None:
    class FakeRedis:
        def __init__(self) -> None:
            self.mode = "none"

        def set(self, *_args: object, **_kwargs: object) -> bool:
            if self.mode == "error":
                raise RedisError("redis unavailable")
            return False

        def eval(self, *_args: object) -> object:
            if self.mode == "error":
                raise RedisError("redis unavailable")
            if self.mode == "invalid":
                return "not-json"
            if self.mode == "list":
                return json.dumps(["not", "an", "object"])
            return None

    store = RedisStateStore.__new__(RedisStateStore)
    store.client = FakeRedis()
    assert store.put("state", {"intent": "login"}, 600) is False
    assert store.consume("state") is None
    store.client.mode = "invalid"
    with pytest.raises(OAuthProviderError):
        store.consume("state")
    store.client.mode = "list"
    assert store.consume("state") is None
    store.client.mode = "error"
    with pytest.raises(OAuthProviderError):
        store.put("state", {}, 600)
    with pytest.raises(OAuthProviderError):
        store.consume("state")


def test_github_oauth_configuration_and_client_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubOAuthService(state_store=type("Store", (), {"put": lambda *_args: True})())
    with pytest.raises(OAuthConfigurationError):
        service.start(_request_with_query(), intent="invalid")

    monkeypatch.setattr(settings, "GITHUB_OAUTH_CALLBACK_URL", None)
    with pytest.raises(OAuthConfigurationError):
        service.start(_request_with_query())

    monkeypatch.setattr(
        settings,
        "GITHUB_OAUTH_CALLBACK_URL",
        "https://api.example.test/api/v1/auth/github/callback",
    )

    class FailingClient:
        def create_authorization_url(self, *_args: object, **_kwargs: object) -> None:
            raise RuntimeError("provider failed")

        def fetch_token(self, *_args: object, **_kwargs: object) -> dict[str, str]:
            return {}

        def close(self) -> None:
            return None

    service = GitHubOAuthService(
        state_store=type(
            "Store", (), {"put": lambda *_args: True}
        )(),
        http_client_factory=lambda: FailingClient(),
    )
    with pytest.raises(OAuthProviderError):
        service.start(_request_with_query())
    with pytest.raises(OAuthProviderError):
        service.exchange_code("code", "verifier")


def test_github_fetch_identity_requires_verified_primary_email() -> None:
    class Response:
        def __init__(self, status_code: int, payload: object) -> None:
            self.status_code = status_code
            self.payload = payload

        def json(self) -> object:
            return self.payload

    class Client:
        def __init__(self, responses: list[Response]) -> None:
            self.responses = responses

        def get(self, *_args: object, **_kwargs: object) -> Response:
            return self.responses.pop(0)

        def close(self) -> None:
            return None

    success = GitHubOAuthService(
        http_client_factory=lambda: Client(
            [
                Response(200, {"id": 123}),
                Response(200, [{"email": "user@example.com", "verified": True, "primary": True}]),
            ]
        )
    )
    assert success.fetch_identity("oauth-token")["provider_subject"] == "123"

    for responses, error in (
        ([Response(500, {}), Response(200, [])], OAuthProviderError),
        ([Response(200, []), Response(200, [])], OAuthProviderError),
        ([Response(200, {"id": 1}), Response(200, [{"email": "user@example.com", "verified": False, "primary": True}])], UnverifiedOAuthEmail),
    ):
        service = GitHubOAuthService(
            http_client_factory=lambda responses=responses: Client(list(responses))
        )
        with pytest.raises(error):
            service.fetch_identity("oauth-token")


def test_github_callback_rejects_invalid_state_payloads(
    monkeypatch: pytest.MonkeyPatch, session: Session
) -> None:
    monkeypatch.setattr(
        settings,
        "GITHUB_OAUTH_CALLBACK_URL",
        "https://api.example.test/api/v1/auth/github/callback",
    )

    class Store:
        def __init__(self, payload: dict[str, str] | None) -> None:
            self.payload = payload

        def consume(self, _key: str) -> dict[str, str] | None:
            return self.payload

    for payload in (None, {}, {"intent": "invalid", "code_verifier": "verifier"}):
        service = GitHubOAuthService(session=session, state_store=Store(payload))
        request = _request_with_query("code=code&state=state", cookie="state")
        with pytest.raises(InvalidOAuthState):
            service.callback(request)

    service = GitHubOAuthService(
        state_store=Store({"intent": "login", "code_verifier": "verifier"})
    )
    with pytest.raises(OAuthConfigurationError):
        service.callback(
            _request_with_query("code=code&state=state", cookie="state")
        )

    service = GitHubOAuthService(state_store=Store({"code_verifier": "verifier"}))
    request = _request_with_query("error=access_denied&state=state&code=code", cookie="state")
    with pytest.raises(InvalidOAuthState):
        service.callback(request)
