from __future__ import annotations

import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from starlette.requests import Request

from app import crud
from app.core.security import get_password_hash
from app.models import (
    EmailVerificationToken,
    OAuthIdentity,
    PasswordResetToken,
    User,
)
from app.services.github_oauth import GitHubOAuthService, InvalidOAuthState
from app.services.identity import (
    EmailVerificationService,
    IdentityConflict,
    InvalidVerificationToken,
    PasswordResetService,
    UnverifiedOAuthEmail,
)


class FakeStateStore:
    def __init__(self) -> None:
        self.values: dict[str, tuple[dict[str, str], int]] = {}
        self.consume_count = 0

    def put(self, key: str, value: dict[str, str], ttl_seconds: int) -> bool:
        if key in self.values:
            return False
        self.values[key] = (value, ttl_seconds)
        return True

    def consume(self, key: str) -> dict[str, str] | None:
        self.consume_count += 1
        stored = self.values.pop(key, None)
        return stored[0] if stored else None


def _new_user(
    session: Session,
    *,
    email: str | None = None,
    email_verified: bool = False,
) -> User:
    user = User(
        email=email or f"{secrets.token_hex(12)}@example.com",
        hashed_password=get_password_hash(secrets.token_urlsafe(32)),
        email_verified=email_verified,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def _request_with_query(query: str = "", *, cookie: str | None = None) -> Request:
    headers = []
    if cookie:
        headers.append((b"cookie", f"github_oauth_state={cookie}".encode()))
    return Request(
        {
            "type": "http",
            "scheme": "https",
            "server": ("api.example.test", 443),
            "path": "/api/v1/auth/github/callback",
            "query_string": query.encode(),
            "headers": headers,
        }
    )


def test_verification_token_is_hashed_and_single_use(session: Session) -> None:
    user = _new_user(session)
    service = EmailVerificationService(session=session, mailer=Mock())

    raw_token = service.issue_verification_token(user.id)
    stored = session.exec(select(EmailVerificationToken)).one()

    assert raw_token not in stored.token_hash
    assert stored.consumed_at is None
    assert service.verify(raw_token).email_verified is True
    session.refresh(stored)
    assert stored.consumed_at is not None

    with pytest.raises(InvalidVerificationToken):
        service.verify(raw_token)


def test_email_verification_request_renders_generated_template(
    monkeypatch: pytest.MonkeyPatch, session: Session
) -> None:
    from app.core.config import settings

    user = _new_user(session)
    monkeypatch.setattr(settings, "SMTP_HOST", "mailpit")
    monkeypatch.setattr(settings, "EMAILS_FROM_EMAIL", "noreply@example.com")
    mailer = Mock()

    EmailVerificationService(session=session, mailer=mailer).request(user.id)

    mailer.assert_called_once()
    html_content = mailer.call_args.kwargs["html_content"]
    assert "Verify your email address" in html_content
    assert "{{ link }}" not in html_content
    stored = session.exec(select(EmailVerificationToken)).one()
    assert len(stored.token_hash) == 64


def test_expired_verification_token_is_rejected(session: Session) -> None:
    user = _new_user(session)
    service = EmailVerificationService(session=session, mailer=Mock())
    raw_token = service.issue_verification_token(user.id)
    stored = session.exec(select(EmailVerificationToken)).one()
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.add(stored)
    session.commit()

    with pytest.raises(InvalidVerificationToken):
        service.verify(raw_token)

    session.refresh(user)
    assert user.email_verified is False


def test_github_link_requires_verified_email_and_never_merges_accounts(
    session: Session,
) -> None:
    owner = _new_user(
        session,
        email=f"{secrets.token_hex(12)}@example.com",
        email_verified=True,
    )
    other = _new_user(
        session,
        email=f"{secrets.token_hex(12)}@example.com",
        email_verified=True,
    )
    service = EmailVerificationService(session=session, mailer=Mock())
    provider_subject = secrets.token_urlsafe(24)

    linked = service.identity.link_github(
        owner.id,
        provider_subject,
        str(owner.email),
        email_verified=True,
    )
    assert linked.user_id == owner.id

    with pytest.raises(IdentityConflict):
        service.identity.link_github(
            other.id,
            provider_subject,
            str(other.email),
            email_verified=True,
        )

    with pytest.raises(UnverifiedOAuthEmail):
        service.identity.link_github(
            other.id,
            secrets.token_urlsafe(24),
            str(other.email),
            email_verified=False,
        )

    binding_owner = _new_user(session, email_verified=False)
    active_binding = service.identity.link_github(
        binding_owner.id,
        secrets.token_urlsafe(24),
        f"{secrets.token_hex(12)}@example.com",
        email_verified=True,
        allow_active_binding=True,
    )
    assert active_binding.user_id == binding_owner.id


def test_unknown_github_login_does_not_create_local_account(session: Session) -> None:
    service = EmailVerificationService(session=session, mailer=Mock())
    before_users = session.exec(select(User)).all()
    provider_subject = secrets.token_urlsafe(24)
    email = f"{secrets.token_hex(12)}@example.com"

    with pytest.raises(IdentityConflict):
        service.identity.resolve_github_login(
            provider_subject,
            email,
            email_verified=True,
        )

    assert session.exec(select(User)).all() == before_users
    assert session.exec(select(OAuthIdentity)).all() == []


def test_email_verification_rolls_back_token_when_user_update_fails(
    monkeypatch: pytest.MonkeyPatch, session: Session
) -> None:
    user = _new_user(session)
    service = EmailVerificationService(session=session, mailer=Mock())
    raw_token = service.issue_verification_token(user.id)
    original_commit = session.commit
    monkeypatch.setattr(session, "commit", Mock(side_effect=RuntimeError("commit failed")))

    with pytest.raises(RuntimeError, match="commit failed"):
        service.verify(raw_token)

    monkeypatch.setattr(session, "commit", original_commit)
    assert service.verify(raw_token).email_verified is True


def test_password_reset_consume_can_join_user_transaction(session: Session) -> None:
    service = EmailVerificationService(session=session, mailer=Mock())
    user = _new_user(session)
    raw_token = service.issue_password_reset_token(user.id)

    assert service.consume_password_reset_token(raw_token, commit=False) == user.id
    session.rollback()
    assert service.consume_password_reset_token(raw_token) == user.id


def test_legacy_password_reset_consume_can_join_user_transaction(
    session: Session,
) -> None:
    user = _new_user(session)
    service = PasswordResetService(session=session, mailer=Mock())
    raw_token = secrets.token_urlsafe(32)

    assert (
        service.consume_legacy_token(
            raw_token, str(user.email), commit=False
        )
        == user.id
    )
    session.rollback()
    assert (
        service.consume_legacy_token(raw_token, str(user.email), commit=True)
        == user.id
    )


def test_crud_email_lookup_is_case_insensitive(session: Session) -> None:
    email = f"{secrets.token_hex(12)}@Example.com"
    user = _new_user(session, email=email)

    assert crud.get_user_by_email(session=session, email=email.upper()) == user


def test_identity_rate_limiter_uses_atomic_redis_counter() -> None:
    from app.services.identity import RateLimitExceeded, RedisRateLimiter

    class FakeRedis:
        def __init__(self) -> None:
            self.calls: list[tuple[str, int, str, int]] = []
            self.result = 1

        def eval(
            self, script: str, numkeys: int, key: str, window_seconds: int
        ) -> int:
            self.calls.append((script, numkeys, key, window_seconds))
            return self.result

    fake_redis = FakeRedis()
    limiter = RedisRateLimiter(client=fake_redis)
    identifier = f"{secrets.token_hex(12)}@example.com"

    limiter.check(
        scope="password-reset",
        identifier=identifier,
        limit=2,
        window_seconds=60,
    )
    script, numkeys, key, window_seconds = fake_redis.calls[0]
    assert "INCR" in script
    assert "EXPIRE" in script
    assert numkeys == 1
    assert identifier not in key
    assert window_seconds == 60

    fake_redis.result = 3
    with pytest.raises(RateLimitExceeded):
        limiter.check(
            scope="password-reset",
            identifier=identifier,
            limit=2,
            window_seconds=60,
        )


def test_password_reset_token_is_stored_only_as_hash(session: Session) -> None:
    user = _new_user(session)
    service = EmailVerificationService(session=session, mailer=Mock())
    raw_token = service.issue_password_reset_token(user.id)
    stored = session.exec(select(PasswordResetToken)).one()

    assert raw_token not in stored.token_hash
    assert service.consume_password_reset_token(raw_token) == user.id
    session.refresh(stored)
    assert stored.consumed_at is not None
    with pytest.raises(InvalidVerificationToken):
        service.consume_password_reset_token(raw_token)


def test_github_start_uses_redis_ttl_scope_and_pkce(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", secrets.token_urlsafe(16))
    monkeypatch.setattr(settings, "GITHUB_CLIENT_SECRET", secrets.token_urlsafe(32))
    callback_uri = "https://api.example.test/api/v1/auth/github/callback"
    monkeypatch.setattr(settings, "GITHUB_OAUTH_CALLBACK_URL", callback_uri)
    state_store = FakeStateStore()
    service = GitHubOAuthService(state_store=state_store)

    response = service.start(_request_with_query())
    query = parse_qs(urlparse(response.headers["location"]).query)
    state = query["state"][0]
    challenge = query["code_challenge"][0]
    stored_payload, ttl = state_store.values[state]

    assert query["scope"] == ["read:user user:email"]
    assert query["code_challenge_method"] == ["S256"]
    assert ttl == 600
    assert stored_payload["code_verifier"]
    verifier = stored_payload["code_verifier"]
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    assert challenge == expected
    assert response.headers["set-cookie"].lower().count("httponly") == 1
    assert "secure" in response.headers["set-cookie"].lower()
    assert "samesite=lax" in response.headers["set-cookie"].lower()


def test_github_exchange_uses_exact_callback_uri_and_verifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", secrets.token_urlsafe(16))
    monkeypatch.setattr(settings, "GITHUB_CLIENT_SECRET", secrets.token_urlsafe(32))
    callback_uri = "https://api.example.test/api/v1/auth/github/callback"
    monkeypatch.setattr(settings, "GITHUB_OAUTH_CALLBACK_URL", callback_uri)
    captured: dict[str, object] = {}
    access_token = secrets.token_urlsafe(32)

    class FakeClient:
        def fetch_token(self, url: str, **kwargs: object) -> dict[str, str]:
            captured["url"] = url
            captured["kwargs"] = kwargs
            return {"access_token": access_token}

        def close(self) -> None:
            return None

    service = GitHubOAuthService(
        state_store=FakeStateStore(),
        http_client_factory=lambda: FakeClient(),
    )
    code_verifier = secrets.token_urlsafe(32)
    assert service.exchange_code(secrets.token_urlsafe(16), code_verifier) == access_token

    data = captured["kwargs"]
    assert data["redirect_uri"] == callback_uri
    assert data["code_verifier"] == code_verifier


def test_github_callback_consumes_state_once_and_does_not_persist_access_token(
    monkeypatch: pytest.MonkeyPatch,
    session: Session,
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", secrets.token_urlsafe(16))
    monkeypatch.setattr(settings, "GITHUB_CLIENT_SECRET", secrets.token_urlsafe(32))
    monkeypatch.setattr(
        settings,
        "GITHUB_OAUTH_CALLBACK_URL",
        "https://api.example.test/api/v1/auth/github/callback",
    )
    state_store = FakeStateStore()
    state = secrets.token_urlsafe(24)
    github_email = f"{secrets.token_hex(12)}@example.com"
    _new_user(session, email=github_email, email_verified=True)
    state_store.put(
        state,
        {
            "code_verifier": secrets.token_urlsafe(32),
            "intent": "login",
            "user_id": "",
        },
        600,
    )
    service = GitHubOAuthService(session=session, state_store=state_store)
    access_token = secrets.token_urlsafe(32)
    service.exchange_code = Mock(return_value=access_token)
    service.fetch_identity = Mock(
        return_value={
            "provider_subject": secrets.token_urlsafe(16),
            "email": github_email,
            "email_verified": True,
        }
    )

    request = _request_with_query(
        f"code={secrets.token_urlsafe(16)}&state={state}", cookie=state
    )
    response = service.callback(request)

    assert response.status_code in {302, 303, 307}
    assert state_store.consume_count == 1
    assert access_token not in json.dumps(response.headers, default=str)
    assert not hasattr(response, "oauth_access_token")

    with pytest.raises(InvalidOAuthState):
        service.callback(request)


def test_github_callback_requires_state_cookie(
    monkeypatch: pytest.MonkeyPatch, session: Session
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", secrets.token_urlsafe(16))
    monkeypatch.setattr(settings, "GITHUB_CLIENT_SECRET", secrets.token_urlsafe(32))
    monkeypatch.setattr(
        settings,
        "GITHUB_OAUTH_CALLBACK_URL",
        "https://api.example.test/api/v1/auth/github/callback",
    )
    state_store = FakeStateStore()
    state = secrets.token_urlsafe(24)
    state_store.put(
        state,
        {
            "code_verifier": secrets.token_urlsafe(32),
            "intent": "login",
            "user_id": "",
        },
        600,
    )
    service = GitHubOAuthService(session=session, state_store=state_store)

    with pytest.raises(InvalidOAuthState):
        service.callback(
            _request_with_query(f"code={secrets.token_urlsafe(16)}&state={state}")
        )
