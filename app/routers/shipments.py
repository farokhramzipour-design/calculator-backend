from __future__ import annotations

import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.deps import get_current_user, get_db_session
from app.models.shipment import Shipment
from app.models.shipment_costs import ShipmentCosts
from app.models.shipment_item import ShipmentItem
from app.repositories.shipment_repo import ShipmentRepository
from app.schemas.shipment import (
    ShipmentCreate,
    ShipmentDetail,
    ShipmentItemCreate,
    ShipmentItemRead,
    ShipmentItemUpdate,
    ShipmentList,
    ShipmentRead,
    ShipmentUpdate,
    ShipmentCostsRead,
    ShipmentCostsUpdate,
)

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.post("", response_model=ShipmentRead)
async def create_shipment(
    payload: ShipmentCreate,
    user=Depends(get_current_user),
    session=Depends(get_db_session),
):
    repo = ShipmentRepository(session)
    shipment = Shipment(
        user_id=user.id,
        direction=payload.direction,
        destination_country=payload.destination_country,
        origin_country_default=payload.origin_country_default,
        incoterm=payload.incoterm,
        currency=payload.currency,
        import_date=_parse_date(payload.import_date),
    )
    return await repo.create(shipment)


@router.get("", response_model=ShipmentList)
async def list_shipments(user=Depends(get_current_user), session=Depends(get_db_session)):
    repo = ShipmentRepository(session)
    shipments = await repo.list(user.id)
    return ShipmentList(shipments=shipments)


@router.get("/{shipment_id}", response_model=ShipmentDetail)
async def get_shipment(shipment_id: str, user=Depends(get_current_user), session=Depends(get_db_session)):
    repo = ShipmentRepository(session)
    shipment = await repo.get(shipment_id, user.id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    return shipment


@router.patch("/{shipment_id}", response_model=ShipmentRead)
async def update_shipment(
    shipment_id: str,
    payload: ShipmentUpdate,
    user=Depends(get_current_user),
    session=Depends(get_db_session),
):
    repo = ShipmentRepository(session)
    shipment = await repo.get(shipment_id, user.id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key == "import_date":
            value = _parse_date(value)
        setattr(shipment, key, value)
    return await repo.update(shipment)


@router.delete("/{shipment_id}")
async def delete_shipment(shipment_id: str, user=Depends(get_current_user), session=Depends(get_db_session)):
    repo = ShipmentRepository(session)
    shipment = await repo.get(shipment_id, user.id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    await repo.delete(shipment)
    return {"status": "ok"}


@router.put("/{shipment_id}/costs", response_model=ShipmentCostsRead)
async def upsert_costs(
    shipment_id: str,
    payload: ShipmentCostsUpdate,
    user=Depends(get_current_user),
    session=Depends(get_db_session),
):
    repo = ShipmentRepository(session)
    shipment = await repo.get(shipment_id, user.id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")

    costs = shipment.costs or ShipmentCosts(shipment_id=shipment.id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(costs, key, value)
    if payload.insurance_amount is not None:
        costs.insurance_is_estimated = False
    return await repo.upsert_costs(shipment.id, costs)


@router.get("/{shipment_id}/costs", response_model=ShipmentCostsRead)
async def get_costs(shipment_id: str, user=Depends(get_current_user), session=Depends(get_db_session)):
    repo = ShipmentRepository(session)
    shipment = await repo.get(shipment_id, user.id)
    if not shipment or not shipment.costs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Costs not found")
    return shipment.costs


@router.post("/{shipment_id}/items", response_model=ShipmentItemRead)
async def add_item(
    shipment_id: str,
    payload: ShipmentItemCreate,
    user=Depends(get_current_user),
    session=Depends(get_db_session),
):
    repo = ShipmentRepository(session)
    shipment = await repo.get(shipment_id, user.id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")

    passport_item = None
    if payload.passport_item_id:
        from app.models.passport import PassportItem

        result = await session.execute(
            select(PassportItem).where(
                PassportItem.id == uuid.UUID(payload.passport_item_id), PassportItem.user_id == user.id
            )
        )
        passport_item = result.scalar_one_or_none()
        if not passport_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport item not found")

    item = ShipmentItem(
        shipment_id=uuid.UUID(str(shipment_id)),
        description=payload.description or (passport_item.name if passport_item else ""),
        hs_code=payload.hs_code or (passport_item.hs_code if passport_item else ""),
        origin_country=payload.origin_country,
        additional_code=payload.additional_code,
        passport_item_id=uuid.UUID(payload.passport_item_id) if payload.passport_item_id else None,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        goods_value=payload.goods_value,
        weight_net_kg=payload.weight_net_kg or (passport_item.weight_per_unit if passport_item else None),
    )
    return await repo.add_item(item)


@router.post("/{shipment_id}/items/from-passport", response_model=ShipmentItemRead)
async def add_item_from_passport(
    shipment_id: str,
    passport_item_id: str,
    quantity: Decimal,
    unit_price: Decimal,
    user=Depends(get_current_user),
    session=Depends(get_db_session),
):
    repo = ShipmentRepository(session)
    shipment = await repo.get(shipment_id, user.id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")

    from app.models.passport import PassportItem
    result = await session.execute(
        select(PassportItem).where(PassportItem.id == uuid.UUID(passport_item_id), PassportItem.user_id == user.id)
    )
    passport_item = result.scalar_one_or_none()
    if not passport_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport item not found")

    item = ShipmentItem(
        shipment_id=uuid.UUID(str(shipment_id)),
        passport_item_id=passport_item.id,
        description=passport_item.name,
        hs_code=passport_item.hs_code or "",
        origin_country=shipment.origin_country_default,
        quantity=quantity,
        unit_price=unit_price,
        weight_net_kg=passport_item.weight_per_unit or passport_item.weight,
    )
    return await repo.add_item(item)


def _parse_date(value: str | None):
    if not value:
        return None
    from datetime import date

    return date.fromisoformat(value)


@router.put("/{shipment_id}/items/{item_id}", response_model=ShipmentItemRead)
async def update_item(
    shipment_id: str,
    item_id: str,
    payload: ShipmentItemUpdate,
    user=Depends(get_current_user),
    session=Depends(get_db_session),
):
    repo = ShipmentRepository(session)
    shipment = await repo.get(shipment_id, user.id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    item = next((i for i in shipment.items if str(i.id) == item_id), None)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    data = payload.model_dump(exclude_unset=True)
    passport_item = None
    if "passport_item_id" in data and data["passport_item_id"]:
        from app.models.passport import PassportItem

        result = await session.execute(
            select(PassportItem).where(PassportItem.id == uuid.UUID(data["passport_item_id"]), PassportItem.user_id == user.id)
        )
        passport_item = result.scalar_one_or_none()
        if not passport_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport item not found")

    for key, value in data.items():
        setattr(item, key, value)

    if passport_item:
        if not item.description:
            item.description = passport_item.name
        if not item.hs_code:
            item.hs_code = passport_item.hs_code
        if not item.weight_net_kg:
            item.weight_net_kg = passport_item.weight_per_unit
    return await repo.update_item(item)


@router.delete("/{shipment_id}/items/{item_id}")
async def delete_item(
    shipment_id: str,
    item_id: str,
    user=Depends(get_current_user),
    session=Depends(get_db_session),
):
    repo = ShipmentRepository(session)
    shipment = await repo.get(shipment_id, user.id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    item = next((i for i in shipment.items if str(i.id) == item_id), None)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await repo.delete_item(item)
    return {"status": "ok"}
