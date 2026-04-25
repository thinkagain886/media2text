# -*- coding: utf-8 -*-
"""应用启动前环境检查与配置摘要日志"""

import importlib.util
import shutil
from typing import Any, Dict, List

from core.config_loader import settings
from core.logger import get_logger

LOG = get_logger("startup")

# 不在日志中打印的敏感 / 保密字段（须从 Redis 读取的 Key 类配置）
_SECRET_FIELDS = {
    "dashscope_api_key",
    "qwen_api_key",
    "oss_access_key_id",
    "oss_access_key_secret",
    "oss_bucket_name",
    "oss_endpoint",
    "notion_integration_token",
    "feishu_app_secret",
}


def check_ffmpeg() -> None:
    """未安装则报错并给出安装说明。"""
    path = shutil.which("ffmpeg")
    if path:
        LOG.info("FFmpeg：已安装 | path=%s", path, extra={"trace_id": "-"})
        return
    msg = (
        "FFmpeg 未安装或不在 PATH 中。\n"
        "  Windows（Chocolatey）: choco install ffmpeg\n"
        "  Windows（手动）: 从 https://ffmpeg.org/download.html 下载，解压后将 bin 加入系统 PATH\n"
        "  Ubuntu/Debian: sudo apt update && sudo apt install -y ffmpeg\n"
        "  macOS（Homebrew）: brew install ffmpeg\n"
        "安装后请重新打开终端并确认执行 ffmpeg -version 成功。"
    )
    LOG.error("%s", msg, extra={"trace_id": "-"})
    raise RuntimeError("FFmpeg 未安装")


def check_redis_sync() -> None:
    """Redis 不可连则报错并提示 docker 启动方式。"""
    import redis as redis_sync

    try:
        r = redis_sync.from_url(
            settings.redis_url,
            socket_connect_timeout=3,
            decode_responses=True,
        )
        r.ping()
        r.close()
        LOG.info("Redis：连接成功 | url=%s", settings.redis_url, extra={"trace_id": "-"})
    except Exception as e:
        hint = (
            "Redis 无法连接，请确认服务已启动。\n"
            "  若使用本项目 docker-compose（项目根目录）：\n"
            "    docker compose up -d\n"
            "  或单独启动 Redis：\n"
            "    docker run -d --name redis-mt -p 6379:6379 redis:7-alpine\n"
            f"  当前 REDIS_URL={settings.redis_url}\n"
            f"  错误详情: {e}"
        )
        LOG.error("%s", hint, extra={"trace_id": "-"})
        raise RuntimeError("Redis 未启动或不可达") from e


def check_funasr_optional() -> None:
    """FunASR 未安装仅警告（可使用百炼 API 转写）。"""
    try:
        # 使用 find_spec 快速检查包是否存在，避免触发完整初始化（约 9 秒）
        spec = importlib.util.find_spec("funasr")
        if spec is not None:
            LOG.info(
                "FunASR：Python 包已安装（模块将在首次转写时延迟加载）",
                extra={"trace_id": "-"},
            )
        else:
            raise ImportError("funasr not found")
    except ImportError:
        LOG.warning(
            "FunASR：未安装，本地转写不可用；仍可使用「阿里云百炼 API」转写。\n"
            "  安装示例: pip install funasr modelscope\n"
            "  （首次运行会下载模型，耗时较长）",
            extra={"trace_id": "-"},
        )


def _mask_secret_status(value: Any) -> str:
    s = (str(value) if value is not None else "").strip()
    return "已配置" if s else "未配置"


def log_llm_and_oss_status(cfg: Dict[str, Any]) -> None:
    """大模型 Key、OSS 是否配置（不打印具体值）。"""
    ds = cfg.get("dashscope_api_key") or ""
    qw = cfg.get("qwen_api_key") or ""
    LOG.info(
        "密钥状态 | DashScope（百炼转写等）: %s | 通义千问（总结）: %s",
        _mask_secret_status(ds),
        _mask_secret_status(qw),
        extra={"trace_id": "-"},
    )

    oss_fields = [
        "oss_access_key_id",
        "oss_access_key_secret",
        "oss_bucket_name",
        "oss_endpoint",
    ]
    oss_ok = all((cfg.get(k) or "").strip() for k in oss_fields)
    if oss_ok:
        LOG.info("OSS：四项均已配置（具体值不打印）", extra={"trace_id": "-"})
    else:
        missing = [k for k in oss_fields if not (cfg.get(k) or "").strip()]
        LOG.info(
            "OSS：未完整配置，缺少或为空: %s（上传 OSS / 百炼转写需要完整 OSS）",
            ", ".join(missing),
            extra={"trace_id": "-"},
        )


def log_public_config_snapshot(cfg: Dict[str, Any]) -> None:
    """打印除保密字段外的 Redis 配置项及当前值。"""
    keys: List[str] = sorted(k for k in cfg.keys() if k not in _SECRET_FIELDS)
    LOG.info("---------- Redis 配置快照（不含密钥与 OSS 连接串）----------", extra={"trace_id": "-"})
    for k in keys:
        LOG.info("  %s = %r", k, cfg.get(k), extra={"trace_id": "-"})
    LOG.info("---------- 配置快照结束 ----------", extra={"trace_id": "-"})


def log_integration_schema_manual() -> None:
    """启动时打印 Notion / 飞书需手动创建的字段。"""
    from services.integration_payload import INTEGRATION_SCHEMA_ROWS

    parts_n = []
    parts_f = []
    for row in INTEGRATION_SCHEMA_ROWS:
        k = row["key"]
        parts_n.append(f"{k} ({row['notion_type']})")
        parts_f.append(f"{k} ({row['feishu_type']})")
    LOG.info(
        "--- Notion 字段（需手动在数据库中创建）---\n%s",
        " | ".join(parts_n),
        extra={"trace_id": "-"},
    )
    LOG.info(
        "--- 飞书字段（需手动在多维表格中创建）---\n%s",
        " | ".join(parts_f),
        extra={"trace_id": "-"},
    )


async def run_post_redis_checks(cfg: Dict[str, Any]) -> None:
    """在 Redis 已可用且已读到配置后调用。"""
    check_funasr_optional()
    log_llm_and_oss_status(cfg)
    log_public_config_snapshot(cfg)
    log_integration_schema_manual()
