"""
AI Expert System - Configuration Module
全域配置與 Logging 系統
"""

import os
import logging

# ========== 動態 API 配置 ==========
# 全域變數,用於儲存動態設定的 API 資訊
_dynamic_api_key = ""
_dynamic_base_url = "http://innoai.cminl.oa/agency/proxy/openai/platform"
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
# 解析用模型 (Backend Parsing) — 統一與 backend/config.py 對齊
DEFAULT_TEXT_MODEL = "gpt-4o-mini"          # 純文字解析 (預算友善)
DEFAULT_VISION_MODEL = "gpt-4o"             # 圖文解析
ALTERNATIVE_TEXT_MODEL = "gemini-2.5-flash" # 替代文字模型
ALTERNATIVE_VISION_MODEL = "gemini-2.5-pro" # 替代視覺模型

# 問答用模型 (Frontend Chat)
DEFAULT_CHAT_MODEL = "gpt-4o-mini"          # 預設推理模型 (快速且經濟)
ADVANCED_CHAT_MODELS = [                    # 進階選項
    "gpt-4o",                               # 高階推理
    "gpt-4.1-preview",                      # 最新高階
    "gemini-2.5-flash",                     # Gemini 快速
    "gemini-2.5-pro",                       # Gemini 高階
]

# Embedding 模型
EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI Embedding API
EMBEDDING_DIMENSION = 1536                  # 向量維度

# 模型成本等級標示 (用於 UI 顯示) — 統一 13 模型
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


# ========== API 模式常數 ==========
API_MODE_TEXT_ONLY = "text_only"   # 純文字模式（省錢）
API_MODE_VISION = "vision"          # Vision 模式（分析圖片）
API_MODE_AUTO = "auto"              # 自動判斷（有圖用 Vision）

# ========== 資料庫配置 ==========
# 統一使用 v2 資料庫路徑（與 backend/config.py 一致）
import pathlib
_BASE_DIR = pathlib.Path(__file__).parent.resolve()
DB_PATH = str(_BASE_DIR / "backend" / "data" / "documents" / "knowledge_v2.db")
TOKEN_DB_PATH = str(_BASE_DIR / "backend" / "data" / "documents" / "tokenrecord_v2.db")


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

# ========== 文件分組配置 ==========
DOCUMENT_GROUPING = {
    'enabled': True,
    'dynamic_chunk_selection': True,  # 啟用動態chunk選擇
    
    # 動態選擇閾值
    'similarity_thresholds': {
        'high': 0.85,      # 高相關度: 必選
        'medium': 0.70,    # 中等相關度: 最多3個
        'low': 0.50        # 低相關度: 最多1個
    },
    
    # 雙模式token預算
    'token_budget': {
        'training': None,  # 訓練模式: 無限制
        'qa': 2500         # 問答模式: 單次對話上限
    },
    
    # 摘要處理
    'use_db_summary_directly': True,  # 直接從SQL提取,不經GPT
    'fallback_preview_length': 100    # 若無摘要,顯示前N字
}

# 初始化時輸出配置資訊
logger.info("=" * 50)
logger.info("AI Expert System - Configuration Loaded")
logger.info(f"Database Path: {DB_PATH}")
logger.info(f"Base URL: {BASE_URL}")
logger.info(f"Vision Model: {MODEL_VISION}")
logger.info(f"Text Model: {MODEL_TEXT}")
logger.info("=" * 50)

