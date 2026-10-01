from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status

from app.api.deps import SessionDep, get_current_active_superuser
from app.models import ApiDefinition
from app.schemas.catalog import (
    CATALOG_SLUG_PATTERN,
    ApiDefinitionAdmin,
    ApiDefinitionCreate,
    ApiDefinitionUpdate,
)
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
) -> ApiDefinitionAdmin:
    try:
        definition = ApiCatalogService(session).create(slug, payload)
    except CatalogConflictError as exc:
        raise HTTPException(status_code=409, detail="Catalog slug already exists") from exc
    return _admin_response(definition)


@router.patch("/{slug}", response_model=ApiDefinitionAdmin)
def update_catalog_definition(
    slug: SlugPath,
    payload: ApiDefinitionUpdate,
    session: SessionDep,
) -> ApiDefinitionAdmin:
    try:
        definition = ApiCatalogService(session).update(slug, payload)
    except CatalogNotFoundError as exc:
        raise HTTPException(status_code=404, detail="API definition not found") from exc
    return _admin_response(definition)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalog_definition(slug: SlugPath, session: SessionDep) -> Response:
    try:
        ApiCatalogService(session).delete(slug)
    except CatalogNotFoundError as exc:
        raise HTTPException(status_code=404, detail="API definition not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
