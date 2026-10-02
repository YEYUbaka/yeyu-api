"""Harden catalog adapter, provider and internal path boundaries.

Revision ID: 20261005_harden_catalog_boundaries
Revises: 20261004_add_audit_events
Create Date: 2026-10-05
"""

from alembic import op

revision = "20261005_harden_catalog_boundaries"
down_revision = "20261004_add_audit_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_api_definition_status_allowed",
        "api_definition",
        "status IN ('trial', 'healthy', 'published', 'draft', 'disabled')",
    )
    op.create_check_constraint(
        "ck_api_definition_adapter_name_allowlist",
        "api_definition",
        "adapter_name = 'builtin-tools'",
    )
    op.create_check_constraint(
        "ck_api_definition_provider_ref_allowlist",
        "api_definition",
        "provider_ref IS NULL OR provider_ref IN "
        "('provider:internal-tools', 'builtin-tools:time', 'builtin-tools:uuid')",
    )
    op.create_check_constraint(
        "ck_api_definition_path_internal",
        "api_definition",
        "path LIKE '/%' AND path NOT LIKE '//%' "
        "AND path NOT LIKE '%://%' AND path NOT LIKE '%?%' "
        "AND path NOT LIKE '%#%' AND path NOT LIKE '%..%' "
        "AND path NOT LIKE '%\\%' ESCAPE '!' "
        "AND path NOT LIKE '%!%%' ESCAPE '!'",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_api_definition_path_internal",
        "api_definition",
        type_="check",
    )
    op.drop_constraint(
        "ck_api_definition_provider_ref_allowlist",
        "api_definition",
        type_="check",
    )
    op.drop_constraint(
        "ck_api_definition_adapter_name_allowlist",
        "api_definition",
        type_="check",
    )
    op.drop_constraint(
        "ck_api_definition_status_allowed",
        "api_definition",
        type_="check",
    )
