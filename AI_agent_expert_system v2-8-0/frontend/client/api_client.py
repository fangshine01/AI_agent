"""
API Client - 聚合 Facade (v3.0.0)

統一入口：ChatClient + AdminClient 的所有方法透過 APIClient 使用。
各領域客戶端已拆分至：
- client.base_client.BaseClient  通用 HTTP 請求 & BYOK 身份管理
- client.chat_client.ChatClient  問答 / Auth / History / Search
- client.admin_client.AdminClient  管理 / 上傳 / 文件 / Token / GDPR

依 organizing-streamlit-code skill：
  單一職責拆分，api_client.py 從 567 行縮減為 Facade。

變更紀錄:
- v3.0.0: 拆分為 BaseClient / ChatClient / AdminClient，本檔改為 MRO 聚合
- v2.2.0: 新增 BYOK header 支援、Auth 驗證、Chat History CRUD
"""

from client.chat_client import ChatClient
from client.admin_client import AdminClient


class APIClient(ChatClient, AdminClient):
    """
    聚合 API 客戶端  向後相容

    透過 Python MRO 聚合 ChatClient 與 AdminClient（均繼承 BaseClient），
    保持所有既有 import / 呼叫不需變更。
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url=base_url)