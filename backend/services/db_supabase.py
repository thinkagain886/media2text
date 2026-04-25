# -*- coding: utf-8 -*-
"""
Supabase / Postgres 适配器（supabase-py）。

建表示例见文件末尾 SQL 注释。主键使用自增 id，record_uuid 唯一，便于与 SQLite 接口统一使用整数 id。
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple

from services.batch_mode_util import normalize_batch_mode_db, normalize_batch_mode_display
from services.db_adapter import BaseDBAdapter


def _normalize_supabase_url(url: str) -> str:
    """
    create_client 只需要项目根 URL（https://xxx.supabase.co）。
    若误填了 …/rest/v1，与客户端内部拼接后会变成 …/rest/v1/rest/v1/… → 404 / PGRST125。
    """
    s = (url or "").strip().rstrip("/")
    low = s.lower()
    for suf in ("/rest/v1",):
        if low.endswith(suf):
            s = s[: -len(suf)].rstrip("/")
            break
    return s


class SupabaseAdapter(BaseDBAdapter):
    def __init__(self, url: str, key: str, table: str = "records") -> None:
        self._url = _normalize_supabase_url((url or "").strip())
        self._key = (key or "").strip()
        self._table = table.strip() or "records"
        self._client: Any = None

    def _ensure(self) -> None:
        if not self._url or not self._key:
            raise ValueError("Supabase 未配置：请在设置中填写 supabase_url 与 supabase_key")
        if self._client is None:
            from supabase import create_client

            self._client = create_client(self._url, self._key)

    def _run(self, fn, *a, **kw):
        self._ensure()
        return fn(*a, **kw)

    async def init(self) -> None:
        await asyncio.to_thread(self._ensure)

    def _to_item(self, d: Dict[str, Any]) -> Dict[str, Any]:
        if not d:
            return d
        if isinstance(d.get("source_files"), str):
            try:
                d["source_files"] = json.loads(d["source_files"])
            except Exception:
                d["source_files"] = []
        for k in ("transcript_on_oss", "has_summary", "notion_pushed", "feishu_pushed"):
            if k in d and not isinstance(d[k], bool):
                d[k] = bool(d[k])
        d["transcript_uploaded_oss"] = d.get("transcript_on_oss", False)
        d["summarized"] = d.get("has_summary", False)
        d["pushed_notion"] = d.get("notion_pushed", False)
        d["pushed_feishu"] = d.get("feishu_pushed", False)
        d["recognition_type"] = d.get("recognition_type") or "funasr"
        bm = d.get("batch_mode")
        d["batch_mode_display"] = normalize_batch_mode_display(bm)
        return d

    def _insert_row(self, record: Dict[str, Any]) -> Tuple[int, str]:
        self._ensure()
        ru = (record.get("record_uuid") or "").strip() or uuid.uuid4().hex
        bm = normalize_batch_mode_db(record.get("batch_mode"))
        payload = {
            "task_id": record.get("task_id", ""),
            "category": record.get("category", "默认分类"),
            "batch_mode": bm,
            "title": record.get("title", ""),
            "source_files": json.dumps(record.get("source_files", []), ensure_ascii=False),
            "captions": record.get("captions"),
            "summary": record.get("summary"),
            "status": record.get("status", "success"),
            "transcript_on_oss": bool(record.get("transcript_on_oss")),
            "has_summary": bool(record.get("has_summary")),
            "notion_pushed": bool(record.get("notion_pushed")),
            "feishu_pushed": bool(record.get("feishu_pushed")),
            "record_uuid": ru,
            "recognition_type": (record.get("recognition_type") or "funasr")[:32],
        }
        res = self._client.table(self._table).insert(payload).execute()
        rows = getattr(res, "data", None) or []
        if not rows:
            raise RuntimeError("Supabase insert 无返回数据")
        row = rows[0]
        rid = int(row.get("id", 0))
        ruuid = str(row.get("record_uuid") or ru)
        return rid, ruuid

    async def save_record(self, record: Dict[str, Any]) -> Tuple[int, str]:
        return await asyncio.to_thread(self._insert_row, record)

    def _upd_summary(self, record_id: int, summary: str, has_summary: bool) -> None:
        self._ensure()
        self._client.table(self._table).update(
            {"summary": summary, "has_summary": has_summary}
        ).eq("id", record_id).execute()

    async def update_record_summary(self, record_id: int, summary: str, has_summary: bool = True) -> None:
        await asyncio.to_thread(self._upd_summary, record_id, summary, has_summary)

    def _upd_cap(self, record_id: int, source_files: List[dict], transcript_on_oss: bool) -> None:
        self._ensure()
        self._client.table(self._table).update(
            {
                "source_files": json.dumps(source_files, ensure_ascii=False),
                "transcript_on_oss": transcript_on_oss,
            }
        ).eq("id", record_id).execute()

    async def update_record_caption_oss(
        self,
        record_id: int,
        source_files: List[dict],
        transcript_on_oss: bool = True,
    ) -> None:
        await asyncio.to_thread(self._upd_cap, record_id, source_files, transcript_on_oss)

    def _upd_content(
        self,
        record_id: int,
        captions: Optional[str],
        summary: Optional[str],
    ) -> None:
        self._ensure()
        patch: Dict[str, Any] = {}
        if captions is not None:
            patch["captions"] = captions
        if summary is not None:
            patch["summary"] = summary
            patch["has_summary"] = bool(str(summary).strip())
        if not patch:
            return
        self._client.table(self._table).update(patch).eq("id", record_id).execute()

    async def update_record_content(
        self,
        record_id: int,
        *,
        captions: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> None:
        if captions is None and summary is None:
            return
        await asyncio.to_thread(self._upd_content, record_id, captions, summary)

    def _get_records(self, page: int, page_size: int) -> dict:
        self._ensure()
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        start = (page - 1) * page_size
        end = start + page_size - 1
        q = (
            self._client.table(self._table)
            .select("*", count="exact")
            .order("id", desc=True)
            .range(start, end)
        )
        res = q.execute()
        total = getattr(res, "count", None)
        if total is None:
            total = len(res.data or [])
        rows = res.data or []
        items = [self._to_item(dict(r)) for r in rows]
        return {"total": total, "items": items}

    async def get_records(self, page: int = 1, page_size: int = 20) -> dict:
        return await asyncio.to_thread(self._get_records, page, page_size)

    def _get_one(self, record_id: int) -> Optional[dict]:
        self._ensure()
        res = self._client.table(self._table).select("*").eq("id", record_id).limit(1).execute()
        rows = res.data or []
        if not rows:
            return None
        return self._to_item(dict(rows[0]))

    async def get_record(self, record_id: int) -> Optional[dict]:
        return await asyncio.to_thread(self._get_one, record_id)

    def _export(self, ids: Optional[Sequence[int]]) -> List[dict]:
        self._ensure()
        q = self._client.table(self._table).select("*").order("id")
        if ids is not None and len(ids) > 0:
            clean = []
            for x in ids:
                try:
                    xi = int(x)
                    if xi > 0:
                        clean.append(xi)
                except (TypeError, ValueError):
                    continue
            if not clean:
                return []
            res = q.in_("id", clean).execute()
        else:
            res = q.execute()
        return [self._to_item(dict(r)) for r in (res.data or [])]

    async def fetch_records_for_export(self, ids: Optional[Sequence[int]]) -> List[dict]:
        return await asyncio.to_thread(self._export, ids)

    def _push_flags(self, record_ids: Sequence[int], notion: bool, feishu: bool) -> None:
        self._ensure()
        for rid in record_ids:
            patch: Dict[str, Any] = {}
            if notion:
                patch["notion_pushed"] = True
            if feishu:
                patch["feishu_pushed"] = True
            if patch:
                self._client.table(self._table).update(patch).eq("id", int(rid)).execute()

    async def update_push_flags(
        self,
        record_ids: Sequence[int],
        *,
        notion: bool = False,
        feishu: bool = False,
    ) -> None:
        clean: List[int] = []
        for x in record_ids:
            try:
                xi = int(x)
                if xi > 0:
                    clean.append(xi)
            except (TypeError, ValueError):
                continue
        if not clean:
            return
        await asyncio.to_thread(self._push_flags, clean, notion, feishu)

    def _del_one(self, record_id: int) -> None:
        self._ensure()
        self._client.table(self._table).delete().eq("id", record_id).execute()

    async def delete_record(self, record_id: int) -> None:
        await asyncio.to_thread(self._del_one, record_id)

    def _del_many(self, ids: Sequence[int]) -> int:
        self._ensure()
        clean: List[int] = []
        for rid in ids:
            try:
                xi = int(rid)
                if xi > 0:
                    clean.append(xi)
            except (TypeError, ValueError):
                continue
        if not clean:
            return 0
        self._client.table(self._table).delete().in_("id", clean).execute()
        return len(clean)

    async def delete_records(self, ids: Sequence[int]) -> int:
        return await asyncio.to_thread(self._del_many, ids)

    def _clear(self) -> None:
        self._ensure()
        res = self._client.table(self._table).select("id").execute()
        for row in res.data or []:
            rid = row.get("id")
            if rid is not None:
                self._client.table(self._table).delete().eq("id", rid).execute()

    async def clear_all_records(self) -> None:
        await asyncio.to_thread(self._clear)


"""
-- Supabase SQL 示例（在 SQL Editor 执行；可按需调整）
CREATE TABLE IF NOT EXISTS public.records (
    id BIGSERIAL PRIMARY KEY,
    record_uuid TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    task_id TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '默认分类',
    batch_mode TEXT NOT NULL DEFAULT '单数据',
    title TEXT NOT NULL DEFAULT '',
    source_files TEXT NOT NULL DEFAULT '[]',
    captions TEXT,
    summary TEXT,
    status TEXT NOT NULL DEFAULT 'success',
    transcript_on_oss BOOLEAN NOT NULL DEFAULT FALSE,
    has_summary BOOLEAN NOT NULL DEFAULT FALSE,
    notion_pushed BOOLEAN NOT NULL DEFAULT FALSE,
    feishu_pushed BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_records_created ON public.records (created_at DESC);

CREATE OR REPLACE FUNCTION public.set_records_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_records_updated ON public.records;
CREATE TRIGGER tr_records_updated
BEFORE UPDATE ON public.records
FOR EACH ROW EXECUTE FUNCTION public.set_records_updated_at();

ALTER TABLE public.records ENABLE ROW LEVEL SECURITY;
-- 按需为 anon/service_role 添加 policy
"""
