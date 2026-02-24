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
# 注意：系統不再提供默認 API Key，所有用戶必須使用自己的 API Key (BYOK 模式)
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://innoai.cminl.oa/agency/proxy/openai/platform")

# 相容性別名 (供舊代碼使用，但不包含 API Key)
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

# 可用模型清單 (v2.4.0 - 依據 GPT_support.md 更新)
# 企業 API Proxy 統一端點，同時支援 OpenAI / Google / Azure 模型
# 格式：list of dict，含 display_name、model_id、category、cost_label
AVAILABLE_MODELS = [
    # ===== OpenAI 平台 (12 個) =====
    {"display_name": "OpenAI-GPT-4o",         "model_id": "gpt-4o",               "category": "OpenAI 標準",  "cost_label": "💰💰"},
    {"display_name": "OpenAI-GPT-4o-mini",     "model_id": "gpt-4o-mini",          "category": "OpenAI 標準",  "cost_label": "💰"},
    {"display_name": "OpenAI-GPT-4.1",         "model_id": "gpt-4.1",              "category": "OpenAI 進階",  "cost_label": "💰💰💰"},
    {"display_name": "OpenAI-GPT-4.1-Mini",    "model_id": "gpt-4.1-mini",         "category": "OpenAI 輕量",  "cost_label": "💰"},
    {"display_name": "OpenAI-GPT-4-Turbo",     "model_id": "gpt-4-turbo-preview",  "category": "OpenAI 舊版",  "cost_label": "💰💰💰"},
    {"display_name": "OpenAI-GPT-4-Vision",    "model_id": "gpt-4-vision-preview", "category": "OpenAI 視覺",  "cost_label": "💰💰💰"},
    {"display_name": "OpenAI-O1",              "model_id": "o1",                   "category": "OpenAI 推理",  "cost_label": "💰💰💰"},
    {"display_name": "OpenAI-O1-Mini",         "model_id": "o1-mini",              "category": "OpenAI 推理",  "cost_label": "💰💰"},
    {"display_name": "OpenAI-O3-mini",         "model_id": "o3-mini",              "category": "OpenAI 推理",  "cost_label": "💰💰"},
    {"display_name": "OpenAI-O4-Mini",         "model_id": "o4-mini",              "category": "OpenAI 推理",  "cost_label": "💰💰"},
    {"display_name": "GPT-5-mini",             "model_id": "gpt-5-mini",           "category": "OpenAI 未來",  "cost_label": "💰💰"},
    {"display_name": "GPT-5.1",                "model_id": "gpt-5.1",              "category": "OpenAI 未來",  "cost_label": "💰💰💰"},
    # ===== Google 平台 (10 個) =====
    {"display_name": "Google-Gemini-2.5-Pro",        "model_id": "gemini-2.5-pro",            "category": "Google 進階",  "cost_label": "💰💰💰"},
    {"display_name": "Google-Gemini-2.5-Flash",       "model_id": "gemini-2.5-flash",          "category": "Google 標準",  "cost_label": "💰"},
    {"display_name": "Google-Gemini-2.5-Flash-Lite",  "model_id": "gemini-2.5-flash-lite",     "category": "Google 輕量",  "cost_label": "💰"},
    {"display_name": "Google-Gemini-2.0-Flash",       "model_id": "gemini-2.0-flash",          "category": "Google 標準",  "cost_label": "💰"},
    {"display_name": "Google-Gemini-2.0-Flash-Lite",  "model_id": "gemini-2.0-flash-lite",     "category": "Google 輕量",  "cost_label": "💰"},
    {"display_name": "Google-Gemini-1.5-Flash",       "model_id": "gemini-1.5-flash-latest",   "category": "Google 舊版",  "cost_label": "💰"},
    {"display_name": "Gemini-3-Pro-Preview",          "model_id": "gemini-3-pro-preview",      "category": "Google 未來",  "cost_label": "💰💰💰"},
    {"display_name": "Gemini-3-Flash-Preview",        "model_id": "gemini-3-flash-preview",    "category": "Google 未來",  "cost_label": "💰💰"},
    {"display_name": "Gemini-2.5-Flash-Image",        "model_id": "gemini-2.5-flash-image",    "category": "Google 視覺",  "cost_label": "💰💰"},
    {"display_name": "Gemini-3-Pro-Image",            "model_id": "gemini-3-pro-image-preview", "category": "Google 視覺", "cost_label": "💰💰💰"},
    # ===== Azure 平台 (9 個) =====
    {"display_name": "Azure-GPT-4o",       "model_id": "gpt-4o",      "category": "Azure 標準",  "cost_label": "💰💰"},
    {"display_name": "Azure-GPT-4o-mini",  "model_id": "gpt-4o-mini", "category": "Azure 標準",  "cost_label": "💰"},
    {"display_name": "Azure-GPT-4o-0806", "model_id": "gpt-4o-0806", "category": "Azure 標準",  "cost_label": "💰💰"},
    {"display_name": "Azure-GPT-4.1",     "model_id": "gpt-4.1",     "category": "Azure 進階",  "cost_label": "💰💰💰"},
    {"display_name": "Azure-GPT-4.1-Mini","model_id": "gpt-4.1-mini","category": "Azure 輕量",  "cost_label": "💰"},
    {"display_name": "Azure-O1-Mini",     "model_id": "o1-mini",     "category": "Azure 推理",  "cost_label": "💰💰"},
    {"display_name": "Azure-GPT-O4-Mini", "model_id": "o4-mini",     "category": "Azure 推理",  "cost_label": "💰💰"},
    {"display_name": "Azure-GPT-4-Turbo", "model_id": "gpt-4",       "category": "Azure 舊版",  "cost_label": "💰💰💰"},
    {"display_name": "Azure-GPT-5.1",     "model_id": "gpt-5.1",     "category": "Azure 未來",  "cost_label": "💰💰💰"},
]

# 模型分類標籤 (v2.4.0 - 供反查用，key 為 model_id)
MODEL_CATEGORIES = {m["model_id"]: m["category"] for m in AVAILABLE_MODELS}

# 模型費用標籤 (v2.4.0 - 供反查用，key 為 model_id)
MODEL_COST_LABELS = {m["model_id"]: m["cost_label"] for m in AVAILABLE_MODELS}

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
    # 系統採用 BYOK (Bring Your Own Key) 模式
    warnings.append("系統採用 BYOK 模式：所有用戶必須提供自己的 API Key，系統不提供共享 Key。")

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


# ========== 配置管理方法 (v2.3.0) ==========
ANALYSIS_MODE = "auto"

def get_api_config() -> dict:
    """取得當前 API 配置（不包含 API Key，用戶必須自行提供）"""
    return {
        "base_url": OPENAI_BASE_URL,
        "model_vision": DEFAULT_VISION_MODEL,
        "model_text": DEFAULT_TEXT_MODEL,
        "analysis_mode": ANALYSIS_MODE,
    }

def set_api_config(
    base_url: str = None,
    model_vision: str = None,
    model_text: str = None,
    analysis_mode: str = None,
):
    """更新 API 配置 (不包含 API Key 設定)"""
    global OPENAI_BASE_URL, DEFAULT_VISION_MODEL, DEFAULT_TEXT_MODEL, ANALYSIS_MODE, BASE_URL

    if base_url is not None:
        OPENAI_BASE_URL = base_url
        BASE_URL = base_url
    if model_vision is not None:
        DEFAULT_VISION_MODEL = model_vision
    if model_text is not None:
        DEFAULT_TEXT_MODEL = model_text
    if analysis_mode is not None:
        ANALYSIS_MODE = analysis_mode

    logger.info(f"API 配置已更新: url={OPENAI_BASE_URL}, mode={ANALYSIS_MODE}")
