# -*- coding: utf-8 -*-
"""第三方集成字段说明"""

from fastapi import APIRouter

from services.integration_payload import INTEGRATION_SCHEMA_ROWS

router = APIRouter(tags=["integrations"])


@router.get("/integrations/schema")
async def integration_schema():
    return {
        "fields": INTEGRATION_SCHEMA_ROWS,
        "notion_note": "Database 列名与 key 完全一致；title=Title；record_uuid/captions/summary/source_files=Rich text；created_at/updated_at=Date；category/batch_mode=Select。",
        "feishu_note": "列名与 key 一致；created_at/updated_at 为「日期时间」列，接口写入 UTC 毫秒时间戳（整数）。captions/summary/source_files 须多行文本；source_files 勿用「多选」。",
    }
