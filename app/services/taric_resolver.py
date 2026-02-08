from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.repositories.taric_repo import TaricRepository
from app.models.taric import TaricResolvedCache


PREFERENTIAL_CODES = {"103", "105", "106", "142", "143", "144", "145"}
ANTI_DUMPING_CODES = {"551", "552", "553", "554"}


@dataclass
class DutyComponent:
    measure_uid: str
    measure_type_code: str
    expression: str
    kind: str
    rate: Decimal | None
    uom: str | None
    requires_additional_code: bool = False


@dataclass
class ResolvedTaricResult:
    goods_code: str
    matched_goods_code: str | None
    duties: list[DutyComponent]
    requirements: list[dict[str, Any]]
    legal_refs: list[str]
    effective_duty_rate: Decimal | None
    notes: list[str]


class TaricResolver:
    def __init__(self, repo: TaricRepository) -> None:
        self.repo = repo

    async def resolve_taric(
        self,
        goods_code: str,
        origin_country_code: str,
        as_of: date,
        additional_code: str | None = None,
        snapshot_date: date | None = None,
    ) -> ResolvedTaricResult:
        snapshot_date = snapshot_date or await self.repo.get_latest_snapshot_date()
        if not snapshot_date:
            return ResolvedTaricResult(
                goods_code=goods_code,
                matched_goods_code=None,
                duties=[],
                requirements=[],
                legal_refs=[],
                effective_duty_rate=None,
                notes=["No TARIC snapshot loaded."],
            )

        cached = await self.repo.get_cached(snapshot_date, goods_code, origin_country_code, as_of, additional_code)
        if cached:
            payload = cached.payload
            duties = []
            for d in payload.get("duties", []):
                rate = Decimal(d["rate"]) if d.get("rate") is not None else None
                duties.append(
                    DutyComponent(
                        measure_uid=d["measure_uid"],
                        measure_type_code=d["measure_type_code"],
                        expression=d["expression"],
                        kind=d["kind"],
                        rate=rate,
                        uom=d.get("uom"),
                        requires_additional_code=d.get("requires_additional_code", False),
                    )
                )
            return ResolvedTaricResult(
                goods_code=payload["goods_code"],
                matched_goods_code=payload.get("matched_goods_code"),
                duties=duties,
                requirements=payload.get("requirements", []),
                legal_refs=payload.get("legal_refs", []),
                effective_duty_rate=Decimal(payload["effective_duty_rate"]) if payload.get("effective_duty_rate") else None,
                notes=payload.get("notes", []),
            )

        codes = self._candidate_codes(goods_code)
        goods_rows = await self.repo.get_goods_candidates(codes, as_of)
        matched_codes = {row.goods_code for row in goods_rows}
        matched_code = next((code for code in codes if code in matched_codes), None)

        measures = await self.repo.get_measures(list(matched_codes) or codes, as_of)
        applicable_measures = []
        for measure in measures:
            applies = await self.repo.geo_applies(measure.geo_code, origin_country_code, as_of)
            if applies:
                applicable_measures.append(measure)

        measure_uids = [m.measure_uid for m in applicable_measures]
        duty_expressions = await self.repo.get_measure_duty_expressions(measure_uids)
        expressions_by_measure: dict[str, list[str]] = {}
        expression_ids = [str(d.expression_id) for d in duty_expressions if d.expression_id]
        expression_rows = await self.repo.get_duty_expressions(expression_ids)
        expression_map = {str(row.id): row for row in expression_rows}
        for expr in duty_expressions:
            text = expr.expression_text
            if not text and expr.expression_id and str(expr.expression_id) in expression_map:
                text = expression_map[str(expr.expression_id)].expression_text
            if not text:
                continue
            expressions_by_measure.setdefault(expr.measure_uid, []).append(text)

        additional_codes = await self.repo.get_measure_additional_codes(measure_uids)
        add_code_map: dict[str, list[tuple[str, str]]] = {}
        for ac in additional_codes:
            add_code_map.setdefault(ac.measure_uid, []).append((ac.additional_code_type, ac.additional_code))

        conditions = await self.repo.get_measure_conditions(measure_uids)
        requirements = [
            {
                "measure_uid": cond.measure_uid,
                "condition_code": cond.condition_code,
                "action_code": cond.action_code,
                "certificate_type_code": cond.certificate_type_code,
            }
            for cond in conditions
        ]

        legal_refs = list({m.regulation_ref for m in applicable_measures if m.regulation_ref})

        duties: list[DutyComponent] = []
        notes: list[str] = []
        for measure in applicable_measures:
            exprs = expressions_by_measure.get(measure.measure_uid, []) or ["0%"]
            has_additional = measure.measure_uid in add_code_map
            requires_additional = has_additional and not additional_code
            if has_additional and additional_code:
                allowed = {code for _, code in add_code_map[measure.measure_uid]}
                if additional_code not in allowed:
                    requires_additional = True
            for expr in exprs:
                kind, rate, uom = self._parse_expression(expr)
                duties.append(
                    DutyComponent(
                        measure_uid=measure.measure_uid,
                        measure_type_code=measure.measure_type_code,
                        expression=expr,
                        kind=kind,
                        rate=rate,
                        uom=uom,
                        requires_additional_code=requires_additional,
                    )
                )

        effective_rate = self._select_effective_rate(duties)

        payload = {
            "goods_code": goods_code,
            "matched_goods_code": matched_code,
            "duties": [self._duty_to_payload(d) for d in duties],
            "requirements": requirements,
            "legal_refs": legal_refs,
            "effective_duty_rate": str(effective_rate) if effective_rate is not None else None,
            "notes": notes,
        }
        await self.repo.upsert_cache(
            TaricResolvedCache(
                snapshot_date=snapshot_date,
                goods_code=goods_code,
                origin_country=origin_country_code,
                as_of_date=as_of,
                additional_code=additional_code,
                payload=payload,
            )
        )

        return ResolvedTaricResult(
            goods_code=goods_code,
            matched_goods_code=matched_code,
            duties=duties,
            requirements=requirements,
            legal_refs=legal_refs,
            effective_duty_rate=effective_rate,
            notes=notes,
        )

    def _duty_to_payload(self, duty: DutyComponent) -> dict[str, Any]:
        return {
            "measure_uid": duty.measure_uid,
            "measure_type_code": duty.measure_type_code,
            "expression": duty.expression,
            "kind": duty.kind,
            "rate": str(duty.rate) if duty.rate is not None else None,
            "uom": duty.uom,
            "requires_additional_code": duty.requires_additional_code,
        }

    def _candidate_codes(self, goods_code: str) -> list[str]:
        cleaned = "".join(ch for ch in goods_code if ch.isdigit())
        lengths = [10, 8, 6, 4, 2]
        return [cleaned[:length] for length in lengths if len(cleaned) >= length]

    def _parse_expression(self, expr: str) -> tuple[str, Decimal | None, str | None]:
        expr = expr.strip()
        if "%" in expr:
            try:
                rate = Decimal(expr.replace("%", "").strip()) / Decimal("100")
                return "ad_valorem", rate, None
            except Exception:
                return "unknown", None, None
        if "EUR" in expr.upper():
            return "specific", None, "EUR"
        return "unknown", None, None

    def _select_effective_rate(self, duties: list[DutyComponent]) -> Decimal | None:
        pref = [d for d in duties if d.measure_type_code in PREFERENTIAL_CODES and d.kind == "ad_valorem"]
        if pref:
            return pref[0].rate
        third_country = [d for d in duties if d.kind == "ad_valorem" and d.measure_type_code not in ANTI_DUMPING_CODES]
        if third_country:
            return third_country[0].rate
        return None
