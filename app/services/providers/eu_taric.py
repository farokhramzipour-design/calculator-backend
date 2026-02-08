from __future__ import annotations

from decimal import Decimal

from app.core.config import get_settings
from app.models.enums import ProviderType
from app.models.rate_snapshot import RateSnapshot
from app.repositories.fallback_repo import EuTaricRepository
from app.repositories.rate_snapshot_repo import RateSnapshotRepository
from app.services.providers.base import redis_get_json, redis_set_json
from app.services.providers.http_client import CircuitBreaker, get_json
from app.services.providers.types import DutyRateResult

TTL_SECONDS = 86400
_cb = CircuitBreaker()


class EuTaricProvider:
    def __init__(self, session) -> None:
        self.session = session
        self.settings = get_settings()
        self.repo = EuTaricRepository(session)
        self.snapshot_repo = RateSnapshotRepository(session)

    async def get_duty_rate(
        self, hs_code: str, origin_country: str | None, preference_flag: bool, shipment_id=None
    ) -> DutyRateResult:
        cache_key = f"eu_taric:{hs_code}:{origin_country}:{preference_flag}"
        cached = await redis_get_json(cache_key)
        if cached:
            return DutyRateResult(
                rate=Decimal(str(cached["rate"])),
                source="redis",
                is_estimated=False,
                missing=False,
                raw_payload=cached,
            )

        db_rate = await self.repo.get_rate(hs_code, origin_country, preference_flag)
        if db_rate:
            await redis_set_json(cache_key, {"rate": str(db_rate.duty_rate)}, TTL_SECONDS)
            return DutyRateResult(rate=Decimal(db_rate.duty_rate), source="db", is_estimated=True, missing=False)

        if self.settings.eu_taric_api_base and self.settings.eu_taric_api_key and _cb.allow():
            try:
                url = f"{self.settings.eu_taric_api_base}/taric"
                payload = await get_json(
                    url,
                    headers={"Authorization": f"Bearer {self.settings.eu_taric_api_key}"},
                    params={"hs_code": hs_code, "origin": origin_country, "preference": str(preference_flag).lower()},
                )
                rate = Decimal(str(payload.get("duty_rate")))
                await redis_set_json(cache_key, {"rate": str(rate)}, TTL_SECONDS)
                if shipment_id is not None:
                    snapshot = RateSnapshot(
                        shipment_id=shipment_id,
                        provider=ProviderType.EU_TARIC,
                        request_key={"hs_code": hs_code, "origin": origin_country},
                        response_payload=payload,
                        ttl_seconds=TTL_SECONDS,
                    )
                    await self.snapshot_repo.create(snapshot)
                _cb.record_success()
                return DutyRateResult(rate=rate, source="api", is_estimated=False, missing=False, raw_payload=payload)
            except Exception:
                _cb.record_failure()

        return DutyRateResult(rate=None, source="missing", is_estimated=True, missing=True)
