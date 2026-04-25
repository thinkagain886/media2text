# -*- coding: utf-8 -*-
"""FFmpeg 异步提取音频为 MP3"""

import asyncio
import math
import shutil
import subprocess
from pathlib import Path
from typing import Optional


async def video_to_audio(temp_path: Path, output_mp3: Path) -> Path:
    """
    将视频转为 16kHz 64kbps MP3。
    输出目录自动创建。
    """
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(temp_path.resolve()),
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ab",
        "64k",
        "-ar",
        "16000",
        str(output_mp3.resolve()),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = (stderr or b"").decode("utf-8", errors="replace")
        raise RuntimeError(f"FFmpeg 失败: {err[:2000]}")
    return output_mp3


def probe_media_duration_seconds_sync(path: Path) -> Optional[float]:
    """
    ffprobe 读取媒体时长（秒）。失败返回 None。
    """
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path.resolve()),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            return None
        raw = (proc.stdout or "").strip()
        if not raw:
            return None
        v = float(raw)
        if not math.isfinite(v) or v <= 0:
            return None
        return v
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


async def probe_media_duration_seconds(path: Path) -> Optional[float]:
    return await asyncio.to_thread(probe_media_duration_seconds_sync, path)


async def audio_to_mp3_if_needed(src: Path, output_mp3: Path) -> Path:
    """若非 mp3，则转码为 mp3；已是 mp3 则复制目标路径（仍走 ffmpeg 统一参数）。"""
    if src.suffix.lower() == ".mp3":
        output_mp3.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, output_mp3)
        return output_mp3
    return await video_to_audio(src, output_mp3)
