from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_invoice_item_vat"
down_revision = "0004_invoice_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoice_items", sa.Column("vat_code", sa.String(length=64)))
    op.drop_column("invoices", "vat_code")


def downgrade() -> None:
    op.add_column("invoices", sa.Column("vat_code", sa.String(length=64)))
    op.drop_column("invoice_items", "vat_code")
