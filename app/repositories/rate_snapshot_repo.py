from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rate_snapshot import RateSnapshot
from app.models.enums import ProviderType


class RateSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_valid_snapshot(self, shipment_id, provider: ProviderType, request_key: dict) -> RateSnapshot | None:
        result = await self.session.execute(
            select(RateSnapshot)
            .where(
                RateSnapshot.shipment_id == shipment_id,
                RateSnapshot.provider == provider,
                RateSnapshot.request_key == request_key,
            )
            .order_by(RateSnapshot.fetched_at.desc())
        )
        snapshot = result.scalar_one_or_none()
        if not snapshot:
            return None
        expires_at = snapshot.fetched_at + timedelta(seconds=snapshot.ttl_seconds)
        if expires_at < datetime.now(timezone.utc):
            return None
        return snapshot

    async def create(self, snapshot: RateSnapshot) -> RateSnapshot:
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        return snapshot
