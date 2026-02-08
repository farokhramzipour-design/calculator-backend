from __future__ import annotations

import uuid
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ShipmentItem(Base):
    __tablename__ = "shipment_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=False)

    description: Mapped[str] = mapped_column(String(255), nullable=False)
    hs_code: Mapped[str] = mapped_column(String(16), nullable=False)
    origin_country: Mapped[str] = mapped_column(String(2), nullable=False)
    additional_code: Mapped[str | None] = mapped_column(String(8))

    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    goods_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    weight_net_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    shipment = relationship("Shipment", back_populates="items")
