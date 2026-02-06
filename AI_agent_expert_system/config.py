"""
AI Expert System - Configuration Module
全域配置與 Logging 系統
"""

import os
import logging

# ========== 動態 API 配置 ==========
# 全域變數,用於儲存動態設定的 API 資訊
_dynamic_api_key = ""
_dynamic_base_url = "https://api.openai.com/v1"
_dynamic_model_vision = "gpt-4o"
_dynamic_model_text = "gpt-4o-mini"
_dynamic_analysis_mode = "auto"

# 預設值(可選)
API_KEY = _dynamic_api_key
BASE_URL = _dynamic_base_url
MODEL_VISION = _dynamic_model_vision
MODEL_TEXT = _dynamic_model_text
ANALYSIS_MODE = _dynamic_analysis_mode


def set_api_config(api_key: str = None, base_url: str = None, 
                   model_vision: str = None, model_text: str = None,
                   analysis_mode: str = None):
    """
    設定 API 配置(用於後台管理介面)
    
    Args:
        api_key: OpenAI API Key
        base_url: API Base URL
        model_vision: Vision 模型名稱
        model_text: Text 模型名稱
    """
    global _dynamic_api_key, _dynamic_base_url, _dynamic_model_vision, _dynamic_model_text, _dynamic_analysis_mode
    global API_KEY, BASE_URL, MODEL_VISION, MODEL_TEXT, ANALYSIS_MODE
    
    if api_key is not None:
        _dynamic_api_key = api_key.strip()
        API_KEY = api_key.strip()
    
    if base_url is not None:
        _dynamic_base_url = base_url
        BASE_URL = base_url
    
    if model_vision is not None:
        _dynamic_model_vision = model_vision
        MODEL_VISION = model_vision
    
    if model_text is not None:
        _dynamic_model_text = model_text
        MODEL_TEXT = model_text
        
    if analysis_mode is not None:
        _dynamic_analysis_mode = analysis_mode
        ANALYSIS_MODE = analysis_mode
    
    logger.info(f"✅ API 配置已更新: Base URL={BASE_URL}")


def get_api_config() -> dict:
    """
    取得當前 API 配置
    
    Returns:
        dict: {'api_key': str, 'base_url': str, 'model_vision': str, 'model_text': str}
    """
    return {
        'api_key': API_KEY,
        'base_url': BASE_URL,
        'model_vision': MODEL_VISION,
        'model_text': MODEL_TEXT,
        'analysis_mode': ANALYSIS_MODE
    }


# ========== v3.0 模型配置 ==========
# 解析用模型 (Backend Parsing)
DEFAULT_TEXT_MODEL = "gpt-4o-mini"          # 純文字解析 (預算友善)
DEFAULT_VISION_MODEL = "gpt-4o"             # 圖文解析
ALTERNATIVE_TEXT_MODEL = "gemini-2.0-flash-exp"  # 替代文字模型
ALTERNATIVE_VISION_MODEL = "gemini-2.0-flash-exp"  # 替代視覺模型

# 問答用模型 (Frontend Chat)
DEFAULT_CHAT_MODEL = "gpt-4o-mini"          # 預設推理模型 (快速且經濟)
ADVANCED_CHAT_MODELS = [                    # 進階選項
    "gpt-4o",                               # 高階推理
    "gemini-2.0-flash-exp"                  # Gemini 高階
]

# Embedding 模型
EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI Embedding API
EMBEDDING_DIMENSION = 1536                  # 向量維度

# 模型成本等級標示 (用於 UI 顯示)
MODEL_COST_LABELS = {
    "gpt-4o-mini": "💰",
    "gpt-4o": "💰💰",
    "gemini-2.0-flash-exp": "💰💰"
}


# ========== API 模式常數 ==========
API_MODE_TEXT_ONLY = "text_only"   # 純文字模式（省錢）
API_MODE_VISION = "vision"          # Vision 模式（分析圖片）
API_MODE_AUTO = "auto"              # 自動判斷（有圖用 Vision）

# ========== 資料庫配置 ==========
# 使用絕對路徑確保無論從哪裡執行都能找到資料庫
import pathlib
_BASE_DIR = pathlib.Path(__file__).parent.resolve()
DB_PATH = str(_BASE_DIR / "data" / "knowledge.db")
TOKEN_DB_PATH = str(_BASE_DIR / "data" / "tokenrecord.db")  # 獨立的 Token 記錄資料庫


# ========== Logging 配置 ==========
# 確保 logs 目錄存在
os.makedirs('data/logs', exist_ok=True)

# 配置 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 初始化時輸出配置資訊
logger.info("=" * 50)
logger.info("AI Expert System - Configuration Loaded")
logger.info(f"Database Path: {DB_PATH}")
logger.info(f"Base URL: {BASE_URL}")
logger.info(f"Vision Model: {MODEL_VISION}")
logger.info(f"Text Model: {MODEL_TEXT}")
logger.info("=" * 50)
