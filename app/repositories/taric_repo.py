from __future__ import annotations

from datetime import date
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.taric import (
    AdditionalCode,
    DutyExpression,
    GeoArea,
    GeoAreaMember,
    GoodsDescription,
    GoodsNomenclature,
    Measure,
    MeasureAdditionalCode,
    MeasureCondition,
    MeasureDutyExpression,
    Regulation,
    TaricResolvedCache,
    TaricSnapshot,
)


class TaricRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_latest_snapshot_date(self) -> date | None:
        result = await self.session.execute(
            select(TaricSnapshot.snapshot_date).order_by(TaricSnapshot.snapshot_date.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_snapshot(self, snapshot_date: date) -> TaricSnapshot | None:
        result = await self.session.execute(
            select(TaricSnapshot).where(TaricSnapshot.snapshot_date == snapshot_date)
        )
        return result.scalar_one_or_none()

    async def get_goods_candidates(self, codes: list[str], as_of: date) -> list[GoodsNomenclature]:
        result = await self.session.execute(
            select(GoodsNomenclature).where(
                GoodsNomenclature.goods_code.in_(codes),
                self._valid_on(GoodsNomenclature.valid_from, GoodsNomenclature.valid_to, as_of),
            )
        )
        return list(result.scalars().all())

    async def get_goods_description(self, goods_code: str, as_of: date, lang: str = "EN") -> GoodsDescription | None:
        result = await self.session.execute(
            select(GoodsDescription).where(
                GoodsDescription.goods_code == goods_code,
                GoodsDescription.lang == lang,
                self._valid_on(GoodsDescription.valid_from, GoodsDescription.valid_to, as_of),
            )
        )
        return result.scalar_one_or_none()

    async def get_measures(self, goods_codes: list[str], as_of: date) -> list[Measure]:
        result = await self.session.execute(
            select(Measure).where(
                Measure.goods_code.in_(goods_codes),
                self._valid_on(Measure.valid_from, Measure.valid_to, as_of),
            )
        )
        return list(result.scalars().all())

    async def geo_applies(self, geo_code: str, origin: str, as_of: date) -> bool:
        if geo_code == origin or geo_code == "ERGA_OMNES":
            return True
        result = await self.session.execute(
            select(GeoAreaMember).where(
                GeoAreaMember.group_geo_code == geo_code,
                GeoAreaMember.member_geo_code == origin,
                self._valid_on(GeoAreaMember.valid_from, GeoAreaMember.valid_to, as_of),
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_measure_duty_expressions(self, measure_uids: list[str]) -> list[MeasureDutyExpression]:
        if not measure_uids:
            return []
        result = await self.session.execute(
            select(MeasureDutyExpression).where(MeasureDutyExpression.measure_uid.in_(measure_uids))
        )
        return list(result.scalars().all())

    async def get_duty_expressions(self, expression_ids: list[str]) -> list[DutyExpression]:
        if not expression_ids:
            return []
        result = await self.session.execute(select(DutyExpression).where(DutyExpression.id.in_(expression_ids)))
        return list(result.scalars().all())

    async def get_measure_additional_codes(self, measure_uids: list[str]) -> list[MeasureAdditionalCode]:
        if not measure_uids:
            return []
        result = await self.session.execute(
            select(MeasureAdditionalCode).where(MeasureAdditionalCode.measure_uid.in_(measure_uids))
        )
        return list(result.scalars().all())

    async def get_additional_codes(self, codes: list[tuple[str, str]], as_of: date) -> list[AdditionalCode]:
        if not codes:
            return []
        filters = [
            and_(AdditionalCode.code_type == code_type, AdditionalCode.code == code)
            for code_type, code in codes
        ]
        result = await self.session.execute(
            select(AdditionalCode).where(or_(*filters), self._valid_on(AdditionalCode.valid_from, AdditionalCode.valid_to, as_of))
        )
        return list(result.scalars().all())

    async def get_measure_conditions(self, measure_uids: list[str]) -> list[MeasureCondition]:
        if not measure_uids:
            return []
        result = await self.session.execute(
            select(MeasureCondition).where(MeasureCondition.measure_uid.in_(measure_uids))
        )
        return list(result.scalars().all())

    async def get_regulations(self, refs: list[str]) -> list[Regulation]:
        if not refs:
            return []
        result = await self.session.execute(select(Regulation).where(Regulation.regulation_ref.in_(refs)))
        return list(result.scalars().all())

    async def get_cached(self, snapshot_date: date, goods_code: str, origin: str, as_of: date, additional_code: str | None):
        result = await self.session.execute(
            select(TaricResolvedCache).where(
                TaricResolvedCache.snapshot_date == snapshot_date,
                TaricResolvedCache.goods_code == goods_code,
                TaricResolvedCache.origin_country == origin,
                TaricResolvedCache.as_of_date == as_of,
                TaricResolvedCache.additional_code == additional_code,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_cache(self, cache: TaricResolvedCache) -> TaricResolvedCache:
        self.session.add(cache)
        await self.session.commit()
        await self.session.refresh(cache)
        return cache

    def _valid_on(self, from_col, to_col, as_of: date):
        return and_(
            or_(from_col.is_(None), from_col <= as_of),
            or_(to_col.is_(None), to_col >= as_of),
        )
