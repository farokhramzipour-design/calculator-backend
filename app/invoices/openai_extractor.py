from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from docx import Document

from app.core.config import get_settings


def _docx_to_text(path: Path) -> str:
    doc = Document(path)
    return "\n".join([p.text for p in doc.paragraphs if p.text])


def _normalize_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except Exception:
        return None


async def extract_invoice(file_path: Path, file_type: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    schema = {
        "type": "object",
        "properties": {
            "invoice_number": {"type": ["string", "null"]},
            "invoice_date": {"type": ["string", "null"], "description": "ISO date"},
            "supplier_name": {"type": ["string", "null"]},
            "buyer_name": {"type": ["string", "null"]},
            "buyer_address": {"type": ["string", "null"]},
            "seller_address": {"type": ["string", "null"]},
            "buyer_eori": {"type": ["string", "null"]},
            "seller_eori": {"type": ["string", "null"]},
            "incoterm": {"type": ["string", "null"]},
            "currency": {"type": ["string", "null"]},
            "subtotal": {"type": ["number", "string", "null"]},
            "freight": {"type": ["number", "string", "null"]},
            "insurance": {"type": ["number", "string", "null"]},
            "tax_total": {"type": ["number", "string", "null"]},
            "total": {"type": ["number", "string", "null"]},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "hs_code": {"type": ["string", "null"]},
                        "origin_country": {"type": ["string", "null"]},
                        "vat_code": {"type": ["string", "null"]},
                        "pack_count": {"type": ["number", "string", "null"]},
                        "pack_type": {"type": ["string", "null"]},
                        "net_weight": {"type": ["number", "string", "null"]},
                        "gross_weight": {"type": ["number", "string", "null"]},
                        "quantity": {"type": ["number", "string", "null"]},
                        "unit_price": {"type": ["number", "string", "null"]},
                        "total_price": {"type": ["number", "string", "null"]},
                    },
                    "required": [
                        "description",
                        "hs_code",
                        "origin_country",
                        "vat_code",
                        "pack_count",
                        "pack_type",
                        "net_weight",
                        "gross_weight",
                        "quantity",
                        "unit_price",
                        "total_price",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["items"],
        "additionalProperties": False,
    }

    prompt = (
        "Extract invoice data from the provided document. The invoice may be in any language. "
        "Return JSON matching the provided schema. Use ISO dates and numbers. "
        "If a field is missing, return null. JSON only."
    )

    async with httpx.AsyncClient(timeout=60) as client:
        if file_type == "pdf":
            with open(file_path, "rb") as f:
                upload_resp = await client.post(
                    "https://api.openai.com/v1/files",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    files={"file": (file_path.name, f, "application/pdf")},
                    data={"purpose": "user_data"},
                )
            upload_resp.raise_for_status()
            file_id = upload_resp.json()["id"]
            payload = {
                "model": settings.openai_model,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_file", "file_id": file_id},
                        ],
                    }
                ],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "invoice_extract",
                        "schema": schema,
                        "strict": True,
                    }
                },
            }
        else:
            text = _docx_to_text(file_path)
            payload = {
                "model": settings.openai_model,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_text", "text": text},
                        ],
                    }
                ],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "invoice_extract",
                        "schema": schema,
                        "strict": True,
                    }
                },
            }

        response = await client.post(
            "https://api.openai.com/v1/responses",
            headers=headers,
            json=payload,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"OpenAI error {response.status_code}: {response.text}") from exc
        data = response.json()
        output_text = _extract_output_text(data)
        extracted = json.loads(output_text)
        return extracted


def _extract_output_text(data: dict) -> str:
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and "text" in content:
                return content["text"]
    raise ValueError("No output text found in OpenAI response")
