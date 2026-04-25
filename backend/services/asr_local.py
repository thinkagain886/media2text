# -*- coding: utf-8 -*-
"""FunASR：单例 + 加载状态（idle/loading/ready/failed）"""

from __future__ import annotations

import asyncio
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config_loader import settings
from core.logger import get_logger, log_error, log_step, log_timing

LOG = get_logger("asr_local")

_model_lock = threading.Lock()
_model: Any = None
_init_time: Optional[float] = None

_status: str = "idle"
_load_err: Optional[str] = None
_async_ready = asyncio.Event()
_bg_task: Optional[asyncio.Task] = None


def get_status_payload() -> Dict[str, Any]:
    return {"status": _status, "error": _load_err}


def _create_model() -> Any:
    from funasr import AutoModel

    model_dir = settings.modelscope_cache or os.path.expanduser("~/.cache/modelscope")
    LOG.info("使用 ModelScope 模型缓存目录: %s", model_dir)
    return AutoModel(
        model="paraformer-zh",
        vad_model="fsmn-vad",
        vad_kwargs={"max_single_segment_time": 60000},
        punc_model="ct-punc",
        device="cpu",
        model_dir=model_dir,
    )


def get_funasr_model() -> Any:
    """同步加载单例（可在后台线程调用）。"""
    global _model, _init_time
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            t0 = time.perf_counter()
            cache_hint = settings.modelscope_cache or os.path.expanduser(
                "~/.cache/modelscope"
            )
            log_step(
                LOG,
                "-",
                "init",
                "开始初始化 FunASR 模型",
                modelscope_cache=cache_hint,
            )
            _model = _create_model()
            _init_time = time.perf_counter() - t0
            log_timing(LOG, "-", "funasr_init", _init_time)
    return _model


async def _wait_ready(trace_id: str) -> None:
    if _status == "ready":
        return
    if _status == "failed":
        raise RuntimeError(_load_err or "FunASR 加载失败")
    await _async_ready.wait()
    if _status == "failed":
        raise RuntimeError(_load_err or "FunASR 加载失败")


async def schedule_preload_if_needed(trace_id: str = "-") -> None:
    """触发表征加载（若尚未开始）。"""
    global _bg_task, _status, _load_err
    if _status == "ready":
        return
    if _status == "loading":
        return
    if _bg_task and not _bg_task.done():
        return
    if _status == "failed":
        _status = "idle"
        _load_err = None

    _status = "loading"
    _load_err = None
    _async_ready.clear()

    async def _run() -> None:
        global _status, _load_err
        try:
            LOG.info("FunASR 模型加载中（后台）...", extra={"trace_id": trace_id})
            t0 = time.perf_counter()
            await asyncio.to_thread(get_funasr_model)
            elapsed = time.perf_counter() - t0
            _status = "ready"
            LOG.info("FunASR 模型加载完成，耗时 %.2fs", elapsed, extra={"trace_id": trace_id})
        except Exception as e:
            _status = "failed"
            _load_err = str(e)
            LOG.warning("FunASR 加载失败: %s", e, extra={"trace_id": trace_id})
        finally:
            _async_ready.set()

    _bg_task = asyncio.create_task(_run())


def start_background_preload_from_lifespan(trace_id: str = "-") -> None:
    """lifespan 内非阻塞调用。"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(schedule_preload_if_needed(trace_id))


def _sync_transcribe(audio_path: Path) -> str:
    model = get_funasr_model()
    res: List[Any] = model.generate(
        input=str(audio_path.resolve()),
        batch_size_s=300,
        hotword="",
    )
    if not res:
        return ""
    first = res[0]
    if isinstance(first, dict) and "text" in first:
        return str(first["text"])
    return ""


async def transcribe(audio_path: Path, trace_id: str) -> str:
    log_step(LOG, trace_id, "funasr", "开始本地转写", file=str(audio_path))
    if _status == "idle":
        await schedule_preload_if_needed(trace_id)
    await _wait_ready(trace_id)
    t0 = time.perf_counter()
    try:
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, _sync_transcribe, audio_path)
    except Exception as e:
        log_error(LOG, trace_id, "funasr", e, file=str(audio_path))
        raise
    elapsed = time.perf_counter() - t0
    log_timing(
        LOG,
        trace_id,
        "funasr_transcribe",
        elapsed,
        file=str(audio_path),
        chars=len(text or ""),
    )
    return text or ""
