# -*- coding: utf-8 -*-
"""阿里云 OSS 上传（同步实现 + asyncio.to_thread 包装）"""

import asyncio
from pathlib import Path
from typing import Literal

import oss2

from core.logger import get_logger
from core.retry import retry_sync
from models.schemas import ProcessConfig
from services.filename_clean import safe_display_stem
from services.file_hash import sha256_bytes_prefix8

LOG = get_logger("oss_uploader")

# 供「仅文本」上传时与 process 中算法一致
caption_content_hash8 = sha256_bytes_prefix8


def category_segment(category: str) -> str:
    """目录名净化。"""
    s = "".join(c for c in (category or "") if c not in '\\/:*?"<>|').strip()
    return s or "默认分类"


def build_public_url(bucket: str, endpoint: str, object_key: str) -> str:
    """公网 URL：https://{bucket}.{endpoint}/{key}"""
    from urllib.parse import quote

    ep = endpoint.strip().replace("https://", "").replace("http://", "").strip("/")
    key = object_key.lstrip("/")
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
    content_hash8: str,
    display_stem: str,
    subdir: Literal["audios", "captions"],
    cfg: ProcessConfig,
) -> str:
    h8 = (content_hash8 or "").lower()[:8]
    safe = safe_display_stem(display_stem)
    cat = category_segment(cfg.category)
    if subdir == "audios":
        object_key = f"{cat}/audios/{h8}_{safe}.mp3"
    else:
        object_key = f"{cat}/captions/{h8}_{safe}_transcript.md"
    bucket = _bucket(cfg)
    LOG.info("OSS put | %s", object_key)
    headers: dict = {}
    if subdir == "audios":
        headers["Content-Type"] = "audio/mpeg"
    elif subdir == "captions":
        headers["Content-Type"] = "text/markdown; charset=utf-8"
    def _do_put() -> None:
        with open(local_file, "rb") as f:
            bucket.put_object(object_key, f, headers=headers)

    retry_sync(_do_put, op=f"OSS put {object_key}", log=LOG)
    return build_public_url(
        cfg.oss_bucket_name.strip(),
        cfg.oss_endpoint.strip(),
        object_key,
    )


async def upload_to_oss(
    local_file: Path,
    content_hash8: str,
    display_stem: str,
    subdir: Literal["audios", "captions"],
    cfg: ProcessConfig,
) -> str:
    return await asyncio.to_thread(
        _upload_file_sync,
        local_file,
        content_hash8,
        display_stem,
        subdir,
        cfg,
    )


def _upload_caption_sync(
    markdown_text: str, content_hash8: str, display_stem: str, cfg: ProcessConfig
) -> str:
    h8 = (content_hash8 or "").lower()[:8]
    safe = safe_display_stem(display_stem)
    cat = category_segment(cfg.category)
    object_key = f"{cat}/captions/{h8}_{safe}_transcript.md"
    bucket = _bucket(cfg)
    LOG.info("OSS put caption | %s", object_key)
    data = markdown_text.encode("utf-8")

    def _do_put() -> None:
        bucket.put_object(
            object_key,
            data,
            headers={"Content-Type": "text/markdown; charset=utf-8"},
        )

    retry_sync(_do_put, op=f"OSS put caption {object_key}", log=LOG)
    return build_public_url(
        cfg.oss_bucket_name.strip(),
        cfg.oss_endpoint.strip(),
        object_key,
    )


async def upload_caption_to_oss(
    markdown_text: str,
    content_hash8: str,
    display_stem: str,
    cfg: ProcessConfig,
) -> str:
    return await asyncio.to_thread(
        _upload_caption_sync,
        markdown_text,
        content_hash8,
        display_stem,
        cfg,
    )
