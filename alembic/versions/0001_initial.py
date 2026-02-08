from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "shipments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("direction", sa.Enum("IMPORT_UK", "IMPORT_EU", "EXPORT_UK", "EXPORT_EU", name="direction")),
        sa.Column("destination_country", sa.String(length=2)),
        sa.Column("origin_country_default", sa.String(length=2), nullable=False),
        sa.Column("incoterm", sa.Enum("EXW", "FOB", "CIF", "DDP", "FCA", "CPT", "CIP", "DAP", name="incoterm")),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("fx_rate_to_gbp", sa.String(length=32)),
        sa.Column("fx_rate_to_eur", sa.String(length=32)),
        sa.Column("status", sa.Enum("DRAFT", "NEEDS_INPUT", "READY", "CALCULATED", name="shipmentstatus")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "shipment_costs",
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shipments.id"), primary_key=True),
        sa.Column("freight_amount", sa.Numeric(18, 4)),
        sa.Column("insurance_amount", sa.Numeric(18, 4)),
        sa.Column("insurance_is_estimated", sa.Boolean(), default=False),
        sa.Column("brokerage_amount", sa.Numeric(18, 4)),
        sa.Column("port_fees_amount", sa.Numeric(18, 4)),
        sa.Column("inland_transport_amount", sa.Numeric(18, 4)),
        sa.Column("other_incidental_amount", sa.Numeric(18, 4)),
        sa.Column("notes", sa.String(length=1024)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "shipment_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shipments.id"), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("hs_code", sa.String(length=16), nullable=False),
        sa.Column("origin_country", sa.String(length=2), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("goods_value", sa.Numeric(18, 4)),
        sa.Column("weight_net_kg", sa.Numeric(18, 4)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "rate_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shipments.id"), nullable=False),
        sa.Column("provider", sa.Enum("UK_TARIFF", "EU_TARIC", "VAT", "FX", name="providertype")),
        sa.Column("request_key", postgresql.JSONB, nullable=False),
        sa.Column("response_payload", postgresql.JSONB, nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False),
    )

    op.create_table(
        "calculations",
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shipments.id"), primary_key=True),
        sa.Column("customs_value", sa.Numeric(18, 4), nullable=False),
        sa.Column("duty_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("vat_base", sa.Numeric(18, 4), nullable=False),
        sa.Column("vat_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("other_duties_total", sa.Numeric(18, 4), nullable=False, default=0),
        sa.Column("authorities_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("landed_cost_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("landed_cost_per_unit", sa.Numeric(18, 4), nullable=False),
        sa.Column("assumptions", postgresql.JSONB, nullable=False),
        sa.Column("warnings", postgresql.JSONB, nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("engine_version", sa.String(length=32), nullable=False),
    )

    op.create_table(
        "tariff_rate_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("destination_region", sa.String(length=8), nullable=False),
        sa.Column("commodity_code", sa.String(length=16), nullable=False),
        sa.Column("origin_country", sa.String(length=2)),
        sa.Column("preference_flag", sa.Boolean(), default=False),
        sa.Column("duty_rate", sa.Numeric(8, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "vat_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("rate_type", sa.String(length=32), nullable=False, default="standard"),
        sa.Column("rate", sa.Numeric(8, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "eu_taric_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hs_code", sa.String(length=16), nullable=False),
        sa.Column("origin_country", sa.String(length=2)),
        sa.Column("preference_flag", sa.Boolean(), default=False),
        sa.Column("duty_rate", sa.Numeric(8, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "fx_rates_daily",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("base", sa.String(length=3), nullable=False),
        sa.Column("quote", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("fx_rates_daily")
    op.drop_table("eu_taric_rates")
    op.drop_table("vat_rates")
    op.drop_table("tariff_rate_overrides")
    op.drop_table("calculations")
    op.drop_table("rate_snapshots")
    op.drop_table("shipment_items")
    op.drop_table("shipment_costs")
    op.drop_table("shipments")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS providertype")
    op.execute("DROP TYPE IF EXISTS shipmentstatus")
    op.execute("DROP TYPE IF EXISTS incoterm")
    op.execute("DROP TYPE IF EXISTS direction")
