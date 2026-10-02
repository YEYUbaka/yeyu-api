import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, delete, func, select

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import (
    Item,
    Message,
    UpdatePassword,
    User,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.schemas.identity import GitHubLinkRequest
from app.services.audit import AuditService
from app.services.github_oauth import GitHubOAuthService, OAuthConfigurationError
from app.services.identity import (
    EmailVerificationService,
    RateLimitExceeded,
    RateLimitUnavailable,
    RedisRateLimiter,
)
from app.utils import generate_new_account_email, send_email

router = APIRouter(prefix="/users", tags=["users"])


def _enforce_user_identity_limit(
    request: Request, *, scope: str, subject: str
) -> None:
    host = request.client.host if request.client else "unknown"
    try:
        RedisRateLimiter().check(
            scope=scope,
            identifier=f"{host}:{subject}",
            limit=settings.IDENTITY_RATE_LIMIT_PER_MINUTE,
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


def _safe_changed_fields(values: dict[str, object]) -> list[str]:
    return sorted(
        key
        for key in values
        if key not in {"password", "hashed_password", "token", "secret"}
    )


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """

    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = (
        select(User).order_by(col(User.created_at).desc()).offset(skip).limit(limit)
    )
    users = session.exec(statement).all()

    users_public = [UserPublic.model_validate(user) for user in users]
    return UsersPublic(data=users_public, count=count)


@router.post(
    "/", dependencies=[Depends(get_current_active_superuser)], response_model=UserPublic
)
def create_user(
    *,
    session: SessionDep,
    user_in: UserCreate,
    request: Request,
    current_user: CurrentUser,
) -> Any:
    """
    Create new user.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    try:
        user = crud.create_user(
            session=session,
            user_create=user_in,
            commit=False,
        )
        AuditService(session).record(
            actor_id=current_user.id,
            action="user.create",
            object_type="user",
            object_id=str(user.id),
            outcome="success",
            metadata={
                "changed_fields": _safe_changed_fields(
                    user_in.model_dump(exclude_unset=True)
                )
            },
            request_id=getattr(request.state, "request_id", None),
        )
        session.commit()
        session.refresh(user)
    except (SQLAlchemyError, ValueError) as exc:
        session.rollback()
        raise HTTPException(
            status_code=503, detail="User operation temporarily unavailable"
        ) from exc
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """

    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    email_changed = bool(
        user_in.email and str(user_in.email).casefold() != str(current_user.email).casefold()
    )
    user_data = user_in.model_dump(exclude_unset=True)
    if email_changed:
        user_data["email_verified"] = False
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    if email_changed:
        EmailVerificationService(session=session).request(current_user.id)
    return current_user


@router.post("/me/email-verification", response_model=Message, status_code=202)
def request_my_email_verification(
    request: Request, *, session: SessionDep, current_user: CurrentUser
) -> Message:
    _enforce_user_identity_limit(
        request,
        scope="email-verification",
        subject=str(current_user.id),
    )
    if not current_user.email_verified:
        EmailVerificationService(session=session).request(current_user.id)
    return Message(message="If that email is registered, we sent a verification link")


@router.post("/me/github/link", response_class=RedirectResponse)
def start_github_link(
    request: Request,
    body: GitHubLinkRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> RedirectResponse:
    _enforce_user_identity_limit(
        request,
        scope="github-link",
        subject=str(current_user.id),
    )
    verified, _ = verify_password(body.current_password, current_user.hashed_password)
    if not verified:
        raise HTTPException(status_code=400, detail="Incorrect password")
    try:
        return GitHubOAuthService(session=session).start(
            request,
            intent="link",
            user_id=current_user.id,
        )
    except OAuthConfigurationError as exc:
        raise HTTPException(status_code=503, detail="GitHub login is unavailable") from exc


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    verified, _ = verify_password(body.current_password, current_user.hashed_password)
    if not verified:
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return current_user


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")


@router.post("/signup", response_model=UserPublic)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user_create = UserCreate.model_validate(user_in)
    user = crud.create_user(session=session, user_create=user_create)
    EmailVerificationService(session=session).request(user.id)
    return user


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
    request: Request,
    current_user: CurrentUser,
) -> Any:
    """
    Update a user.
    """

    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    email_changed = bool(
        user_in.email
        and str(user_in.email).casefold() != str(db_user.email).casefold()
    )
    if email_changed:
        db_user.email_verified = False
    try:
        db_user = crud.update_user(
            session=session,
            db_user=db_user,
            user_in=user_in,
            commit=False,
        )
        AuditService(session).record(
            actor_id=current_user.id,
            action="user.update",
            object_type="user",
            object_id=str(db_user.id),
            outcome="success",
            metadata={
                "changed_fields": _safe_changed_fields(
                    user_in.model_dump(exclude_unset=True)
                ),
                "email_changed": email_changed,
            },
            request_id=getattr(request.state, "request_id", None),
        )
        session.commit()
        session.refresh(db_user)
    except (SQLAlchemyError, ValueError) as exc:
        session.rollback()
        raise HTTPException(
            status_code=503, detail="User operation temporarily unavailable"
        ) from exc
    if email_changed:
        EmailVerificationService(session=session).request(db_user.id)
    return db_user


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep,
    current_user: CurrentUser,
    user_id: uuid.UUID,
    request: Request,
) -> Message:
    """
    Delete a user.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    try:
        statement = delete(Item).where(col(Item.owner_id) == user_id)
        session.exec(statement)
        session.delete(user)
        AuditService(session).record(
            actor_id=current_user.id,
            action="user.delete",
            object_type="user",
            object_id=str(user_id),
            outcome="success",
            metadata={"deleted_items": True},
            request_id=getattr(request.state, "request_id", None),
        )
        session.commit()
    except (SQLAlchemyError, ValueError) as exc:
        session.rollback()
        raise HTTPException(
            status_code=503, detail="User operation temporarily unavailable"
        ) from exc
    return Message(message="User deleted successfully")
