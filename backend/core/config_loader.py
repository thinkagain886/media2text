# -*- coding: utf-8 -*-
"""加载 .env 与全局路径配置"""

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = BACKEND_ROOT.parent
_ROOT_ENV_PATH = _REPO_ROOT / ".env"
_BACKEND_ENV_PATH = BACKEND_ROOT / ".env"

# 1）仓库根目录 .env：Docker Compose / 团队共用
# 2）backend/.env：可选；后加载且 override=True，可覆盖同名项
# 二者均启用 interpolate：backend/.env 里可写 REDIS_URL=redis://${REDIS_HOST}:${REDIS_DB_PORT}/0
# （${…} 从当前 os.environ 解析，故根 .env 需先加载）。语法为 $VAR / ${VAR}，不是单独的 {}
#
# 根目录第一次 load_dotenv(..., override=False)：若进程里已有同名变量（Docker Compose 注入的 REDIS_URL
# 等），以环境为准，避免根 .env 里的本机 Redis 覆盖容器配置。backend/.env 仍为 override=True。
load_dotenv(_ROOT_ENV_PATH, interpolate=True, override=False)
load_dotenv(_BACKEND_ENV_PATH, override=True, interpolate=True)

# 必须在 import funasr / modelscope 之前固定缓存目录（process 路由会提前加载 asr_local）
_msc_raw = (os.getenv("MODELSCOPE_CACHE") or "").strip()
if _msc_raw:
    _msc_path = Path(_msc_raw).expanduser()
    if not _msc_path.is_absolute():
        _msc_path = (BACKEND_ROOT / _msc_path).resolve()
    else:
        _msc_path = _msc_path.resolve()
    _msc_path.mkdir(parents=True, exist_ok=True)
    os.environ["MODELSCOPE_CACHE"] = str(_msc_path)


def _parse_origins(raw: str) -> List[str]:
    raw = (raw or "*").strip()
    if raw == "*":
        return ["*"]
    return [x.strip() for x in raw.split(",") if x.strip()]


class Settings:
    """运行时配置（环境变量）。"""

    redis_url: str = (os.getenv("REDIS_URL") or "redis://localhost:6379/0").strip()
    sqlite_path: Path = BACKEND_ROOT / (os.getenv("SQLITE_PATH") or "./media2text.db").strip()
    temp_dir: Path = BACKEND_ROOT / (os.getenv("TEMP_DIR") or "./temp").strip()
    preload_funasr: bool = os.getenv("PRELOAD_FUNASR", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    # 与上面 os.environ 一致；未设置 MODELSCOPE_CACHE 时 ModelScope 默认用用户目录 ~/.cache/modelscope
    modelscope_cache: str = os.getenv("MODELSCOPE_CACHE", "")
    cors_origins: List[str] = _parse_origins(os.getenv("CORS_ORIGINS", "*"))
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    # 前端构建产物（生产静态托管）
    frontend_dist: Path = BACKEND_ROOT.parent / "frontend" / "dist"


settings = Settings()
