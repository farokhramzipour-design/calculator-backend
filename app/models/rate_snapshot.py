from __future__ import annotations

import uuid
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ProviderType


class RateSnapshot(Base):
    __tablename__ = "rate_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=False)

    provider: Mapped[ProviderType] = mapped_column(Enum(ProviderType), nullable=False)
    request_key: Mapped[dict] = mapped_column(JSONB, nullable=False)
    response_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
