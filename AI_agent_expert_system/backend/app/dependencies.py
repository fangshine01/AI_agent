"""
FastAPI 依賴注入模組
提供共享的資料庫連線、配置等
"""

import sys
import os
import pathlib

# 確保專案根目錄在 Python path 中
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import database, ai_core, search
import config as app_config


def get_database():
    """取得資料庫模組"""
    return database


def get_ai_core():
    """取得 AI Core 模組"""
    return ai_core


def get_search():
    """取得搜尋模組"""
    return search


def get_config():
    """取得配置"""
    return app_config
