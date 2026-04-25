# -*- coding: utf-8 -*-
"""FunASR 加载状态"""

from fastapi import APIRouter

from services import asr_local

router = APIRouter(prefix="/asr", tags=["asr"])


@router.get("/status")
async def get_asr_status():
    return asr_local.get_status_payload()


@router.post("/load-funasr")
async def trigger_load_funasr():
    await asr_local.schedule_preload_if_needed()
    return asr_local.get_status_payload()
