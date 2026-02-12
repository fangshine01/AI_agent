"""
FastAPI 主程式 - AI Expert System Backend
啟動方式: uvicorn backend.app.main:app --reload --port 8000
"""

import os
import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path

# 確保專案根目錄在 Python path 中
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import backend.config as cfg
from backend.app.middleware.cors import setup_cors
from backend.app.middleware.token_tracker import TokenTrackerMiddleware
from backend.app.api.v1 import chat, ingestion, files, admin, search

logger = logging.getLogger(__name__)

# 全域: Watcher Observer
_watcher_observer = None


def _ensure_all_databases():
    """確保所有資料庫已初始化（首次在新主機使用時自動建立）"""
    from backend.app.utils.db_init import ensure_databases

    # 後端 v2 資料庫
    ensure_databases(cfg.DB_PATH, cfg.TOKEN_DB_PATH)

    # 根目錄舊版資料庫 (core 模組使用)
    try:
        import config as root_config
        ensure_databases(root_config.DB_PATH, root_config.TOKEN_DB_PATH)
    except (ImportError, AttributeError) as e:
        logger.warning(f"⚠️ 無法初始化根目錄資料庫: {e}")

    # 確保檔案處理目錄存在
    for dir_path in [
        cfg.RAW_FILES_DIR, cfg.ARCHIVED_FILES_DIR,
        cfg.FAILED_FILES_DIR, cfg.GENERATED_MD_DIR,
    ]:
        os.makedirs(dir_path, exist_ok=True)
    logger.info("📂 所有資料目錄已就緒")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    global _watcher_observer

    # Startup: 確保資料庫存在（首次使用自動建立）
    _ensure_all_databases()

    # Startup: 啟動檔案監控
    if cfg.ENABLE_FILE_WATCHER:
        try:
            from backend.app.services.file_watcher import start_file_watcher

            watcher_config = {
                "raw_dir": cfg.RAW_FILES_DIR,
                "archive_dir": cfg.ARCHIVED_FILES_DIR,
                "failed_dir": cfg.FAILED_FILES_DIR,
                "generated_md_dir": cfg.GENERATED_MD_DIR,
                "debounce": cfg.WATCHER_DEBOUNCE_SECONDS,
            }
            _watcher_observer = start_file_watcher(watcher_config)
            logger.info("👁️ File Watcher 已啟動")
        except Exception as e:
            logger.warning(f"⚠️ File Watcher 啟動失敗: {e}")

    logger.info("🚀 FastAPI 服務啟動完成")

    yield  # 應用運行期間

    # Shutdown: 停止監控
    if _watcher_observer:
        _watcher_observer.stop()
        _watcher_observer.join()
        logger.info("👋 File Watcher 已停止")


# 初始化 FastAPI 應用
app = FastAPI(
    title="AI Expert System API",
    description="知識庫問答與自動化文件處理 API",
    version="2.0.0",
    lifespan=lifespan,
)

# 設定 CORS
setup_cors(app)

# Token 追蹤中介層
app.add_middleware(TokenTrackerMiddleware)

# API Key 驗證中介層 (可選，需在 .env 設定 ENABLE_API_AUTH=true)
from backend.app.middleware.api_auth import APIKeyMiddleware, is_api_auth_enabled, log_auth_status
if is_api_auth_enabled():
    app.add_middleware(APIKeyMiddleware)
log_auth_status()

# 掛載靜態檔案目錄
# 警告: 這些目錄的檔案可以被直接下載，如需保護請啟用 API Key 驗證
for dir_name, dir_path in [
    ("archived", cfg.ARCHIVED_FILES_DIR),
    ("generated", cfg.GENERATED_MD_DIR),
]:
    os.makedirs(dir_path, exist_ok=True)
    app.mount(f"/files/{dir_name}", StaticFiles(directory=dir_path), name=dir_name)

# 註冊 API 路由
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["Ingestion"])
app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])


@app.get("/")
async def root():
    """API 首頁"""
    return {
        "message": "AI Expert System API",
        "version": "2.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "watcher_running": _watcher_observer is not None and _watcher_observer.is_alive(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=cfg.API_HOST,
        port=cfg.API_PORT,
        reload=True,
    )
