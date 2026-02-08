from __future__ import annotations

import uuid
from decimal import Decimal
from sqlalchemy import Date, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TariffRateOverride(Base):
    __tablename__ = "tariff_rate_overrides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_region: Mapped[str] = mapped_column(String(8), nullable=False)
    commodity_code: Mapped[str] = mapped_column(String(16), nullable=False)
    origin_country: Mapped[str | None] = mapped_column(String(2))
    preference_flag: Mapped[bool] = mapped_column(default=False)
    duty_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VatRate(Base):
    __tablename__ = "vat_rates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    rate_type: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EuTaricRate(Base):
    __tablename__ = "eu_taric_rates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hs_code: Mapped[str] = mapped_column(String(16), nullable=False)
    origin_country: Mapped[str | None] = mapped_column(String(2))
    preference_flag: Mapped[bool] = mapped_column(default=False)
    duty_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FxRateDaily(Base):
    __tablename__ = "fx_rates_daily"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base: Mapped[str] = mapped_column(String(3), nullable=False)
    quote: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    rate_date: Mapped[Date] = mapped_column(Date, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
