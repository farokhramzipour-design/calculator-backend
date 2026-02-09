from __future__ import annotations

import uuid
from pydantic import BaseModel

from app.schemas.common import BaseSchema


class CountryRead(BaseSchema):
    id: uuid.UUID
    code: str
    name: str
    region: str


class CountryList(BaseModel):
    countries: list[CountryRead]
