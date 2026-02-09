from __future__ import annotations

import re
from decimal import Decimal

from app.core.config import get_settings
from app.models.enums import ProviderType
from app.models.rate_snapshot import RateSnapshot
from app.repositories.fallback_repo import TariffOverrideRepository
from app.repositories.rate_snapshot_repo import RateSnapshotRepository
from app.services.providers.base import redis_get_json, redis_set_json
from app.services.providers.http_client import CircuitBreaker, get_json
from app.services.providers.types import DutyRateResult

TTL_SECONDS = 86400
_cb = CircuitBreaker()


class UkTariffProvider:
    def __init__(self, session) -> None:
        self.session = session
        self.settings = get_settings()
        self.snapshot_repo = RateSnapshotRepository(session)
        self.override_repo = TariffOverrideRepository(session)

    async def get_duty_rate(
        self,
        shipment_id,
        commodity_code: str,
        origin_country: str | None,
        preference_flag: bool,
    ) -> DutyRateResult:
        cache_key = f"uk_tariff:{commodity_code}"
        cached = await redis_get_json(cache_key)
        if cached:
            rate = self._extract_ad_valorem(cached)
            return DutyRateResult(rate=rate, source="redis", is_estimated=False, missing=rate is None, raw_payload=cached)

        if shipment_id is not None:
            snapshot = await self.snapshot_repo.get_valid_snapshot(
                shipment_id, ProviderType.UK_TARIFF, {"commodity_code": commodity_code}
            )
            if snapshot:
                rate = self._extract_ad_valorem(snapshot.response_payload)
                return DutyRateResult(rate=rate, source="snapshot", is_estimated=False, missing=rate is None)

        if not _cb.allow():
            return await self._fallback(commodity_code, origin_country, preference_flag)

        url = f"{self.settings.uk_tariff_api_base}/commodities/{commodity_code}"
        try:
            payload = await get_json(url)
            await redis_set_json(cache_key, payload, TTL_SECONDS)
            if shipment_id is not None:
                snapshot = RateSnapshot(
                    shipment_id=shipment_id,
                    provider=ProviderType.UK_TARIFF,
                    request_key={"commodity_code": commodity_code},
                    response_payload=payload,
                    ttl_seconds=TTL_SECONDS,
                )
                await self.snapshot_repo.create(snapshot)
            _cb.record_success()
            rate = self._extract_ad_valorem(payload)
            return DutyRateResult(rate=rate, source="uk_api", is_estimated=False, missing=rate is None, raw_payload=payload)
        except Exception:
            _cb.record_failure()
            return await self._fallback(commodity_code, origin_country, preference_flag)

    async def _fallback(
        self, commodity_code: str, origin_country: str | None, preference_flag: bool
    ) -> DutyRateResult:
        override = await self.override_repo.get_rate("UK", commodity_code, origin_country, preference_flag)
        if not override:
            return DutyRateResult(rate=None, source="override_missing", is_estimated=True, missing=True)
        return DutyRateResult(rate=Decimal(override.duty_rate), source="override", is_estimated=True, missing=False)

    async def get_commodity_details(self, commodity_code: str) -> dict:
        cache_key = f"uk_tariff:commodity:{commodity_code}"
        cached = await redis_get_json(cache_key)
        if cached:
            return cached

        url = f"{self.settings.uk_tariff_api_base}/commodities/{commodity_code}"
        payload = await get_json(url)
        await redis_set_json(cache_key, payload, TTL_SECONDS)
        return payload

    def _extract_ad_valorem(self, payload: dict) -> Decimal | None:
        included = payload.get("included", [])
        for item in included:
            if item.get("type") != "measure":
                continue
            attrs = item.get("attributes", {})
            expression = attrs.get("duty_expression") or ""
            match = re.search(r"([0-9.]+)\s*%", expression)
            if match:
                return Decimal(match.group(1)) / Decimal("100")
        return None
