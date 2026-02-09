from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.services.providers.base import redis_get_json, redis_set_json
from app.services.providers.http_client import get_json

TTL_SECONDS = 86400


class UkTariffSearchProvider:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def search_by_description(self, query: str) -> dict[str, Any]:
        cache_key = f"uk_tariff_search:{query}"
        cached = await redis_get_json(cache_key)
        if cached:
            return cached

        if not self.settings.uk_tariff_search_key:
            raise RuntimeError("UK_TARIFF_SEARCH_KEY is not configured")

        url = f"{self.settings.uk_tariff_search_base}/search.json"
        params = {"q": query}
        payload = await get_json(url, params=params, headers={"X-Api-Key": self.settings.uk_tariff_search_key})
        await redis_set_json(cache_key, payload, TTL_SECONDS)
        return payload
