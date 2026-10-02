from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from sqlmodel import Session, select

from app.models import ApiDefinition


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _freeze(nested) for key, nested in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze(nested) for nested in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_thaw(nested) for nested in value]
    return value


@dataclass(frozen=True, slots=True)
class CatalogSeed:
    slug: str
    name: str
    summary: str
    category: str
    method: str
    path: str
    auth_type: str
    parameters: tuple[Mapping[str, Any], ...]
    response_schema: Mapping[str, Any]
    error_codes: tuple[Mapping[str, Any], ...]
    examples: tuple[Mapping[str, Any], ...]
    visibility: str
    status: str
    is_free: bool
    source_label: str
    adapter_name: str
    provider_ref: str | None
    cache_rules: Mapping[str, Any]

    def model_kwargs(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "summary": self.summary,
            "category": self.category,
            "method": self.method,
            "path": self.path,
            "auth_type": self.auth_type,
            "parameters": _thaw(self.parameters),
            "response_schema": _thaw(self.response_schema),
            "error_codes": _thaw(self.error_codes),
            "examples": _thaw(self.examples),
            "visibility": self.visibility,
            "status": self.status,
            "is_free": self.is_free,
            "source_label": self.source_label,
            "adapter_name": self.adapter_name,
            "provider_ref": self.provider_ref,
            "cache_rules": _thaw(self.cache_rules),
        }


_COMMON_ERROR_CODES = _freeze(
    [
        {
            "status": 401,
            "code": "API_KEY_REQUIRED",
            "description": "请求必须提供 X-API-Key。",
        },
        {
            "status": 401,
            "code": "API_KEY_INVALID",
            "description": "API Key 无效。",
        },
        {
            "status": 401,
            "code": "API_KEY_REVOKED",
            "description": "API Key 已撤销。",
        },
        {
            "status": 403,
            "code": "ACCOUNT_UNVERIFIED",
            "description": "API Key 所属账号尚未完成邮箱验证。",
        },
        {
            "status": 403,
            "code": "ACCOUNT_SUSPENDED",
            "description": "API Key 所属账号已被停用。",
        },
        {
            "status": 403,
            "code": "IP_NOT_ALLOWED",
            "description": "客户端 IP 不在允许范围内。",
        },
        {
            "status": 403,
            "code": "POLICY_DISABLED",
            "description": "该 API 的调用策略已停用。",
        },
        {
            "status": 422,
            "code": "INVALID_PARAMETERS",
            "description": "查询参数不符合接口约束。",
        },
        {
            "status": 429,
            "code": "MINUTE_LIMIT",
            "description": "超过账号分钟调用限制。",
        },
        {
            "status": 429,
            "code": "IP_MINUTE_LIMIT",
            "description": "超过客户端 IP 分钟调用限制。",
        },
        {
            "status": 429,
            "code": "DAILY_QUOTA_EXCEEDED",
            "description": "超过每日调用额度。",
        },
        {
            "status": 429,
            "code": "CONCURRENCY_LIMIT",
            "description": "超过并发调用限制。",
        },
        {
            "status": 502,
            "code": "UPSTREAM_ERROR",
            "description": "执行适配器返回错误。",
        },
        {
            "status": 503,
            "code": "QUOTA_UNAVAILABLE",
            "description": "配额服务暂时不可用。",
        },
        {
            "status": 504,
            "code": "UPSTREAM_TIMEOUT",
            "description": "执行超过请求超时限制。",
        },
    ]
)


PUBLIC_CATALOG_SEEDS: tuple[CatalogSeed, ...] = (
    CatalogSeed(
        slug="time",
        name="时间查询",
        summary="按可选 IANA 时区返回当前 UTC、Unix 时间戳和本地时间。",
        category="tools",
        method="GET",
        path="/v1/tools/time",
        auth_type="api_key",
        parameters=(
            _freeze(
                {
                    "name": "timezone",
                    "in": "query",
                    "required": False,
                    "description": "可选的 IANA 时区名称，省略时使用 UTC。",
                    "schema": {
                        "type": "string",
                        "default": "UTC",
                        "examples": ["UTC", "Asia/Shanghai"],
                    },
                }
            ),
        ),
        response_schema=_freeze(
            {
                "type": "object",
                "properties": {
                    "utc": {"type": "string", "format": "date-time"},
                    "unix_timestamp": {"type": "number"},
                    "timezone": {"type": "string"},
                    "local": {"type": "string", "format": "date-time"},
                },
                "required": ["utc", "unix_timestamp", "timezone", "local"],
                "additionalProperties": False,
            }
        ),
        error_codes=_COMMON_ERROR_CODES,
        examples=(
            _freeze(
                {
                    "language": "curl",
                    "request": (
                        "curl -G https://api.yeyubaka.top/v1/tools/time "
                        "-H \"X-API-Key: <YOUR_API_KEY>\" "
                        "--data-urlencode \"timezone=Asia/Shanghai\""
                    ),
                    "response": {
                        "utc": "2026-01-01T00:00:00Z",
                        "unix_timestamp": 1767225600,
                        "timezone": "Asia/Shanghai",
                        "local": "2026-01-01T08:00:00+08:00",
                    },
                }
            ),
        ),
        visibility="public",
        status="published",
        is_free=True,
        source_label="Yeyu API",
        adapter_name="builtin-tools",
        provider_ref="builtin-tools:time",
        cache_rules=_freeze(
            {
                "cacheable": False,
                "ttl_seconds": 0,
                "stale_if_error": False,
            }
        ),
    ),
    CatalogSeed(
        slug="uuid",
        name="UUID v4 生成器",
        summary="生成一个随机 UUID v4，不接受任何查询参数。",
        category="tools",
        method="GET",
        path="/v1/tools/uuid",
        auth_type="api_key",
        parameters=(),
        response_schema=_freeze(
            {
                "type": "object",
                "properties": {
                    "uuid": {"type": "string", "format": "uuid"},
                    "version": {"type": "integer", "const": 4},
                },
                "required": ["uuid", "version"],
                "additionalProperties": False,
            }
        ),
        error_codes=_COMMON_ERROR_CODES,
        examples=(
            _freeze(
                {
                    "language": "curl",
                    "request": (
                        "curl https://api.yeyubaka.top/v1/tools/uuid "
                        "-H \"X-API-Key: <YOUR_API_KEY>\""
                    ),
                    "response": {
                        "uuid": "00000000-0000-4000-8000-000000000000",
                        "version": 4,
                    },
                }
            ),
        ),
        visibility="public",
        status="published",
        is_free=True,
        source_label="Yeyu API",
        adapter_name="builtin-tools",
        provider_ref="builtin-tools:uuid",
        cache_rules=_freeze(
            {
                "cacheable": False,
                "ttl_seconds": 0,
                "stale_if_error": False,
            }
        ),
    ),
)


def seed_public_catalog(session: Session) -> None:
    """Insert missing builtin catalog definitions without changing existing rows."""

    added = False
    for seed in PUBLIC_CATALOG_SEEDS:
        existing = session.exec(
            select(ApiDefinition).where(ApiDefinition.slug == seed.slug)
        ).first()
        if existing is not None:
            continue
        session.add(ApiDefinition(**seed.model_kwargs()))
        added = True

    if added:
        session.commit()


__all__ = ["CatalogSeed", "PUBLIC_CATALOG_SEEDS", "seed_public_catalog"]
