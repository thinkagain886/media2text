# -*- coding: utf-8 -*-
"""数据库访问入口：委托 core.db_factory（SQLite / Supabase）。"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.db_factory import get_db


async def init_db() -> None:
    await (await get_db()).init()


async def save_record(record: Dict[str, Any]) -> Tuple[int, str]:
    return await (await get_db()).save_record(record)


async def update_record_summary(record_id: int, summary: str, has_summary: bool = True) -> None:
    await (await get_db()).update_record_summary(record_id, summary, has_summary)


async def update_record_caption_oss(
    record_id: int,
    source_files: List[dict],
    transcript_on_oss: bool = True,
) -> None:
    await (await get_db()).update_record_caption_oss(
        record_id, source_files, transcript_on_oss
    )


async def update_record_content(
    record_id: int,
    *,
    captions: Optional[str] = None,
    summary: Optional[str] = None,
) -> None:
    await (await get_db()).update_record_content(
        record_id, captions=captions, summary=summary
    )


async def get_records(page: int = 1, page_size: int = 20) -> dict:
    return await (await get_db()).get_records(page=page, page_size=page_size)


async def get_record(record_id: int) -> Optional[dict]:
    return await (await get_db()).get_record(record_id)


async def fetch_records_for_export(ids: Optional[Sequence[int]]) -> List[dict]:
    return await (await get_db()).fetch_records_for_export(ids)


async def update_push_flags(
    record_ids: Sequence[int], *, notion: bool = False, feishu: bool = False
) -> None:
    await (await get_db()).update_push_flags(record_ids, notion=notion, feishu=feishu)


async def delete_record(record_id: int) -> None:
    await (await get_db()).delete_record(record_id)


async def delete_records(ids: Sequence[int]) -> int:
    return await (await get_db()).delete_records(ids)


async def clear_all_records() -> None:
    await (await get_db()).clear_all_records()
