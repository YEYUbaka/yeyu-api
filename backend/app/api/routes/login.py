from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.core import security
from app.core.config import settings
from app.models import Message, NewPassword, Token, User, UserPublic
from app.schemas.identity import EmailAddressRequest
from app.services.github_oauth import (
    GitHubOAuthService,
    InvalidOAuthState,
    OAuthConfigurationError,
    OAuthError,
    OAuthProviderError,
)
from app.services.identity import (
    EmailVerificationService,
    IdentityConflict,
    InvalidVerificationToken,
    PasswordResetService,
    RateLimitExceeded,
    RateLimitUnavailable,
    RedisRateLimiter,
    UnverifiedOAuthEmail,
)
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    verify_password_reset_token,
)

router = APIRouter(tags=["login"])


def _enforce_identity_limit(
    request: Request,
    *,
    scope: str,
    subject: str = "",
    limit: int | None = None,
) -> None:
    host = request.client.host if request.client else "unknown"
    try:
        RedisRateLimiter().check(
            scope=scope,
            identifier=f"{host}:{subject}",
            limit=limit or settings.IDENTITY_RATE_LIMIT_PER_MINUTE,
            window_seconds=60,
        )
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail="Too many identity requests",
            headers={"Retry-After": "60"},
        ) from exc
    except RateLimitUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="Identity service temporarily unavailable",
        ) from exc


@router.post("/login/access-token")
def login_access_token(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = crud.authenticate(
        session=session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user


def _request_password_reset(*, session: Any, email: str) -> Message:
    user = crud.get_user_by_email(session=session, email=email)
    if user is not None and user.is_active:
        PasswordResetService(session=session).request(user.id)
    return Message(
        message="If that email is registered, we sent a password recovery link"
    )


@router.post(
    "/auth/request-password-reset",
    response_model=Message,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_password_reset(
    request: Request, *, session: SessionDep, body: EmailAddressRequest
) -> Message:
    """Request a reset link without disclosing whether the email exists."""
    _enforce_identity_limit(
        request,
        scope="password-reset",
        subject=str(body.email).casefold(),
    )
    return _request_password_reset(session=session, email=str(body.email))


@router.post(
    "/auth/request-email-verification",
    response_model=Message,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_email_verification(
    request: Request, *, session: SessionDep, body: EmailAddressRequest
) -> Message:
    _enforce_identity_limit(
        request,
        scope="email-verification",
        subject=str(body.email).casefold(),
    )
    user = crud.get_user_by_email(session=session, email=str(body.email))
    if user is not None and user.is_active and not user.email_verified:
        EmailVerificationService(session=session).request(user.id)
    return Message(message="If that email is registered, we sent a verification link")


@router.post("/auth/logout", response_model=Message)
def logout(response: Response) -> Message:
    response.delete_cookie(
        settings.AUTH_COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return Message(message="Logged out successfully")


@router.get("/auth/verify-email", response_model=Message)
def verify_email(
    *, session: SessionDep, token: str = Query(min_length=1, max_length=512)
) -> Message:
    try:
        EmailVerificationService(session=session).verify(token)
    except InvalidVerificationToken as exc:
        raise HTTPException(
            status_code=400, detail="Invalid or expired verification token"
        ) from exc
    return Message(message="Email verified successfully")


@router.get("/auth/github", response_class=RedirectResponse)
def github_login(request: Request, session: SessionDep) -> RedirectResponse:
    _enforce_identity_limit(
        request,
        scope="github-login",
        limit=settings.IDENTITY_OAUTH_RATE_LIMIT_PER_MINUTE,
    )
    try:
        return GitHubOAuthService(session=session).start(request)
    except (OAuthConfigurationError, OAuthProviderError) as exc:
        raise HTTPException(status_code=503, detail="GitHub login is unavailable") from exc


@router.get("/auth/github/callback", response_class=RedirectResponse)
def github_callback(request: Request, session: SessionDep) -> RedirectResponse:
    try:
        return GitHubOAuthService(session=session).callback(request)
    except InvalidOAuthState as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc
    except (IdentityConflict, UnverifiedOAuthEmail) as exc:
        raise HTTPException(
            status_code=409,
            detail="GitHub identity requires an existing verified account binding",
        ) from exc
    except OAuthError as exc:
        raise HTTPException(status_code=502, detail="GitHub login failed") from exc


@router.post("/password-recovery/{email}")
def recover_password(request: Request, email: str, session: SessionDep) -> Message:
    """
    Password Recovery
    """
    _enforce_identity_limit(
        request,
        scope="password-reset",
        subject=email.casefold(),
    )
    return _request_password_reset(session=session, email=email)


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """
    Reset password
    """
    reset_service = PasswordResetService(session=session)
    try:
        user_id = reset_service.consume_token(body.token)
    except InvalidVerificationToken:
        # Existing template links are signed JWTs. Consume them once while
        # migrating to hashed database-backed reset records.
        email = verify_password_reset_token(token=body.token)
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token") from None
        try:
            user_id = reset_service.consume_legacy_token(
                body.token, email, commit=False
            )
        except InvalidVerificationToken:
            raise HTTPException(status_code=400, detail="Invalid token") from None
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid token")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    user.hashed_password = security.get_password_hash(body.new_password)
    session.add(user)
    session.commit()
    return Message(message="Password updated successfully")


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content,
        headers={"X-Email-Subject": email_data.subject},
    )
