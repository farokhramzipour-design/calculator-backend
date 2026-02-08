from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user, get_db_session
from app.schemas.calculation import CalculationResponse
from app.services.calculator import CalculatorService

router = APIRouter(prefix="/shipments", tags=["calculation"])


@router.post("/{shipment_id}/calculate", response_model=CalculationResponse)
async def calculate(shipment_id: str, user=Depends(get_current_user), session=Depends(get_db_session)):
    service = CalculatorService(session)
    result = await service.calculate(shipment_id, user.id)
    return CalculationResponse(
        status=result.status,
        required_fields=result.required_fields,
        message=result.message,
        breakdown=result.breakdown,
        per_item=result.per_item,
        assumptions=result.assumptions,
        warnings=result.warnings,
    )
