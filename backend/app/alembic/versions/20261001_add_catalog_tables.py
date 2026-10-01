"""Add curated API catalog metadata.

Revision ID: 20261001_add_catalog_tables
Revises: 20260930_add_identity_tables
Create Date: 2026-10-01
"""

import sqlalchemy as sa
from alembic import context, op

revision = "20261001_add_catalog_tables"
down_revision = "20260930_add_identity_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_definition",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("auth_type", sa.String(length=32), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("response_schema", sa.JSON(), nullable=False),
        sa.Column("error_codes", sa.JSON(), nullable=False),
        sa.Column("examples", sa.JSON(), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_free", sa.Boolean(), nullable=False),
        sa.Column("source_label", sa.String(length=255), nullable=False),
        sa.Column("adapter_name", sa.String(length=128), nullable=False),
        sa.Column("provider_ref", sa.String(length=255), nullable=True),
        sa.Column("cache_rules", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_api_definition_slug"),
        sa.CheckConstraint(
            "auth_type = 'api_key'", name="ck_api_definition_auth_type"
        ),
    )
    op.create_index("ix_api_definition_slug", "api_definition", ["slug"])
    op.create_index("ix_api_definition_category", "api_definition", ["category"])
    op.create_index("ix_api_definition_visibility", "api_definition", ["visibility"])
    op.create_index("ix_api_definition_status", "api_definition", ["status"])


def downgrade() -> None:
    if not context.is_offline_mode():
        connection = op.get_bind()
        catalog_table = sa.table("api_definition")
        count = connection.execute(
            sa.select(sa.func.count()).select_from(catalog_table)
        ).scalar_one()
        if count:
            raise RuntimeError(
                "Refusing catalog migration downgrade: api_definition contains data"
            )

    op.drop_index("ix_api_definition_status", table_name="api_definition")
    op.drop_index("ix_api_definition_visibility", table_name="api_definition")
    op.drop_index("ix_api_definition_category", table_name="api_definition")
    op.drop_index("ix_api_definition_slug", table_name="api_definition")
    op.drop_table("api_definition")
