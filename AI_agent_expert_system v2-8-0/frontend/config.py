"""
Frontend Configuration
前端配置 (API URL、Port 等)
"""

import os
from dotenv import load_dotenv

load_dotenv()

# API 配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_V1_URL = f"{API_BASE_URL}/api/v1"

# 前端配置
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "8501"))
FRONTEND_CHAT_PORT = int(os.getenv("FRONTEND_CHAT_PORT", "8501"))
FRONTEND_ADMIN_PORT = int(os.getenv("FRONTEND_ADMIN_PORT", "8502"))
