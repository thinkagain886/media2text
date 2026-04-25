# -*- coding: utf-8 -*-
"""推送 / Excel 导出统一字段（与 integrations/schema 一致）"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from services.batch_mode_util import normalize_batch_mode_display

INTEGRATION_KEYS_ORDER: List[str] = [
    "record_uuid",
    "created_at",
    "updated_at",
    "title",
    "category",
    "batch_mode",
    "recognition_type",
    "captions",
    "summary",
    "source_files",
]

# Excel/CSV 导出：不含 id；title 为首列（便于 Notion CSV 导入）
EXPORT_COLUMN_ORDER: List[str] = [
    "title",
    "record_uuid",
    "created_at",
    "updated_at",
    "category",
    "batch_mode",
    "recognition_type",
    "captions",
    "summary",
    "source_files",
]

INTEGRATION_SCHEMA_ROWS: List[Dict[str, str]] = [
    {"key": "title", "notion_type": "Title（首列标题）", "feishu_type": "文本"},
    {"key": "record_uuid", "notion_type": "Rich text", "feishu_type": "文本"},
    {
        "key": "created_at",
        "notion_type": "Date（库中设为含时间）",
        "feishu_type": "日期时间（毫秒时间戳，整数）",
    },
    {
        "key": "updated_at",
        "notion_type": "Date（库中设为含时间）",
        "feishu_type": "日期时间（毫秒时间戳，整数）",
    },
    {"key": "category", "notion_type": "Select", "feishu_type": "文本"},
    {"key": "batch_mode", "notion_type": "Select", "feishu_type": "文本"},
    {
        "key": "recognition_type",
        "notion_type": "Select",
        "feishu_type": "文本",
    },
    {"key": "captions", "notion_type": "Rich text", "feishu_type": "多行文本"},
    {"key": "summary", "notion_type": "Rich text", "feishu_type": "多行文本"},
    {
        "key": "source_files",
        "notion_type": "Rich text（JSON）",
        "feishu_type": "多行文本（勿用「多选」，否则易报 1254063）",
    },
]


def row_datetime_to_iso_utc_z(val: Any) -> str:
    """
    SQLite DATETIME（约定 UTC、无时区后缀）、Supabase TIMESTAMPTZ、或 ISO 字符串 → 统一为 ISO8601 UTC（…Z）。
    供 Notion Date、导出 CSV/Excel、以及飞书毫秒换算使用。
    """
    if val is None:
        return ""
    s = str(val).strip()
    if not s:
        return ""
    s2 = s.replace("Z", "+00:00")
    if " " in s2 and "T" not in s2[:19]:
        s2 = s2.replace(" ", "T", 1)
    try:
        dt = datetime.fromisoformat(s2)
    except ValueError:
        return s
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def row_datetime_to_ms_utc(val: Any) -> int:
    """飞书「日期」/「日期时间」列：毫秒 Unix 时间戳（整数，UTC）。"""
    z = row_datetime_to_iso_utc_z(val)
    if not z:
        return int(time.time() * 1000)
    try:
        dt = datetime.fromisoformat(z.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except Exception:
        return int(time.time() * 1000)


def sanitize_source_files_public(raw: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for x in raw or []:
        if not isinstance(x, dict):
            continue
        out.append(
            {
                "filename": x.get("filename") or "",
                "original_filename": x.get("original_filename") or None,
                "audio_oss_url": x.get("audio_oss_url"),
                "caption_oss_url": x.get("caption_oss_url"),
            }
        )
    return out


def integration_dict_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """单行历史记录 → 对外统一结构（顺序由 INTEGRATION_KEYS_ORDER 约定）。"""
    sfs = sanitize_source_files_public(row.get("source_files"))
    bm = normalize_batch_mode_display(row.get("batch_mode"))
    created = row_datetime_to_iso_utc_z(row.get("created_at"))
    updated = row_datetime_to_iso_utc_z(row.get("updated_at") or row.get("created_at"))
    return {
        "record_uuid": str(row.get("record_uuid") or ""),
        "created_at": created,
        "updated_at": updated,
        "title": str(row.get("title") or ""),
        "category": str(row.get("category") or ""),
        "batch_mode": bm,
        "recognition_type": str(row.get("recognition_type") or "funasr"),
        "captions": row.get("captions") or "",
        "summary": row.get("summary") or "",
        "source_files": json.dumps(sfs, ensure_ascii=False),
    }
