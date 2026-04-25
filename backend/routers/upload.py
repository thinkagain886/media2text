# -*- coding: utf-8 -*-
"""文件上传"""

import uuid
from pathlib import Path
from typing import List

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile

from core.config_loader import BACKEND_ROOT, settings
from core.logger import get_logger, log_step
from services.file_detector import detect_file_type

router = APIRouter(tags=["upload"])
LOG = get_logger("upload")


def _temp_root() -> Path:
    td = settings.temp_dir
    if not td.is_absolute():
        return (BACKEND_ROOT / td).resolve()
    return td.resolve()


@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    多文件上传，保存到 temp/{uuid}_{原文件名}。
    返回 file_id, filename, size, file_type, temp_path（相对 backend 根）。
    """
    if not files:
        raise HTTPException(status_code=400, detail="未选择文件")

    temp_dir = _temp_root()
    temp_dir.mkdir(parents=True, exist_ok=True)
    root = BACKEND_ROOT
    out = []

    for uf in files:
        orig = uf.filename or "unnamed"
        safe = Path(orig).name
        uid = uuid.uuid4().hex
        dest = temp_dir / f"{uid}_{safe}"

        try:
            async with aiofiles.open(dest, "wb") as f:
                while True:
                    chunk = await uf.read(1024 * 1024)
                    if not chunk:
                        break
                    await f.write(chunk)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"保存失败: {e}") from e

        try:
            ft = detect_file_type(dest)
        except ValueError as e:
            dest.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=str(e)) from e

        st = dest.stat()
        try:
            rel = dest.relative_to(root).as_posix()
        except ValueError:
            rel = dest.as_posix()

        log_step(
            LOG,
            "-",
            "upload",
            "已保存上传文件",
            filename=safe,
            size=st.st_size,
            file_type=ft,
        )

        out.append(
            {
                "file_id": uid,
                "filename": safe,
                "size": st.st_size,
                "file_type": ft,
                "temp_path": rel,
            }
        )

    return out
