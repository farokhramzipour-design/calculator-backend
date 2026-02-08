from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Landed Cost Calculator"
    environment: str = "local"
    api_prefix: str = "/api"
    jwt_secret: str = Field(default="change_me", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_minutes: int = 43200

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/landed_cost",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    uk_tariff_api_base: str = Field(
        default="https://www.trade-tariff.service.gov.uk/api/v2",
        alias="UK_TARIFF_API_BASE",
    )
    ecb_api_base: str = Field(
        default="https://data-api.ecb.europa.eu/service/data/EXR",
        alias="ECB_API_BASE",
    )
    vat_api_base: str | None = Field(default=None, alias="VAT_API_BASE")
    vat_api_key: str | None = Field(default=None, alias="VAT_API_KEY")

    eu_taric_api_base: str | None = Field(default=None, alias="EU_TARIC_API_BASE")
    eu_taric_api_key: str | None = Field(default=None, alias="EU_TARIC_API_KEY")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
