# -*- coding: utf-8 -*-
"""FFmpeg 异步提取音频为 MP3"""

import asyncio
import shutil
from pathlib import Path


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


async def audio_to_mp3_if_needed(src: Path, output_mp3: Path) -> Path:
    """若非 mp3，则转码为 mp3；已是 mp3 则复制目标路径（仍走 ffmpeg 统一参数）。"""
    if src.suffix.lower() == ".mp3":
        output_mp3.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, output_mp3)
        return output_mp3
    return await video_to_audio(src, output_mp3)
