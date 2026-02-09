from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class License(Base):
    __tablename__ = "licenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    license_type: Mapped[str] = mapped_column(String(64), nullable=False)
    license_number: Mapped[str | None] = mapped_column(String(64))
    issuer: Mapped[str | None] = mapped_column(String(255))
    expires_on: Mapped[date | None] = mapped_column(Date)

    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)

    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    shipments = relationship("ShipmentLicense", back_populates="license", cascade="all, delete-orphan")


class ShipmentLicense(Base):
    __tablename__ = "shipment_licenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=False)
    license_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("licenses.id"), nullable=False)

    license = relationship("License", back_populates="shipments")
