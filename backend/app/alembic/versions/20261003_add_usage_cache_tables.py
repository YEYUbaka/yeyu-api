"""Add authoritative daily usage and cache metadata tables.

Revision ID: 20261003_add_usage_cache_tables
Revises: 20261002_add_key_policy_tables
Create Date: 2026-10-03
"""

import sqlalchemy as sa
from alembic import context, op

revision = "20261003_add_usage_cache_tables"
down_revision = "20261002_add_key_policy_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usage_daily",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("utc_date", sa.Date(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("api_key_id", sa.Uuid(), nullable=False),
        sa.Column("api_slug", sa.String(length=100), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("weighted_units", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["api_key_id"], ["api_key.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "request_count >= 0",
            name="ck_usage_daily_request_count_nonnegative",
        ),
        sa.CheckConstraint(
            "weighted_units >= 0",
            name="ck_usage_daily_weighted_units_nonnegative",
        ),
        sa.UniqueConstraint(
            "utc_date",
            "user_id",
            "api_key_id",
            "api_slug",
            name="uq_usage_daily_dimension",
        ),
    )
    op.create_index("ix_usage_daily_utc_date", "usage_daily", ["utc_date"])
    op.create_index("ix_usage_daily_user_id", "usage_daily", ["user_id"])
    op.create_index("ix_usage_daily_api_key_id", "usage_daily", ["api_key_id"])
    op.create_index("ix_usage_daily_api_slug", "usage_daily", ["api_slug"])

    op.create_table(
        "cache_entry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("api_slug", sa.String(length=100), nullable=False),
        sa.Column("params_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("data_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stale_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "api_slug",
            "params_fingerprint",
            name="uq_cache_entry_api_params",
        ),
    )
    op.create_index("ix_cache_entry_api_slug", "cache_entry", ["api_slug"])
    op.create_index(
        "ix_cache_entry_params_fingerprint",
        "cache_entry",
        ["params_fingerprint"],
    )


def _refuse_if_populated(table_name: str) -> None:
    if context.is_offline_mode():
        raise RuntimeError(
            "Refusing usage/cache migration downgrade in offline mode: "
            f"cannot verify whether {table_name} contains data"
        )
    connection = op.get_bind()
    table = sa.table(table_name)
    if connection.execute(sa.select(sa.func.count()).select_from(table)).scalar_one():
        raise RuntimeError(
            f"Refusing usage/cache migration downgrade: {table_name} contains data"
        )


def downgrade() -> None:
    _refuse_if_populated("cache_entry")
    _refuse_if_populated("usage_daily")

    op.drop_index(
        "ix_cache_entry_params_fingerprint", table_name="cache_entry"
    )
    op.drop_index("ix_cache_entry_api_slug", table_name="cache_entry")
    op.drop_table("cache_entry")

    op.drop_index("ix_usage_daily_api_slug", table_name="usage_daily")
    op.drop_index("ix_usage_daily_api_key_id", table_name="usage_daily")
    op.drop_index("ix_usage_daily_user_id", table_name="usage_daily")
    op.drop_index("ix_usage_daily_utc_date", table_name="usage_daily")
    op.drop_table("usage_daily")
