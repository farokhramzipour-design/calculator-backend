from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class CalculationResponse(BaseModel):
    status: str
    required_fields: list[str] = Field(default_factory=list)
    message: str | None = None
    breakdown: dict[str, Any] | None = None
    per_item: list[dict[str, Any]] | None = None
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
