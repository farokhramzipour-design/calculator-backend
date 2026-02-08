from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_invoices"
down_revision = "0002_taric"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shipments.id")),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_type", sa.String(length=16), nullable=False),
        sa.Column("invoice_number", sa.String(length=64)),
        sa.Column("invoice_date", sa.Date()),
        sa.Column("supplier_name", sa.String(length=255)),
        sa.Column("buyer_name", sa.String(length=255)),
        sa.Column("currency", sa.String(length=3)),
        sa.Column("subtotal", sa.Numeric(18, 4)),
        sa.Column("freight", sa.Numeric(18, 4)),
        sa.Column("insurance", sa.Numeric(18, 4)),
        sa.Column("tax_total", sa.Numeric(18, 4)),
        sa.Column("total", sa.Numeric(18, 4)),
        sa.Column("extracted_payload", postgresql.JSONB),
        sa.Column("status", sa.Enum("UPLOADED", "EXTRACTED", "REVIEWED", "CONFIRMED", name="invoicestatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "invoice_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("hs_code", sa.String(length=16)),
        sa.Column("origin_country", sa.String(length=2)),
        sa.Column("quantity", sa.Numeric(18, 4)),
        sa.Column("unit_price", sa.Numeric(18, 4)),
        sa.Column("total_price", sa.Numeric(18, 4)),
    )


def downgrade() -> None:
    op.drop_table("invoice_items")
    op.drop_table("invoices")
    op.execute("DROP TYPE IF EXISTS invoicestatus")
