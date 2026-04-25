# -*- coding: utf-8 -*-
"""Notion Database：integration 字段集 + 按 record_uuid upsert"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from core.logger import get_logger, log_error, log_timing
from models.schemas import ProcessConfig
from services.integration_payload import integration_dict_from_row, row_datetime_to_iso_utc_z
from services.push_common import (
    normalize_notion_database_id,
    notion_rich_prop,
    notion_title_prop,
)

NOTION_VERSION = "2022-06-28"
_PAGES = "https://api.notion.com/v1/pages"
_QUERY = "https://api.notion.com/v1/databases/{}/query"

LOG = get_logger("notion_push")


def validate_notion_database_id_config(raw: str) -> None:
    s = (raw or "").strip()
    if not s:
        raise ValueError("Notion Database ID 为空")
    compact = re.sub(r"[^0-9a-fA-F]", "", s)
    if len(compact) == 32:
        return
    if re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", s, re.I
    ):
        return
    raise ValueError("Notion database_id 须为 32 位 hex 或标准 UUID")


def _notion_date_start(val: Any) -> Optional[str]:
    """Notion Date（含时间）：UTC ISO8601，与 integration 字典一致。"""
    s = row_datetime_to_iso_utc_z(val)
    return s or None


def notion_props_from_integration(d: Dict[str, Any]) -> Dict[str, Any]:
    props: Dict[str, Any] = {}
    props["record_uuid"] = notion_rich_prop(str(d.get("record_uuid") or ""))
    c = _notion_date_start(d.get("created_at"))
    u = _notion_date_start(d.get("updated_at"))
    props["created_at"] = {"date": {"start": c}} if c else {"date": None}
    props["updated_at"] = {"date": {"start": u}} if u else {"date": None}
    props["title"] = notion_title_prop(str(d.get("title") or "")[:2000])
    cat = str(d.get("category") or "默认分类").strip() or "默认分类"
    bm = str(d.get("batch_mode") or "单数据").strip() or "单数据"
    props["category"] = {"select": {"name": cat[:100]}}
    props["batch_mode"] = {"select": {"name": bm[:100]}}
    props["captions"] = notion_rich_prop(str(d.get("captions") or ""))
    props["summary"] = notion_rich_prop(str(d.get("summary") or ""))
    props["source_files"] = notion_rich_prop(str(d.get("source_files") or ""))
    return props


async def _query_page_id_by_uuid(
    client: httpx.AsyncClient,
    *,
    db_id: str,
    record_uuid: str,
    headers: Dict[str, str],
    trace_id: str,
) -> Optional[str]:
    body = {
        "page_size": 1,
        "filter": {
            "property": "record_uuid",
            "rich_text": {"equals": record_uuid},
        },
    }
    url = _QUERY.format(db_id)
    t0 = datetime.now(timezone.utc)
    r = await client.post(url, headers=headers, json=body)
    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
    log_timing(LOG, trace_id, "notion_query_uuid", elapsed, uuid=record_uuid[:8])
    if r.status_code >= 400:
        log_error(LOG, trace_id, "notion_query", Exception(r.text[:400]), status=r.status_code)
        return None
    data = r.json()
    results = data.get("results") or []
    if not results:
        return None
    return str(results[0].get("id") or "")


async def push_items_to_notion(
    items: List[Dict[str, Any]],
    cfg: ProcessConfig,
    *,
    trace_id: str = "-",
) -> None:
    token = (cfg.notion_integration_token or "").strip()
    raw_id = (cfg.notion_database_id or "").strip()
    if not token or not raw_id:
        raise ValueError("请在设置中填写 Notion Integration Token 与 Database ID")

    validate_notion_database_id_config(raw_id)

    try:
        db_id = normalize_notion_database_id(raw_id)
    except ValueError as e:
        raise ValueError(str(e)) from e

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
        for it in items:
            props = notion_props_from_integration(dict(it))
            ru = str(it.get("record_uuid") or "").strip()
            page_id: Optional[str] = None
            if ru:
                page_id = await _query_page_id_by_uuid(
                    client, db_id=db_id, record_uuid=ru, headers=headers, trace_id=trace_id
                )

            try:
                if page_id:
                    patch_url = f"{_PAGES}/{page_id}"
                    r = await client.patch(
                        patch_url, headers=headers, json={"properties": props}
                    )
                else:
                    body = {"parent": {"database_id": db_id}, "properties": props}
                    r = await client.post(_PAGES, headers=headers, json=body)
            except httpx.RequestError as e:
                raise ValueError(
                    "无法连接到 api.notion.com（网络或代理）。"
                    f" ({type(e).__name__}: {e})"
                ) from e

            if r.status_code >= 400:
                msg = f"Notion HTTP {r.status_code}: {r.text[:800]}"
                if r.status_code < 500:
                    raise ValueError(msg)
                raise RuntimeError(msg)
