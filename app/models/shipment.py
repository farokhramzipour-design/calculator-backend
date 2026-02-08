from __future__ import annotations

import uuid
from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Direction, Incoterm, ShipmentStatus


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(\"users.id\"), nullable=False)

    direction: Mapped[Direction] = mapped_column(Enum(Direction), nullable=False)
    destination_country: Mapped[str | None] = mapped_column(String(2))
    origin_country_default: Mapped[str] = mapped_column(String(2), nullable=False)
    incoterm: Mapped[Incoterm] = mapped_column(Enum(Incoterm), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    import_date: Mapped[Date | None] = mapped_column(Date)
    fx_rate_to_gbp: Mapped[str | None] = mapped_column(String(32))
    fx_rate_to_eur: Mapped[str | None] = mapped_column(String(32))

    status: Mapped[ShipmentStatus] = mapped_column(Enum(ShipmentStatus), nullable=False, default=ShipmentStatus.DRAFT)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="shipments")
    costs = relationship("ShipmentCosts", back_populates="shipment", uselist=False)
    items = relationship("ShipmentItem", back_populates="shipment")
    calculation = relationship("Calculation", back_populates="shipment", uselist=False)
