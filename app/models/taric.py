from __future__ import annotations

import uuid
from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TaricSnapshot(Base):
    __tablename__ = "taric_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_date: Mapped[Date] = mapped_column(Date, nullable=False)
    source_label: Mapped[str] = mapped_column(String(64), nullable=False)
    imported_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    files_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_taric_snapshot_date", "snapshot_date"),
        Index("ux_taric_snapshot_hash", "snapshot_date", "files_hash", unique=True),
    )


class GoodsNomenclature(Base):
    __tablename__ = "goods_nomenclature"

    goods_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    parent_goods_code: Mapped[str | None] = mapped_column(String(16))
    level: Mapped[int | None] = mapped_column(Integer)
    suffix: Mapped[str | None] = mapped_column(String(8))
    valid_from: Mapped[Date | None] = mapped_column(Date)
    valid_to: Mapped[Date | None] = mapped_column(Date)
    source_record_id: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        Index("ix_goods_nomenclature_code_valid", "goods_code", "valid_from", "valid_to"),
    )


class GoodsDescription(Base):
    __tablename__ = "goods_description"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goods_code: Mapped[str] = mapped_column(String(16), nullable=False)
    lang: Mapped[str] = mapped_column(String(2), nullable=False, default="EN")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[Date | None] = mapped_column(Date)
    valid_to: Mapped[Date | None] = mapped_column(Date)

    __table_args__ = (
        Index("ix_goods_description_code_valid", "goods_code", "valid_from", "valid_to"),
    )


class GeoArea(Base):
    __tablename__ = "geo_area"

    geo_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    type: Mapped[str | None] = mapped_column(String(16))
    description: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[Date | None] = mapped_column(Date)
    valid_to: Mapped[Date | None] = mapped_column(Date)


class GeoAreaMember(Base):
    __tablename__ = "geo_area_member"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_geo_code: Mapped[str] = mapped_column(String(16), nullable=False)
    member_geo_code: Mapped[str] = mapped_column(String(16), nullable=False)
    valid_from: Mapped[Date | None] = mapped_column(Date)
    valid_to: Mapped[Date | None] = mapped_column(Date)

    __table_args__ = (
        Index("ix_geo_area_member_group", "group_geo_code", "member_geo_code"),
    )


class Measure(Base):
    __tablename__ = "measure"

    measure_uid: Mapped[str] = mapped_column(String(64), primary_key=True)
    goods_code: Mapped[str] = mapped_column(String(16), nullable=False)
    measure_type_code: Mapped[str] = mapped_column(String(16), nullable=False)
    geo_code: Mapped[str] = mapped_column(String(16), nullable=False)
    regulation_ref: Mapped[str | None] = mapped_column(String(64))
    valid_from: Mapped[Date | None] = mapped_column(Date)
    valid_to: Mapped[Date | None] = mapped_column(Date)
    raw_payload_json: Mapped[dict | None] = mapped_column(JSONB)
    orphan_goods_code: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        Index("ix_measure_goods_date", "goods_code", "valid_from", "valid_to"),
        Index("ix_measure_geo", "geo_code"),
    )


class DutyExpression(Base):
    __tablename__ = "duty_expression"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expression_text: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(3))
    uom: Mapped[str | None] = mapped_column(String(16))
    valid_from: Mapped[Date | None] = mapped_column(Date)
    valid_to: Mapped[Date | None] = mapped_column(Date)


class MeasureDutyExpression(Base):
    __tablename__ = "measure_duty_expression"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    measure_uid: Mapped[str] = mapped_column(String(64), ForeignKey("measure.measure_uid"), nullable=False)
    expression_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("duty_expression.id"))
    expression_text: Mapped[str | None] = mapped_column(String(255))
    seq_no: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (Index("ix_measure_duty_measure", "measure_uid"),)


class AdditionalCode(Base):
    __tablename__ = "additional_code"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_type: Mapped[str] = mapped_column(String(8), nullable=False)
    code: Mapped[str] = mapped_column(String(8), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[Date | None] = mapped_column(Date)
    valid_to: Mapped[Date | None] = mapped_column(Date)

    __table_args__ = (Index("ix_additional_code", "code_type", "code", "valid_from", "valid_to"),)


class MeasureAdditionalCode(Base):
    __tablename__ = "measure_additional_code"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    measure_uid: Mapped[str] = mapped_column(String(64), ForeignKey("measure.measure_uid"), nullable=False)
    additional_code_type: Mapped[str] = mapped_column(String(8), nullable=False)
    additional_code: Mapped[str] = mapped_column(String(8), nullable=False)


class MeasureCondition(Base):
    __tablename__ = "measure_condition"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    measure_uid: Mapped[str] = mapped_column(String(64), ForeignKey("measure.measure_uid"), nullable=False)
    condition_code: Mapped[str | None] = mapped_column(String(8))
    action_code: Mapped[str | None] = mapped_column(String(8))
    certificate_type_code: Mapped[str | None] = mapped_column(String(8))
    valid_from: Mapped[Date | None] = mapped_column(Date)
    valid_to: Mapped[Date | None] = mapped_column(Date)


class Regulation(Base):
    __tablename__ = "regulation"

    regulation_ref: Mapped[str] = mapped_column(String(64), primary_key=True)
    published_date: Mapped[Date | None] = mapped_column(Date)
    valid_from: Mapped[Date | None] = mapped_column(Date)
    valid_to: Mapped[Date | None] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(Text)


class TaricResolvedCache(Base):
    __tablename__ = "taric_resolved_cache"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_date: Mapped[Date] = mapped_column(Date, nullable=False)
    goods_code: Mapped[str] = mapped_column(String(16), nullable=False)
    origin_country: Mapped[str] = mapped_column(String(16), nullable=False)
    as_of_date: Mapped[Date] = mapped_column(Date, nullable=False)
    additional_code: Mapped[str | None] = mapped_column(String(8))
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_taric_resolved_cache_key", "snapshot_date", "goods_code", "origin_country", "as_of_date", "additional_code", unique=True),
    )
