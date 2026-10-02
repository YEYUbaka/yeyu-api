from __future__ import annotations

import re
from collections.abc import Mapping
from uuid import UUID

from sqlmodel import Session

from app.models import AuditEvent
from app.services.redaction import RedactionService

_AUDIT_COMPONENT_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*\Z")


class AuditService:
    """Create audit events in the caller-owned transaction."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        actor_id: UUID | None,
        action: str,
        object_type: str,
        object_id: str,
        outcome: str,
        metadata: Mapping[str, object],
        *,
        request_id: str | None = None,
    ) -> None:
        details = RedactionService.sanitize_metadata(metadata)
        self._validate_component(action, "action", 64)
        self._validate_component(object_type, "object_type", 64)
        self._validate_component(outcome, "outcome", 32)
        self._validate_identifier(object_id, "object_id", 128)
        if request_id is not None:
            self._validate_identifier(request_id, "request_id", 128)

        self.session.add(
            AuditEvent(
                actor_id=actor_id,
                request_id=request_id,
                action=action,
                object_type=object_type,
                object_id=object_id,
                outcome=outcome,
                details=details,
            )
        )

    @staticmethod
    def _validate_component(value: str, name: str, max_length: int) -> None:
        if (
            not isinstance(value, str)
            or not value
            or len(value) > max_length
            or _AUDIT_COMPONENT_PATTERN.fullmatch(value) is None
        ):
            raise ValueError(
                f"{name} must be 1-{max_length} ASCII identifier characters"
            )

    @staticmethod
    def _validate_identifier(value: str, name: str, max_length: int) -> None:
        if (
            not isinstance(value, str)
            or not value
            or len(value) > max_length
            or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)
        ):
            raise ValueError(f"{name} must be 1-{max_length} safe characters")
