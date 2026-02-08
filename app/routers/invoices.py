from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.deps import get_current_user, get_db_session
from app.invoices.openai_extractor import extract_invoice, _normalize_decimal, _parse_date
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.schemas.invoice import InvoiceRead, InvoiceAssignRequest, InvoiceReviewUpdate

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("/upload", response_model=InvoiceRead)
async def upload_invoice(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF or DOCX allowed")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    stored_path = upload_dir / f"{file_id}{suffix}"
    stored_path.write_bytes(await file.read())

    try:
        extracted = await extract_invoice(stored_path, "pdf" if suffix == ".pdf" else "docx")
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    invoice = Invoice(
        user_id=user.id,
        file_path=str(stored_path),
        file_type=suffix.replace(".", ""),
        invoice_number=extracted.get("invoice_number"),
        invoice_date=_parse_date(extracted.get("invoice_date")),
        supplier_name=extracted.get("supplier_name"),
        buyer_name=extracted.get("buyer_name"),
        currency=extracted.get("currency"),
        subtotal=_normalize_decimal(extracted.get("subtotal")),
        freight=_normalize_decimal(extracted.get("freight")),
        insurance=_normalize_decimal(extracted.get("insurance")),
        tax_total=_normalize_decimal(extracted.get("tax_total")),
        total=_normalize_decimal(extracted.get("total")),
        extracted_payload=extracted,
        status=InvoiceStatus.EXTRACTED,
    )
    session.add(invoice)
    await session.flush()

    for item in extracted.get("items", []):
        session.add(
            InvoiceItem(
                invoice_id=invoice.id,
                description=item.get("description", ""),
                hs_code=item.get("hs_code"),
                origin_country=item.get("origin_country"),
                quantity=_normalize_decimal(item.get("quantity")),
                unit_price=_normalize_decimal(item.get("unit_price")),
                total_price=_normalize_decimal(item.get("total_price")),
            )
        )

    await session.commit()
    await session.refresh(invoice)
    return invoice


@router.get("", response_model=list[InvoiceRead])
async def list_invoices(user=Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(
        select(Invoice).where(Invoice.user_id == user.id).options(selectinload(Invoice.items))
    )
    return list(result.scalars().all())


@router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(invoice_id: uuid.UUID, user=Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == user.id).options(selectinload(Invoice.items))
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@router.post("/{invoice_id}/review", response_model=InvoiceRead)
async def review_invoice(
    invoice_id: uuid.UUID,
    payload: InvoiceReviewUpdate,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == user.id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    invoice.status = payload.status
    await session.commit()
    await session.refresh(invoice)
    return invoice


@router.post("/assign", response_model=InvoiceRead)
async def assign_invoice_to_shipment(
    shipment_id: uuid.UUID,
    payload: InvoiceAssignRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(select(Invoice).where(Invoice.id == payload.invoice_id, Invoice.user_id == user.id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    invoice.shipment_id = shipment_id
    await session.commit()
    await session.refresh(invoice)
    return invoice
