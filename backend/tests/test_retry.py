# -*- coding: utf-8 -*-
"""重试逻辑与 OSS/转写集成测试（mock，无需真实网络）"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# backend 作为包根目录
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from core.retry import MAX_ATTEMPTS, retry_async, retry_sync  # noqa: E402


LOG = logging.getLogger("test_retry")


@pytest.fixture(autouse=True)
def _fast_retry(monkeypatch):
    """测试时不真实 sleep。"""
    monkeypatch.setattr("core.retry.time.sleep", lambda _: None)

    async def _noop_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("core.retry.asyncio.sleep", _noop_sleep)


def test_retry_sync_succeeds_on_second_attempt():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] < 2:
            raise ConnectionError("ssl eof")
        return "ok"

    assert retry_sync(fn, op="test", log=LOG) == "ok"
    assert calls["n"] == 2


def test_retry_sync_fails_after_max_attempts():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise OSError("network down")

    with pytest.raises(OSError, match="network down"):
        retry_sync(fn, op="test", log=LOG)
    assert calls["n"] == MAX_ATTEMPTS


@pytest.mark.asyncio
async def test_retry_async_succeeds_on_third_attempt():
    calls = {"n": 0}

    async def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return 42

    assert await retry_async(fn, op="test", log=LOG) == 42
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_retry_async_fails_after_max_attempts():
    calls = {"n": 0}

    async def fn():
        calls["n"] += 1
        raise ValueError("permanent")

    with pytest.raises(ValueError, match="permanent"):
        await retry_async(fn, op="test", log=LOG)
    assert calls["n"] == MAX_ATTEMPTS


def test_oss_upload_retries_put_object(tmp_path):
    from models.schemas import ProcessConfig
    from services import oss_uploader

    mp3 = tmp_path / "a.mp3"
    mp3.write_bytes(b"\xff\xfb\x90")

    cfg = ProcessConfig(
        oss_access_key_id="id",
        oss_access_key_secret="secret",
        oss_bucket_name="bucket",
        oss_endpoint="oss-cn-beijing.aliyuncs.com",
        category="测试",
    )

    calls = {"n": 0}
    mock_bucket = MagicMock()

    def put_side_effect(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] < 2:
            raise ConnectionError("SSL EOF")

    mock_bucket.put_object.side_effect = put_side_effect

    with patch.object(oss_uploader, "_bucket", return_value=mock_bucket):
        url = oss_uploader._upload_file_sync(
            mp3, "abcd1234", "sample", "audios", cfg
        )

    assert calls["n"] == 2
    assert mock_bucket.put_object.call_count == 2
    assert "bucket.oss-cn-beijing.aliyuncs.com" in url
    assert "abcd1234_sample.mp3" in url


def test_oss_upload_fails_after_three_attempts(tmp_path):
    from models.schemas import ProcessConfig
    from services import oss_uploader

    mp3 = tmp_path / "b.mp3"
    mp3.write_bytes(b"data")

    cfg = ProcessConfig(
        oss_access_key_id="id",
        oss_access_key_secret="secret",
        oss_bucket_name="bucket",
        oss_endpoint="oss-cn-beijing.aliyuncs.com",
    )

    mock_bucket = MagicMock()
    mock_bucket.put_object.side_effect = ConnectionError("SSL EOF")

    with patch.object(oss_uploader, "_bucket", return_value=mock_bucket):
        with pytest.raises(ConnectionError, match="SSL EOF"):
            oss_uploader._upload_file_sync(mp3, "deadbeef", "x", "audios", cfg)

    assert mock_bucket.put_object.call_count == MAX_ATTEMPTS


@pytest.mark.asyncio
async def test_dashscope_transcribe_retries(monkeypatch):
    from services import asr_dashscope

    calls = {"n": 0}

    async def fake_once(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("百炼转写提交失败: ssl")
        return "你好世界"

    monkeypatch.setattr(asr_dashscope, "_transcribe_once", fake_once)

    text = await asr_dashscope.transcribe(
        "https://bucket.oss-cn-beijing.aliyuncs.com/a.mp3",
        "sk-test",
        "trace-1",
    )
    assert text == "你好世界"
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_funasr_transcribe_retries(monkeypatch, tmp_path):
    from services import asr_local

    audio = tmp_path / "c.mp3"
    audio.write_bytes(b"audio")

    calls = {"n": 0}

    def fake_sync(_path):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("funasr boom")
        return "转写结果"

    monkeypatch.setattr(asr_local, "_status", "ready")
    monkeypatch.setattr(asr_local, "_sync_transcribe", fake_sync)

    text = await asr_local.transcribe(audio, "trace-2")
    assert text == "转写结果"
    assert calls["n"] == 3
