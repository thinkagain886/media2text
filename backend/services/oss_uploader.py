# -*- coding: utf-8 -*-
"""阿里云 OSS 上传（同步实现 + asyncio.to_thread 包装）"""

import asyncio
import time
from pathlib import Path
from typing import Literal
from urllib.parse import quote

import oss2

from models.schemas import ProcessConfig


def category_segment(category: str) -> str:
    """目录名净化。"""
    s = "".join(c for c in (category or "") if c not in '\\/:*?"<>|').strip()
    return s or "默认分类"


def build_public_url(bucket: str, endpoint: str, object_key: str) -> str:
    """公网 URL：https://{bucket}.{endpoint}/{key}"""
    ep = endpoint.strip().replace("https://", "").replace("http://", "").strip("/")
    key = object_key.lstrip("/")
    # 对 object_key 进行 URL 编码，安全字符保留 / 等路径分隔符
    # 这样 #、空格、中文等特殊字符会被正确转义，避免 DashScope 下载失败
    safe_key = quote(key, safe="/-_.~")
    return f"https://{bucket}.{ep}/{safe_key}"


def _bucket(cfg: ProcessConfig) -> oss2.Bucket:
    auth = oss2.Auth(
        cfg.oss_access_key_id.strip(),
        cfg.oss_access_key_secret.strip(),
    )
    ep = cfg.oss_endpoint.strip()
    if not ep.startswith("http"):
        ep = f"https://{ep}"
    return oss2.Bucket(auth, ep, cfg.oss_bucket_name.strip())


def _upload_file_sync(
    local_file: Path,
    original_filename: str,
    subdir: Literal["audios", "captions"],
    cfg: ProcessConfig,
) -> str:
    cat = category_segment(cfg.category)
    ts = int(time.time() * 1000)
    safe = Path(original_filename).name.replace("\\", "_").replace("/", "_")
    object_key = f"{cat}/{subdir}/{ts}_{safe}"
    bucket = _bucket(cfg)
    headers: dict = {}
    if subdir == "audios":
        headers["Content-Type"] = "audio/mpeg"
    elif subdir == "captions":
        headers["Content-Type"] = "text/markdown; charset=utf-8"
    with open(local_file, "rb") as f:
        bucket.put_object(object_key, f, headers=headers)
    return build_public_url(
        cfg.oss_bucket_name.strip(),
        cfg.oss_endpoint.strip(),
        object_key,
    )


async def upload_to_oss(
    local_file: Path,
    original_filename: str,
    subdir: Literal["audios", "captions"],
    cfg: ProcessConfig,
) -> str:
    return await asyncio.to_thread(
        _upload_file_sync,
        local_file,
        original_filename,
        subdir,
        cfg,
    )


def _upload_caption_sync(markdown_text: str, original_filename: str, cfg: ProcessConfig) -> str:
    cat = category_segment(cfg.category)
    ts = int(time.time() * 1000)
    stem = Path(original_filename).stem
    object_key = f"{cat}/captions/{ts}_{stem}_transcript.md"
    bucket = _bucket(cfg)
    data = markdown_text.encode("utf-8")
    bucket.put_object(
        object_key,
        data,
        headers={"Content-Type": "text/markdown; charset=utf-8"},
    )
    return build_public_url(
        cfg.oss_bucket_name.strip(),
        cfg.oss_endpoint.strip(),
        object_key,
    )


async def upload_caption_to_oss(
    markdown_text: str,
    original_filename: str,
    cfg: ProcessConfig,
) -> str:
    return await asyncio.to_thread(
        _upload_caption_sync,
        markdown_text,
        original_filename,
        cfg,
    )
