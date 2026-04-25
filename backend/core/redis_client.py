# -*- coding: utf-8 -*-
"""Redis 异步客户端与配置 / 分类 / 提示词存取"""

import json
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from core.config_loader import settings
from models.schemas import DEFAULT_CONFIG_DICT, DEFAULT_PROMPTS_DICT

CONFIG_HASH_KEY = "media2text:config"
CATEGORIES_SET_KEY = "media2text:categories"
PROMPTS_HASH_KEY = "media2text:prompts"

_redis: Optional[redis.Redis] = None


def _bool_from_str(v: str) -> bool:
    return v.lower() in ("1", "true", "yes", "on")


def _coerce_field(key: str, value: str) -> Any:
    if key in (
        "save_audio_local",
        "save_audio_oss",
        "transcribe_enabled",
        "transcript_save_local",
        "transcript_save_oss",
        "summary_enabled",
        "save_to_db",
        "push_notion_enabled",
        "push_feishu_enabled",
    ):
        return _bool_from_str(value)
    return value


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


async def init_defaults() -> None:
    """若 key 不存在则写入默认配置、默认分类、内置提示词。"""
    r = await get_redis()
    exists = await r.exists(CONFIG_HASH_KEY)
    if not exists:
        flat = {k: _to_redis_str(v) for k, v in DEFAULT_CONFIG_DICT.items()}
        await r.hset(CONFIG_HASH_KEY, mapping=flat)
    ccount = await r.scard(CATEGORIES_SET_KEY)
    if ccount == 0:
        await r.sadd(CATEGORIES_SET_KEY, "默认分类")
    pexists = await r.exists(PROMPTS_HASH_KEY)
    if not pexists:
        await r.hset(PROMPTS_HASH_KEY, mapping=DEFAULT_PROMPTS_DICT)


async def reset_all_to_defaults() -> None:
    """删除配置、分类、提示词相关 Redis key，并写入与首次安装一致的默认值。"""
    r = await get_redis()
    await r.delete(CONFIG_HASH_KEY)
    await r.delete(CATEGORIES_SET_KEY)
    await r.delete(PROMPTS_HASH_KEY)
    flat = {k: _to_redis_str(v) for k, v in DEFAULT_CONFIG_DICT.items()}
    await r.hset(CONFIG_HASH_KEY, mapping=flat)
    await r.sadd(CATEGORIES_SET_KEY, "默认分类")
    await r.hset(PROMPTS_HASH_KEY, mapping=DEFAULT_PROMPTS_DICT)


def _to_redis_str(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


async def get_config() -> dict:
    """获取全部配置（字典，类型已还原）。"""
    r = await get_redis()
    raw = await r.hgetall(CONFIG_HASH_KEY)
    if not raw:
        return dict(DEFAULT_CONFIG_DICT)
    out: Dict[str, Any] = {}
    for k, v in raw.items():
        if k in DEFAULT_CONFIG_DICT:
            dv = DEFAULT_CONFIG_DICT[k]
            if isinstance(dv, bool):
                out[k] = _bool_from_str(v)
            else:
                out[k] = v
        else:
            out[k] = v
    return out


async def update_config(data: dict) -> None:
    """批量更新配置字段（仅更新提供的键）。"""
    r = await get_redis()
    if not data:
        return
    flat = {k: _to_redis_str(v) for k, v in data.items()}
    await r.hset(CONFIG_HASH_KEY, mapping=flat)


async def get_categories() -> List[str]:
    r = await get_redis()
    members = await r.smembers(CATEGORIES_SET_KEY)
    return sorted(members)


async def add_category(name: str) -> bool:
    """添加分类；已存在返回 False。"""
    name = (name or "").strip()
    if not name:
        return False
    r = await get_redis()
    n = await r.sadd(CATEGORIES_SET_KEY, name)
    return n == 1


async def remove_category(name: str) -> None:
    """删除分类；「默认分类」不可删。"""
    name = (name or "").strip()
    if not name:
        raise ValueError("分类名为空")
    if name == "默认分类":
        raise ValueError("不能删除「默认分类」")
    r = await get_redis()
    n = await r.srem(CATEGORIES_SET_KEY, name)
    if n == 0:
        raise ValueError("分类不存在")


async def get_prompts() -> Dict[str, str]:
    r = await get_redis()
    return await r.hgetall(PROMPTS_HASH_KEY)


async def add_prompt(title: str, content: str) -> None:
    r = await get_redis()
    await r.hset(PROMPTS_HASH_KEY, title, content)


async def delete_prompt(title: str) -> None:
    r = await get_redis()
    await r.hdel(PROMPTS_HASH_KEY, title)


async def rename_prompt(old_title: str, new_title: str, content: str) -> None:
    """修改 Hash 键名（标题）；old 与 new 须已校验。"""
    r = await get_redis()
    await r.hdel(PROMPTS_HASH_KEY, old_title)
    await r.hset(PROMPTS_HASH_KEY, new_title, content)


async def get_prompt_content(title: str) -> str:
    """按标题取提示词内容；空则使用「默认总结」。"""
    r = await get_redis()
    t = (title or "").strip() or "默认总结"
    content = await r.hget(PROMPTS_HASH_KEY, t)
    if content:
        return content
    return DEFAULT_PROMPTS_DICT.get("默认总结", "请对下列内容做简明总结：")


async def export_prompts_list() -> List[Dict[str, str]]:
    """供 API 返回 [{title, content}]。"""
    d = await get_prompts()
    return [{"title": k, "content": v} for k, v in sorted(d.items())]


async def replace_categories(names: List[str]) -> None:
    """覆盖分类集合（须含「默认分类」，否则自动补上）。"""
    seen = sorted({str(x).strip() for x in names if str(x).strip()})
    if "默认分类" not in seen:
        seen.insert(0, "默认分类")
    r = await get_redis()
    await r.delete(CATEGORIES_SET_KEY)
    await r.sadd(CATEGORIES_SET_KEY, *seen)


async def replace_prompts_list(items: List[Dict[str, Any]]) -> None:
    """覆盖提示词 Hash；若无「默认总结」则写入内置默认。"""
    r = await get_redis()
    await r.delete(PROMPTS_HASH_KEY)
    for it in items:
        title = str((it or {}).get("title") or "").strip()
        content = str((it or {}).get("content") or "")
        if title:
            await r.hset(PROMPTS_HASH_KEY, title, content)
    prompts = await r.hgetall(PROMPTS_HASH_KEY)
    if "默认总结" not in prompts:
        await r.hset(
            PROMPTS_HASH_KEY,
            "默认总结",
            DEFAULT_PROMPTS_DICT.get("默认总结", "请对下列内容做简明总结："),
        )
