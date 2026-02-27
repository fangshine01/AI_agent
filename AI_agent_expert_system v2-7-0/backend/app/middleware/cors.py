"""
CORS 中介層配置
"""

from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app):
    """設定 CORS"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8501",
            "http://localhost:8502",
            "http://127.0.0.1:8501",
            "http://127.0.0.1:8502",
            "*",  # 開發環境允許所有來源
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
