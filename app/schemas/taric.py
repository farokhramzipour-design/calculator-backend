from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from app.services.taric_resolver import ResolvedTaricResult


class TaricGoodsResponse(BaseModel):
    goods_code: str
    valid: bool
    description: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class TaricDutyComponent(BaseModel):
    measure_uid: str
    measure_type_code: str
    expression: str
    kind: str
    rate: Decimal | None
    uom: str | None
    requires_additional_code: bool


class TaricResolveResponse(BaseModel):
    goods_code: str
    matched_goods_code: str | None
    duties: list[TaricDutyComponent]
    requirements: list[dict[str, Any]]
    legal_refs: list[str]
    effective_duty_rate: Decimal | None
    notes: list[str]

    @classmethod
    def from_result(cls, result: ResolvedTaricResult) -> "TaricResolveResponse":
        return cls(
            goods_code=result.goods_code,
            matched_goods_code=result.matched_goods_code,
            duties=[TaricDutyComponent(**d.__dict__) for d in result.duties],
            requirements=result.requirements,
            legal_refs=result.legal_refs,
            effective_duty_rate=result.effective_duty_rate,
            notes=result.notes,
        )
