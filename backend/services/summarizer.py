# -*- coding: utf-8 -*-
"""可扩展的 AI 总结服务（当前：通义千问）"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any

from dashscope import Generation

from core.logger import get_logger, log_error, log_step, log_timing

LOG = get_logger("summarizer")


class BaseSummarizer(ABC):
    @abstractmethod
    async def summarize(self, text: str, prompt: str, trace_id: str) -> str:
        raise NotImplementedError


class QwenSummarizer(BaseSummarizer):
    def __init__(self, api_key: str, model: str = "qwen-plus") -> None:
        self._api_key = api_key.strip()
        self._model = model

    async def summarize(self, text: str, prompt: str, trace_id: str) -> str:
        if not self._api_key:
            raise ValueError("未配置通义千问 API Key（qwen_api_key）")
        user_content = f"{prompt}\n\n{text}"
        log_step(
            LOG,
            trace_id,
            "summarize",
            "调用通义千问",
            model=self._model,
            prompt_preview=(prompt[:50] if prompt else ""),
            input_chars=len(text or ""),
        )
        t0 = time.perf_counter()

        def _call() -> Any:
            return Generation.call(
                model=self._model,
                messages=[{"role": "user", "content": user_content}],
                api_key=self._api_key,
                result_format="message",
            )

        try:
            rsp = await asyncio.to_thread(_call)
        except Exception as e:
            log_error(LOG, trace_id, "summarize", e)
            raise

        elapsed = time.perf_counter() - t0
        if getattr(rsp, "status_code", None) != 200:
            msg = getattr(rsp, "message", "") or ""
            log_error(
                LOG,
                trace_id,
                "summarize",
                RuntimeError(msg),
                code=getattr(rsp, "code", ""),
            )
            raise RuntimeError(f"通义千问调用失败: {msg}")

        out = ""
        output = getattr(rsp, "output", None)
        if output is not None:
            tx = getattr(output, "text", None)
            if tx:
                out = str(tx).strip()
            if not out:
                choices = getattr(output, "choices", None)
                if choices and len(choices) > 0:
                    m = getattr(choices[0], "message", None)
                    if m is not None:
                        out = str(getattr(m, "content", "") or "").strip()
        log_timing(
            LOG,
            trace_id,
            "summarize",
            elapsed,
            output_chars=len(out or ""),
            model=self._model,
        )
        return out


def get_summarizer(model_name: str, api_key: str) -> BaseSummarizer:
    """工厂：当前支持 qwen。"""
    name = (model_name or "qwen").lower()
    if name == "qwen":
        return QwenSummarizer(api_key=api_key)
    raise ValueError(f"不支持的总结模型: {model_name}")
