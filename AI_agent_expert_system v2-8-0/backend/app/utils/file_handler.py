"""
檔案操作工具函數
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


def save_uploaded_file(file_content: bytes, filename: str, dest_dir: str) -> str:
    """
    儲存上傳的檔案到指定目錄

    Args:
        file_content: 檔案內容 (bytes)
        filename: 檔案名稱
        dest_dir: 目標目錄

    Returns:
        str: 儲存路徑
    """
    os.makedirs(dest_dir, exist_ok=True)
    file_path = os.path.join(dest_dir, filename)

    # 處理同名檔案
    if os.path.exists(file_path):
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        while os.path.exists(file_path):
            file_path = os.path.join(dest_dir, f"{stem}_{counter}{suffix}")
            counter += 1

    with open(file_path, "wb") as f:
        f.write(file_content)

    logger.info(f"✅ 檔案已儲存: {file_path}")
    return file_path


def get_file_status(filename: str, raw_dir: str, archive_dir: str, failed_dir: str) -> dict:
    """
    查詢檔案處理狀態

    Returns:
        dict: {'status': 'pending'|'completed'|'failed'|'not_found', 'path': str}
    """
    raw_path = os.path.join(raw_dir, filename)
    archive_path = os.path.join(archive_dir, filename)
    failed_path = os.path.join(failed_dir, filename)

    if os.path.exists(archive_path):
        return {"status": "completed", "path": archive_path}
    elif os.path.exists(failed_path):
        # 嘗試讀取錯誤描述
        error_log = os.path.join(failed_dir, f"{filename}.error.txt")
        error_msg = ""
        if os.path.exists(error_log):
            with open(error_log, "r", encoding="utf-8") as f:
                error_msg = f.read()
        return {"status": "failed", "path": failed_path, "error": error_msg}
    elif os.path.exists(raw_path):
        return {"status": "pending", "path": raw_path}
    else:
        return {"status": "not_found", "path": ""}


def list_files_in_dir(dir_path: str, extensions: Optional[List[str]] = None) -> List[dict]:
    """列出目錄中的檔案"""
    if not os.path.exists(dir_path):
        return []

    files = []
    for entry in os.scandir(dir_path):
        if entry.is_file():
            if entry.name.startswith("."):
                continue
            if extensions and not any(entry.name.endswith(ext) for ext in extensions):
                continue
            stat = entry.stat()
            files.append({
                "filename": entry.name,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "path": entry.path,
            })

    files.sort(key=lambda x: x["modified"], reverse=True)
    return files
