from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_invoice_fields"
down_revision = "0003_invoices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("buyer_address", sa.Text()))
    op.add_column("invoices", sa.Column("seller_address", sa.Text()))
    op.add_column("invoices", sa.Column("buyer_eori", sa.String(length=64)))
    op.add_column("invoices", sa.Column("seller_eori", sa.String(length=64)))
    op.add_column("invoices", sa.Column("vat_code", sa.String(length=64)))
    op.add_column("invoices", sa.Column("incoterm", sa.String(length=8)))

    op.add_column("invoice_items", sa.Column("pack_count", sa.Numeric(18, 4)))
    op.add_column("invoice_items", sa.Column("pack_type", sa.String(length=64)))
    op.add_column("invoice_items", sa.Column("net_weight", sa.Numeric(18, 4)))
    op.add_column("invoice_items", sa.Column("gross_weight", sa.Numeric(18, 4)))


def downgrade() -> None:
    op.drop_column("invoice_items", "gross_weight")
    op.drop_column("invoice_items", "net_weight")
    op.drop_column("invoice_items", "pack_type")
    op.drop_column("invoice_items", "pack_count")

    op.drop_column("invoices", "incoterm")
    op.drop_column("invoices", "vat_code")
    op.drop_column("invoices", "seller_eori")
    op.drop_column("invoices", "buyer_eori")
    op.drop_column("invoices", "seller_address")
    op.drop_column("invoices", "buyer_address")
