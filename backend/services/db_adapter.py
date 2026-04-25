# -*- coding: utf-8 -*-
"""数据库适配器抽象基类"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Tuple


class BaseDBAdapter(ABC):
    """SQLite / Supabase 统一接口。"""

    @abstractmethod
    async def init(self) -> None:
        ...

    @abstractmethod
    async def save_record(self, record: Dict[str, Any]) -> Tuple[int, str]:
        """返回 (整数 id, record_uuid 32位 hex)"""

    @abstractmethod
    async def update_record_summary(self, record_id: int, summary: str, has_summary: bool = True) -> None:
        ...

    @abstractmethod
    async def update_record_caption_oss(
        self,
        record_id: int,
        source_files: List[dict],
        transcript_on_oss: bool = True,
    ) -> None:
        ...

    @abstractmethod
    async def update_record_content(
        self,
        record_id: int,
        *,
        captions: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> None:
        """更新原文/总结；未传入的字段不改。任意字段变更会刷新 updated_at。"""

    @abstractmethod
    async def get_records(self, page: int = 1, page_size: int = 20) -> dict:
        ...

    @abstractmethod
    async def get_record(self, record_id: int) -> Optional[dict]:
        ...

    @abstractmethod
    async def fetch_records_for_export(self, ids: Optional[Sequence[int]]) -> List[dict]:
        ...

    @abstractmethod
    async def update_push_flags(
        self,
        record_ids: Sequence[int],
        *,
        notion: bool = False,
        feishu: bool = False,
    ) -> None:
        ...

    @abstractmethod
    async def delete_record(self, record_id: int) -> None:
        ...

    @abstractmethod
    async def delete_records(self, ids: Sequence[int]) -> int:
        ...

    @abstractmethod
    async def clear_all_records(self) -> None:
        ...
