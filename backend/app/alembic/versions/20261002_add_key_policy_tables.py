"""Add API key lifecycle and API policy tables.

Revision ID: 20261002_add_key_policy_tables
Revises: 20261001_add_catalog_tables
Create Date: 2026-10-02
"""

import sqlalchemy as sa
from alembic import context, op

revision = "20261002_add_key_policy_tables"
down_revision = "20261001_add_catalog_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_key",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("prefix", sa.String(length=32), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("hash_version", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "key_hash",
            "hash_version",
            name="uq_api_key_key_hash_version",
        ),
    )
    op.create_index("ix_api_key_user_id", "api_key", ["user_id"], unique=False)
    op.create_index("ix_api_key_prefix", "api_key", ["prefix"], unique=False)
    op.create_index("ix_api_key_key_hash", "api_key", ["key_hash"], unique=False)

    op.create_table(
        "api_policy",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("api_definition_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("api_key_id", sa.Uuid(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("minute_limit", sa.Integer(), nullable=False),
        sa.Column("ip_minute_limit", sa.Integer(), nullable=False),
        sa.Column("daily_limit", sa.Integer(), nullable=False),
        sa.Column("concurrency_limit", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("allowed_ips", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["api_definition_id"], ["api_definition.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_key.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "api_definition_id",
            name="uq_api_policy_api_definition_id",
        ),
    )
    op.create_index(
        "ix_api_policy_api_definition_id",
        "api_policy",
        ["api_definition_id"],
        unique=False,
    )
    op.create_index("ix_api_policy_user_id", "api_policy", ["user_id"], unique=False)
    op.create_index(
        "ix_api_policy_api_key_id", "api_policy", ["api_key_id"], unique=False
    )


def downgrade() -> None:
    if not context.is_offline_mode():
        connection = op.get_bind()
        for table_name in ("api_policy", "api_key"):
            table = sa.table(table_name)
            count = connection.execute(
                sa.select(sa.func.count()).select_from(table)
            ).scalar_one()
            if count:
                raise RuntimeError(
                    f"Refusing key/policy migration downgrade: {table_name} contains data"
                )

    op.drop_index("ix_api_policy_api_key_id", table_name="api_policy")
    op.drop_index("ix_api_policy_user_id", table_name="api_policy")
    op.drop_index("ix_api_policy_api_definition_id", table_name="api_policy")
    op.drop_table("api_policy")
    op.drop_index("ix_api_key_key_hash", table_name="api_key")
    op.drop_index("ix_api_key_prefix", table_name="api_key")
    op.drop_index("ix_api_key_user_id", table_name="api_key")
    op.drop_table("api_key")
