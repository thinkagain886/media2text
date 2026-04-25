# -*- coding: utf-8 -*-
"""推送：按输出 JSON 扁平化字段；Notion Database ID 规范化"""

import json
import re
from typing import Any, Dict, List, Tuple

# 输出 JSON（ProcessResult 序列化）字段说明，供用户在 Notion / 飞书中手动建列
OUTPUT_FIELD_GUIDE: List[Dict[str, str]] = [
    {"key": "title", "notion_type": "Title（标题）", "feishu_type": "文本 或 多行文本"},
    {"key": "captions", "notion_type": "Rich text（富文本）", "feishu_type": "多行文本"},
    {"key": "summary", "notion_type": "Rich text", "feishu_type": "多行文本"},
    {"key": "status", "notion_type": "Rich text", "feishu_type": "文本"},
    {"key": "error_msg", "notion_type": "Rich text", "feishu_type": "多行文本"},
    {"key": "record_id", "notion_type": "Rich text（存数字）", "feishu_type": "文本"},
    {"key": "record_uuid", "notion_type": "Rich text（32 位 hex）", "feishu_type": "文本"},
    {
        "key": "source_files",
        "notion_type": "Rich text（JSON 字符串）",
        "feishu_type": "多行文本（JSON）",
    },
]


def normalize_notion_database_id(raw: str) -> str:
    """
    Notion API 要求 database_id 为标准 UUID。
    支持：完整带连字符、32 位无连字符 hex、或 Notion URL 中的 id。
    """
    s = (raw or "").strip()
    if not s:
        raise ValueError("Notion Database ID 为空")

    # 从 URL 提取 32 hex
    m = re.search(r"([0-9a-f]{32})(?:\?|$|/)", s, re.I)
    hex32 = None
    if m:
        hex32 = m.group(1).lower()
    else:
        compact = re.sub(r"[^0-9a-fA-F]", "", s)
        if len(compact) == 32:
            hex32 = compact.lower()

    if hex32 and len(hex32) == 32:
        return (
            f"{hex32[:8]}-{hex32[8:12]}-{hex32[12:16]}-"
            f"{hex32[16:20]}-{hex32[20:]}"
        )

    # 已是标准 UUID 格式
    if re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        s,
        re.I,
    ):
        return s.lower()

    raise ValueError(
        "Notion Database ID 须为 32 位十六进制或标准 UUID（可在数据库页面 URL 中复制 id= 后一段），"
        "不能填数据库名称或 workspace 名。"
    )


def _rich_chunks(text: str, size: int = 1800) -> List[str]:
    if not text:
        return [""]
    out: List[str] = []
    i = 0
    while i < len(text):
        out.append(text[i : i + size])
        i += size
    return out


def notion_rich_prop(text: str) -> Dict[str, Any]:
    t = text or ""
    if not t.strip():
        t = " "
    parts: List[Dict[str, Any]] = []
    for ch in _rich_chunks(t):
        parts.append({"type": "text", "text": {"content": ch}})
    return {"rich_text": parts}


def notion_title_prop(title: str) -> Dict[str, Any]:
    return {"title": [{"type": "text", "text": {"content": (title or "")[:2000]}}]}


def item_to_notion_properties(item: Dict[str, Any]) -> Dict[str, Any]:
    """按输出 JSON 键名映射；title 列用 Title，其余用 Rich text。"""
    props: Dict[str, Any] = {}
    title_val = str(item.get("title") or "")[:2000]

    for key, val in item.items():
        if val is None:
            continue
        if key == "title":
            props[key] = notion_title_prop(title_val)
            continue
        if isinstance(val, (dict, list)):
            props[key] = notion_rich_prop(json.dumps(val, ensure_ascii=False))
        elif isinstance(val, bool):
            props[key] = notion_rich_prop("true" if val else "false")
        elif isinstance(val, int):
            props[key] = notion_rich_prop(str(val))
        else:
            props[key] = notion_rich_prop(str(val))

    if "title" not in props:
        props["title"] = notion_title_prop(title_val)

    return props


def item_to_feishu_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    """多维表格字段名与 JSON 键一致；复杂类型转 JSON 字符串。"""
    fields: Dict[str, Any] = {}
    for key, val in item.items():
        if val is None:
            continue
        if isinstance(val, (dict, list)):
            fields[key] = json.dumps(val, ensure_ascii=False)
        elif isinstance(val, bool):
            fields[key] = "true" if val else "false"
        else:
            fields[key] = str(val)
    return fields
