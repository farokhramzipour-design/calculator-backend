from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel


class FxRateResponse(BaseModel):
    base: str
    quote: str
    rate: Decimal | None
    source: str


class VatRateResponse(BaseModel):
    country: str
    rate: Decimal | None
    source: str


class TariffRateResponse(BaseModel):
    code: str
    rate: Decimal | None
    source: str
    is_estimated: bool
