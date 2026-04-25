# -*- coding: utf-8 -*-
"""结构化日志：时间戳、级别、trace_id、模块名、消息、可选耗时与附加字段"""

import logging
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from logging import Logger
from typing import Any

_DATE_FMT = "%Y-%m-%d %H:%M:%S"
# 日志行时间按固定时区偏移格式化（默认东八区；避免容器系统为 UTC 时少 8 小时）
_raw_tz_h = os.environ.get("LOG_TZ_OFFSET_HOURS", "8").strip()
try:
    _LOG_TZ_OFFSET_HOURS = int(_raw_tz_h) if _raw_tz_h else 8
except ValueError:
    _LOG_TZ_OFFSET_HOURS = 8
_LOG_TZ = timezone(timedelta(hours=max(-12, min(14, _LOG_TZ_OFFSET_HOURS))))


class _TraceFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "trace_id"):
            record.trace_id = "-"
        return True


class _LineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ct = datetime.fromtimestamp(record.created, tz=_LOG_TZ)
        ts = ct.strftime(_DATE_FMT)
        ms = int(getattr(record, "msecs", 0))
        tid = getattr(record, "trace_id", "-")
        return (
            f"{ts}.{ms:03d} | {record.levelname} | [trace:{tid}] | "
            f"{record.name} | {record.getMessage()}"
        )


def _setup_root_once() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    h = logging.StreamHandler(sys.stdout)
    h.setLevel(logging.INFO)
    h.addFilter(_TraceFilter())
    h.setFormatter(_LineFormatter())
    root.addHandler(h)


def get_logger(name: str) -> Logger:
    """获取带模块名的 logger。"""
    _setup_root_once()
    return logging.getLogger(name)


def log_step(
    logger: Logger,
    trace_id: str,
    step: str,
    msg: str,
    **kwargs: Any,
) -> None:
    """记录处理步骤（INFO）。"""
    tail = ""
    if kwargs:
        tail = " | " + " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(
        "%s | %s%s",
        step,
        msg,
        tail,
        extra={"trace_id": trace_id},
    )


def log_timing(
    logger: Logger,
    trace_id: str,
    step: str,
    elapsed: float,
    **kwargs: Any,
) -> None:
    """记录耗时（INFO）。"""
    parts = [f"耗时={elapsed:.2f}s"]
    for k, v in kwargs.items():
        parts.append(f"{k}={v}")
    tail = " | " + " | ".join(parts)
    logger.info("%s | 完成%s", step, tail, extra={"trace_id": trace_id})


def log_error(
    logger: Logger,
    trace_id: str,
    step: str,
    error: BaseException,
    **kwargs: Any,
) -> None:
    """记录错误（ERROR），含堆栈。"""
    tb = traceback.format_exc()
    tail = ""
    if kwargs:
        tail = " | " + " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.error(
        "%s | %s: %s%s\n%s",
        step,
        type(error).__name__,
        error,
        tail,
        tb,
        extra={"trace_id": trace_id},
    )
