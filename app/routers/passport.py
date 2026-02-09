from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_session
from app.models.passport import PassportItem
from app.schemas.passport import PassportItemCreate, PassportItemRead, PassportItemUpdate

router = APIRouter(prefix="/passport", tags=["passport"])


@router.post("", response_model=PassportItemRead)
async def create_item(
    payload: PassportItemCreate,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    item = PassportItem(user_id=user.id, **payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("", response_model=list[PassportItemRead])
async def list_items(user=Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(PassportItem).where(PassportItem.user_id == user.id))
    return list(result.scalars().all())


@router.get("/{item_id}", response_model=PassportItemRead)
async def get_item(item_id: uuid.UUID, user=Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(
        select(PassportItem).where(PassportItem.id == item_id, PassportItem.user_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport item not found")
    return item


@router.patch("/{item_id}", response_model=PassportItemRead)
async def update_item(
    item_id: uuid.UUID,
    payload: PassportItemUpdate,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(PassportItem).where(PassportItem.id == item_id, PassportItem.user_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport item not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    await session.commit()
    await session.refresh(item)
    return item


@router.delete("/{item_id}")
async def delete_item(item_id: uuid.UUID, user=Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(
        select(PassportItem).where(PassportItem.id == item_id, PassportItem.user_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport item not found")
    await session.delete(item)
    await session.commit()
    return {"status": "ok"}
