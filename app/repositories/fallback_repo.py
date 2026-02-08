from __future__ import annotations

from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fallback_tables import EuTaricRate, FxRateDaily, TariffRateOverride, VatRate


class TariffOverrideRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_rate(
        self,
        destination_region: str,
        commodity_code: str,
        origin_country: str | None,
        preference_flag: bool,
    ) -> TariffRateOverride | None:
        result = await self.session.execute(
            select(TariffRateOverride).where(
                TariffRateOverride.destination_region == destination_region,
                TariffRateOverride.commodity_code == commodity_code,
                TariffRateOverride.origin_country == origin_country,
                TariffRateOverride.preference_flag == preference_flag,
            )
        )
        return result.scalar_one_or_none()


class VatRateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_standard_rate(self, country: str) -> VatRate | None:
        result = await self.session.execute(
            select(VatRate).where(VatRate.country == country, VatRate.rate_type == "standard")
        )
        return result.scalar_one_or_none()


class EuTaricRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_rate(self, hs_code: str, origin_country: str | None, preference_flag: bool) -> EuTaricRate | None:
        result = await self.session.execute(
            select(EuTaricRate).where(
                EuTaricRate.hs_code == hs_code,
                EuTaricRate.origin_country == origin_country,
                EuTaricRate.preference_flag == preference_flag,
            )
        )
        return result.scalar_one_or_none()


class FxRateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_rate(self, base: str, quote: str, rate_date: date) -> FxRateDaily | None:
        result = await self.session.execute(
            select(FxRateDaily).where(
                FxRateDaily.base == base,
                FxRateDaily.quote == quote,
                FxRateDaily.rate_date == rate_date,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, rate: FxRateDaily) -> FxRateDaily:
        self.session.add(rate)
        await self.session.commit()
        await self.session.refresh(rate)
        return rate
