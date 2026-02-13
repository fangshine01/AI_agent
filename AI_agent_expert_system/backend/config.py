"""
Backend Configuration Module
擴展現有 config.py，新增 FastAPI、Watcher、Gemini 配置
"""
import os
import sys
import pathlib
import logging
from dotenv import load_dotenv

# 加入專案根目錄到 Python path (以便匯入現有 core/ 模組)
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# 載入 .env
load_dotenv(PROJECT_ROOT / ".env")

# ========== API 配置 ==========
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://innoai.cminl.oa/agency/proxy/openai/platform")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# 相容性別名 (供 chat.py 和 ai_core 使用)
API_KEY = OPENAI_API_KEY
BASE_URL = OPENAI_BASE_URL

# ========== 檔案路徑 (相對於 backend/) ==========
BACKEND_DIR = pathlib.Path(__file__).parent.resolve()
RAW_FILES_DIR = str(BACKEND_DIR / os.getenv("RAW_FILES_DIR", "data/raw_files"))
ARCHIVED_FILES_DIR = str(BACKEND_DIR / os.getenv("ARCHIVED_FILES_DIR", "data/archived_files"))
GENERATED_MD_DIR = str(BACKEND_DIR / os.getenv("GENERATED_MD_DIR", "data/generated_md"))
FAILED_FILES_DIR = str(BACKEND_DIR / os.getenv("FAILED_FILES_DIR", "data/failed_files"))
LOGS_DIR = str(BACKEND_DIR / "data" / "logs")

# ========== Watcher 配置 ==========
ENABLE_FILE_WATCHER = os.getenv("ENABLE_FILE_WATCHER", "true").lower() == "true"
WATCHER_DEBOUNCE_SECONDS = int(os.getenv("WATCHER_DEBOUNCE_SECONDS", "2"))
WATCHER_POLL_INTERVAL = int(os.getenv("WATCHER_POLL_INTERVAL", "1"))

# ========== 資料庫 (全新 v2) ==========
DB_PATH = str(BACKEND_DIR / os.getenv("DB_PATH", "data/documents/knowledge_v2.db"))
TOKEN_DB_PATH = str(BACKEND_DIR / os.getenv("TOKEN_DB_PATH", "data/documents/tokenrecord_v2.db"))

# ========== API Server ==========
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# ========== 模型配置 ==========
DEFAULT_TEXT_MODEL = "gpt-4o-mini"
DEFAULT_VISION_MODEL = "gpt-4o"
DEFAULT_CHAT_MODEL = "gpt-4o-mini"
GEMINI_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

# 可用模型清單 (v2.2.0 - 前端 Model 選擇器使用)
# 企業 API 同時支援 OpenAI 與 Gemini 模型，透過相同 proxy 端點
AVAILABLE_MODELS = {
    # --- 正式模型 ---
    "GPT-4.1": "gpt-4.1-preview",
    "GPT-4.1-mini": "gpt-4.1-mini-preview",
    "GPT-4o": "gpt-4o",
    "GPT-4o-mini": "gpt-4o-mini",
    "gemini-2.5-pro": "gemini-2.5-pro",
    "gemini-2.5-flash": "gemini-2.5-flash",
    "gemini-2.5-flash-Lite": "gemini-2.5-flash-lite",
    # --- 預覽 / 未來模型 ---
    "GPT-5.1": "gpt-5.1-preview",
    "GPT-5-mini": "gpt-5-mini-preview",
    "gemini 3.0 Pro Preview": "gemini-3.0-pro-preview",
    "gemini 3.0 Pro flash Preview": "gemini-3.0-flash-preview",
    # --- 圖片優化模型 ---
    "gemini 2.5 flash image(nano banana)": "gemini-2.5-flash-nano-banana",
    "gemini 3.0 Pro image Preview(nano banana pro)": "gemini-3.0-pro-nano-banana",
}

# 模型分類標籤（供前端 UI 分組顯示）
MODEL_CATEGORIES = {
    "gpt-4.1-preview": "Default High-end",
    "gpt-4.1-mini-preview": "Default Fast",
    "gpt-4o": "Standard",
    "gpt-4o-mini": "Standard Fast",
    "gemini-2.5-pro": "Google High-end",
    "gemini-2.5-flash": "Google Fast",
    "gemini-2.5-flash-lite": "Google Lite",
    "gpt-5.1-preview": "Future",
    "gpt-5-mini-preview": "Future",
    "gemini-3.0-pro-preview": "Future",
    "gemini-3.0-flash-preview": "Future",
    "gemini-2.5-flash-nano-banana": "Image Optimized",
    "gemini-3.0-pro-nano-banana": "Image Optimized",
}

MODEL_COST_LABELS = {
    "gpt-4o-mini": "💰",
    "gpt-4o": "💰💰",
    "gpt-4.1-preview": "💰💰💰",
    "gpt-4.1-mini-preview": "💰",
    "gpt-5.1-preview": "💰💰💰",
    "gpt-5-mini-preview": "💰💰",
    "gemini-2.5-flash": "💰",
    "gemini-2.5-flash-lite": "💰",
    "gemini-2.5-pro": "💰💰💰",
    "gemini-3.0-pro-preview": "💰💰💰",
    "gemini-3.0-flash-preview": "💰💰",
    "gemini-2.5-flash-nano-banana": "💰",
    "gemini-3.0-pro-nano-banana": "💰💰",
}

# ========== Session 與安全配置 (v2.2.0) ==========
SESSION_TTL = int(os.getenv("SESSION_TTL", "86400"))  # 預設 24 小時
SESSION_MAX_TTL = int(os.getenv("SESSION_MAX_TTL", "604800"))  # 最長 7 天

# ========== Rate Limiting 配置 (v2.2.0) ==========
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "500"))
ADMIN_RATE_LIMIT_PER_MINUTE = int(os.getenv("ADMIN_RATE_LIMIT_PER_MINUTE", "100"))

# ========== Input 驗證 (v2.2.0) ==========
MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", "2000"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))

# ========== Logging ==========
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "backend.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)
logger.info("=" * 50)
logger.info("AI Expert System Backend - Config Loaded")
logger.info(f"  DB_PATH: {DB_PATH}")
logger.info(f"  RAW_FILES_DIR: {RAW_FILES_DIR}")
logger.info(f"  WATCHER: {'ON' if ENABLE_FILE_WATCHER else 'OFF'}")
logger.info("=" * 50)


# ========== 配置驗證 (v2.2.0 Phase 2) ==========

def validate_config(strict: bool = False) -> list:
    """
    啟動時驗證關鍵配置

    Args:
        strict: True 時缺少必要設定會 raise RuntimeError

    Returns:
        list: 警告訊息清單
    """
    warnings = []

    # 必要配置檢查
    required_paths = {
        "DB_PATH": DB_PATH,
        "TOKEN_DB_PATH": TOKEN_DB_PATH,
    }
    for name, path in required_paths.items():
        parent = pathlib.Path(path).parent
        if not parent.exists():
            try:
                parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"  📁 自動建立目錄: {parent}")
            except Exception as e:
                msg = f"無法建立資料庫目錄 {parent}: {e}"
                warnings.append(msg)
                if strict:
                    raise RuntimeError(msg)

    # API Key 檢查（警告級別，BYOK 模式下非必要）
    if not OPENAI_API_KEY and not GEMINI_API_KEY:
        warnings.append("未設定任何系統級 API Key (OPENAI_API_KEY 或 GEMINI_API_KEY)。BYOK 模式下使用者需自行提供。")

    # 數值範圍檢查
    if RATE_LIMIT_PER_MINUTE < 1 or RATE_LIMIT_PER_MINUTE > 1000:
        warnings.append(f"RATE_LIMIT_PER_MINUTE={RATE_LIMIT_PER_MINUTE} 超出合理範圍 (1-1000)")
    if SESSION_TTL < 300:
        warnings.append(f"SESSION_TTL={SESSION_TTL} 低於 5 分鐘，可能過短")
    if MAX_QUERY_LENGTH < 100:
        warnings.append(f"MAX_QUERY_LENGTH={MAX_QUERY_LENGTH} 低於 100，可能影響使用者體驗")

    for w in warnings:
        logger.warning(f"  ⚠️ {w}")

    return warnings


# 啟動時自動執行配置驗證（非 strict 模式，僅警告）
_config_warnings = validate_config(strict=False)
if _config_warnings:
    logger.warning(f"  配置驗證發現 {len(_config_warnings)} 個警告")
