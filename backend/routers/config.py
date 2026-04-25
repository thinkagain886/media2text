# -*- coding: utf-8 -*-
"""配置 API（Redis）"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import oss2
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from core import redis_client as R
from core.db_factory import get_db, reset_db_adapter
from core.logger import get_logger, log_error
from dashscope import Generation

router = APIRouter(tags=["config"])
LOG = get_logger("config_api")


class CategoryBody(BaseModel):
    name: str


class PromptBody(BaseModel):
    title: str
    content: str


class TestOssBody(BaseModel):
    oss_access_key_id: str
    oss_access_key_secret: str
    oss_bucket_name: str
    oss_endpoint: str


class TestDashScopeBody(BaseModel):
    dashscope_api_key: str


class PromptPutBody(BaseModel):
    content: str = ""
    new_title: Optional[str] = None


class ConfigImportPayload(BaseModel):
    """前端导出的快照或手工编辑的 JSON；未出现的段不修改。"""

    model_config = ConfigDict(extra="ignore")

    schema_version: int = 1
    exported_at: Optional[str] = None
    app: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    categories: Optional[List[str]] = None
    prompts: Optional[List[Dict[str, Any]]] = None


@router.get("/config")
async def get_config():
    return await R.get_config()


@router.put("/config")
async def put_config(data: Dict[str, Any]):
    await R.update_config(data)
    return {"ok": True}


@router.post("/config/reset")
async def post_config_reset():
    """清空 Redis 中的应用配置、分类与提示词，并恢复为默认。"""
    await R.reset_all_to_defaults()
    return {"ok": True}


@router.get("/config/categories")
async def get_categories():
    return await R.get_categories()


@router.post("/config/categories")
async def post_category(body: CategoryBody):
    ok = await R.add_category(body.name)
    if not ok:
        raise HTTPException(status_code=400, detail="分类已存在或名称无效")
    return {"ok": True}


@router.delete("/config/categories")
async def delete_category(name: str = Query(..., description="要删除的分类名")):
    try:
        await R.remove_category(name.strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True}


@router.get("/config/prompts")
async def get_prompts_list():
    return await R.export_prompts_list()


@router.post("/config/prompts")
async def post_prompt(body: PromptBody):
    await R.add_prompt(body.title.strip(), body.content)
    return {"ok": True}


@router.delete("/config/prompts")
async def delete_prompt(title: str = Query(..., description="提示词标题")):
    if title.strip() == "默认总结":
        raise HTTPException(status_code=400, detail="内置提示词「默认总结」不可删除")
    await R.delete_prompt(title)
    return {"ok": True}


@router.put("/config/prompts/{title}")
async def put_prompt(title: str, body: PromptPutBody):
    """更新提示词内容；非「默认总结」可通过 new_title 改标题。"""
    t = title.strip()
    if not t:
        raise HTTPException(status_code=400, detail="标题为空")
    exists = await R.get_prompts()
    if t not in exists:
        raise HTTPException(status_code=404, detail="提示词不存在")
    new_t = (body.new_title or "").strip() if body.new_title is not None else ""
    if new_t == t:
        new_t = ""
    if new_t:
        if t == "默认总结":
            raise HTTPException(
                status_code=400, detail="内置提示词「默认总结」不可修改标题",
            )
        if new_t == "默认总结":
            raise HTTPException(
                status_code=400, detail="不能使用保留标题「默认总结」",
            )
        if new_t in exists:
            raise HTTPException(status_code=400, detail=f"标题「{new_t}」已存在")
        await R.rename_prompt(t, new_t, body.content or "")
        cfg = await R.get_config()
        if (cfg.get("summary_prompt_title") or "").strip() == t:
            await R.update_config({"summary_prompt_title": new_t})
    else:
        await R.add_prompt(t, body.content or "")
    return {"ok": True}


def _mask_config_value(key: str, value: Any) -> str:
    kl = key.lower()
    s = "" if value is None else str(value)
    if any(x in kl for x in ("key", "secret", "token", "password")):
        if len(s) <= 8:
            return "****"
        return f"{s[:4]}****{s[-4:]}"
    if isinstance(value, bool):
        return "开" if value else "关"
    return s


@router.get("/config/export-json")
async def export_config_json():
    """完整快照：Redis 配置 + 分类 + 提示词（不脱敏，勿泄露）。"""
    cfg = await R.get_config()
    cats = await R.get_categories()
    prompts = await R.export_prompts_list()
    return {
        "schema_version": 1,
        "app": "media2text",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "config": cfg,
        "categories": cats,
        "prompts": prompts,
    }


@router.post("/config/import-json")
async def post_import_json(payload: ConfigImportPayload):
    """按段写入：仅有 config 则只更新配置项；含 categories/prompts 则整段替换。"""
    if (
        not payload.config
        and payload.categories is None
        and payload.prompts is None
    ):
        raise HTTPException(
            status_code=400,
            detail="JSON 中至少需包含 config、categories、prompts 之一",
        )
    try:
        if payload.config:
            await R.update_config(payload.config)
        if payload.categories is not None:
            await R.replace_categories(payload.categories)
        if payload.prompts is not None:
            await R.replace_prompts_list(payload.prompts)
    except Exception as e:
        log_error(LOG, "-", "import_json", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True}


@router.get("/config/export-markdown")
async def export_config_markdown():
    cfg = await R.get_config()
    cats = await R.get_categories()
    prompts = await R.export_prompts_list()
    lines: List[str] = [
        "# media2text 配置导出",
        "",
        f"> 导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Redis 配置项",
        "",
        "| 配置项 | 值 |",
        "|--------|-----|",
    ]
    for k in sorted(cfg.keys()):
        lines.append(f"| {k} | {_mask_config_value(k, cfg.get(k))} |")
    lines.extend(["", "## 分类列表", ""])
    for c in cats:
        lines.append(f"- {c}")
    lines.extend(["", "## 提示词列表", ""])
    for p in prompts:
        lines.append(f"### {p.get('title')}")
        lines.append("")
        lines.append(p.get("content") or "")
        lines.append("")
    return "\n".join(lines)


@router.post("/config/test-db")
async def test_db():
    reset_db_adapter()
    try:
        dba = await get_db()
        await dba.init()
        _ = await dba.get_records(page=1, page_size=1)
        return {"ok": True, "message": "数据库连接正常"}
    except Exception as e:
        log_error(LOG, "-", "test_db", e)
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/config/test-oss")
async def test_oss(body: TestOssBody):
    """验证 OSS 凭证：尝试列举 1 个对象。"""
    try:
        auth = oss2.Auth(body.oss_access_key_id.strip(), body.oss_access_key_secret.strip())
        ep = body.oss_endpoint.strip()
        if not ep.startswith("http"):
            ep = f"https://{ep}"
        bucket = oss2.Bucket(auth, ep, body.oss_bucket_name.strip())
        result = bucket.list_objects(max_keys=1)
        return {"ok": True, "message": "连接成功", "count_hint": len(result.object_list)}
    except Exception as e:
        log_error(LOG, "-", "test_oss", e)
        raise HTTPException(status_code=400, detail=f"OSS 测试失败: {e}") from e


@router.post("/config/test-dashscope")
async def test_dashscope(body: TestDashScopeBody):
    """使用通义千问最小请求验证 API Key。"""
    key = body.dashscope_api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API Key 为空")
    try:
        rsp = Generation.call(
            model="qwen-plus",
            messages=[{"role": "user", "content": "ping"}],
            api_key=key,
            result_format="message",
        )
        if getattr(rsp, "status_code", None) != 200:
            raise RuntimeError(getattr(rsp, "message", "") or "调用失败")
        return {"ok": True, "message": "连接成功"}
    except Exception as e:
        log_error(LOG, "-", "test_dashscope", e)
        raise HTTPException(status_code=400, detail=f"DashScope 测试失败: {e}") from e
