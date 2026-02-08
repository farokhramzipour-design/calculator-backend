from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.taric_resolver import DutyComponent, ResolvedTaricResult, TaricResolver


class FakeTaricRepo:
    def __init__(self):
        self.snapshot_date = date(2025, 1, 1)
        self.goods = {}
        self.measures = {}
        self.geo_members = set()
        self.duty_expr = {}

    async def get_latest_snapshot_date(self):
        return self.snapshot_date

    async def get_cached(self, *args, **kwargs):
        return None

    async def upsert_cache(self, cache):
        return cache

    async def get_goods_candidates(self, codes, as_of):
        return [self.goods[c] for c in codes if c in self.goods]

    async def get_measures(self, goods_codes, as_of):
        results = []
        for code in goods_codes:
            results.extend(self.measures.get(code, []))
        return results

    async def geo_applies(self, geo_code, origin, as_of):
        if geo_code == "ERGA_OMNES" or geo_code == origin:
            return True
        return (geo_code, origin) in self.geo_members

    async def get_measure_duty_expressions(self, measure_uids):
        return [
            SimpleNamespace(measure_uid=uid, expression_text=self.duty_expr.get(uid), expression_id=None)
            for uid in measure_uids
            if uid in self.duty_expr
        ]

    async def get_duty_expressions(self, expression_ids):
        return []

    async def get_measure_additional_codes(self, measure_uids):
        return []

    async def get_measure_conditions(self, measure_uids):
        return []

    async def get_regulations(self, refs):
        return []


@pytest.mark.asyncio
async def test_resolver_hierarchy_inheritance():
    repo = FakeTaricRepo()
    repo.goods["1234"] = SimpleNamespace(goods_code="1234")
    repo.measures["1234"] = [
        SimpleNamespace(measure_uid="m1", goods_code="1234", measure_type_code="103", geo_code="ERGA_OMNES", regulation_ref=None)
    ]
    repo.duty_expr["m1"] = "5%"

    resolver = TaricResolver(repo)
    result = await resolver.resolve_taric("1234567890", "CN", date(2025, 1, 2))
    assert result.matched_goods_code == "1234"
    assert result.effective_duty_rate == Decimal("0.05")


@pytest.mark.asyncio
async def test_resolver_geo_membership():
    repo = FakeTaricRepo()
    repo.goods["0101"] = SimpleNamespace(goods_code="0101")
    repo.measures["0101"] = [
        SimpleNamespace(measure_uid="m2", goods_code="0101", measure_type_code="103", geo_code="GRP1", regulation_ref=None)
    ]
    repo.duty_expr["m2"] = "10%"
    repo.geo_members.add(("GRP1", "CN"))

    resolver = TaricResolver(repo)
    result = await resolver.resolve_taric("0101", "CN", date(2025, 1, 2))
    assert result.effective_duty_rate == Decimal("0.1")
