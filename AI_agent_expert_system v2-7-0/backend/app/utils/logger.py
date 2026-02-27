"""
日誌系統配置 (v2.2.0 Phase 2)

功能：
- JSON 格式化日誌（含 timestamp, level, user_id_hash, endpoint, response_time）
- RotatingFileHandler（50MB/檔，保留 10 個）
- 隱私保護：自動遮罩 API Key

使用方式：
    from backend.app.utils.logger import setup_logging
    setup_logging()  # 在 main.py lifespan 中呼叫
"""

import os
import logging
import json
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler

import backend.config as cfg


# ========== API Key 遮罩 ==========

# 匹配 OpenAI-style key: sk-xxxx...xxxx
_KEY_PATTERN = re.compile(r'(sk-[a-zA-Z0-9]{4})[a-zA-Z0-9]{20,}([a-zA-Z0-9]{4})')
# 匹配 Gemini-style key: AIzaSy-xxxx
_GEMINI_KEY_PATTERN = re.compile(r'(AIzaSy[a-zA-Z0-9_-]{4})[a-zA-Z0-9_-]{20,}')


def mask_sensitive_data(text: str) -> str:
    """
    遮罩日誌中的敏感資料

    sk-abcd...wxyz → sk-abcd****wxyz
    AIzaSyABCD... → AIzaSyABCD****
    """
    text = _KEY_PATTERN.sub(r'\1****\2', text)
    text = _GEMINI_KEY_PATTERN.sub(r'\1****', text)
    return text


# ========== JSON 格式化器 ==========

class JSONFormatter(logging.Formatter):
    """
    JSON 結構化日誌格式化器

    輸出格式：
    {"timestamp": "...", "level": "INFO", "logger": "...", "message": "...", ...}
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": mask_sensitive_data(record.getMessage()),
        }

        # 附加 extra 欄位（如 user_id, endpoint 等）
        for key in ("user_id", "endpoint", "response_time", "error_id", "method", "status_code"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        # 例外資訊
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": mask_sensitive_data(str(record.exc_info[1])),
            }

        return json.dumps(log_entry, ensure_ascii=False)


class SafeFormatter(logging.Formatter):
    """
    標準格式化器 + API Key 遮罩

    用於 Console 輸出，保持可讀性
    """

    def format(self, record: logging.LogRecord) -> str:
        record.msg = mask_sensitive_data(str(record.msg))
        return super().format(record)


# ========== Setup ==========

def setup_logging(
    log_dir: str = None,
    log_level: str = "INFO",
    max_bytes: int = 50 * 1024 * 1024,  # 50MB
    backup_count: int = 10,
    enable_json: bool = True,
):
    """
    配置全域日誌系統

    Args:
        log_dir: 日誌目錄（預設使用 config.LOGS_DIR）
        log_level: 日誌等級
        max_bytes: 單一日誌檔最大大小
        backup_count: 保留的歷史檔案數量
        enable_json: 是否啟用 JSON 格式（檔案日誌）
    """
    log_dir = log_dir or cfg.LOGS_DIR
    os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 清除既有 handler（避免重複）
    root_logger.handlers.clear()

    # 1. Console Handler（人類可讀格式 + Key 遮罩）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(SafeFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    root_logger.addHandler(console_handler)

    # 2. 主日誌檔（JSON 格式 + 輪轉）
    main_log_path = os.path.join(log_dir, "backend.log")
    file_handler = RotatingFileHandler(
        main_log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    if enable_json:
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(SafeFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
    root_logger.addHandler(file_handler)

    # 3. 錯誤日誌檔（僅 WARNING+）
    error_log_path = os.path.join(log_dir, "errors.log")
    error_handler = RotatingFileHandler(
        error_log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(JSONFormatter() if enable_json else SafeFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    root_logger.addHandler(error_handler)

    # 4. 告警日誌檔（供監控系統讀取）
    alerts_log_path = os.path.join(log_dir, "alerts.log")
    alerts_handler = RotatingFileHandler(
        alerts_log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    alerts_handler.setLevel(logging.CRITICAL)
    alerts_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(alerts_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("watchdog").setLevel(logging.WARNING)

    root_logger.info("📝 日誌系統已初始化 (JSON=%s, dir=%s)", enable_json, log_dir)
