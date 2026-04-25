# -*- coding: utf-8 -*-
"""历史记录补操作：总结、字幕上传 OSS、单条推送"""

from pathlib import Path
from typing import Any, Dict

from core import redis_client as R
from core.logger import get_logger
from models.schemas import DEFAULT_CONFIG_DICT, ProcessConfig, process_config_from_merged
from services import db
from services.feishu_push import push_items_to_feishu
from services.integration_payload import integration_dict_from_row
from services.notion_push import push_items_to_notion
from services.oss_uploader import upload_caption_to_oss
from services.summarizer import get_summarizer

LOG = get_logger("history_ops")


async def _merged_cfg() -> ProcessConfig:
    merged = dict(DEFAULT_CONFIG_DICT)
    merged.update(await R.get_config())
    return process_config_from_merged(merged)


async def summarize_record(record_id: int) -> Dict[str, Any]:
    row = await db.get_record(record_id)
    if not row:
        raise ValueError("记录不存在")
    caps = (row.get("captions") or "").strip()
    if not caps:
        raise ValueError("无原文可总结")

    cfg = await _merged_cfg()
    prompt = await R.get_prompt_content(cfg.summary_prompt_title)
    summ = get_summarizer(cfg.summary_model, cfg.qwen_api_key)
    text = await summ.summarize(caps, prompt, trace_id=f"his{record_id}")

    await db.update_record_summary(record_id, text, True)
    return await db.get_record(record_id)


async def upload_caption_oss_record(record_id: int) -> Dict[str, Any]:
    row = await db.get_record(record_id)
    if not row:
        raise ValueError("记录不存在")
    caps = row.get("captions")
    if not caps or not str(caps).strip():
        raise ValueError("无字幕文本可上传")

    cfg = await _merged_cfg()
    fn = f"{Path((row.get('title') or 'caption').strip() or 'caption').stem}.md"
    url = await upload_caption_to_oss(str(caps), fn, cfg)

    sfs: list = list(row.get("source_files") or [])
    if sfs and isinstance(sfs, list):
        if isinstance(sfs[0], dict):
            sfs[0] = {**sfs[0], "caption_oss_url": url}
        else:
            sfs = [{"filename": fn, "caption_oss_url": url}]
    else:
        sfs = [{"filename": fn, "caption_oss_url": url}]

    await db.update_record_caption_oss(record_id, sfs, True)
    return await db.get_record(record_id)


async def push_record_notion(record_id: int) -> Dict[str, Any]:
    row = await db.get_record(record_id)
    if not row:
        raise ValueError("记录不存在")
    cfg = await _merged_cfg()
    payload = integration_dict_from_row(row)
    await push_items_to_notion([payload], cfg, trace_id=f"h{record_id}")
    await db.update_push_flags([record_id], notion=True)
    out = await db.get_record(record_id)
    if not out:
        raise ValueError("记录不存在")
    return out


async def push_record_feishu(record_id: int) -> Dict[str, Any]:
    row = await db.get_record(record_id)
    if not row:
        raise ValueError("记录不存在")
    cfg = await _merged_cfg()
    payload = integration_dict_from_row(row)
    await push_items_to_feishu([payload], cfg, trace_id=f"h{record_id}")
    await db.update_push_flags([record_id], feishu=True)
    out = await db.get_record(record_id)
    if not out:
        raise ValueError("记录不存在")
    return out
