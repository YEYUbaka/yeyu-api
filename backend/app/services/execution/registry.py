from __future__ import annotations

from collections.abc import Mapping

from app.services.execution.adapters.tools import TimeAdapter, UuidAdapter
from app.services.execution.models import ApiAdapter, ExecutionError

BUILTIN_SLUGS = frozenset({"time", "uuid"})
ALLOWED_ADAPTER_NAMES = frozenset({"builtin-tools"})


class UnknownApiSlug(ExecutionError):
    code = "UNKNOWN_API_SLUG"
    public_message = "API slug is not available"


class AdapterRegistry:
    """Registry whose keys and adapter names are fixed at construction time."""

    def __init__(self, overrides: Mapping[str, ApiAdapter] | None = None) -> None:
        adapters: dict[str, ApiAdapter] = {
            "time": TimeAdapter(),
            "uuid": UuidAdapter(),
        }
        for slug, adapter in (overrides or {}).items():
            if slug not in BUILTIN_SLUGS:
                raise UnknownApiSlug("only fixed builtin slugs may be overridden")
            if not isinstance(adapter, ApiAdapter):
                raise TypeError("registry entries must implement ApiAdapter")
            if adapter.adapter_name not in ALLOWED_ADAPTER_NAMES:
                raise ValueError("adapter is not in the fixed allowlist")
            adapters[slug] = adapter
        self._adapters = adapters

    def get(self, slug: str) -> ApiAdapter:
        if not isinstance(slug, str) or slug not in BUILTIN_SLUGS:
            raise UnknownApiSlug("API slug is not in the fixed allowlist")
        try:
            return self._adapters[slug]
        except KeyError as exc:
            raise UnknownApiSlug("API slug is not registered") from exc

    def __contains__(self, slug: object) -> bool:
        return isinstance(slug, str) and slug in self._adapters

    def slugs(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))


__all__ = [
    "ALLOWED_ADAPTER_NAMES",
    "BUILTIN_SLUGS",
    "AdapterRegistry",
    "UnknownApiSlug",
]
