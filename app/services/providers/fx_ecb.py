from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.config import get_settings
from app.models.fallback_tables import FxRateDaily
from app.repositories.fallback_repo import FxRateRepository
from app.services.providers.base import redis_get_json, redis_set_json
from app.models.enums import ProviderType
from app.models.rate_snapshot import RateSnapshot
from app.repositories.rate_snapshot_repo import RateSnapshotRepository
from app.services.providers.http_client import CircuitBreaker, get_json
from app.services.providers.types import FxRateResult

TTL_SECONDS = 86400
_cb = CircuitBreaker()


class FxProvider:
    def __init__(self, session) -> None:
        self.session = session
        self.settings = get_settings()
        self.repo = FxRateRepository(session)
        self.snapshot_repo = RateSnapshotRepository(session)

    async def get_rate(self, base: str, quote: str, shipment_id=None) -> FxRateResult:
        if base == quote:
            return FxRateResult(rate=Decimal("1"), source="identity", rate_date=str(date.today()))

        cache_key = f"fx:{base}:{quote}"
        cached = await redis_get_json(cache_key)
        if cached:
            return FxRateResult(rate=Decimal(str(cached["rate"])), source="redis", rate_date=cached.get("rate_date"))

        rate_date = date.today()
        db_rate = await self.repo.get_rate(base, quote, rate_date)
        if db_rate:
            return FxRateResult(rate=Decimal(db_rate.rate), source="db", rate_date=str(db_rate.rate_date))

        if not _cb.allow():
            return FxRateResult(rate=None, source="unavailable", rate_date=None)

        url = f"{self.settings.ecb_api_base}/D.{base}.{quote}.SP00.A"
        params = {"format": "jsondata"}
        try:
            payload = await get_json(url, params=params)
            rate, rate_date = self._extract_rate(payload)
            if rate is None:
                return FxRateResult(rate=None, source="ecb_missing", rate_date=rate_date, raw_payload=payload)
            await redis_set_json(cache_key, {"rate": str(rate), "rate_date": rate_date}, TTL_SECONDS)
            if rate_date:
                fx = FxRateDaily(base=base, quote=quote, rate=rate, rate_date=date.fromisoformat(rate_date))
                await self.repo.upsert(fx)
            if shipment_id is not None:
                snapshot = RateSnapshot(
                    shipment_id=shipment_id,
                    provider=ProviderType.FX,
                    request_key={"base": base, "quote": quote},
                    response_payload=payload,
                    ttl_seconds=TTL_SECONDS,
                )
                await self.snapshot_repo.create(snapshot)
            _cb.record_success()
            return FxRateResult(rate=rate, source="ecb", rate_date=rate_date, raw_payload=payload)
        except Exception:
            _cb.record_failure()
            return FxRateResult(rate=None, source="ecb_error", rate_date=None)

    def _extract_rate(self, payload: dict) -> tuple[Decimal | None, str | None]:
        try:
            series = payload["dataSets"][0]["series"]
            observations = next(iter(series.values()))["observations"]
            last_key = sorted(observations.keys())[-1]
            last_value = observations[last_key][0]
            dates = payload["structure"]["dimensions"]["observation"][0]["values"]
            rate_date = dates[int(last_key)]["id"]
            return Decimal(str(last_value)), rate_date
        except Exception:
            return None, None
