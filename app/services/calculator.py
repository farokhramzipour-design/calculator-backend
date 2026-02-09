from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calculation import Calculation
from app.models.enums import Direction, Incoterm, ShipmentStatus
from app.models.shipment_costs import ShipmentCosts
from app.repositories.shipment_repo import ShipmentRepository
from app.repositories.taric_repo import TaricRepository
from app.services.providers.eu_taric import EuTaricProvider
from app.services.providers.fx_ecb import FxProvider
from app.services.providers.types import DutyRateResult, FxRateResult, VatRateResult
from app.services.providers.uk_tariff import UkTariffProvider
from app.services.providers.vat import VatRateProvider
from app.services.taric_resolver import ANTI_DUMPING_CODES, TaricResolver

ENGINE_VERSION = "1.0.0"


@dataclass
class CalculationResult:
    status: str
    required_fields: list[str]
    message: str | None
    breakdown: dict[str, Any] | None
    per_item: list[dict[str, Any]] | None
    assumptions: list[str]
    warnings: list[str]


class CalculatorService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.shipment_repo = ShipmentRepository(session)
        self.uk_provider = UkTariffProvider(session)
        self.eu_provider = EuTaricProvider(session)
        self.vat_provider = VatRateProvider(session)
        self.fx_provider = FxProvider(session)
        self.taric_resolver = TaricResolver(TaricRepository(session))

    async def calculate(self, shipment_id, user_id) -> CalculationResult:
        shipment = await self.shipment_repo.get(shipment_id, user_id)
        if not shipment:
            return CalculationResult(
                status="not_found",
                required_fields=[],
                message="Shipment not found",
                breakdown=None,
                per_item=None,
                assumptions=[],
                warnings=[],
            )

        costs = shipment.costs or ShipmentCosts(shipment_id=shipment.id)
        items = shipment.items

        required_fields = []
        message = None
        assumptions: list[str] = []
        warnings: list[str] = []

        if shipment.incoterm in {Incoterm.EXW, Incoterm.FOB}:
            if costs.freight_amount is None:
                required_fields.append("freight_amount")
            if costs.insurance_amount is None:
                required_fields.append("insurance_amount")
            if required_fields:
                message = "Freight and insurance are required for EXW/FOB to compute customs value."
                shipment.status = ShipmentStatus.NEEDS_INPUT
                await self.shipment_repo.update(shipment)
                return CalculationResult(
                    status="needs_input",
                    required_fields=required_fields,
                    message=message,
                    breakdown=None,
                    per_item=None,
                    assumptions=assumptions,
                    warnings=warnings,
                )

        if shipment.incoterm in {Incoterm.CIF, Incoterm.DDP, Incoterm.CFR}:
            assumptions.append("Incoterm implies shipping/insurance included unless overridden.")

        if costs.insurance_amount is None:
            total_goods = self._sum_goods_value(items)
            costs.insurance_amount = (total_goods * Decimal("0.005")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            costs.insurance_is_estimated = True
            assumptions.append("Insurance estimated at 0.5% of goods value.")
            if shipment.costs is None:
                shipment.costs = costs
            self.session.add(costs)

        fx_result = await self._ensure_fx_rate(shipment)
        fx_rate = fx_result.rate if fx_result.rate is not None else Decimal("1")
        if fx_result.rate is None:
            warnings.append("FX rate unavailable; calculation uses 1.0.")

        total_goods_value = self._sum_goods_value(items) * fx_rate
        freight = (costs.freight_amount or Decimal("0")) * fx_rate
        insurance = (costs.insurance_amount or Decimal("0")) * fx_rate

        customs_value = total_goods_value + freight + insurance

        per_item_results: list[dict[str, Any]] = []
        total_duty = Decimal("0")

        for item in items:
            item_goods_value = (item.goods_value or (item.quantity * item.unit_price)) * fx_rate
            allocation_ratio = (item_goods_value / total_goods_value) if total_goods_value > 0 else Decimal("0")
            item_customs_value = item_goods_value + (freight * allocation_ratio) + (insurance * allocation_ratio)
            duty_components = []
            item_duty = Decimal("0")
            duty_rate = Decimal("0")

            if shipment.direction == Direction.IMPORT_EU:
                as_of_date = shipment.import_date or date.today()
                taric_result = await self.taric_resolver.resolve_taric(
                    goods_code=item.hs_code,
                    origin_country_code=item.origin_country,
                    as_of=as_of_date,
                    additional_code=getattr(item, "additional_code", None),
                )
                if taric_result.effective_duty_rate is None:
                    warnings.append(f"No TARIC duty rate found for HS {item.hs_code}; treated as 0.")
                else:
                    duty_rate = taric_result.effective_duty_rate
                    base_amount = (item_customs_value * duty_rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                    item_duty += base_amount
                    duty_components.append(
                        {
                            "type": "ad_valorem",
                            "rate": str(duty_rate),
                            "amount": str(base_amount),
                            "source": "taric_base",
                        }
                    )

                for comp in taric_result.duties:
                    if comp.requires_additional_code:
                        warnings.append(f"Additional code required for measure {comp.measure_uid} on HS {item.hs_code}.")
                    if comp.kind == "ad_valorem" and comp.rate and comp.measure_type_code in ANTI_DUMPING_CODES:
                        amount = (item_customs_value * comp.rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                        item_duty += amount
                        duty_components.append(
                            {
                                "type": "anti_dumping",
                                "rate": str(comp.rate),
                                "amount": str(amount),
                                "measure_uid": comp.measure_uid,
                            }
                        )
                    if comp.kind == "specific":
                        amount, reason = self._compute_specific_duty(comp.expression, item)
                        if amount is None and reason:
                            warnings.append(reason)
                        if amount is not None:
                            item_duty += amount
                            duty_components.append(
                                {
                                    "type": "specific",
                                    "expression": comp.expression,
                                    "amount": str(amount),
                                    "measure_uid": comp.measure_uid,
                                }
                            )

            else:
                duty_result = await self._get_duty_rate(shipment.direction, shipment.id, item.hs_code, item.origin_country)
                if duty_result.missing or duty_result.rate is None:
                    warnings.append(f"Missing duty rate for HS {item.hs_code}; treated as 0.")
                    duty_rate = Decimal("0")
                else:
                    duty_rate = duty_result.rate
                    if duty_result.is_estimated:
                        warnings.append(f"Duty rate for HS {item.hs_code} is estimated.")

                item_duty = (item_customs_value * duty_rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                duty_components.append({"type": "ad_valorem", "rate": str(duty_rate), "amount": str(item_duty)})

            total_duty += item_duty

            per_item_results.append(
                {
                    "item_id": str(item.id),
                    "hs_code": item.hs_code,
                    "customs_value": str(item_customs_value),
                    "duty_rate": str(duty_rate),
                    "duty_amount": str(item_duty),
                    "duty_components": duty_components,
                }
            )

        other_duties = Decimal("0")
        incidental = sum(
            [
                (costs.brokerage_amount or Decimal("0")) * fx_rate,
                (costs.port_fees_amount or Decimal("0")) * fx_rate,
                (costs.inland_transport_amount or Decimal("0")) * fx_rate,
                (costs.other_incidental_amount or Decimal("0")) * fx_rate,
            ]
        )

        vat_rate_result = await self._get_vat_rate(shipment)
        if vat_rate_result.rate is None:
            warnings.append("Missing VAT rate; treated as 0.")
            vat_rate = Decimal("0")
        else:
            vat_rate = vat_rate_result.rate

        vat_base = customs_value + total_duty + other_duties + incidental
        vat_total = (vat_base * vat_rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        authorities_total = total_duty + vat_total + other_duties
        landed_cost_total = total_goods_value + freight + insurance + incidental + authorities_total
        total_units = sum([item.quantity for item in items]) if items else Decimal("1")
        if total_units <= 0:
            total_units = Decimal("1")
            warnings.append("Total quantity is zero; per-unit cost uses 1 as divisor.")
        landed_cost_per_unit = (landed_cost_total / total_units).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        calculation = Calculation(
            shipment_id=shipment.id,
            customs_value=customs_value,
            duty_total=total_duty,
            vat_base=vat_base,
            vat_total=vat_total,
            other_duties_total=other_duties,
            authorities_total=authorities_total,
            landed_cost_total=landed_cost_total,
            landed_cost_per_unit=landed_cost_per_unit,
            assumptions=assumptions,
            warnings=warnings,
            engine_version=ENGINE_VERSION,
        )
        await self.session.merge(calculation)
        shipment.status = ShipmentStatus.CALCULATED
        await self.session.commit()

        breakdown = {
            "customs_value": str(customs_value),
            "duty_total": str(total_duty),
            "vat_base": str(vat_base),
            "vat_total": str(vat_total),
            "other_duties_total": str(other_duties),
            "authorities_total": str(authorities_total),
            "landed_cost_total": str(landed_cost_total),
            "landed_cost_per_unit": str(landed_cost_per_unit),
        }

        return CalculationResult(
            status="ok",
            required_fields=[],
            message=None,
            breakdown=breakdown,
            per_item=per_item_results,
            assumptions=assumptions,
            warnings=warnings,
        )

    async def _get_duty_rate(
        self,
        direction: Direction,
        shipment_id,
        hs_code: str,
        origin_country: str | None,
    ) -> DutyRateResult:
        if direction == Direction.IMPORT_UK:
            return await self.uk_provider.get_duty_rate(shipment_id, hs_code, origin_country, False)
        if direction == Direction.IMPORT_EU:
            return await self.eu_provider.get_duty_rate(hs_code, origin_country, False, shipment_id=shipment_id)
        return DutyRateResult(rate=Decimal("0"), source="export", is_estimated=True, missing=False)

    async def _get_vat_rate(self, shipment) -> VatRateResult:
        if shipment.direction == Direction.IMPORT_UK:
            return await self.vat_provider.get_standard_rate("GB", shipment_id=shipment.id)
        if shipment.direction == Direction.IMPORT_EU:
            if not shipment.destination_country:
                return VatRateResult(rate=None, source="missing_country")
            return await self.vat_provider.get_standard_rate(shipment.destination_country, shipment_id=shipment.id)
        return VatRateResult(rate=Decimal("0"), source="export")

    async def _ensure_fx_rate(self, shipment) -> FxRateResult:
        base = shipment.currency
        if shipment.direction == Direction.IMPORT_UK:
            quote = "GBP"
        else:
            quote = "EUR"

        if quote == "GBP" and shipment.fx_rate_to_gbp:
            return FxRateResult(rate=Decimal(str(shipment.fx_rate_to_gbp)), source="shipment", rate_date=None)
        if quote == "EUR" and shipment.fx_rate_to_eur:
            return FxRateResult(rate=Decimal(str(shipment.fx_rate_to_eur)), source="shipment", rate_date=None)

        result = await self.fx_provider.get_rate(base, quote, shipment_id=shipment.id)
        if result.rate is None:
            return result

        if quote == "GBP":
            shipment.fx_rate_to_gbp = str(result.rate)
        if quote == "EUR":
            shipment.fx_rate_to_eur = str(result.rate)
        await self.shipment_repo.update(shipment)
        return result

    def _sum_goods_value(self, items) -> Decimal:
        total = Decimal("0")
        for item in items:
            if item.goods_value is None:
                item.goods_value = (item.quantity * item.unit_price).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                try:
                    self.session.add(item)
                except Exception:
                    pass
            total += Decimal(item.goods_value)
        return total

    def _compute_specific_duty(self, expression: str, item) -> tuple[Decimal | None, str | None]:
        expr = expression.lower()
        if "kg" in expr:
            if not item.weight_net_kg:
                return None, "Specific duty requires weight_kg to compute."
            amount = self._extract_amount(expr)
            unit = self._extract_unit(expr)
            if amount is None or unit is None:
                return None, "Specific duty expression could not be parsed."
            return (amount * (item.weight_net_kg / unit)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP), None
        return None, "Specific duty requires quantity/weight to compute."

    def _extract_amount(self, expr: str) -> Decimal | None:
        import re

        match = re.search(r"([0-9]+(?:\\.[0-9]+)?)", expr)
        if not match:
            return None
        return Decimal(match.group(1))

    def _extract_unit(self, expr: str) -> Decimal | None:
        import re

        match = re.search(r"/\\s*([0-9]+(?:\\.[0-9]+)?)\\s*kg", expr)
        if not match:
            return Decimal("1")
        return Decimal(match.group(1))
