# -*- coding: utf-8 -*-
"""通用重试（同步 / 异步）"""

from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable, Tuple, TypeVar

T = TypeVar("T")

MAX_ATTEMPTS = 3
_RETRY_DELAYS_SEC: Tuple[float, ...] = (1.0, 2.0)


def _delay_before_retry(attempt: int) -> float:
    idx = attempt - 1
    if idx < 0 or not _RETRY_DELAYS_SEC:
        return 0.0
    return _RETRY_DELAYS_SEC[min(idx, len(_RETRY_DELAYS_SEC) - 1)]


def retry_sync(
    fn: Callable[[], T],
    *,
    op: str,
    log,
    trace_id: str = "-",
    max_attempts: int = MAX_ATTEMPTS,
) -> T:
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt >= max_attempts:
                break
            wait = _delay_before_retry(attempt)
            log.warning(
                "%s 失败，%ds 后重试 (%d/%d) | trace=%s | %s",
                op,
                wait,
                attempt,
                max_attempts,
                trace_id,
                e,
                extra={"trace_id": trace_id},
            )
            time.sleep(wait)
    assert last_exc is not None
    raise last_exc


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    op: str,
    log,
    trace_id: str = "-",
    max_attempts: int = MAX_ATTEMPTS,
) -> T:
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except Exception as e:
            last_exc = e
            if attempt >= max_attempts:
                break
            wait = _delay_before_retry(attempt)
            log.warning(
                "%s 失败，%ds 后重试 (%d/%d) | trace=%s | %s",
                op,
                wait,
                attempt,
                max_attempts,
                trace_id,
                e,
                extra={"trace_id": trace_id},
            )
            await asyncio.sleep(wait)
    assert last_exc is not None
    raise last_exc
