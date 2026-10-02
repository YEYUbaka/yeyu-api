from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import ApiDefinition
from app.schemas.catalog import (
    ApiAuth,
    ApiDefinitionCreate,
    ApiDefinitionUpdate,
    ApiDetail,
    CatalogItem,
    CatalogPage,
)


class CatalogNotFoundError(Exception):
    """The requested public or administrative catalog record does not exist."""


class CatalogConflictError(Exception):
    """A catalog slug is already in use."""


PUBLIC_STATUSES = ("healthy", "published")
_SENSITIVE_METADATA_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "private_key",
    "provider_ref",
    "secret",
    "token",
)


def _now() -> datetime:
    return datetime.now(UTC)


def _sanitize_public_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, nested in value.items():
            normalized_key = str(key).casefold().replace("-", "_")
            if any(part in normalized_key for part in _SENSITIVE_METADATA_KEY_PARTS):
                continue
            sanitized[str(key)] = _sanitize_public_metadata(nested)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_public_metadata(nested) for nested in value]
    return value


class ApiCatalogService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _public_filter() -> Any:
        return (ApiDefinition.visibility == "public") & (
            ApiDefinition.status.in_(PUBLIC_STATUSES)
        )

    @staticmethod
    def _item(definition: ApiDefinition) -> CatalogItem:
        return CatalogItem.model_validate(definition)

    @staticmethod
    def _detail(definition: ApiDefinition) -> ApiDetail:
        return ApiDetail(
            slug=definition.slug,
            name=definition.name,
            summary=definition.summary,
            category=definition.category,
            method=definition.method,
            path=definition.path,
            auth=ApiAuth(type="api_key"),
            is_free=definition.is_free,
            status=definition.status,
            updated_at=definition.updated_at,
            parameters=_sanitize_public_metadata(definition.parameters),
            response_schema=_sanitize_public_metadata(definition.response_schema),
            errors=_sanitize_public_metadata(definition.error_codes),
            examples=_sanitize_public_metadata(definition.examples),
            source=definition.source_label,
            cache_rules=_sanitize_public_metadata(definition.cache_rules),
        )

    def search(
        self,
        *,
        query: str | None,
        category: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> CatalogPage:
        statement = select(ApiDefinition).where(self._public_filter())
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(
                    ApiDefinition.slug.ilike(pattern),
                    ApiDefinition.name.ilike(pattern),
                    ApiDefinition.summary.ilike(pattern),
                    ApiDefinition.path.ilike(pattern),
                )
            )
        if category:
            statement = statement.where(ApiDefinition.category == category)
        if status:
            statement = statement.where(ApiDefinition.status == status)

        count = self.session.exec(
            select(func.count()).select_from(statement.subquery())
        ).one()
        definitions = self.session.exec(
            statement.order_by(ApiDefinition.slug)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return CatalogPage(
            data=[self._item(item) for item in definitions],
            count=count,
            page=page,
            page_size=page_size,
        )

    def get_public(self, slug: str) -> ApiDetail:
        definition = self.session.exec(
            select(ApiDefinition).where(
                ApiDefinition.slug == slug,
                self._public_filter(),
            )
        ).first()
        if definition is None:
            raise CatalogNotFoundError
        return self._detail(definition)

    def get_admin(self, slug: str) -> ApiDefinition:
        definition = self.session.exec(
            select(ApiDefinition).where(ApiDefinition.slug == slug)
        ).first()
        if definition is None:
            raise CatalogNotFoundError
        return definition

    def create(
        self,
        slug: str,
        payload: ApiDefinitionCreate,
        *,
        commit: bool = True,
    ) -> ApiDefinition:
        if self.session.exec(
            select(ApiDefinition).where(ApiDefinition.slug == slug)
        ).first():
            raise CatalogConflictError
        data = payload.model_dump(exclude_unset=True)
        data.pop("slug", None)
        definition = ApiDefinition(
            slug=slug,
            source_label=str(data.pop("source", "Yeyu API")),
            **data,
        )
        try:
            self.session.add(definition)
            self.session.flush()
            if commit:
                self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise CatalogConflictError from exc
        if commit:
            self.session.refresh(definition)
        return definition

    def update(
        self,
        slug: str,
        payload: ApiDefinitionUpdate,
        *,
        commit: bool = True,
    ) -> ApiDefinition:
        definition = self.get_admin(slug)
        data = payload.model_dump(exclude_unset=True)
        if "source" in data:
            definition.source_label = str(data.pop("source"))
        definition.sqlmodel_update(data)
        definition.updated_at = _now()
        self.session.add(definition)
        self.session.flush()
        if commit:
            self.session.commit()
            self.session.refresh(definition)
        return definition

    def delete(self, slug: str, *, commit: bool = True) -> None:
        definition = self.get_admin(slug)
        self.session.delete(definition)
        self.session.flush()
        if commit:
            self.session.commit()
