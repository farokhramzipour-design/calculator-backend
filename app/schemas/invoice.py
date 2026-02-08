from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema

from app.models.invoice import InvoiceStatus


class InvoiceItemRead(BaseSchema):
    id: uuid.UUID
    description: str
    hs_code: str | None
    origin_country: str | None
    quantity: Decimal | None
    unit_price: Decimal | None
    total_price: Decimal | None


class InvoiceRead(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    shipment_id: uuid.UUID | None
    file_type: str
    invoice_number: str | None
    invoice_date: date | None
    supplier_name: str | None
    buyer_name: str | None
    currency: str | None
    subtotal: Decimal | None
    freight: Decimal | None
    insurance: Decimal | None
    tax_total: Decimal | None
    total: Decimal | None
    status: InvoiceStatus
    items: list[InvoiceItemRead] = Field(default_factory=list)


class InvoiceAssignRequest(BaseModel):
    invoice_id: uuid.UUID


class InvoiceReviewUpdate(BaseModel):
    status: InvoiceStatus
