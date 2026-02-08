from __future__ import annotations

from decimal import Decimal
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ShipmentCosts(Base):
    __tablename__ = "shipment_costs"

    shipment_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shipments.id"), primary_key=True)

    freight_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    insurance_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    insurance_is_estimated: Mapped[bool] = mapped_column(Boolean, default=False)
    brokerage_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    port_fees_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    inland_transport_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    other_incidental_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    notes: Mapped[str | None] = mapped_column(String(1024))

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    shipment = relationship("Shipment", back_populates="costs")
