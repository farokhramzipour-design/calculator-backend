from __future__ import annotations

import uuid
from decimal import Decimal
from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class PassportItemCreate(BaseModel):
    name: str
    description: str | None = None
    hs_code: str | None = None
    supplier: str | None = None
    weight_per_unit: Decimal | None = None
    notes: str | None = None


class PassportItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    hs_code: str | None = None
    supplier: str | None = None
    weight_per_unit: Decimal | None = None
    notes: str | None = None


class PassportItemRead(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str | None
    hs_code: str | None
    supplier: str | None
    weight_per_unit: Decimal | None
    notes: str | None
