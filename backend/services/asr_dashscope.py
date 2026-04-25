# -*- coding: utf-8 -*-
"""阿里云百炼文件转写（需公网 OSS URL）"""

import asyncio
import json
import time
import urllib.request
from typing import Any, Dict, Optional

from dashscope.audio.asr import Transcription
from dashscope.common.constants import TaskStatus

from core.logger import get_logger, log_error, log_step, log_timing

LOG = get_logger("asr_dashscope")

# 百炼轮询：基于 ffprobe 媒体时长（秒）；拿到 task_id 后轮询总时限
_DASHSCOPE_POLL_DEADLINE_SEC = 600.0
_FIRST_WAIT_MIN_SEC = 0.2
# 首等：片长 × 1.5%（每 100s 音频等 1.5s 再查第一次），下限 0.2s；极长片封顶避免久无反馈
_FIRST_WAIT_RATIO = 0.015
_FIRST_WAIT_MAX_SEC = 120.0
# 第 2 次及以后每次未完成时的固定 sleep，由时长映射到 [0.5, 5]
_REPEAT_SLEEP_MIN_SEC = 0.5
_REPEAT_SLEEP_MAX_SEC = 5.0
# repeat = clamp( T / _REPEAT_SLEEP_DIVISOR )
_REPEAT_SLEEP_DIVISOR = 600.0
# ffprobe 失败时用于估算的默认时长（秒）
_FALLBACK_DURATION_SEC = 120.0


def dashscope_first_wait_after_submit_sec(duration_sec: float) -> float:
    """提交成功后、第 1 次 fetch 前的本地等待（秒）：max(0.5, T×8%) 再封顶。"""
    d = max(0.0, float(duration_sec))
    if d <= 0:
        d = _FALLBACK_DURATION_SEC
    raw = d * _FIRST_WAIT_RATIO
    return max(_FIRST_WAIT_MIN_SEC, min(_FIRST_WAIT_MAX_SEC, raw))


def dashscope_repeat_poll_sleep_sec(duration_sec: float) -> float:
    """第 1 次 fetch 之后，若仍处理中，每次再查询前的固定 sleep（秒）。"""
    d = max(0.0, float(duration_sec))
    if d <= 0:
        d = _FALLBACK_DURATION_SEC
    raw = d / _REPEAT_SLEEP_DIVISOR
    return max(_REPEAT_SLEEP_MIN_SEC, min(_REPEAT_SLEEP_MAX_SEC, raw))


def _out_dict(rsp: Any) -> Dict[str, Any]:
    out = getattr(rsp, "output", None)
    if out is None:
        return {}
    if isinstance(out, dict):
        return out
    try:
        return dict(out)
    except Exception:
        return {}


def _text_from_transcription_payload(data: Any) -> str:
    """从 transcription_url 下载的 JSON 或内联结构中抽取全文（百炼多为 transcripts 数组）。"""
    if data is None:
        return ""
    if isinstance(data, list):
        parts: list[str] = []
        for item in data:
            if isinstance(item, dict):
                t = item.get("text") or item.get("sentence") or item.get("content")
                if t:
                    parts.append(str(t).strip())
        return " ".join(parts) if parts else ""
    if isinstance(data, dict):
        if data.get("text"):
            return str(data["text"]).strip()
        for key in ("transcripts", "sentences", "words", "results", "result"):
            arr = data.get(key)
            if not isinstance(arr, list) or not arr:
                continue
            parts = []
            for item in arr:
                if not isinstance(item, dict):
                    continue
                t = item.get("text") or item.get("sentence") or item.get("content")
                if t:
                    parts.append(str(t).strip())
            if parts:
                return " ".join(parts)
    return ""


def _norm_task_status(st: Any) -> str:
    if st is None:
        return ""
    return str(st).strip().upper()


def _extract_text(final_rsp: Any) -> str:
    """解析百炼返回结果，兼容对象/字典格式及 transcription_url 下载。"""
    try:
        out = getattr(final_rsp, "output", None)
        if not out:
            LOG.warning("响应无 output 字段")
            return ""

        od = out if isinstance(out, dict) else getattr(out, "__dict__", {})
        if not isinstance(od, dict):
            od = dict(out) if hasattr(out, "keys") else {}

        results = od.get("results")
        try:
            snap = json.dumps(od, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            snap = str(od)[:8000]
        if len(snap) > 16000:
            snap = snap[:16000] + "...(truncated)"
        LOG.info("百炼转写 output 快照 | %s", snap, extra={"trace_id": "-"})

        if not isinstance(results, list) or not results:
            LOG.warning("results 为空或格式异常, output keys: %s", list(od.keys()))
            return ""

        r0 = results[0]
        r0_d = r0 if isinstance(r0, dict) else getattr(r0, "__dict__", {})

        sub_err = r0_d.get("subtask_status") or r0_d.get("message") or ""
        if sub_err and str(sub_err).upper() not in ("SUCCEEDED", "SUCCESS", ""):
            LOG.warning(
                "百炼子任务状态: %s | result[0] keys=%s",
                sub_err,
                list(r0_d.keys()),
            )

        # 1. 直接包含 text 字段
        if r0_d.get("text"):
            return str(r0_d["text"]).strip()

        # 2. transcripts 数组结构（部分版本内联在 results[0]）
        trs = r0_d.get("transcripts")
        if isinstance(trs, list) and trs:
            t0 = trs[0] if isinstance(trs[0], dict) else getattr(trs[0], "__dict__", {})
            if t0.get("text"):
                return str(t0["text"]).strip()

        # 3. transcription_url：下载 JSON，常见为 {"transcripts":[{"text":"..."}]}，不是顶层 list
        trans_url = r0_d.get("transcription_url")
        if trans_url:
            try:
                LOG.info("检测到 transcription_url，正在下载解析 | url=%s...", str(trans_url)[:120])
                req = urllib.request.Request(trans_url, headers={"User-Agent": "Python/DashScope"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                text = _text_from_transcription_payload(data)
                if text:
                    return text
                LOG.warning(
                    "transcription_url JSON 未解析出文本 | 顶层类型=%s keys=%s",
                    type(data).__name__,
                    list(data.keys()) if isinstance(data, dict) else "n/a",
                )
            except Exception as e:
                LOG.error("解析 transcription_url 失败: %s", e)

        LOG.warning("未提取到文本。r0 包含的字段: %s", list(r0_d.keys()))
        return ""
    except Exception as e:
        LOG.error("_extract_text 处理异常: %s", e)
        return ""


async def transcribe(
    oss_url: str,
    api_key: str,
    trace_id: str,
    audio_duration_sec: Optional[float] = None,
    audio_bytes: Optional[int] = None,
) -> str:
    if not (oss_url or "").strip():
        raise ValueError("百炼API需要OSS URL，请在设置中开启[上传音频到OSS]选项")

    log_step(
        LOG,
        trace_id,
        "dashscope_asr",
        "提交百炼转写任务",
        oss_url=oss_url,
        model="paraformer-v2",
        audio_duration_sec=audio_duration_sec,
        audio_bytes=audio_bytes,
    )

    def _submit():
        return Transcription.async_call(
            model="paraformer-v2",
            file_urls=[oss_url],
            api_key=api_key,
            language_hints=["zh", "en"],
        )

    t0 = time.perf_counter()
    try:
        task_response = await asyncio.to_thread(_submit)
    except Exception as e:
        log_error(LOG, trace_id, "dashscope_submit", e, oss_url=oss_url)
        raise RuntimeError(f"百炼转写提交失败: {e}") from e

    if getattr(task_response, "status_code", None) != 200:
        msg = getattr(task_response, "message", "") or ""
        code = getattr(task_response, "code", "") or ""
        log_error(
            LOG,
            trace_id,
            "dashscope_submit",
            RuntimeError(msg),
            status_code=getattr(task_response, "status_code", None),
            code=code,
            message=msg,
        )
        raise RuntimeError(f"百炼转写提交失败: {code} {msg}")

    od0 = _out_dict(task_response)
    task_id = od0.get("task_id")
    if not task_id and getattr(task_response, "output", None) is not None:
        task_id = getattr(task_response.output, "task_id", None)
    if not task_id:
        raise RuntimeError("百炼未返回 task_id")
    log_step(LOG, trace_id, "dashscope_asr", "已提交任务", task_id=task_id)

    if audio_duration_sec is None or audio_duration_sec <= 0:
        LOG.warning(
            "百炼：未获取到有效 ffprobe 时长，轮询间隔按兜底 %.0fs 估算",
            _FALLBACK_DURATION_SEC,
            extra={"trace_id": trace_id},
        )
    d_used = (
        float(audio_duration_sec)
        if (audio_duration_sec is not None and audio_duration_sec > 0)
        else _FALLBACK_DURATION_SEC
    )
    first_wait = dashscope_first_wait_after_submit_sec(d_used)
    repeat_sleep = dashscope_repeat_poll_sleep_sec(d_used)
    LOG.info(
        "百炼：轮询参数（媒体时长 %.2fs）| 首等=%.2fs（片长×%.1f%%，封顶 %.0fs）"
        " | 未完成时固定再隔=%.2fs（T/%.0f，限 %.1f~%.1fs）| 轮询总时限=%.0fs | task_id=%s",
        d_used,
        first_wait,
        _FIRST_WAIT_RATIO * 100,
        _FIRST_WAIT_MAX_SEC,
        repeat_sleep,
        _REPEAT_SLEEP_DIVISOR,
        _REPEAT_SLEEP_MIN_SEC,
        _REPEAT_SLEEP_MAX_SEC,
        _DASHSCOPE_POLL_DEADLINE_SEC,
        task_id,
        extra={"trace_id": trace_id},
    )

    deadline = time.perf_counter() + _DASHSCOPE_POLL_DEADLINE_SEC
    last_rsp: Optional[Any] = None
    poll_round = 0

    LOG.info(
        "百炼：提交成功，本地先 asyncio.sleep(%.2f)s 后再发起第 1 次查询 | task_id=%s",
        first_wait,
        task_id,
        extra={"trace_id": trace_id},
    )
    await asyncio.sleep(first_wait)

    while time.perf_counter() < deadline:
        poll_round += 1
        if poll_round == 1:
            LOG.info(
                "百炼：开始第 1 次查询任务状态 | task_id=%s",
                task_id,
                extra={"trace_id": trace_id},
            )

        def _fetch():
            return Transcription.fetch(task_id, api_key=api_key)

        t_fetch = time.perf_counter()
        try:
            rsp = await asyncio.to_thread(_fetch)
        except Exception as e:
            log_error(LOG, trace_id, "dashscope_poll", e, task_id=task_id)
            raise

        fetch_sec = time.perf_counter() - t_fetch
        last_rsp = rsp
        od = _out_dict(rsp)
        st = od.get("task_status") or od.get("taskStatus")
        nst = _norm_task_status(st)

        if nst == _norm_task_status(TaskStatus.SUCCEEDED):
            LOG.info(
                "百炼：第 %d 次查询成功 | 耗时 %.2fs | task_id=%s",
                poll_round,
                fetch_sec,
                task_id,
                extra={"trace_id": trace_id},
            )
            try:
                snap = json.dumps(od, ensure_ascii=False, default=str)
                if len(snap) > 4000:
                    snap = snap[:4000] + "...(truncated)"
                LOG.info(
                    "百炼：成功结果 output 摘要 | task_id=%s | %s",
                    task_id,
                    snap,
                    extra={"trace_id": trace_id},
                )
            except (TypeError, ValueError):
                LOG.info(
                    "百炼：成功结果 output 摘要 | task_id=%s | %s",
                    task_id,
                    str(od)[:4000],
                    extra={"trace_id": trace_id},
                )
            break
        if nst in (
            _norm_task_status(TaskStatus.FAILED),
            _norm_task_status(TaskStatus.CANCELED),
            _norm_task_status(TaskStatus.UNKNOWN),
        ):
            msg = od.get("message") or getattr(rsp, "message", "") or ""
            sc = getattr(rsp, "status_code", None)
            log_error(
                LOG,
                trace_id,
                "dashscope_task",
                RuntimeError(str(msg)),
                task_id=task_id,
                status_code=sc,
                message=msg,
            )
            raise RuntimeError(
                f"百炼转写失败: task_id={task_id} status_code={sc} message={msg}"
            )
        LOG.info(
            "百炼：第 %d 次查询仍未完成（当前状态=%s）。本地将 asyncio.sleep(%.2f)s 后"
            " 发起第 %d 次查询（固定间隔，由片长推算）| task_id=%s",
            poll_round,
            st,
            repeat_sleep,
            poll_round + 1,
            task_id,
            extra={"trace_id": trace_id},
        )
        await asyncio.sleep(repeat_sleep)

    else:
        raise TimeoutError(
            f"百炼转写超时（{_DASHSCOPE_POLL_DEADLINE_SEC:.0f}s） task_id={task_id}"
        )

    text = _extract_text(last_rsp)
    if not (text or "").strip():
        LOG.error(
            "百炼任务已成功但解析文本为空 | task_id=%s | 请查看上方 output 快照与 transcription_url JSON 结构",
            task_id,
            extra={"trace_id": trace_id},
        )
    elapsed = time.perf_counter() - t0
    log_timing(
        LOG,
        trace_id,
        "dashscope_asr",
        elapsed,
        task_id=task_id,
        chars=len(text or ""),
    )
    LOG.info(
        "百炼语音识别结束 | 总耗时=%.2fs | 共轮询 %d 次 | 输出字数=%d | task_id=%s",
        elapsed,
        poll_round,
        len(text or ""),
        task_id,
        extra={"trace_id": trace_id},
    )
    return text
