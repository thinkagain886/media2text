# -*- coding: utf-8 -*-
"""根据 Redis 配置返回数据库适配器单例"""

from pathlib import Path
from typing import Any, Dict, Optional

from core import redis_client as R
from core.config_loader import BACKEND_ROOT, settings
from models.schemas import DEFAULT_CONFIG_DICT
from services.db_adapter import BaseDBAdapter

_adapter: Optional[BaseDBAdapter] = None
_adapter_sig: str = ""


def _sqlite_path_from_config(merged: Dict[str, Any]) -> Path:
    raw = (merged.get("sqlite_path") or "").strip()
    if raw:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            return (BACKEND_ROOT / p).resolve()
        return p.resolve()
    sp = settings.sqlite_path
    if not sp.is_absolute():
        return (BACKEND_ROOT / sp).resolve()
    return sp.resolve()


def _make_sig(merged: Dict[str, Any]) -> str:
    eng = (merged.get("db_engine") or "sqlite").lower().strip()
    if eng == "supabase":
        return (
            f"{eng}|{merged.get('supabase_url','')}|{merged.get('supabase_key','')}|{merged.get('supabase_table','records')}"
        )
    return f"{eng}|{_sqlite_path_from_config(merged)}"


async def get_db() -> BaseDBAdapter:
    """获取当前应使用的适配器（配置变更后自动重建）。"""
    global _adapter, _adapter_sig
    merged = dict(DEFAULT_CONFIG_DICT)
    merged.update(await R.get_config())
    sig = _make_sig(merged)
    if _adapter is not None and sig == _adapter_sig:
        return _adapter

    eng = (merged.get("db_engine") or "sqlite").lower().strip()
    _adapter_sig = sig

    if eng == "supabase":
        from services.db_supabase import SupabaseAdapter

        _adapter = SupabaseAdapter(
            url=(merged.get("supabase_url") or "").strip(),
            key=(merged.get("supabase_key") or "").strip(),
            table=(merged.get("supabase_table") or "records").strip() or "records",
        )
    else:
        from services.db_sqlite import SQLiteAdapter

        _adapter = SQLiteAdapter(_sqlite_path_from_config(merged))

    await _adapter.init()
    return _adapter


def reset_db_adapter() -> None:
    """测试或热切换时可清空单例。"""
    global _adapter, _adapter_sig
    _adapter = None
    _adapter_sig = ""
