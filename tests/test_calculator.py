import asyncio
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.enums import Direction, Incoterm, ShipmentStatus
from app.models.shipment_costs import ShipmentCosts
from app.services.calculator import CalculatorService
from app.services.taric_resolver import DutyComponent, ResolvedTaricResult
from app.services.providers.types import DutyRateResult, FxRateResult, VatRateResult


class FakeSession:
    def __init__(self) -> None:
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None

    async def merge(self, obj):
        self.add(obj)
        return obj


class FakeShipmentRepo:
    def __init__(self, shipment):
        self.shipment = shipment

    async def get(self, shipment_id, user_id):
        return self.shipment

    async def update(self, shipment):
        return shipment


@pytest.mark.asyncio
async def test_exw_missing_freight_insurance_needs_input():
    shipment = SimpleNamespace(
        id="s1",
        user_id="u1",
        direction=Direction.IMPORT_UK,
        destination_country=None,
        origin_country_default="CN",
        incoterm=Incoterm.EXW,
        currency="USD",
        import_date=None,
        fx_rate_to_gbp=None,
        fx_rate_to_eur=None,
        status=ShipmentStatus.DRAFT,
        items=[],
        costs=ShipmentCosts(shipment_id="s1"),
    )

    service = CalculatorService(FakeSession())
    service.shipment_repo = FakeShipmentRepo(shipment)

    result = await service.calculate("s1", "u1")
    assert result.status == "needs_input"
    assert "freight_amount" in result.required_fields
    assert "insurance_amount" in result.required_fields


@pytest.mark.asyncio
async def test_cif_full_data_calculates():
    item = SimpleNamespace(
        id="i1",
        hs_code="0101",
        origin_country="CN",
        quantity=Decimal("10"),
        unit_price=Decimal("100"),
        goods_value=None,
    )
    shipment = SimpleNamespace(
        id="s2",
        user_id="u1",
        direction=Direction.IMPORT_UK,
        destination_country=None,
        origin_country_default="CN",
        incoterm=Incoterm.CIF,
        currency="USD",
        import_date=None,
        fx_rate_to_gbp=None,
        fx_rate_to_eur=None,
        status=ShipmentStatus.DRAFT,
        items=[item],
        costs=ShipmentCosts(
            shipment_id="s2",
            freight_amount=Decimal("50"),
            insurance_amount=Decimal("10"),
            insurance_is_estimated=False,
            brokerage_amount=Decimal("5"),
            port_fees_amount=Decimal("0"),
            inland_transport_amount=Decimal("0"),
            other_incidental_amount=Decimal("0"),
        ),
    )

    service = CalculatorService(FakeSession())
    service.shipment_repo = FakeShipmentRepo(shipment)

    async def duty_rate(*args, **kwargs):
        return DutyRateResult(rate=Decimal("0.1"), source="test", is_estimated=False, missing=False)

    async def vat_rate(*args, **kwargs):
        return VatRateResult(rate=Decimal("0.2"), source="test")

    async def fx_rate(*args, **kwargs):
        return FxRateResult(rate=Decimal("0.8"), source="test", rate_date=None)

    service._get_duty_rate = duty_rate
    service._get_vat_rate = vat_rate
    service._ensure_fx_rate = fx_rate

    result = await service.calculate("s2", "u1")
    assert result.status == "ok"
    assert Decimal(result.breakdown["customs_value"]) == Decimal("848.0000")
    assert Decimal(result.breakdown["duty_total"]) == Decimal("84.8000")
    assert Decimal(result.breakdown["vat_total"]) > 0


@pytest.mark.asyncio
async def test_multi_item_different_rates():
    item1 = SimpleNamespace(
        id="i1",
        hs_code="0101",
        origin_country="CN",
        quantity=Decimal("5"),
        unit_price=Decimal("100"),
        goods_value=None,
    )
    item2 = SimpleNamespace(
        id="i2",
        hs_code="0202",
        origin_country="US",
        quantity=Decimal("5"),
        unit_price=Decimal("200"),
        goods_value=None,
    )
    shipment = SimpleNamespace(
        id="s3",
        user_id="u1",
        direction=Direction.IMPORT_EU,
        destination_country="FR",
        origin_country_default="CN",
        incoterm=Incoterm.CIF,
        currency="EUR",
        import_date=None,
        fx_rate_to_gbp=None,
        fx_rate_to_eur=None,
        status=ShipmentStatus.DRAFT,
        items=[item1, item2],
        costs=ShipmentCosts(
            shipment_id="s3",
            freight_amount=Decimal("100"),
            insurance_amount=Decimal("20"),
            insurance_is_estimated=False,
            brokerage_amount=Decimal("0"),
            port_fees_amount=Decimal("0"),
            inland_transport_amount=Decimal("0"),
            other_incidental_amount=Decimal("0"),
        ),
    )

    service = CalculatorService(FakeSession())
    service.shipment_repo = FakeShipmentRepo(shipment)

    async def resolve_taric(goods_code, origin_country_code, as_of, additional_code=None, snapshot_date=None):
        if goods_code == "0101":
            duties = [DutyComponent("m1", "103", "5%", "ad_valorem", Decimal("0.05"), None)]
            return ResolvedTaricResult(goods_code, goods_code, duties, [], [], Decimal("0.05"), [])
        duties = [DutyComponent("m2", "103", "20%", "ad_valorem", Decimal("0.2"), None)]
        return ResolvedTaricResult(goods_code, goods_code, duties, [], [], Decimal("0.2"), [])

    async def vat_rate(*args, **kwargs):
        return VatRateResult(rate=Decimal("0.2"), source="test")

    async def fx_rate(*args, **kwargs):
        return FxRateResult(rate=Decimal("1"), source="test", rate_date=None)

    service.taric_resolver.resolve_taric = resolve_taric
    service._get_vat_rate = vat_rate
    service._ensure_fx_rate = fx_rate

    result = await service.calculate("s3", "u1")
    assert result.status == "ok"
    per_item = {item["hs_code"]: Decimal(item["duty_amount"]) for item in result.per_item}
    assert per_item["0101"] > 0
    assert per_item["0202"] > per_item["0101"]
