from __future__ import annotations

from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Calculation(Base):
    __tablename__ = "calculations"

    shipment_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shipments.id"), primary_key=True)

    customs_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    duty_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    vat_base: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    vat_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    other_duties_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    authorities_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    landed_cost_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    landed_cost_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    assumptions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    calculated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)

    shipment = relationship("Shipment", back_populates="calculation")
