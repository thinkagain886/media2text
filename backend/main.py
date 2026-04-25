# -*- coding: utf-8 -*-
"""FastAPI 入口"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core import redis_client as R
from core.config_loader import settings
from core.logger import get_logger
from core.startup_checks import (
    check_ffmpeg,
    check_redis_sync,
    run_post_redis_checks,
)
from routers import asr as asr_router
from routers import config, history, integrations, process, push, upload
from services import asr_local
from services.db import init_db

LOG = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动前环境检查（FFmpeg / Redis 失败则中止启动）
    check_ffmpeg()
    check_redis_sync()

    await R.init_defaults()
    await init_db()
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    settings.frontend_dist.mkdir(parents=True, exist_ok=True)

    cfg = await R.get_config()
    await run_post_redis_checks(cfg)

    if settings.preload_funasr and (cfg.get("asr_engine") or "funasr") == "funasr":
        asr_local.start_background_preload_from_lifespan("-")
    elif settings.preload_funasr:
        LOG.info(
            "已设置 PRELOAD_FUNASR=true，但当前 Redis asr_engine 非 funasr，跳过 FunASR 预加载",
            extra={"trace_id": "-"},
        )
    yield
    await R.close_redis()


app = FastAPI(title="Media2Text API v2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(process.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(push.router, prefix="/api")
app.include_router(integrations.router, prefix="/api")
app.include_router(asr_router.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


_dist = settings.frontend_dist
if _dist.is_dir() and any(_dist.iterdir()):
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")


def main():
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
