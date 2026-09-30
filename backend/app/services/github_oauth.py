from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import socket
import ssl
from collections.abc import Callable
from datetime import timedelta
from typing import Any, Protocol
from urllib.parse import urlencode, urlparse
from uuid import UUID

import httpx
from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.services.identity import (
    IdentityService,
    UnverifiedOAuthEmail,
)


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
    """Small RESP client for the OAuth nonce path.

    The application deliberately does not fall back to process memory: a
    multi-worker deployment must share and atomically consume OAuth state in
    Redis.
    """

    _key_prefix = "yeyu:oauth:state:"
    _consume_script = (
        "local value = redis.call('GET', KEYS[1]); "
        "if value then redis.call('DEL', KEYS[1]); end; return value"
    )

    def __init__(self, redis_url: str | None = None) -> None:
        parsed = urlparse(redis_url or settings.REDIS_URL)
        if parsed.scheme not in {"redis", "rediss"} or not parsed.hostname:
            raise OAuthConfigurationError
        self.host = parsed.hostname
        self.port = parsed.port or 6379
        self.password = parsed.password
        self.database = int(parsed.path.lstrip("/") or "0")
        self.tls = parsed.scheme == "rediss"

    def _connection(self) -> socket.socket:
        connection: socket.socket = socket.create_connection(
            (self.host, self.port), timeout=settings.GITHUB_OAUTH_TIMEOUT_SECONDS
        )
        if self.tls:
            context = ssl.create_default_context()
            connection = context.wrap_socket(connection, server_hostname=self.host)
        return connection

    @staticmethod
    def _command(*parts: str) -> bytes:
        encoded = [part.encode("utf-8") for part in parts]
        result = bytearray(f"*{len(encoded)}\r\n".encode())
        for part in encoded:
            result.extend(f"${len(part)}\r\n".encode())
            result.extend(part)
            result.extend(b"\r\n")
        return bytes(result)

    @staticmethod
    def _read_line(connection: socket.socket) -> bytes:
        line = bytearray()
        while not line.endswith(b"\r\n"):
            chunk = connection.recv(1)
            if not chunk:
                raise OAuthProviderError
            line.extend(chunk)
        return bytes(line[:-2])

    @classmethod
    def _read_response(cls, connection: socket.socket) -> str | int | None:
        prefix = connection.recv(1)
        if prefix == b"$":
            length = int(cls._read_line(connection))
            if length == -1:
                return None
            value = bytearray()
            while len(value) < length + 2:
                value.extend(connection.recv(length + 2 - len(value)))
            return bytes(value[:-2]).decode("utf-8")
        if prefix in {b"+", b":", b"-"}:
            line = cls._read_line(connection)
            if prefix == b":":
                return int(line)
            if prefix == b"-":
                raise OAuthProviderError
            return line.decode("utf-8")
        raise OAuthProviderError

    def _execute(self, *parts: str) -> str | int | None:
        with self._connection() as connection:
            if self.password:
                connection.sendall(self._command("AUTH", self.password))
                self._read_response(connection)
            if self.database:
                connection.sendall(self._command("SELECT", str(self.database)))
                self._read_response(connection)
            connection.sendall(self._command(*parts))
            return self._read_response(connection)

    def put(self, key: str, value: dict[str, str], ttl_seconds: int) -> bool:
        response = self._execute(
            "SET",
            f"{self._key_prefix}{key}",
            json.dumps(value, separators=(",", ":")),
            "EX",
            str(ttl_seconds),
            "NX",
        )
        return response == "OK"

    def consume(self, key: str) -> dict[str, str] | None:
        response = self._execute(
            "EVAL",
            self._consume_script,
            "1",
            f"{self._key_prefix}{key}",
        )
        if response is None:
            return None
        try:
            value = json.loads(str(response))
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
        self.http_client_factory = http_client_factory or (
            lambda: httpx.Client(timeout=settings.GITHUB_OAUTH_TIMEOUT_SECONDS)
        )

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

    def start(
        self,
        request: Request,
        *,
        intent: str = "login",
        user_id: UUID | None = None,
    ) -> RedirectResponse:
        if intent not in {"login", "link"} or (intent == "link" and user_id is None):
            raise OAuthConfigurationError
        callback_uri = self._callback_uri()
        client_id = self._client_id()
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        payload = {
            "code_verifier": code_verifier,
            "intent": intent,
            "user_id": str(user_id) if user_id else "",
        }
        if not self.state_store.put(state, payload, self.STATE_TTL_SECONDS):
            raise OAuthProviderError

        query = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": callback_uri,
                "scope": self._scope,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        response = RedirectResponse(
            url=f"{settings.GITHUB_OAUTH_AUTHORIZE_URL}?{query}",
            status_code=307,
        )
        response.set_cookie(
            "github_oauth_state",
            state,
            max_age=self.STATE_TTL_SECONDS,
            httponly=True,
            secure=True,
            samesite="lax",
        )
        return response

    def _client_request(self, method: str, url: str, **kwargs: Any) -> Any:
        client = self.http_client_factory()
        try:
            return getattr(client, method)(url, **kwargs)
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()

    def exchange_code(self, code: str, code_verifier: str) -> str:
        client_secret = settings.GITHUB_CLIENT_SECRET
        if not client_secret:
            raise OAuthConfigurationError
        response = self._client_request(
            "post",
            settings.GITHUB_OAUTH_TOKEN_URL,
            data={
                "client_id": self._client_id(),
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": self._callback_uri(),
                "code_verifier": code_verifier,
            },
            headers={"Accept": "application/json"},
        )
        if response.status_code != 200:
            raise OAuthProviderError
        try:
            token = response.json().get("access_token")
        except (TypeError, ValueError, AttributeError) as exc:
            raise OAuthProviderError from exc
        if not isinstance(token, str) or not token:
            raise OAuthProviderError
        return token

    def fetch_identity(self, access_token: str) -> dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
        }
        user_response = self._client_request(
            "get", f"{settings.GITHUB_API_BASE_URL}/user", headers=headers
        )
        if user_response.status_code != 200:
            raise OAuthProviderError
        email_response = self._client_request(
            "get", f"{settings.GITHUB_API_BASE_URL}/user/emails", headers=headers
        )
        if email_response.status_code != 200:
            raise OAuthProviderError
        try:
            profile = user_response.json()
            emails = email_response.json()
        except (TypeError, ValueError) as exc:
            raise OAuthProviderError from exc
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

        access_token = self.exchange_code(
            code, state_payload["code_verifier"]
        )
        try:
            github_identity = self.fetch_identity(access_token)
            identity_service = IdentityService(self.session)
            if state_payload.get("intent") == "link":
                user_id = UUID(state_payload.get("user_id", ""))
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
                access_token = ""
            else:
                user, _ = identity_service.resolve_github_login(
                    github_identity["provider_subject"],
                    github_identity["email"],
                    github_identity["email_verified"],
                )
        finally:
            # The provider token is request-scoped and is never persisted.
            access_token = ""

        response = RedirectResponse(url=settings.FRONTEND_HOST, status_code=303)
        response.delete_cookie("github_oauth_state")
        if state_payload.get("intent") != "link":
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


# Import here to keep the service module's public imports small and avoid a
# model import cycle during application startup.
from app.models import User  # noqa: E402
