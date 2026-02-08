from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from enum import Enum

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InvoiceStatus(str, Enum):
    UPLOADED = "UPLOADED"
    EXTRACTED = "EXTRACTED"
    REVIEWED = "REVIEWED"
    CONFIRMED = "CONFIRMED"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    shipment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shipments.id"))

    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)

    invoice_number: Mapped[str | None] = mapped_column(String(64))
    invoice_date: Mapped[date | None] = mapped_column(Date)
    supplier_name: Mapped[str | None] = mapped_column(String(255))
    buyer_name: Mapped[str | None] = mapped_column(String(255))
    currency: Mapped[str | None] = mapped_column(String(3))

    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    freight: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    insurance: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    tax_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    total: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))

    extracted_payload: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[InvoiceStatus] = mapped_column(SAEnum(InvoiceStatus), default=InvoiceStatus.UPLOADED, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)

    description: Mapped[str] = mapped_column(String(255), nullable=False)
    hs_code: Mapped[str | None] = mapped_column(String(16))
    origin_country: Mapped[str | None] = mapped_column(String(2))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))

    invoice = relationship("Invoice", back_populates="items")
