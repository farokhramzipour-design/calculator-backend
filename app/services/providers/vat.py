from __future__ import annotations

from decimal import Decimal

from app.core.config import get_settings
from app.models.enums import ProviderType
from app.models.rate_snapshot import RateSnapshot
from app.repositories.fallback_repo import VatRateRepository
from app.repositories.rate_snapshot_repo import RateSnapshotRepository
from app.services.providers.base import redis_get_json, redis_set_json
from app.services.providers.http_client import CircuitBreaker, get_json
from app.services.providers.types import VatRateResult

TTL_SECONDS = 86400
_cb = CircuitBreaker()


class VatRateProvider:
    def __init__(self, session) -> None:
        self.session = session
        self.settings = get_settings()
        self.repo = VatRateRepository(session)
        self.snapshot_repo = RateSnapshotRepository(session)

    async def get_standard_rate(self, country: str, shipment_id=None) -> VatRateResult:
        cache_key = f"vat:{country}:standard"
        cached = await redis_get_json(cache_key)
        if cached:
            return VatRateResult(rate=Decimal(str(cached["rate"])), source="redis", raw_payload=cached)

        db_rate = await self.repo.get_standard_rate(country)
        if db_rate:
            await redis_set_json(cache_key, {"rate": str(db_rate.rate)}, TTL_SECONDS)
            return VatRateResult(rate=Decimal(db_rate.rate), source="db")

        if self.settings.vat_api_base and self.settings.vat_api_key and _cb.allow():
            try:
                url = f"{self.settings.vat_api_base}/vat-rate-check"
                payload = await get_json(
                    url,
                    headers={"x-api-key": self.settings.vat_api_key},
                    params={"country_code": country, "rate_type": "GOODS"},
                )
                rate = self._extract_standard_rate(payload)
                await redis_set_json(cache_key, {"rate": str(rate)}, TTL_SECONDS)
                if shipment_id is not None:
                    snapshot = RateSnapshot(
                        shipment_id=shipment_id,
                        provider=ProviderType.VAT,
                        request_key={"country": country},
                        response_payload=payload,
                        ttl_seconds=TTL_SECONDS,
                    )
                    await self.snapshot_repo.create(snapshot)
                _cb.record_success()
                return VatRateResult(rate=rate, source="vatapi", raw_payload=payload)
            except Exception:
                _cb.record_failure()

        return VatRateResult(rate=None, source="missing")

    def _extract_standard_rate(self, payload: dict) -> Decimal:
        rates = payload.get("rates") or payload.get("rate") or {}
        if isinstance(rates, dict):
            standard = rates.get("standard") or rates.get("STANDARD")
            if isinstance(standard, dict) and "rate" in standard:
                return self._normalize_rate(Decimal(str(standard["rate"])))
            if isinstance(rates.get("goods"), dict) and "rate" in rates["goods"]:
                return self._normalize_rate(Decimal(str(rates["goods"]["rate"])))
        if "standard_rate" in payload:
            return self._normalize_rate(Decimal(str(payload["standard_rate"])))
        raise ValueError("Unable to extract standard VAT rate from VAT API response")

    def _normalize_rate(self, rate: Decimal) -> Decimal:
        return rate / Decimal("100") if rate > 1 else rate
