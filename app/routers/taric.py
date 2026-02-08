from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.deps import get_db_session
from app.repositories.taric_repo import TaricRepository
from app.schemas.taric import TaricGoodsResponse, TaricResolveResponse
from app.services.taric_resolver import TaricResolver
from app.taric.importer import import_taric_files

router = APIRouter(prefix="/taric", tags=["taric"])
admin_router = APIRouter(prefix="/admin/taric", tags=["taric-admin"])


@admin_router.post("/import")
async def import_taric(
    snapshot_date: str | None = Form(default=None),
    goods_file: UploadFile = File(...),
    measures_file: UploadFile = File(...),
    add_codes_file: UploadFile = File(...),
    force: bool = Form(default=False),
):
    if snapshot_date:
        try:
            snap = date.fromisoformat(snapshot_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="snapshot_date must be ISO format YYYY-MM-DD",
            ) from exc
    else:
        snap = date.today()
    with tempfile.TemporaryDirectory() as tmpdir:
        goods_path = Path(tmpdir) / goods_file.filename
        measures_path = Path(tmpdir) / measures_file.filename
        add_path = Path(tmpdir) / add_codes_file.filename
        goods_path.write_bytes(await goods_file.read())
        measures_path.write_bytes(await measures_file.read())
        add_path.write_bytes(await add_codes_file.read())

        result = await import_taric_files(
            goods_file=goods_path,
            measures_file=measures_path,
            add_codes_file=add_path,
            snapshot_date=snap,
            source_label="taric_excel",
            force=force,
        )
    return result


@router.get("/goods/{goods_code}", response_model=TaricGoodsResponse)
async def goods_lookup(goods_code: str, as_of: str | None = None, session=Depends(get_db_session)):
    repo = TaricRepository(session)
    as_of_date = date.fromisoformat(as_of) if as_of else date.today()
    candidates = await repo.get_goods_candidates([goods_code], as_of_date)
    description = await repo.get_goods_description(goods_code, as_of_date)
    return TaricGoodsResponse(
        goods_code=goods_code,
        valid=bool(candidates),
        description=description.description if description else None,
        valid_from=description.valid_from if description else None,
        valid_to=description.valid_to if description else None,
    )


@router.get("/resolve", response_model=TaricResolveResponse)
async def resolve_taric(
    goods_code: str,
    origin: str,
    as_of: str | None = None,
    additional_code: str | None = None,
    session=Depends(get_db_session),
):
    repo = TaricRepository(session)
    resolver = TaricResolver(repo)
    as_of_date = date.fromisoformat(as_of) if as_of else date.today()
    result = await resolver.resolve_taric(
        goods_code=goods_code,
        origin_country_code=origin,
        as_of=as_of_date,
        additional_code=additional_code,
    )
    return TaricResolveResponse.from_result(result)
