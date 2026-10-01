from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from app.api.deps import SessionDep
from app.schemas.catalog import CATALOG_SLUG_PATTERN, ApiDetail, CatalogPage
from app.services.catalog import ApiCatalogService, CatalogNotFoundError

router = APIRouter(prefix="/catalog", tags=["catalog"])
SlugPath = Annotated[
    str,
    Path(
        min_length=1,
        max_length=100,
        pattern=CATALOG_SLUG_PATTERN,
    ),
]


@router.get("", response_model=CatalogPage)
def search_catalog(
    session: SessionDep,
    query: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=64),
    status: str | None = Query(default=None, max_length=32),
    page: int = Query(default=1, ge=1, le=100_000),
    page_size: int = Query(default=20, ge=1, le=100),
) -> CatalogPage:
    return ApiCatalogService(session).search(
        query=query,
        category=category,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/{slug}", response_model=ApiDetail)
def get_catalog_detail(slug: SlugPath, session: SessionDep) -> ApiDetail:
    try:
        return ApiCatalogService(session).get_public(slug)
    except CatalogNotFoundError as exc:
        raise HTTPException(status_code=404, detail="API definition not found") from exc
