"""
Files API - 檔案下載與管理路由
"""

import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Optional

from backend.app.schemas.common import ResponseBase
from backend.app.utils.file_handler import list_files_in_dir

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_dirs():
    """取得檔案目錄配置"""
    import backend.config as cfg
    return cfg.ARCHIVED_FILES_DIR, cfg.GENERATED_MD_DIR, cfg.FAILED_FILES_DIR


@router.get("/download/{filename}")
async def download_file(filename: str, source: str = "archived"):
    """
    下載檔案

    Args:
        filename: 檔案名稱
        source: 來源目錄 ('archived', 'generated', 'failed')
    """
    archived_dir, generated_dir, failed_dir = _get_dirs()

    dir_map = {
        "archived": archived_dir,
        "generated": generated_dir,
        "failed": failed_dir,
    }

    base_dir = dir_map.get(source, archived_dir)
    file_path = os.path.join(base_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"檔案不存在: {filename}")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
    )


@router.get("/list", response_model=ResponseBase)
async def list_files(source: str = "archived", extension: Optional[str] = None):
    """
    列出所有檔案

    Args:
        source: 來源目錄 ('archived', 'generated', 'failed', 'pending')
        extension: 篩選副檔名 (例如 '.md')
    """
    import backend.config as cfg

    dir_map = {
        "archived": cfg.ARCHIVED_FILES_DIR,
        "generated": cfg.GENERATED_MD_DIR,
        "failed": cfg.FAILED_FILES_DIR,
        "pending": cfg.RAW_FILES_DIR,
    }

    base_dir = dir_map.get(source, cfg.ARCHIVED_FILES_DIR)
    extensions = [extension] if extension else None

    files = list_files_in_dir(base_dir, extensions)

    return ResponseBase(
        success=True,
        message=f"找到 {len(files)} 個檔案",
        data={"source": source, "files": files},
    )
