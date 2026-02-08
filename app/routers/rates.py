from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_db_session
from app.schemas.rates import FxRateResponse, TariffRateResponse, VatRateResponse
from app.services.providers.eu_taric import EuTaricProvider
from app.services.providers.fx_ecb import FxProvider
from app.services.providers.uk_tariff import UkTariffProvider
from app.services.providers.vat import VatRateProvider

router = APIRouter(prefix="/rates", tags=["rates"])


@router.get("/fx", response_model=FxRateResponse)
async def fx_rate(base: str, quote: str, session=Depends(get_db_session)):
    provider = FxProvider(session)
    result = await provider.get_rate(base, quote)
    return FxRateResponse(base=base, quote=quote, rate=result.rate, source=result.source)


@router.get("/vat", response_model=VatRateResponse)
async def vat_rate(country: str, session=Depends(get_db_session)):
    provider = VatRateProvider(session)
    result = await provider.get_standard_rate(country)
    return VatRateResponse(country=country, rate=result.rate, source=result.source)


@router.get("/tariff/uk", response_model=TariffRateResponse)
async def uk_tariff(commodity_code: str, session=Depends(get_db_session)):
    provider = UkTariffProvider(session)
    result = await provider.get_duty_rate(None, commodity_code, None, False)
    return TariffRateResponse(code=commodity_code, rate=result.rate, source=result.source, is_estimated=result.is_estimated)


@router.get("/tariff/eu", response_model=TariffRateResponse)
async def eu_tariff(hs_code: str, origin: str | None = None, session=Depends(get_db_session)):
    provider = EuTaricProvider(session)
    result = await provider.get_duty_rate(hs_code, origin, False)
    return TariffRateResponse(code=hs_code, rate=result.rate, source=result.source, is_estimated=result.is_estimated)
