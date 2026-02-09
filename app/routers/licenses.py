from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user, get_db_session
from app.models.license import License, ShipmentLicense
from app.schemas.license import LicenseRead, LicenseAssignRequest

router = APIRouter(prefix="/licenses", tags=["licenses"])


@router.post("/upload", response_model=LicenseRead)
async def upload_license(
    license_type: str = Form(...),
    license_number: str | None = Form(default=None),
    issuer: str | None = Form(default=None),
    expires_on: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type")

    settings = get_settings()
    upload_dir = Path(settings.upload_dir) / "licenses"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    stored_path = upload_dir / f"{file_id}{suffix}"
    stored_path.write_bytes(await file.read())

    parsed_date = date.fromisoformat(expires_on) if expires_on else None

    license_obj = License(
        user_id=user.id,
        license_type=license_type,
        license_number=license_number,
        issuer=issuer,
        expires_on=parsed_date,
        file_path=str(stored_path),
        file_type=suffix.replace(".", ""),
        notes=notes,
    )
    session.add(license_obj)
    await session.commit()
    await session.refresh(license_obj)
    return license_obj


@router.get("", response_model=list[LicenseRead])
async def list_licenses(user=Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(License).where(License.user_id == user.id))
    return list(result.scalars().all())


@router.post("/assign", response_model=LicenseRead)
async def assign_license_to_shipment(
    shipment_id: uuid.UUID,
    payload: LicenseAssignRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(License).where(License.id == payload.license_id, License.user_id == user.id)
    )
    license_obj = result.scalar_one_or_none()
    if not license_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")

    session.add(ShipmentLicense(shipment_id=shipment_id, license_id=license_obj.id))
    await session.commit()
    return license_obj
