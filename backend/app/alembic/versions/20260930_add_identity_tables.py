"""Add email verification and OAuth identity records.

Revision ID: 20260930_add_identity_tables
Revises: fe56fa70289e
Create Date: 2026-09-30

"""

import sqlalchemy as sa
from alembic import op

revision = "20260930_add_identity_tables"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing users stay in place and receive the safe, unverified default.
    op.add_column(
        "user",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column(
        "user",
        "email_verified",
        existing_type=sa.Boolean(),
        server_default=None,
    )

    op.create_table(
        "oauth_identity",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_subject",
            name="uq_oauth_identity_provider_subject",
        ),
    )
    op.create_index(
        "ix_oauth_identity_user_id", "oauth_identity", ["user_id"], unique=False
    )
    op.create_index(
        "ix_oauth_identity_provider_subject",
        "oauth_identity",
        ["provider_subject"],
        unique=False,
    )

    for table_name in ("email_verification_token", "password_reset_token"):
        op.create_table(
            table_name,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "token_hash", name=f"uq_{table_name}_token_hash"
            ),
        )
        op.create_index(
            f"ix_{table_name}_user_id", table_name, ["user_id"], unique=False
        )
        op.create_index(
            f"ix_{table_name}_token_hash", table_name, ["token_hash"], unique=False
        )


def downgrade() -> None:
    # Drop child tables first so their foreign keys never require deleting
    # rows from the existing user table.
    op.drop_table("password_reset_token")
    op.drop_table("email_verification_token")
    op.drop_table("oauth_identity")
    op.drop_column("user", "email_verified")
