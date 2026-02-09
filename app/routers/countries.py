from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db_session
from app.models.country import Country
from app.schemas.country import CountryList

router = APIRouter(prefix="/countries", tags=["countries"])


@router.get("", response_model=CountryList)
async def list_countries(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(Country).order_by(Country.region, Country.name))
    return CountryList(countries=list(result.scalars().all()))
