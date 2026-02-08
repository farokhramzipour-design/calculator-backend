from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import configure_logging, get_logger
from app.db.session import SessionLocal
from app.models.taric import (
    AdditionalCode,
    DutyExpression,
    GeoArea,
    GoodsDescription,
    GoodsNomenclature,
    Measure,
    MeasureAdditionalCode,
    MeasureDutyExpression,
    TaricSnapshot,
)

logger = get_logger()


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [
        str(c)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        for c in df.columns
    ]
    return df


def _parse_date(value: Any) -> date | None:
    if pd.isna(value):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def _to_records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records", date_format="iso"))


async def _upsert(session: AsyncSession, model, rows: list[dict], conflict_cols: list[str]) -> None:
    if not rows:
        return
    stmt = pg_insert(model).values(rows)
    update_cols = {c: getattr(stmt.excluded, c) for c in rows[0].keys() if c not in conflict_cols}
    stmt = stmt.on_conflict_do_update(index_elements=conflict_cols, set_=update_cols)
    await session.execute(stmt)


async def import_taric_files(
    goods_file: Path,
    measures_file: Path,
    add_codes_file: Path,
    snapshot_date: date,
    source_label: str,
    force: bool = False,
) -> dict[str, Any]:
    async with SessionLocal() as session:
        goods_hash = _file_hash(goods_file)
        measures_hash = _file_hash(measures_file)
        add_codes_hash = _file_hash(add_codes_file)
        files_hash = hashlib.sha256(f"{goods_hash}{measures_hash}{add_codes_hash}".encode()).hexdigest()

        existing = await session.execute(
            pg_insert(TaricSnapshot)
            .values(
                snapshot_date=snapshot_date,
                source_label=source_label,
                files_hash=files_hash,
            )
            .on_conflict_do_nothing(index_elements=["snapshot_date", "files_hash"])
            .returning(TaricSnapshot)
        )
        snapshot = existing.scalar_one_or_none()
        if snapshot is None and not force:
            logger.info("taric_import_skip", snapshot_date=str(snapshot_date), files_hash=files_hash)
            return {"status": "skipped", "snapshot_date": str(snapshot_date)}

        goods_df = _normalize_columns(pd.read_excel(goods_file))
        measures_df = _normalize_columns(pd.read_excel(measures_file))
        add_codes_df = _normalize_columns(pd.read_excel(add_codes_file))

        goods_df = goods_df.rename(
            columns={
                "goods_code": "goods_code",
                "commodity_code": "goods_code",
                "parent_goods_code": "parent_goods_code",
                "hierarchical_level": "level",
                "productline_suffix": "suffix",
                "validity_start_date": "valid_from",
                "validity_end_date": "valid_to",
                "record_id": "source_record_id",
            }
        )

        goods_rows = []
        for row in _to_records(goods_df):
            goods_rows.append(
                {
                    "goods_code": str(row.get("goods_code", "")),
                    "parent_goods_code": row.get("parent_goods_code"),
                    "level": row.get("level"),
                    "suffix": row.get("suffix"),
                    "valid_from": _parse_date(row.get("valid_from")),
                    "valid_to": _parse_date(row.get("valid_to")),
                    "source_record_id": row.get("source_record_id"),
                }
            )
        goods_code_set = {row["goods_code"] for row in goods_rows if row["goods_code"]}
        await _upsert(session, GoodsNomenclature, goods_rows, ["goods_code"])

        if "description" in goods_df.columns:
            desc_rows = []
            for row in _to_records(goods_df):
                if not row.get("description"):
                    continue
                desc_rows.append(
                    {
                        "goods_code": str(row.get("goods_code", "")),
                        "lang": row.get("language", "EN"),
                        "description": row.get("description"),
                        "valid_from": _parse_date(row.get("valid_from")),
                        "valid_to": _parse_date(row.get("valid_to")),
                    }
                )
            await _upsert(session, GoodsDescription, desc_rows, ["goods_code", "lang", "valid_from"])

        measures_df = measures_df.rename(
            columns={
                "measure_sid": "measure_uid",
                "measure_uid": "measure_uid",
                "goods_code": "goods_code",
                "commodity_code": "goods_code",
                "measure_type_id": "measure_type_code",
                "measure_type_code": "measure_type_code",
                "geographical_area_id": "geo_code",
                "geo_area_id": "geo_code",
                "regulation_id": "regulation_ref",
                "regulation_ref": "regulation_ref",
                "validity_start_date": "valid_from",
                "validity_end_date": "valid_to",
            }
        )

        measure_rows = []
        geo_rows = []
        for row in _to_records(measures_df):
            geo_code = row.get("geo_code")
            if geo_code:
                geo_rows.append({"geo_code": geo_code, "type": None, "description": None})
            goods_code = str(row.get("goods_code", ""))
            orphan = goods_code not in goods_code_set
            if orphan:
                logger.info("taric_orphan_measure", goods_code=goods_code, measure_uid=row.get("measure_uid"))
            measure_rows.append(
                {
                    "measure_uid": str(row.get("measure_uid")),
                    "goods_code": goods_code,
                    "measure_type_code": str(row.get("measure_type_code", "")),
                    "geo_code": str(geo_code or ""),
                    "regulation_ref": row.get("regulation_ref"),
                    "valid_from": _parse_date(row.get("valid_from")),
                    "valid_to": _parse_date(row.get("valid_to")),
                    "raw_payload_json": row,
                    "orphan_goods_code": orphan,
                }
            )
        await _upsert(session, GeoArea, geo_rows, ["geo_code"])
        await _upsert(session, Measure, measure_rows, ["measure_uid"])

        if "duty_expression" in measures_df.columns:
            expr_rows = []
            link_rows = []
            for row in _to_records(measures_df):
                expr = row.get("duty_expression")
                if not expr:
                    continue
                expr_rows.append(
                    {
                        "expression_text": expr,
                        "currency": row.get("duty_currency"),
                        "uom": row.get("duty_uom"),
                        "valid_from": _parse_date(row.get("valid_from")),
                        "valid_to": _parse_date(row.get("valid_to")),
                    }
                )
                link_rows.append(
                    {
                        "measure_uid": str(row.get("measure_uid")),
                        "expression_text": expr,
                        "seq_no": 1,
                    }
                )
            await _upsert(session, DutyExpression, expr_rows, ["expression_text", "valid_from"])
            await _upsert(session, MeasureDutyExpression, link_rows, ["measure_uid", "expression_text"])

        add_codes_df = add_codes_df.rename(
            columns={
                "additional_code_type_id": "code_type",
                "additional_code_type": "code_type",
                "additional_code": "code",
                "additional_code_id": "code",
                "description": "description",
                "validity_start_date": "valid_from",
                "validity_end_date": "valid_to",
            }
        )

        add_rows = []
        for row in _to_records(add_codes_df):
            add_rows.append(
                {
                    "code_type": row.get("code_type"),
                    "code": row.get("code"),
                    "description": row.get("description"),
                    "valid_from": _parse_date(row.get("valid_from")),
                    "valid_to": _parse_date(row.get("valid_to")),
                }
            )
        await _upsert(session, AdditionalCode, add_rows, ["code_type", "code", "valid_from"])

        if "measure_uid" in add_codes_df.columns and "code_type" in add_codes_df.columns:
            mac_rows = []
            for row in _to_records(add_codes_df):
                if not row.get("measure_uid"):
                    continue
                mac_rows.append(
                    {
                        "measure_uid": str(row.get("measure_uid")),
                        "additional_code_type": row.get("code_type"),
                        "additional_code": row.get("code"),
                    }
                )
            await _upsert(session, MeasureAdditionalCode, mac_rows, ["measure_uid", "additional_code_type", "additional_code"])

        await session.commit()

        logger.info(
            "taric_import_complete",
            snapshot_date=str(snapshot_date),
            files_hash=files_hash,
            goods_rows=len(goods_rows),
            measure_rows=len(measure_rows),
            add_code_rows=len(add_rows),
        )
        return {
            "status": "ok",
            "snapshot_date": str(snapshot_date),
            "files_hash": files_hash,
            "goods_rows": len(goods_rows),
            "measure_rows": len(measure_rows),
            "add_code_rows": len(add_rows),
        }


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-date", required=False)
    parser.add_argument("--dir", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    snapshot_date = date.fromisoformat(args.snapshot_date) if args.snapshot_date else date.today()
    base_dir = Path(args.dir)
    goods_file = next(base_dir.glob("Goods_Nomenclature_*.xlsx"))
    measures_file = next(base_dir.glob("Measures_*.xlsx"))
    add_codes_file = next(base_dir.glob("Add_Codes_*.xlsx"))

    import asyncio

    asyncio.run(
        import_taric_files(
            goods_file=goods_file,
            measures_file=measures_file,
            add_codes_file=add_codes_file,
            snapshot_date=snapshot_date,
            source_label="taric_excel",
            force=args.force,
        )
    )


if __name__ == "__main__":
    main()
