# -*- coding: utf-8 -*-
"""阿里云 OSS 上传（同步实现 + asyncio.to_thread 包装）"""

import asyncio
from pathlib import Path
from typing import Literal

import oss2

from core.logger import get_logger
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


def _object_exists(bucket: oss2.Bucket, key: str) -> bool:
    try:
        bucket.head_object(key)
        return True
    except oss2.exceptions.NoSuchKey:
        return False
    except Exception as e:  # noqa: BLE001
        LOG.warning("OSS head_object 异常 | key=%s | %s", key, e)
        return False


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
    exists = _object_exists(bucket, object_key)
    action = "覆盖上传" if exists else "新建对象"
    LOG.info(
        "OSS 上传 | key=%s | sha256_8=%s | 已存在=%s | 行为=%s",
        object_key,
        h8,
        exists,
        action,
    )
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
    exists = _object_exists(bucket, object_key)
    action = "覆盖上传" if exists else "新建对象"
    LOG.info(
        "OSS 字幕上传 | key=%s | sha256_8(文本)=%s | 已存在=%s | 行为=%s",
        object_key,
        h8,
        exists,
        action,
    )
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
