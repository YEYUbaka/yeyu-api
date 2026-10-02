from __future__ import annotations

from uuid import uuid4

from app.models import AuditEvent
from app.services.audit import AuditService


class SessionDouble:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = False

    def add(self, value: object) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.committed = True


def test_audit_record_is_redacted_and_does_not_commit() -> None:
    session = SessionDouble()
    actor_id = uuid4()

    AuditService(session).record(
        actor_id=actor_id,
        action="catalog.update",
        object_type="api_definition",
        object_id="time",
        outcome="success",
        metadata={
            "changed_fields": ["summary"],
            "Authorization": "<NON_SECRET_AUTH_VALUE>",
            "request_body": {"password": "<NON_SECRET_PASSWORD_VALUE>"},
        },
        request_id="req-test-002",
    )

    assert len(session.added) == 1
    assert session.committed is False
    event = session.added[0]
    assert isinstance(event, AuditEvent)
    assert event.actor_id == actor_id
    assert event.request_id == "req-test-002"
    assert event.details["Authorization"] == "[REDACTED]"
    assert event.details["request_body"]["password"] == "[REDACTED]"  # type: ignore[index]


def test_audit_record_rejects_invalid_action() -> None:
    session = SessionDouble()

    try:
        AuditService(session).record(
            actor_id=None,
            action="",
            object_type="api_definition",
            object_id="time",
            outcome="success",
            metadata={},
        )
    except ValueError as exc:
        assert "action" in str(exc)
    else:
        raise AssertionError("invalid audit action must be rejected")
