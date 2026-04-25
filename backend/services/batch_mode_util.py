# -*- coding: utf-8 -*-
"""batch_mode：配置值 / 存储 / 展示 统一"""
from typing import Any


def normalize_batch_mode_db(raw: Any) -> str:
    """写入 SQLite：统一为中文「单数据」「批数据」。兼容配置里的 separate/merge。"""
    s = str(raw or "").strip()
    if s in ("merge", "批数据"):
        return "批数据"
    if s in ("separate", "单数据"):
        return "单数据"
    if s in ("单数据", "批数据"):
        return s
    return "单数据"


def normalize_batch_mode_display(stored: Any) -> str:
    """列表/对外展示。"""
    s = str(stored or "").strip()
    if s in ("separate", "单数据"):
        return "单数据"
    if s in ("merge", "批数据"):
        return "批数据"
    if s in ("单数据", "批数据"):
        return s
    return "单数据"
