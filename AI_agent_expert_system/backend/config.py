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
GEMINI_MODEL = "gemini-2.0-flash-exp"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

MODEL_COST_LABELS = {
    "gpt-4o-mini": "💰",
    "gpt-4o": "💰💰",
    "gemini-2.0-flash-exp": "💰💰",
    "gemini-2.5-flash": "💰💰",
    "gemini-2.5-pro": "💰💰💰",
}

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
