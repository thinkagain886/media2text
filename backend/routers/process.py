# -*- coding: utf-8 -*-
"""批量处理与 SSE 进度"""

import asyncio
import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from core import redis_client as R
from core.config_loader import BACKEND_ROOT, settings
from core.logger import get_logger, log_error, log_step, log_timing
from models.schemas import (
    BatchProcessRequest,
    ProcessConfig,
    ProcessResult,
    SourceFile,
    merge_config,
    process_config_from_merged,
)
from services import asr_dashscope, asr_local, db
from services.integration_payload import integration_dict_from_row
from services.file_detector import detect_file_type
from services.markdown_formatter import format_merged, format_single
from services.oss_uploader import category_segment, upload_caption_to_oss, upload_to_oss
from services.summarizer import get_summarizer
from services.video_converter import audio_to_mp3_if_needed, video_to_audio

router = APIRouter(prefix="/process", tags=["process"])
LOG = get_logger("process")

TASKS: Dict[str, Dict[str, Any]] = {}


def _temp_root() -> Path:
    td = settings.temp_dir
    if not td.is_absolute():
        return (BACKEND_ROOT / td).resolve()
    return td.resolve()


def _resolve_temp_path(rel: str) -> Path:
    root = BACKEND_ROOT
    p = (root / rel).resolve()
    tr = _temp_root().resolve()
    try:
        p.relative_to(tr)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="非法临时文件路径") from e
    if not p.is_file():
        raise HTTPException(status_code=404, detail=f"文件不存在: {rel}")
    return p


def _cleanup_task_temp_files(task_id: str, files: List[Any]) -> None:
    """
    任务结束后删除：各次上传的原始临时文件，以及 temp 目录下以本任务前缀生成的中间文件（如转码 mp3）。
    上传阶段写入 temp、处理阶段再写同目录，此前未做清理故会堆积。
    """
    tr = _temp_root().resolve()
    root = BACKEND_ROOT.resolve()
    prefix = task_id[:8]
    for fi in files:
        rel = getattr(fi, "temp_path", None)
        if not rel:
            continue
        try:
            p = (root / rel).resolve()
            p.relative_to(tr)
            p.unlink(missing_ok=True)
        except Exception:
            pass
    if tr.is_dir():
        for p in tr.iterdir():
            try:
                if p.is_file() and p.name.startswith(f"{prefix}_"):
                    p.unlink(missing_ok=True)
            except Exception:
                pass


async def _push(
    queue: asyncio.Queue,
    task_id: str,
    file_index: int,
    filename: str,
    step: str,
    step_desc: str,
    progress: int,
    error: Optional[str] = None,
    results: Optional[List[dict]] = None,
) -> None:
    payload: Dict[str, Any] = {
        "task_id": task_id,
        "file_index": file_index,
        "filename": filename,
        "step": step,
        "step_desc": step_desc,
        "progress": max(0, min(100, progress)),
        "error": error,
    }
    if results is not None:
        payload["results"] = results
    await queue.put(payload)


async def _save_audio_local(work: Path, filename: str, cfg: ProcessConfig) -> str:
    cat = category_segment(cfg.category)
    base = Path(cfg.audio_local_base_path)
    if not base.is_absolute():
        base = BACKEND_ROOT / base
    dest_dir = base / cat / "audios"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{Path(filename).stem}.mp3"
    await asyncio.to_thread(shutil.copy2, work, dest)
    return str(dest.resolve())


async def _save_caption_local(markdown_text: str, filename: str, cfg: ProcessConfig) -> str:
    cat = category_segment(cfg.category)
    base = Path(cfg.transcript_local_base_path)
    if not base.is_absolute():
        base = BACKEND_ROOT / base
    dest_dir = base / cat / "captions"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{Path(filename).stem}_transcript.md"

    def _w() -> None:
        dest.write_text(markdown_text, encoding="utf-8")

    await asyncio.to_thread(_w)
    return str(dest.resolve())


def _to_result_dict(pr: ProcessResult) -> dict:
    return json.loads(pr.model_dump_json())


def _record_flags(pr: ProcessResult) -> tuple[bool, bool]:
    transcript_on_oss = any(
        bool((sf.caption_oss_url or "").strip()) for sf in pr.source_files
    )
    has_summary = bool((pr.summary or "").strip())
    return transcript_on_oss, has_summary


async def _save_db(
    task_id: str, cfg: ProcessConfig, pr: ProcessResult
) -> Optional[Tuple[int, str]]:
    if not cfg.save_to_db:
        return None
    to, hs = _record_flags(pr)
    ru = (pr.record_uuid or "").strip() or None
    rid, uuid_out = await db.save_record(
        {
            "task_id": task_id,
            "category": cfg.category,
            "batch_mode": cfg.batch_mode,
            "title": pr.title,
            "source_files": [sf.model_dump() for sf in pr.source_files],
            "captions": pr.captions,
            "summary": pr.summary,
            "status": pr.status,
            "transcript_on_oss": to,
            "has_summary": hs,
            "record_uuid": ru,
        }
    )
    return rid, uuid_out


def _validate_cfg(cfg: ProcessConfig) -> None:
    if cfg.batch_mode == "merge" and not (cfg.merge_title or "").strip():
        raise HTTPException(status_code=400, detail="合并模式必须填写合并标题")
    if cfg.transcribe_enabled and cfg.asr_engine == "dashscope":
        if not (cfg.dashscope_api_key or "").strip():
            raise HTTPException(status_code=400, detail="百炼转写需要配置 DashScope API Key")
        need = [
            cfg.oss_access_key_id,
            cfg.oss_access_key_secret,
            cfg.oss_bucket_name,
            cfg.oss_endpoint,
        ]
        if not all(x.strip() for x in need):
            raise HTTPException(status_code=400, detail="百炼转写需要完整 OSS 配置")


async def _run_pipeline(
    task_id: str,
    cfg: ProcessConfig,
    files: List[Any],
    queue: asyncio.Queue,
) -> List[ProcessResult]:
    trace_id = task_id[:8]
    results: List[ProcessResult] = []
    merge_pairs: List[tuple[str, str]] = []
    merge_sources: List[SourceFile] = []

    for i, fi in enumerate(files):
        filename = fi.filename
        src = _resolve_temp_path(fi.temp_path)

        audio_local_path: Optional[str] = None
        audio_oss_url: Optional[str] = None
        transcript: Optional[str] = None
        markdown_text: Optional[str] = None
        caption_local_path: Optional[str] = None
        caption_oss_url: Optional[str] = None

        try:
            await _push(
                queue,
                task_id,
                i,
                filename,
                "converting",
                "检测文件类型...",
                5,
            )

            ft = detect_file_type(src)
            if ft == "video":
                await _push(
                    queue,
                    task_id,
                    i,
                    filename,
                    "converting",
                    "正在提取音频...",
                    12,
                )
                t0 = time.perf_counter()
                out_mp3 = _temp_root() / f"{task_id[:8]}_{i}_{Path(filename).stem}.mp3"
                await video_to_audio(src, out_mp3)
                log_timing(
                    LOG,
                    trace_id,
                    "video_to_audio",
                    time.perf_counter() - t0,
                    file=filename,
                )
                work_audio = out_mp3
            else:
                await _push(
                    queue,
                    task_id,
                    i,
                    filename,
                    "converting",
                    "准备音频...",
                    10,
                )
                out_mp3 = _temp_root() / f"{task_id[:8]}_{i}_{Path(filename).stem}.mp3"
                work_audio = await audio_to_mp3_if_needed(src, out_mp3)

            if cfg.save_audio_local:
                await _push(
                    queue,
                    task_id,
                    i,
                    filename,
                    "saving",
                    "保存音频到本地...",
                    22,
                )
                audio_local_path = await _save_audio_local(work_audio, filename, cfg)

            need_oss_asr = cfg.transcribe_enabled and cfg.asr_engine == "dashscope"
            if cfg.save_audio_oss or need_oss_asr:
                await _push(
                    queue,
                    task_id,
                    i,
                    filename,
                    "uploading_oss",
                    "上传音频到OSS...",
                    32,
                )
                t0 = time.perf_counter()
                audio_oss_url = await upload_to_oss(
                    work_audio,
                    filename,
                    "audios",
                    cfg,
                )
                log_timing(
                    LOG,
                    trace_id,
                    "oss_upload_audio",
                    time.perf_counter() - t0,
                    file=filename,
                )

            if cfg.transcribe_enabled:
                await _push(
                    queue,
                    task_id,
                    i,
                    filename,
                    "transcribing",
                    "正在转写音频...",
                    45,
                )
                t0 = time.perf_counter()
                if cfg.asr_engine == "funasr":
                    transcript = await asr_local.transcribe(work_audio, trace_id)
                else:
                    if not audio_oss_url:
                        raise ValueError(
                            "百炼API需要OSS URL，请在设置中开启[上传音频到OSS]或配置OSS"
                        )
                    transcript = await asr_dashscope.transcribe(
                        audio_oss_url,
                        cfg.dashscope_api_key,
                        trace_id,
                    )
                log_timing(
                    LOG,
                    trace_id,
                    f"asr_{cfg.asr_engine}",
                    time.perf_counter() - t0,
                    file=filename,
                    chars=len(transcript or ""),
                )
                markdown_text = format_single(filename, transcript or "")

            if cfg.transcribe_enabled and transcript and cfg.transcript_save_local:
                await _push(
                    queue,
                    task_id,
                    i,
                    filename,
                    "saving",
                    "保存字幕到本地...",
                    62,
                )
                caption_local_path = await _save_caption_local(
                    markdown_text or "",
                    filename,
                    cfg,
                )

            if cfg.transcribe_enabled and transcript and cfg.transcript_save_oss:
                await _push(
                    queue,
                    task_id,
                    i,
                    filename,
                    "uploading_oss",
                    "上传字幕到OSS...",
                    72,
                )
                caption_oss_url = await upload_caption_to_oss(
                    markdown_text or "",
                    filename,
                    cfg,
                )

            sf = SourceFile(
                filename=filename,
                audio_local_path=audio_local_path,
                audio_oss_url=audio_oss_url,
                caption_local_path=caption_local_path,
                caption_oss_url=caption_oss_url,
            )

            summary: Optional[str] = None
            if (
                cfg.transcribe_enabled
                and transcript
                and cfg.summary_enabled
                and cfg.batch_mode == "separate"
            ):
                await _push(
                    queue,
                    task_id,
                    i,
                    filename,
                    "summarizing",
                    "AI总结中...",
                    82,
                )
                prompt_content = await R.get_prompt_content(cfg.summary_prompt_title)
                summ = get_summarizer(cfg.summary_model, cfg.qwen_api_key)
                summary = await summ.summarize(transcript, prompt_content, trace_id)

            if cfg.batch_mode == "separate":
                pr = ProcessResult(
                    title=Path(filename).stem,
                    source_files=[sf],
                    captions=markdown_text,
                    summary=summary,
                    status="success",
                )
                saved = await _save_db(task_id, cfg, pr)
                if saved is not None:
                    rid, ru = saved
                    pr = pr.model_copy(update={"record_id": rid, "record_uuid": ru})
                results.append(pr)

            else:
                if cfg.transcribe_enabled and transcript:
                    merge_pairs.append((filename, transcript))
                merge_sources.append(sf)

            await _push(
                queue,
                task_id,
                i,
                filename,
                "done",
                "处理完成",
                100,
            )

        except Exception as e:
            log_error(LOG, trace_id, "process_file", e, file=filename)
            await _push(
                queue,
                task_id,
                i,
                filename,
                "error",
                f"处理失败: {e}",
                0,
                error=str(e),
            )
            if cfg.batch_mode == "separate":
                results.append(
                    ProcessResult(
                        title=Path(filename).stem,
                        source_files=[],
                        status="error",
                        error_msg=str(e),
                    )
                )

    if cfg.batch_mode == "merge" and merge_pairs:
        merged_captions = format_merged(merge_pairs)
        summary: Optional[str] = None
        if cfg.summary_enabled:
            await _push(
                queue,
                task_id,
                0,
                cfg.merge_title or "合并",
                "summarizing",
                "AI总结中（合并）...",
                88,
            )
            prompt_content = await R.get_prompt_content(cfg.summary_prompt_title)
            summ = get_summarizer(cfg.summary_model, cfg.qwen_api_key)
            summary = await summ.summarize(merged_captions, prompt_content, trace_id)

        pr = ProcessResult(
            title=(cfg.merge_title or "").strip() or "合并结果",
            source_files=merge_sources,
            captions=merged_captions,
            summary=summary,
            status="success",
        )
        saved = await _save_db(task_id, cfg, pr)
        if saved is not None:
            rid, ru = saved
            pr = pr.model_copy(update={"record_id": rid, "record_uuid": ru})
        results.append(pr)

    return results


async def _batch_worker(task_id: str, body: BatchProcessRequest) -> None:
    queue: asyncio.Queue = TASKS[task_id]["queue"]
    try:
        base = await R.get_config()
        merged = merge_config(base, body.config)
        cfg = process_config_from_merged(merged)
        _validate_cfg(cfg)

        out = await _run_pipeline(task_id, cfg, body.files, queue)
        rlist = [_to_result_dict(x) for x in out]
        TASKS[task_id]["results"] = rlist
        TASKS[task_id]["status"] = "completed"

        if cfg.push_notion_enabled and rlist:
            try:
                from services.notion_push import push_items_to_notion

                payloads: List[dict] = []
                for x in rlist:
                    rid = x.get("record_id")
                    if not rid:
                        continue
                    row = await db.get_record(int(rid))
                    if row:
                        payloads.append(integration_dict_from_row(row))
                if payloads:
                    await push_items_to_notion(payloads, cfg, trace_id=task_id[:8])
                    ids = [int(x["record_id"]) for x in rlist if x.get("record_id")]
                    if ids:
                        await db.update_push_flags(ids, notion=True)
            except Exception as ex:
                log_error(LOG, task_id[:8], "auto_push_notion", ex)
        if cfg.push_feishu_enabled and rlist:
            try:
                from services.feishu_push import push_items_to_feishu

                payloads_f: List[dict] = []
                for x in rlist:
                    rid = x.get("record_id")
                    if not rid:
                        continue
                    row = await db.get_record(int(rid))
                    if row:
                        payloads_f.append(integration_dict_from_row(row))
                if payloads_f:
                    await push_items_to_feishu(payloads_f, cfg, trace_id=task_id[:8])
                    ids = [int(x["record_id"]) for x in rlist if x.get("record_id")]
                    if ids:
                        await db.update_push_flags(ids, feishu=True)
            except Exception as ex:
                log_error(LOG, task_id[:8], "auto_push_feishu", ex)

        await _push(
            queue,
            task_id,
            -1,
            "",
            "done",
            "全部完成",
            100,
            results=TASKS[task_id]["results"],
        )
    except Exception as e:
        log_error(LOG, task_id[:8], "batch", e)
        TASKS[task_id]["status"] = "failed"
        TASKS[task_id]["error"] = str(e)
        await _push(
            queue,
            task_id,
            -1,
            "",
            "error",
            str(e),
            0,
            error=str(e),
        )
    finally:
        try:
            _cleanup_task_temp_files(task_id, body.files)
        except Exception as ex:
            log_error(LOG, task_id[:8], "temp_cleanup", ex)
        await queue.put(None)


@router.post("/batch")
async def start_batch(body: BatchProcessRequest):
    if not body.files:
        raise HTTPException(status_code=400, detail="文件列表为空")
    task_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    TASKS[task_id] = {
        "queue": queue,
        "status": "running",
        "results": None,
        "error": None,
    }
    asyncio.create_task(_batch_worker(task_id, body))
    return {"task_id": task_id}


@router.get("/progress/{task_id}")
async def progress_sse(task_id: str):
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="任务不存在")
    q: asyncio.Queue = TASKS[task_id]["queue"]

    async def gen():
        try:
            while True:
                item = await q.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            raise

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
