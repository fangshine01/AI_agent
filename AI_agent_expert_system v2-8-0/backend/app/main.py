"""
FastAPI 主程式 - AI Expert System Backend (v2.3.0)
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
from backend.app.middleware.identity import IdentityMiddleware
from backend.app.middleware.error_handler import ErrorHandlerMiddleware
from backend.app.middleware.rate_limiter import setup_rate_limiter
from backend.app.middleware.validation import InputValidationMiddleware
from backend.app.middleware.monitoring import PrometheusMetricsMiddleware, create_metrics_router
from backend.app.api.v1 import chat, ingestion, files, admin, search
from backend.app.api.v1 import auth, history
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.user import router as user_router
from backend.app.api.v1.models import router as models_router
from backend.app.utils.logger import setup_logging

logger = logging.getLogger(__name__)

# 全域: Watcher Observer
_watcher_observer = None


def _ensure_all_databases():
    """確保所有資料庫已初始化（首次在新主機使用時自動建立）"""
    from backend.app.utils.db_init import ensure_databases

    # 統一資料庫路徑（root config 已同步指向 backend v2 路徑）
    ensure_databases(cfg.DB_PATH, cfg.TOKEN_DB_PATH)

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

    # 初始化結構化日誌系統
    setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))

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
    version="2.3.0",
    lifespan=lifespan,
)

# ========== 中介層 (由外到內的順序，最後加入的最先執行) ==========

# 1. CORS (最外層)
setup_cors(app)

# 2. 全域錯誤處理
debug_mode = os.getenv("DEBUG", "false").lower() == "true"
app.add_middleware(ErrorHandlerMiddleware, debug=debug_mode)

# 3. Token 追蹤
app.add_middleware(TokenTrackerMiddleware)

# 4. BYOK 身份識別 (v2.2.0)
app.add_middleware(IdentityMiddleware)

# 5. API Key 驗證 (可選，舊有機制兼容)
from backend.app.middleware.api_auth import APIKeyMiddleware, is_api_auth_enabled, log_auth_status
if is_api_auth_enabled():
    app.add_middleware(APIKeyMiddleware)
log_auth_status()

# 6. Input 驗證 (v2.2.0 Phase 2)
app.add_middleware(InputValidationMiddleware)

# 7. Rate Limiter (v2.2.0)
setup_rate_limiter(app)

# 8. Prometheus Metrics (v2.3.0 Phase 5)
app.add_middleware(PrometheusMetricsMiddleware)

# 掛載靜態檔案目錄
# 警告: 這些目錄的檔案可以被直接下載，如需保護請啟用 API Key 驗證
for dir_name, dir_path in [
    ("archived", cfg.ARCHIVED_FILES_DIR),
    ("generated", cfg.GENERATED_MD_DIR),
]:
    os.makedirs(dir_path, exist_ok=True)
    app.mount(f"/files/{dir_name}", StaticFiles(directory=dir_path), name=dir_name)

# ========== 註冊 API 路由 ==========
# 原有路由
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["Ingestion"])
app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])

# v2.2.0 新增路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(history.router, prefix="/api/v1/history", tags=["History"])
app.include_router(health_router, tags=["Health"])
app.include_router(user_router, prefix="/api/v1/user", tags=["User/GDPR"])
app.include_router(models_router, prefix="/api/v1/models", tags=["Models"])

# Prometheus Metrics 端點 (v2.3.0)
app.include_router(create_metrics_router(), tags=["Monitoring"])


@app.get("/")
async def root():
    """API 首頁"""
    return {
        "message": "AI Expert System API",
        "version": "2.3.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=cfg.API_HOST,
        port=cfg.API_PORT,
        reload=True,
    )
