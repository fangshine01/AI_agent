"""
健康檢查路由 (v2.2.0)

提供：
- /health          → 簡易健康檢查（供 Load Balancer / 監控工具）
- /health/detailed → 詳細健康狀態（DB 連線、磁碟用量、Watcher 狀態、活躍 Session）
"""

import os
import time
import sqlite3
import logging
from datetime import datetime

from fastapi import APIRouter

import backend.config as cfg

logger = logging.getLogger(__name__)
router = APIRouter()

# 記錄啟動時間（供 uptime 計算）
_start_time = time.monotonic()


def _check_db(db_path: str) -> dict:
    """檢查 SQLite DB 連線與 WAL 模式"""
    result = {"path": db_path, "exists": False, "wal_mode": False, "ok": False, "latency_ms": 0}

    if not os.path.exists(db_path):
        return result

    result["exists"] = True
    start = time.monotonic()
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        cursor = conn.cursor()

        # 驗證 WAL 模式
        cursor.execute("PRAGMA journal_mode;")
        journal = cursor.fetchone()[0]
        result["wal_mode"] = (journal.lower() == "wal")

        # 驗證可查詢
        cursor.execute("SELECT 1;")
        conn.close()
        result["ok"] = True
    except Exception as e:
        result["error"] = str(e)

    result["latency_ms"] = round((time.monotonic() - start) * 1000, 2)
    return result


def _get_disk_info(path: str) -> dict:
    """取得磁碟使用情況（Windows 相容）"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(path)
        return {
            "total_gb": round(total / (1024 ** 3), 2),
            "used_gb": round(used / (1024 ** 3), 2),
            "free_gb": round(free / (1024 ** 3), 2),
            "usage_percent": round(used / total * 100, 1),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/health", summary="簡易健康檢查")
async def health_check():
    """
    供監控工具 / Load Balancer 使用的簡易健康檢查

    回傳 200 表示服務運行中
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.2.0",
    }


@router.get("/health/detailed", summary="詳細健康狀態")
async def health_detailed():
    """
    詳細健康檢查，包含：
    - 兩個 SQLite DB 的連線狀態與 WAL 模式
    - 磁碟使用量
    - 關鍵目錄是否存在（含檔案數）
    - 活躍 Session 與使用者數
    - 系統運行時間
    """
    # 檢查兩個資料庫
    knowledge_db = _check_db(cfg.DB_PATH)
    token_db = _check_db(cfg.TOKEN_DB_PATH)

    # 資料庫大小
    for db_info, db_path in [(knowledge_db, cfg.DB_PATH), (token_db, cfg.TOKEN_DB_PATH)]:
        try:
            if os.path.exists(db_path):
                db_info["size_mb"] = round(os.path.getsize(db_path) / (1024 * 1024), 2)
            else:
                db_info["size_mb"] = 0
        except Exception:
            db_info["size_mb"] = 0

    # 磁碟資訊
    disk = _get_disk_info(os.path.dirname(cfg.DB_PATH) or ".")

    # 關鍵目錄（含檔案計數）
    dirs_status = {}
    for name, path in [
        ("raw_files", cfg.RAW_FILES_DIR),
        ("archived", cfg.ARCHIVED_FILES_DIR),
        ("generated_md", cfg.GENERATED_MD_DIR),
    ]:
        exists = os.path.isdir(path)
        file_count = 0
        if exists:
            try:
                file_count = len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
            except Exception:
                pass
        dirs_status[name] = {
            "path": path,
            "exists": exists,
            "file_count": file_count,
        }

    # 活躍 Session 統計
    active_sessions = {"count": 0, "unique_users": 0}
    try:
        from backend.app.utils.session_manager import get_active_session_count, get_active_user_count
        active_sessions["count"] = get_active_session_count()
        active_sessions["unique_users"] = get_active_user_count()
    except Exception as e:
        logger.debug(f"取得 Session 統計失敗: {e}")

    # 整體狀態
    all_ok = knowledge_db["ok"] and token_db["ok"]

    # 運行時間
    uptime_seconds = round(time.monotonic() - _start_time, 1)

    return {
        "status": "healthy" if all_ok else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.2.0",
        "uptime_seconds": uptime_seconds,
        "disk_free_gb": disk.get("free_gb", 0),
        "databases": {
            "knowledge_db": knowledge_db,
            "token_db": token_db,
        },
        "disk": disk,
        "directories": dirs_status,
        "active_sessions": active_sessions,
    }
