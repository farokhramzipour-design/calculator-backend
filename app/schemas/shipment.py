from __future__ import annotations

from datetime import date
from decimal import Decimal
import uuid
from pydantic import BaseModel, Field, field_validator

from app.models.enums import Direction, Incoterm, ShipmentStatus
from app.schemas.common import BaseSchema


class ShipmentCreate(BaseModel):
    direction: Direction
    destination_country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    origin_country_default: str = Field(pattern=r"^[A-Z]{2}$")
    incoterm: Incoterm
    currency: str = Field(min_length=3, max_length=3)
    import_date: str | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str):
        return value.upper() if isinstance(value, str) else value

    @field_validator("destination_country", "origin_country_default", mode="before")
    @classmethod
    def normalize_country(cls, value: str | None):
        return value.upper() if isinstance(value, str) else value


class ShipmentUpdate(BaseModel):
    destination_country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    origin_country_default: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    incoterm: Incoterm | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    status: ShipmentStatus | None = None
    import_date: str | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str | None):
        return value.upper() if isinstance(value, str) else value

    @field_validator("destination_country", "origin_country_default", mode="before")
    @classmethod
    def normalize_country(cls, value: str | None):
        return value.upper() if isinstance(value, str) else value


class ShipmentRead(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    direction: Direction
    destination_country: str | None
    origin_country_default: str
    incoterm: Incoterm
    currency: str
    fx_rate_to_gbp: str | None
    fx_rate_to_eur: str | None
    import_date: date | None
    status: ShipmentStatus


class ShipmentList(BaseModel):
    shipments: list[ShipmentRead]


class ShipmentCostsUpdate(BaseModel):
    freight_amount: Decimal | None = Field(default=None, ge=0)
    insurance_amount: Decimal | None = Field(default=None, ge=0)
    brokerage_amount: Decimal | None = Field(default=None, ge=0)
    port_fees_amount: Decimal | None = Field(default=None, ge=0)
    inland_transport_amount: Decimal | None = Field(default=None, ge=0)
    other_incidental_amount: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None


class ShipmentCostsRead(BaseSchema):
    shipment_id: uuid.UUID
    freight_amount: Decimal | None
    insurance_amount: Decimal | None
    insurance_is_estimated: bool
    brokerage_amount: Decimal | None
    port_fees_amount: Decimal | None
    inland_transport_amount: Decimal | None
    other_incidental_amount: Decimal | None
    notes: str | None


class ShipmentItemCreate(BaseModel):
    description: str
    hs_code: str
    origin_country: str = Field(pattern=r"^[A-Z]{2}$")
    additional_code: str | None = None
    passport_item_id: str | None = None
    quantity: Decimal = Field(ge=0)
    unit_price: Decimal = Field(ge=0)
    goods_value: Decimal | None = Field(default=None, ge=0)
    weight_net_kg: Decimal | None = Field(default=None, ge=0)

    @field_validator("origin_country", mode="before")
    @classmethod
    def normalize_origin_country(cls, value: str):
        return value.upper() if isinstance(value, str) else value

    @field_validator("hs_code", mode="before")
    @classmethod
    def normalize_hs_code(cls, value: str):
        if not isinstance(value, str):
            return value
        return "".join(ch for ch in value if ch.isdigit())


class ShipmentItemUpdate(BaseModel):
    description: str | None = None
    hs_code: str | None = None
    origin_country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    additional_code: str | None = None
    passport_item_id: str | None = None
    quantity: Decimal | None = Field(default=None, ge=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    goods_value: Decimal | None = Field(default=None, ge=0)
    weight_net_kg: Decimal | None = Field(default=None, ge=0)

    @field_validator("origin_country", mode="before")
    @classmethod
    def normalize_origin_country(cls, value: str | None):
        return value.upper() if isinstance(value, str) else value

    @field_validator("hs_code", mode="before")
    @classmethod
    def normalize_hs_code(cls, value: str | None):
        if not isinstance(value, str):
            return value
        return "".join(ch for ch in value if ch.isdigit())


import uuid


class ShipmentItemRead(BaseSchema):
    id: uuid.UUID
    shipment_id: uuid.UUID
    description: str
    hs_code: str
    origin_country: str
    passport_item_id: str | None
    additional_code: str | None
    quantity: Decimal
    unit_price: Decimal
    goods_value: Decimal | None
    weight_net_kg: Decimal | None


class ShipmentDetail(BaseSchema):
    id: uuid.UUID
    items: list[ShipmentItemRead] = Field(default_factory=list)
    costs: ShipmentCostsRead | None = None
    direction: Direction
    destination_country: str | None
    origin_country_default: str
    incoterm: Incoterm
    currency: str
    status: ShipmentStatus
    import_date: date | None
