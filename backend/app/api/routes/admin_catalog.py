from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.models import ApiDefinition
from app.schemas.admin import AdminCatalogPage
from app.schemas.catalog import (
    ALLOWED_STATUS_VALUES,
    CATALOG_SLUG_PATTERN,
    ApiDefinitionAdmin,
    ApiDefinitionCreate,
    ApiDefinitionUpdate,
)
from app.services.audit import AuditService
from app.services.catalog import (
    ApiCatalogService,
    CatalogConflictError,
    CatalogNotFoundError,
)

router = APIRouter(
    prefix="/admin/catalog",
    tags=["admin-catalog"],
    dependencies=[Depends(get_current_active_superuser)],
)
SlugPath = Annotated[
    str,
    Path(
        min_length=1,
        max_length=100,
        pattern=CATALOG_SLUG_PATTERN,
    ),
]


def _admin_response(definition: ApiDefinition) -> ApiDefinitionAdmin:
    return ApiDefinitionAdmin(
        id=definition.id,
        slug=definition.slug,
        name=definition.name,
        summary=definition.summary,
        category=definition.category,
        method=definition.method,
        path=definition.path,
        auth_type=definition.auth_type,
        parameters=definition.parameters,
        response_schema=definition.response_schema,
        error_codes=definition.error_codes,
        examples=definition.examples,
        visibility=definition.visibility,
        status=definition.status,
        is_free=definition.is_free,
        source=definition.source_label,
        adapter_name=definition.adapter_name,
        provider_ref=definition.provider_ref,
        cache_rules=definition.cache_rules,
        created_at=definition.created_at,
        updated_at=definition.updated_at,
    )


@router.post("/{slug}", response_model=ApiDefinitionAdmin, status_code=201)
def create_catalog_definition(
    slug: SlugPath,
    payload: ApiDefinitionCreate,
    session: SessionDep,
    request: Request,
    current_user: CurrentUser,
) -> ApiDefinitionAdmin:
    try:
        definition = ApiCatalogService(session).create(slug, payload, commit=False)
        AuditService(session).record(
            actor_id=current_user.id,
            action="catalog.create",
            object_type="api_definition",
            object_id=slug,
            outcome="success",
            metadata={
                "changed_fields": sorted(payload.model_dump(exclude_unset=True)),
                "status": definition.status,
                "adapter_name": definition.adapter_name,
            },
            request_id=getattr(request.state, "request_id", None),
        )
        session.commit()
        session.refresh(definition)
    except CatalogConflictError as exc:
        raise HTTPException(status_code=409, detail="Catalog slug already exists") from exc
    except (SQLAlchemyError, ValueError) as exc:
        session.rollback()
        raise HTTPException(
            status_code=503, detail="Catalog operation temporarily unavailable"
        ) from exc
    return _admin_response(definition)


@router.patch("/{slug}", response_model=ApiDefinitionAdmin)
def update_catalog_definition(
    slug: SlugPath,
    payload: ApiDefinitionUpdate,
    session: SessionDep,
    request: Request,
    current_user: CurrentUser,
) -> ApiDefinitionAdmin:
    try:
        definition = ApiCatalogService(session).update(slug, payload, commit=False)
        AuditService(session).record(
            actor_id=current_user.id,
            action="catalog.update",
            object_type="api_definition",
            object_id=slug,
            outcome="success",
            metadata={
                "changed_fields": sorted(payload.model_dump(exclude_unset=True)),
            },
            request_id=getattr(request.state, "request_id", None),
        )
        session.commit()
        session.refresh(definition)
    except CatalogNotFoundError as exc:
        raise HTTPException(status_code=404, detail="API definition not found") from exc
    except (SQLAlchemyError, ValueError) as exc:
        session.rollback()
        raise HTTPException(
            status_code=503, detail="Catalog operation temporarily unavailable"
        ) from exc
    return _admin_response(definition)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalog_definition(
    slug: SlugPath,
    session: SessionDep,
    request: Request,
    current_user: CurrentUser,
) -> Response:
    try:
        definition = ApiCatalogService(session).get_admin(slug)
        ApiCatalogService(session).delete(slug, commit=False)
        AuditService(session).record(
            actor_id=current_user.id,
            action="catalog.delete",
            object_type="api_definition",
            object_id=slug,
            outcome="success",
            metadata={"definition_id": str(definition.id)},
            request_id=getattr(request.state, "request_id", None),
        )
        session.commit()
    except CatalogNotFoundError as exc:
        raise HTTPException(status_code=404, detail="API definition not found") from exc
    except (SQLAlchemyError, ValueError) as exc:
        session.rollback()
        raise HTTPException(
            status_code=503, detail="Catalog operation temporarily unavailable"
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=AdminCatalogPage)
def read_admin_catalog(
    session: SessionDep,
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    page: int = Query(default=1, ge=1, le=100_000),
    page_size: int = Query(default=50, ge=1, le=100),
) -> AdminCatalogPage:
    if status_filter is not None and status_filter not in ALLOWED_STATUS_VALUES:
        raise HTTPException(status_code=422, detail="Invalid catalog status filter")

    statement = select(ApiDefinition)
    if status_filter is not None:
        statement = statement.where(ApiDefinition.status == status_filter)

    count = session.exec(
        select(func.count()).select_from(statement.subquery())
    ).one()
    definitions = session.exec(
        statement.order_by(ApiDefinition.slug)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return AdminCatalogPage(
        data=[_admin_response(definition) for definition in definitions],
        count=count,
        page=page,
        page_size=page_size,
    )
