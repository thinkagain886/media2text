# -*- coding: utf-8 -*-
"""媒体类型检测"""

from pathlib import Path
from typing import Literal

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".flv",
    ".wmv",
    ".webm",
    ".ts",
}

AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".ogg",
    ".flac",
    ".opus",
    ".amr",
    ".wma",
}


def detect_file_type(path: str | Path) -> Literal["video", "audio"]:
    """返回 video 或 audio；未知扩展名抛出 ValueError。"""
    p = Path(path)
    ext = p.suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    raise ValueError(f"不支持的文件扩展名: {ext}")
