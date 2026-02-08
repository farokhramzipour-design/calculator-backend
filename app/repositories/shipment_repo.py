from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.shipment import Shipment
from app.models.shipment_costs import ShipmentCosts
from app.models.shipment_item import ShipmentItem


class ShipmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, shipment: Shipment) -> Shipment:
        self.session.add(shipment)
        await self.session.commit()
        await self.session.refresh(shipment)
        return shipment

    async def get(self, shipment_id: str | uuid.UUID, user_id: uuid.UUID) -> Shipment | None:
        value = uuid.UUID(str(shipment_id))
        result = await self.session.execute(
            select(Shipment)
            .where(Shipment.id == value, Shipment.user_id == user_id)
            .options(selectinload(Shipment.items), selectinload(Shipment.costs))
        )
        return result.scalar_one_or_none()

    async def list(self, user_id: uuid.UUID) -> list[Shipment]:
        result = await self.session.execute(select(Shipment).where(Shipment.user_id == user_id))
        return list(result.scalars().all())

    async def delete(self, shipment: Shipment) -> None:
        await self.session.delete(shipment)
        await self.session.commit()

    async def update(self, shipment: Shipment) -> Shipment:
        self.session.add(shipment)
        await self.session.commit()
        await self.session.refresh(shipment)
        return shipment

    async def upsert_costs(self, shipment_id: uuid.UUID, costs: ShipmentCosts) -> ShipmentCosts:
        self.session.add(costs)
        await self.session.commit()
        await self.session.refresh(costs)
        return costs

    async def add_item(self, item: ShipmentItem) -> ShipmentItem:
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def update_item(self, item: ShipmentItem) -> ShipmentItem:
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def delete_item(self, item: ShipmentItem) -> None:
        await self.session.delete(item)
        await self.session.commit()
