# -*- coding: utf-8 -*-
"""历史记录 API"""

from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services import db
from services.history_export import records_to_csv_bytes, records_to_excel_bytes
from services.history_ops import (
    push_record_feishu,
    push_record_notion,
    summarize_record,
    upload_caption_oss_record,
)

router = APIRouter(tags=["history"])


class HistoryIdsBody(BaseModel):
    ids: List[int] = Field(..., min_length=1)


class ExportBody(BaseModel):
    """ids 为空或省略表示导出全部；fmt 默认 xlsx，csv 便于 Notion 导入"""

    ids: Optional[List[int]] = None
    fmt: Literal["xlsx", "csv"] = "xlsx"


class UpdateHistoryBody(BaseModel):
    captions: Optional[str] = None
    summary: Optional[str] = None


@router.get("/history")
async def list_history(page: int = 1, page_size: int = 20):
    return await db.get_records(page=page, page_size=page_size)


@router.get("/history/{record_id}")
async def get_one(record_id: int):
    row = await db.get_record(record_id)
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    return row


@router.delete("/history/{record_id}")
async def remove(record_id: int):
    await db.delete_record(record_id)
    return {"ok": True}


@router.post("/history/delete-batch")
async def delete_batch(body: HistoryIdsBody):
    n = await db.delete_records(body.ids)
    return {"ok": True, "deleted": n}


@router.delete("/history")
async def clear_history():
    await db.clear_all_records()
    return {"ok": True}


@router.post("/history/export-excel")
async def export_excel(body: ExportBody):
    # ids 省略或 [] 表示导出全部
    ids_param = None if body.ids is None or len(body.ids) == 0 else body.ids
    rows = await db.fetch_records_for_export(ids_param)
    if not rows:
        raise HTTPException(status_code=400, detail="没有可导出的记录")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if body.fmt == "csv":
        data = records_to_csv_bytes(rows)
        name = f"history_{ts}.csv"
        return StreamingResponse(
            iter([data]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )
    data = records_to_excel_bytes(rows)
    name = f"history_{ts}.xlsx"
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.put("/history/{record_id}")
async def update_history_record(record_id: int, body: UpdateHistoryBody):
    if body.captions is None and body.summary is None:
        raise HTTPException(status_code=400, detail="至少提供 captions 或 summary")
    await db.update_record_content(
        record_id,
        captions=body.captions,
        summary=body.summary,
    )
    row = await db.get_record(record_id)
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"ok": True, "record": row}


@router.post("/history/{record_id}/summarize")
async def history_summarize(record_id: int):
    try:
        row = await summarize_record(record_id)
        return {"ok": True, "record": row}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/history/{record_id}/upload-caption-oss")
async def history_upload_caption_oss(record_id: int):
    try:
        row = await upload_caption_oss_record(record_id)
        return {"ok": True, "record": row}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/history/{record_id}/push/notion")
async def history_push_notion(record_id: int):
    try:
        row = await push_record_notion(record_id)
        return {"ok": True, "record": row}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/history/{record_id}/push/feishu")
async def history_push_feishu(record_id: int):
    try:
        row = await push_record_feishu(record_id)
        return {"ok": True, "record": row}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
