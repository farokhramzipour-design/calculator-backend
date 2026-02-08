from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class DutyRateResult:
    rate: Decimal | None
    source: str
    is_estimated: bool
    missing: bool
    raw_payload: dict | None = None


@dataclass
class FxRateResult:
    rate: Decimal | None
    source: str
    rate_date: str | None
    raw_payload: dict | None = None


@dataclass
class VatRateResult:
    rate: Decimal | None
    source: str
    raw_payload: dict | None = None
