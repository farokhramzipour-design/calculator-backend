from __future__ import annotations

import uuid
from datetime import date
from pydantic import BaseModel

from app.schemas.common import BaseSchema


class LicenseRead(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    license_type: str
    license_number: str | None
    issuer: str | None
    expires_on: date | None
    file_type: str
    notes: str | None


class LicenseAssignRequest(BaseModel):
    license_id: uuid.UUID


class LicenseBulkAssignRequest(BaseModel):
    license_ids: list[uuid.UUID]
