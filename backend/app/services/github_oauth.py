from __future__ import annotations

import hmac
import json
import secrets
from collections.abc import Callable
from datetime import timedelta
from typing import Any, Protocol
from uuid import UUID

from authlib.integrations.httpx_client import OAuth2Client
from fastapi import Request
from fastapi.responses import RedirectResponse
from redis import Redis
from redis.exceptions import RedisError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.services.identity import IdentityService, UnverifiedOAuthEmail


class OAuthError(Exception):
    """Base class for fail-closed OAuth errors."""


class OAuthConfigurationError(OAuthError):
    pass


class InvalidOAuthState(OAuthError):
    pass


class OAuthProviderError(OAuthError):
    pass


class StateStore(Protocol):
    def put(self, key: str, value: dict[str, str], ttl_seconds: int) -> bool: ...

    def consume(self, key: str) -> dict[str, str] | None: ...


class RedisStateStore:
    """Redis-backed OAuth state with an atomic, one-time consume operation."""

    _key_prefix = "yeyu:oauth:state:"
    _consume_script = (
        "local value = redis.call('GET', KEYS[1]); "
        "if value then redis.call('DEL', KEYS[1]); end; return value"
    )

    def __init__(self, redis_url: str | None = None) -> None:
        try:
            self.client: Redis[str] = Redis.from_url(
                redis_url or settings.REDIS_URL,
                socket_connect_timeout=settings.GITHUB_OAUTH_TIMEOUT_SECONDS,
                socket_timeout=settings.GITHUB_OAUTH_TIMEOUT_SECONDS,
                decode_responses=True,
            )
        except (RedisError, ValueError) as exc:
            raise OAuthConfigurationError from exc

    def put(self, key: str, value: dict[str, str], ttl_seconds: int) -> bool:
        try:
            result = self.client.set(
                f"{self._key_prefix}{key}",
                json.dumps(value, separators=(",", ":")),
                ex=ttl_seconds,
                nx=True,
            )
        except RedisError as exc:
            raise OAuthProviderError from exc
        return bool(result)

    def consume(self, key: str) -> dict[str, str] | None:
        try:
            raw_value = self.client.eval(
                self._consume_script,
                1,
                f"{self._key_prefix}{key}",
            )
        except RedisError as exc:
            raise OAuthProviderError from exc
        if raw_value is None:
            return None
        try:
            value = json.loads(str(raw_value))
        except (TypeError, ValueError) as exc:
            raise OAuthProviderError from exc
        return value if isinstance(value, dict) else None


class GitHubOAuthService:
    STATE_TTL_SECONDS = 600
    _scope = "read:user user:email"

    def __init__(
        self,
        *,
        session: Session | None = None,
        state_store: StateStore | None = None,
        http_client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.session = session
        self.state_store = state_store or RedisStateStore()
        self.http_client_factory = http_client_factory or self._default_client

    @staticmethod
    def _callback_uri() -> str:
        callback_uri = settings.GITHUB_OAUTH_CALLBACK_URL
        if not callback_uri:
            raise OAuthConfigurationError
        return callback_uri

    @staticmethod
    def _client_id() -> str:
        if not settings.GITHUB_CLIENT_ID:
            raise OAuthConfigurationError
        return settings.GITHUB_CLIENT_ID

    @staticmethod
    def _client_secret() -> str:
        if not settings.GITHUB_CLIENT_SECRET:
            raise OAuthConfigurationError
        return settings.GITHUB_CLIENT_SECRET

    @classmethod
    def _default_client(cls) -> OAuth2Client:
        return OAuth2Client(
            client_id=cls._client_id(),
            client_secret=cls._client_secret(),
            code_challenge_method="S256",
            timeout=settings.GITHUB_OAUTH_TIMEOUT_SECONDS,
        )

    def start(
        self,
        request: Request,
        *,
        intent: str = "login",
        user_id: UUID | None = None,
    ) -> RedirectResponse:
        del request
        if intent not in {"login", "link"} or (intent == "link" and user_id is None):
            raise OAuthConfigurationError
        callback_uri = self._callback_uri()
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(48)
        payload = {
            "code_verifier": code_verifier,
            "intent": intent,
            "user_id": str(user_id) if user_id else "",
        }
        if not self.state_store.put(state, payload, self.STATE_TTL_SECONDS):
            raise OAuthProviderError

        client = self.http_client_factory()
        try:
            authorization_url, _ = client.create_authorization_url(
                settings.GITHUB_OAUTH_AUTHORIZE_URL,
                state=state,
                redirect_uri=callback_uri,
                scope=self._scope,
                code_verifier=code_verifier,
                code_challenge_method="S256",
            )
        except Exception as exc:
            raise OAuthProviderError from exc
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()

        response = RedirectResponse(url=authorization_url, status_code=307)
        response.set_cookie(
            "github_oauth_state",
            state,
            max_age=self.STATE_TTL_SECONDS,
            httponly=True,
            secure=True,
            samesite="lax",
        )
        return response

    def exchange_code(self, code: str, code_verifier: str) -> str:
        client = self.http_client_factory()
        try:
            token = client.fetch_token(
                settings.GITHUB_OAUTH_TOKEN_URL,
                code=code,
                redirect_uri=self._callback_uri(),
                code_verifier=code_verifier,
            )
            access_token = token.get("access_token") if isinstance(token, dict) else None
        except Exception as exc:
            raise OAuthProviderError from exc
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()
        if not isinstance(access_token, str) or not access_token:
            raise OAuthProviderError
        return access_token

    def fetch_identity(self, access_token: str) -> dict[str, Any]:
        client = self.http_client_factory()
        try:
            headers = {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
            }
            user_response = client.get(
                f"{settings.GITHUB_API_BASE_URL}/user", headers=headers
            )
            email_response = client.get(
                f"{settings.GITHUB_API_BASE_URL}/user/emails", headers=headers
            )
            if user_response.status_code != 200 or email_response.status_code != 200:
                raise OAuthProviderError
            profile = user_response.json()
            emails = email_response.json()
        except OAuthProviderError:
            raise
        except Exception as exc:
            raise OAuthProviderError from exc
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()
        if not isinstance(profile, dict) or not isinstance(emails, list):
            raise OAuthProviderError
        provider_subject = profile.get("id")
        verified_email = next(
            (
                item
                for item in emails
                if isinstance(item, dict)
                and item.get("verified") is True
                and isinstance(item.get("email"), str)
                and item.get("primary") is True
            ),
            None,
        )
        if not isinstance(provider_subject, (int, str)) or not verified_email:
            raise UnverifiedOAuthEmail
        return {
            "provider_subject": str(provider_subject),
            "email": verified_email["email"],
            "email_verified": True,
        }

    def callback(self, request: Request) -> RedirectResponse:
        state = request.query_params.get("state")
        code = request.query_params.get("code")
        if not state or not code or request.query_params.get("error"):
            raise InvalidOAuthState
        cookie_state = request.cookies.get("github_oauth_state")
        if not cookie_state or not hmac.compare_digest(cookie_state, state):
            raise InvalidOAuthState
        state_payload = self.state_store.consume(state)
        if not state_payload or not state_payload.get("code_verifier"):
            raise InvalidOAuthState
        if self.session is None:
            raise OAuthConfigurationError
        intent = state_payload.get("intent")
        if intent not in {"login", "link"}:
            raise InvalidOAuthState

        access_token = self.exchange_code(code, state_payload["code_verifier"])
        try:
            github_identity = self.fetch_identity(access_token)
            identity_service = IdentityService(self.session)
            if intent == "link":
                try:
                    user_id = UUID(state_payload.get("user_id", ""))
                except ValueError as exc:
                    raise InvalidOAuthState from exc
                identity_service.link_github(
                    user_id,
                    github_identity["provider_subject"],
                    github_identity["email"],
                    github_identity["email_verified"],
                    allow_active_binding=True,
                )
                user = self.session.get(User, user_id)
                if user is None:
                    raise OAuthProviderError
            else:
                user, _ = identity_service.resolve_github_login(
                    github_identity["provider_subject"],
                    github_identity["email"],
                    github_identity["email_verified"],
                )
        finally:
            # The provider token is request-scoped and is never persisted.
            access_token = ""

        response = RedirectResponse(
            url=f"{settings.FRONTEND_HOST.rstrip('/')}/login?oauth=github",
            status_code=303,
        )
        response.delete_cookie("github_oauth_state")
        if intent != "link":
            session_token = security.create_access_token(
                user.id,
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            )
            response.set_cookie(
                settings.AUTH_COOKIE_NAME,
                session_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )
        return response


from app.models import User  # noqa: E402
