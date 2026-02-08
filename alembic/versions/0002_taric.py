from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_taric"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shipments", sa.Column("import_date", sa.Date()))
    op.add_column("shipment_items", sa.Column("additional_code", sa.String(length=8)))

    op.create_table(
        "taric_snapshot",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("source_label", sa.String(length=64), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("files_hash", sa.String(length=128), nullable=False),
        sa.Column("notes", sa.Text()),
    )
    op.create_index("ix_taric_snapshot_date", "taric_snapshot", ["snapshot_date"])
    op.create_index("ux_taric_snapshot_hash", "taric_snapshot", ["snapshot_date", "files_hash"], unique=True)

    op.create_table(
        "goods_nomenclature",
        sa.Column("goods_code", sa.String(length=16), primary_key=True),
        sa.Column("parent_goods_code", sa.String(length=16)),
        sa.Column("level", sa.Integer()),
        sa.Column("suffix", sa.String(length=8)),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.Column("source_record_id", sa.String(length=64)),
    )
    op.create_index("ix_goods_nomenclature_code_valid", "goods_nomenclature", ["goods_code", "valid_from", "valid_to"])

    op.create_table(
        "goods_description",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("goods_code", sa.String(length=16), nullable=False),
        sa.Column("lang", sa.String(length=2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
    )
    op.create_index("ix_goods_description_code_valid", "goods_description", ["goods_code", "valid_from", "valid_to"])

    op.create_table(
        "geo_area",
        sa.Column("geo_code", sa.String(length=16), primary_key=True),
        sa.Column("type", sa.String(length=16)),
        sa.Column("description", sa.Text()),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
    )

    op.create_table(
        "geo_area_member",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_geo_code", sa.String(length=16), nullable=False),
        sa.Column("member_geo_code", sa.String(length=16), nullable=False),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
    )
    op.create_index("ix_geo_area_member_group", "geo_area_member", ["group_geo_code", "member_geo_code"])

    op.create_table(
        "measure",
        sa.Column("measure_uid", sa.String(length=64), primary_key=True),
        sa.Column("goods_code", sa.String(length=16), nullable=False),
        sa.Column("measure_type_code", sa.String(length=16), nullable=False),
        sa.Column("geo_code", sa.String(length=16), nullable=False),
        sa.Column("regulation_ref", sa.String(length=64)),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.Column("raw_payload_json", postgresql.JSONB),
        sa.Column("orphan_goods_code", sa.Boolean(), default=False),
    )
    op.create_index("ix_measure_goods_date", "measure", ["goods_code", "valid_from", "valid_to"])
    op.create_index("ix_measure_geo", "measure", ["geo_code"])

    op.create_table(
        "duty_expression",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("expression_text", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=3)),
        sa.Column("uom", sa.String(length=16)),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
    )

    op.create_table(
        "measure_duty_expression",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("measure_uid", sa.String(length=64), sa.ForeignKey("measure.measure_uid"), nullable=False),
        sa.Column("expression_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("duty_expression.id")),
        sa.Column("expression_text", sa.String(length=255)),
        sa.Column("seq_no", sa.Integer()),
    )
    op.create_index("ix_measure_duty_measure", "measure_duty_expression", ["measure_uid"])

    op.create_table(
        "additional_code",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code_type", sa.String(length=8), nullable=False),
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
    )
    op.create_index("ix_additional_code", "additional_code", ["code_type", "code", "valid_from", "valid_to"])

    op.create_table(
        "measure_additional_code",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("measure_uid", sa.String(length=64), sa.ForeignKey("measure.measure_uid"), nullable=False),
        sa.Column("additional_code_type", sa.String(length=8), nullable=False),
        sa.Column("additional_code", sa.String(length=8), nullable=False),
    )

    op.create_table(
        "measure_condition",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("measure_uid", sa.String(length=64), sa.ForeignKey("measure.measure_uid"), nullable=False),
        sa.Column("condition_code", sa.String(length=8)),
        sa.Column("action_code", sa.String(length=8)),
        sa.Column("certificate_type_code", sa.String(length=8)),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
    )

    op.create_table(
        "regulation",
        sa.Column("regulation_ref", sa.String(length=64), primary_key=True),
        sa.Column("published_date", sa.Date()),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.Column("url", sa.Text()),
    )

    op.create_table(
        "taric_resolved_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("goods_code", sa.String(length=16), nullable=False),
        sa.Column("origin_country", sa.String(length=16), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("additional_code", sa.String(length=8)),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_taric_resolved_cache_key",
        "taric_resolved_cache",
        ["snapshot_date", "goods_code", "origin_country", "as_of_date", "additional_code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_taric_resolved_cache_key", table_name="taric_resolved_cache")
    op.drop_table("taric_resolved_cache")
    op.drop_table("regulation")
    op.drop_table("measure_condition")
    op.drop_table("measure_additional_code")
    op.drop_index("ix_additional_code", table_name="additional_code")
    op.drop_table("additional_code")
    op.drop_index("ix_measure_duty_measure", table_name="measure_duty_expression")
    op.drop_table("measure_duty_expression")
    op.drop_table("duty_expression")
    op.drop_index("ix_measure_geo", table_name="measure")
    op.drop_index("ix_measure_goods_date", table_name="measure")
    op.drop_table("measure")
    op.drop_index("ix_geo_area_member_group", table_name="geo_area_member")
    op.drop_table("geo_area_member")
    op.drop_table("geo_area")
    op.drop_index("ix_goods_description_code_valid", table_name="goods_description")
    op.drop_table("goods_description")
    op.drop_index("ix_goods_nomenclature_code_valid", table_name="goods_nomenclature")
    op.drop_table("goods_nomenclature")
    op.drop_index("ix_taric_snapshot_date", table_name="taric_snapshot")
    op.drop_index("ux_taric_snapshot_hash", table_name="taric_snapshot")
    op.drop_table("taric_snapshot")

    op.drop_column("shipment_items", "additional_code")
    op.drop_column("shipments", "import_date")
