from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_passport_license"
down_revision = "0005_invoice_item_vat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "passport_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("hs_code", sa.String(length=16)),
        sa.Column("supplier", sa.String(length=255)),
        sa.Column("weight_per_unit", sa.Numeric(18, 4)),
        sa.Column("weight", sa.Numeric(18, 4)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.add_column("shipment_items", sa.Column("passport_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("passport_items.id")))
    op.add_column("invoice_items", sa.Column("passport_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("passport_items.id")))

    op.create_table(
        "licenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("license_type", sa.String(length=64), nullable=False),
        sa.Column("license_number", sa.String(length=64)),
        sa.Column("issuer", sa.String(length=255)),
        sa.Column("expires_on", sa.Date()),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_type", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "shipment_licenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shipments.id"), nullable=False),
        sa.Column("license_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("licenses.id"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("shipment_licenses")
    op.drop_table("licenses")

    op.drop_column("invoice_items", "passport_item_id")
    op.drop_column("shipment_items", "passport_item_id")

    op.drop_table("passport_items")
