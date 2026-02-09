from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PassportItem(Base):
    __tablename__ = "passport_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    hs_code: Mapped[str | None] = mapped_column(String(16))
    supplier: Mapped[str | None] = mapped_column(String(255))
    weight_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    weight: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    invoice_items = relationship("InvoiceItem", back_populates="passport_item")
    shipment_items = relationship("ShipmentItem", back_populates="passport_item")
