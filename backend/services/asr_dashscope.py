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


async def transcribe(oss_url: str, api_key: str, trace_id: str) -> str:
    if not (oss_url or "").strip():
        raise ValueError("百炼API需要OSS URL，请在设置中开启[上传音频到OSS]选项")

    log_step(
        LOG,
        trace_id,
        "dashscope_asr",
        "提交百炼转写任务",
        oss_url=oss_url,
        model="paraformer-v2",
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

    deadline = time.perf_counter() + 300.0
    last_rsp: Optional[Any] = None

    while time.perf_counter() < deadline:
        def _fetch():
            return Transcription.fetch(task_id, api_key=api_key)

        try:
            rsp = await asyncio.to_thread(_fetch)
        except Exception as e:
            log_error(LOG, trace_id, "dashscope_poll", e, task_id=task_id)
            raise

        last_rsp = rsp
        od = _out_dict(rsp)
        st = od.get("task_status") or od.get("taskStatus")
        nst = _norm_task_status(st)
        log_step(
            LOG,
            trace_id,
            "dashscope_poll",
            "轮询状态",
            task_id=task_id,
            status=st,
        )

        if nst == _norm_task_status(TaskStatus.SUCCEEDED):
            LOG.info(
                "百炼轮询成功 | task_id=%s | output=%s",
                task_id,
                json.dumps(od, ensure_ascii=False, default=str)[:12000],
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
        await asyncio.sleep(3)
    else:
        raise TimeoutError(f"百炼转写超时（300s） task_id={task_id}")

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
    return text
