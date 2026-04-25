# -*- coding: utf-8 -*-
"""历史记录导出 Excel / CSV（integration 字段集；无 id，title 首列）"""

import csv
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
from typing import Any, Dict, List

# 导出 CSV/Excel 时按东八区展示（与多数用户本地观感一致；数据仍以 UTC 解析）
_EXPORT_DISPLAY_TZ = timezone(timedelta(hours=8), name="CST")

from openpyxl import Workbook

from services.integration_payload import (
    EXPORT_COLUMN_ORDER,
    integration_dict_from_row,
)

_DT_KEYS = frozenset({"created_at", "updated_at"})


def _export_datetime_display(column_key: str, val: Any) -> Any:
    """
    CSV / Excel 展示用：2026/04/24 23:54:14（东八区，中国常用）。
    integration 仍为 UTC 的 …Z；此处先按 UTC 解析再转到东八区格式化。
    """
    if column_key not in _DT_KEYS:
        return val
    if val is None or val == "":
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
        return val
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    local = dt.astimezone(_EXPORT_DISPLAY_TZ)
    return local.strftime("%Y/%m/%d %H:%M:%S")


def records_to_excel_bytes(rows: List[Dict[str, Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "records"
    headers = list(EXPORT_COLUMN_ORDER)
    ws.append(headers)
    for r in rows:
        pack = integration_dict_from_row(r)
        line = [_export_datetime_display(k, pack.get(k, "")) for k in headers]
        ws.append(line)
    bio = BytesIO()
    wb.save(bio)
    return bio.getvalue()


def records_to_csv_bytes(rows: List[Dict[str, Any]]) -> bytes:
    buf = StringIO()
    headers = list(EXPORT_COLUMN_ORDER)
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        pack = integration_dict_from_row(r)
        w.writerow([_export_datetime_display(k, pack.get(k, "")) for k in headers])
    return buf.getvalue().encode("utf-8-sig")
