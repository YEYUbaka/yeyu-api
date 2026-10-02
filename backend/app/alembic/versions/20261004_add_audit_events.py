"""Add redacted administrative audit events.

Revision ID: 20261004_add_audit_events
Revises: 20261003_add_usage_cache_tables
Create Date: 2026-10-04
"""

import sqlalchemy as sa
from alembic import context, op

revision = "20261004_add_audit_events"
down_revision = "20261003_add_usage_cache_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("object_type", sa.String(length=64), nullable=False),
        sa.Column("object_id", sa.String(length=128), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["user.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_event_request_id", "audit_event", ["request_id"])
    op.create_index("ix_audit_event_action", "audit_event", ["action"])
    op.create_index(
        "ix_audit_event_object_type", "audit_event", ["object_type"]
    )
    op.create_index("ix_audit_event_outcome", "audit_event", ["outcome"])
    op.create_index("ix_audit_event_created_at", "audit_event", ["created_at"])


def _refuse_if_populated() -> None:
    if context.is_offline_mode():
        raise RuntimeError(
            "Refusing audit event migration downgrade in offline mode: "
            "cannot verify whether audit_event contains data"
        )

    connection = op.get_bind()
    table = sa.table("audit_event")
    if connection.execute(sa.select(sa.func.count()).select_from(table)).scalar_one():
        raise RuntimeError(
            "Refusing audit event migration downgrade: audit_event contains data"
        )


def downgrade() -> None:
    _refuse_if_populated()

    op.drop_index("ix_audit_event_created_at", table_name="audit_event")
    op.drop_index("ix_audit_event_outcome", table_name="audit_event")
    op.drop_index("ix_audit_event_object_type", table_name="audit_event")
    op.drop_index("ix_audit_event_action", table_name="audit_event")
    op.drop_index("ix_audit_event_request_id", table_name="audit_event")
    op.drop_table("audit_event")
