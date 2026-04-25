# -*- coding: utf-8 -*-
"""推送到 Notion / 飞书"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core import redis_client as R
from core.logger import get_logger, log_error
from models.schemas import DEFAULT_CONFIG_DICT, ProcessConfig, process_config_from_merged
from services import db
from services.feishu_push import push_items_to_feishu
from services.integration_payload import INTEGRATION_SCHEMA_ROWS
from services.notion_push import push_items_to_notion

router = APIRouter(tags=["push"])
LOG = get_logger("push_api")


class PushBody(BaseModel):
    """每项为一条 ProcessResult 的 JSON；record_id 可选用于回写历史推送状态"""

    items: List[Dict[str, Any]] = Field(..., min_length=1)


async def _cfg() -> ProcessConfig:
    merged = dict(DEFAULT_CONFIG_DICT)
    merged.update(await R.get_config())
    return process_config_from_merged(merged)


async def _resolve_integration_payloads(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from services.integration_payload import integration_dict_from_row

    out: List[Dict[str, Any]] = []
    for it in items:
        rid = it.get("record_id")
        if rid is not None:
            try:
                row = await db.get_record(int(rid))
            except (TypeError, ValueError):
                row = None
            if row:
                out.append(integration_dict_from_row(row))
                continue
        out.append(integration_dict_from_row(it))
    return out


@router.get("/push/field-guide")
async def field_guide():
    """兼容旧路径；与 GET /integrations/schema 一致。"""
    return {
        "fields": INTEGRATION_SCHEMA_ROWS,
        "notion_note": "列名与 fields.key 一致；title 为 Title，record_uuid/正文等为 Rich text，日期为 Date，分类/模式为 Select。",
        "feishu_note": "列名与 key 一致；created_at/updated_at 为日期时间列（UTC 毫秒整数）；source_files 勿用多选。",
    }


@router.post("/push/notion")
async def push_notion(body: PushBody):
    cfg = await _cfg()
    payloads = await _resolve_integration_payloads(body.items)
    try:
        await push_items_to_notion(payloads, cfg, trace_id="-")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        log_error(LOG, "-", "push_notion", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

    ids = _collect_record_ids(body.items)
    if ids:
        await db.update_push_flags(ids, notion=True)
    return {"ok": True, "count": len(body.items)}


@router.post("/push/feishu")
async def push_feishu(body: PushBody):
    cfg = await _cfg()
    payloads = await _resolve_integration_payloads(body.items)
    try:
        await push_items_to_feishu(payloads, cfg, trace_id="-")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        log_error(LOG, "-", "push_feishu", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

    ids = _collect_record_ids(body.items)
    if ids:
        await db.update_push_flags(ids, feishu=True)
    return {"ok": True, "count": len(body.items)}


def _collect_record_ids(items: List[Dict[str, Any]]) -> List[int]:
    out: List[int] = []
    for it in items:
        rid = it.get("record_id")
        if rid is None:
            continue
        try:
            i = int(rid)
            if i > 0:
                out.append(i)
        except (TypeError, ValueError):
            continue
    return out
