"""
API Client - 封裝所有後端 HTTP 請求 (v2.2.0)

前端透過此模組與 FastAPI 後端通訊
支援 BYOK (Bring Your Own Key) 身份識別機制

變更紀錄:
- v2.2.0: 新增 BYOK header 支援、Auth 驗證、Chat History CRUD
"""

import logging
import os
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60.0


class APIClient:
    """
    FastAPI 後端 API 客戶端

    支援 BYOK 身份識別：
    - 透過 X-API-Key 和 X-User-Name 標頭傳送身份資訊
    - 後端 IdentityMiddleware 會根據這些標頭產生 user_id
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1"

        # 系統級 API Key（舊有，用於 API Auth 中介層）
        self._system_api_key = os.getenv("SYSTEM_API_KEY", "")

        # BYOK 身份資訊（由使用者在前端設定）
        self._user_api_key: Optional[str] = None
        self._user_name: Optional[str] = None
        self._provider: Optional[str] = None  # "openai" | "gemini"

    # ========== BYOK 身份管理 ==========

    def set_user_identity(self, api_key: str, username: str = ""):
        """
        設定 BYOK 使用者身份

        Args:
            api_key: 使用者的 API Key（企業 API Proxy 統一端點）
            username: 可選的使用者名稱 (用於增加身份唯一性)
        """
        self._user_api_key = api_key
        self._user_name = username
        self._provider = "openai"  # 企業 API Proxy 使用 OpenAI 相容格式
        logger.info(f"[APIClient] BYOK 身份已設定: username={username or '(無)'}")

    def clear_user_identity(self):
        """清除 BYOK 身份資訊"""
        self._user_api_key = None
        self._user_name = None
        self._provider = None
        logger.info("[APIClient] BYOK 身份已清除")

    @property
    def is_authenticated(self) -> bool:
        """是否已設定 BYOK 身份"""
        return self._user_api_key is not None

    def _build_headers(self) -> dict:
        """
        建構請求標頭

        包含：
        - X-API-Key: BYOK 使用者 API Key (供 IdentityMiddleware 計算 user_id)
        - X-User-Name: 可選使用者名稱
        - X-API-Key (系統級): 若有設定 SYSTEM_API_KEY 則附加
        """
        headers = {}

        # BYOK 身份標頭
        if self._user_api_key:
            headers["X-API-Key"] = self._user_api_key
        if self._user_name:
            headers["X-User-Name"] = self._user_name

        # 系統級 API Key (兼容舊有 APIKeyMiddleware)
        if self._system_api_key and "X-API-Key" not in headers:
            headers["X-API-Key"] = self._system_api_key

        return headers

    # ========== 通用請求方法 ==========

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """通用 HTTP 請求方法，自動附加 BYOK 標頭"""
        try:
            url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.api_url}/{path}"
            
            # 合併 BYOK 標頭
            headers = kwargs.get("headers", {})
            headers.update(self._build_headers())
            kwargs["headers"] = headers
            
            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                resp = client.request(method, url, **kwargs)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"API 請求失敗 [{method} {path}]: {e}")
            return {"status": "error", "message": str(e)}

    # ========== Health ==========

    def health_check(self) -> dict:
        """健康檢查"""
        try:
            headers = self._build_headers()
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.base_url}/health", headers=headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"健康檢查失敗: {e}")
            return {"status": "unhealthy", "error": str(e)}

    # ========== Chat ==========

    def chat(
        self,
        query: str,
        query_type: str = "general",
        chat_model: str = "gpt-4o-mini",
        search_limit: int = 5,
        selected_types: List[str] = None,
        filters: Dict[str, Any] = None,
        enable_fuzzy: bool = True,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> dict:
        """
        問答查詢

        Args:
            query: 使用者問題
            query_type: 查詢類型
            chat_model: 問答模型
            search_limit: 搜尋結果數
            selected_types: 限定文件類型
            filters: 額外過濾條件
            enable_fuzzy: 啟用模糊搜尋
            api_key: API Key
            base_url: API Base URL

        Returns:
            dict: 包含 response, search_results, usage 等
        """
        try:
            payload = {
                "query": query,
                "query_type": query_type,
                "chat_model": chat_model,
                "search_limit": search_limit,
                "selected_types": selected_types or [],
                "filters": filters or {},
                "enable_fuzzy": enable_fuzzy,
            }
            if api_key:
                payload["api_key"] = api_key
            if base_url:
                payload["base_url"] = base_url

            # 附加 BYOK 標頭（供 IdentityMiddleware 識別使用者）
            headers = self._build_headers()

            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                resp = client.post(f"{self.api_url}/chat/query", json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Chat API 錯誤: {e.response.status_code} - {e.response.text}")
            return {"success": False, "response": f"API 錯誤: {e.response.status_code}", "usage": {}}
        except Exception as e:
            logger.error(f"Chat 請求失敗: {e}")
            return {"success": False, "response": f"請求失敗: {str(e)}", "usage": {}}

    # ========== Ingestion ==========

    def upload_file(self, file_content: bytes, filename: str, doc_type: str = "Knowledge") -> dict:
        """
        上傳檔案

        Args:
            file_content: 檔案二進制內容
            filename: 檔案名稱
            doc_type: 文件類型

        Returns:
            dict: 上傳結果
        """
        try:
            files = {"file": (filename, file_content)}
            data = {"doc_type": doc_type}

            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                resp = client.post(f"{self.api_url}/ingestion/upload", files=files, data=data, headers=self._build_headers())
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"上傳失敗: {e}")
            return {"success": False, "message": str(e)}

    def upload_multiple_files(self, files_data: List[tuple], doc_type: str = "Knowledge") -> dict:
        """批次上傳"""
        try:
            files = [("files", (name, content)) for name, content in files_data]
            data = {"doc_type": doc_type}

            with httpx.Client(timeout=DEFAULT_TIMEOUT * 2) as client:
                resp = client.post(f"{self.api_url}/ingestion/upload_multiple", files=files, data=data, headers=self._build_headers())
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"批次上傳失敗: {e}")
            return {"success": False, "message": str(e)}

    def get_processing_status(self, filename: str) -> dict:
        """查詢檔案處理狀態"""
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.api_url}/ingestion/status/{filename}", headers=self._build_headers())
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"查詢狀態失敗: {e}")
            return {"status": "error", "message": str(e)}

    def upload_and_process(
        self,
        file_content: bytes,
        filename: str,
        doc_type: str = "Knowledge",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        analysis_mode: str = "auto",
    ) -> dict:
        """
        上傳檔案並立即處理（使用使用者的 API Key）
        不經過 Watcher，直接入庫

        Args:
            file_content: 檔案二進制內容
            filename: 檔案名稱
            doc_type: 文件類型
            api_key: 使用者 API Key
            base_url: API Base URL
            analysis_mode: 分析模式 (text_only / vision / auto)

        Returns:
            dict: 處理結果 (含 doc_id, chunks 等)
        """
        try:
            files = {"file": (filename, file_content)}
            data = {"doc_type": doc_type, "analysis_mode": analysis_mode}
            if api_key:
                data["api_key"] = api_key
            if base_url:
                data["base_url"] = base_url

            with httpx.Client(timeout=DEFAULT_TIMEOUT * 3) as client:
                resp = client.post(
                    f"{self.api_url}/ingestion/upload_and_process",
                    files=files,
                    data=data,
                    headers=self._build_headers(),
                )
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"上傳處理失敗: {e}")
            return {"success": False, "message": str(e)}

    # ========== Files ==========

    def get_file_url(self, filename: str, source: str = "archived") -> str:
        """取得檔案下載 URL"""
        return f"{self.api_url}/files/download/{filename}?source={source}"

    def list_files(self, source: str = "archived") -> dict:
        """列出檔案"""
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.api_url}/files/list", params={"source": source}, headers=self._build_headers())
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"列出檔案失敗: {e}")
            return {"success": False, "data": {"files": []}}

    # ========== Admin ==========

    def get_config(self) -> dict:
        """取得系統配置"""
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.api_url}/admin/config", headers=self._build_headers())
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"取得配置失敗: {e}")
            return {"success": False, "data": {}}

    def update_config(self, config_data: dict = None, **kwargs) -> dict:
        """更新系統配置 (接受 dict 或 keyword arguments)"""
        try:
            payload = config_data if config_data is not None else kwargs
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(f"{self.api_url}/admin/config", json=payload, headers=self._build_headers())
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"更新配置失敗: {e}")
            return {"success": False, "message": str(e)}

    def get_stats(self) -> dict:
        """取得統計資訊"""
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.api_url}/admin/stats", headers=self._build_headers())
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"取得統計失敗: {e}")
            return {"success": False, "data": {"documents": {}, "tokens": {}}}

    def list_documents(self, doc_type: Optional[str] = None) -> dict:
        """列出所有文件"""
        try:
            params = {}
            if doc_type:
                params["doc_type"] = doc_type

            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.api_url}/admin/documents", params=params, headers=self._build_headers())
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"列出文件失敗: {e}")
            return {"success": False, "data": {"documents": []}}

    def delete_document(self, doc_id: int) -> dict:
        """刪除文件"""
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.delete(f"{self.api_url}/admin/documents/{doc_id}", headers=self._build_headers())
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"刪除文件失敗: {e}")
            return {"success": False, "message": str(e)}

    def get_token_stats(self, days: int = 30) -> dict:
        """
        取得 Token 統計（增強版 v2.2.0）

        回傳格式: {summary, daily, by_model, by_operation, by_user, by_hour, top_files}
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{self.api_url}/admin/token_stats",
                    params={"days": days},
                    headers=self._build_headers(),
                )
                resp.raise_for_status()
                result = resp.json()
                # 後端包在 ResponseBase.data 裡
                return result.get("data", result)

        except Exception as e:
            logger.error(f"取得 Token 統計失敗: {e}")
            return {}

    # ========== GDPR 合規 (v2.2.0 新增) ==========

    def export_user_data(self) -> dict:
        """
        匯出當前使用者的所有資料（GDPR 合規）

        Returns:
            dict: 包含 sessions、messages、stats 等個人資料
        """
        return self._request("GET", f"{self.api_url}/user/export")

    def delete_user_data(self, confirm: bool = False) -> dict:
        """
        刪除當前使用者的所有資料（GDPR 合規）

        Args:
            confirm: 必須為 True 才會執行刪除

        Returns:
            dict: 刪除結果
        """
        return self._request(
            "DELETE",
            f"{self.api_url}/user/data",
            params={"confirm": str(confirm).lower()},
        )

    def get_user_stats(self) -> dict:
        """
        取得當前使用者的個人統計

        Returns:
            dict: 包含 session 數、message 數、模型使用分佈等
        """
        return self._request("GET", f"{self.api_url}/user/stats")

    # ========== Search ==========

    def semantic_search(self, query: str, top_k: int = 5, doc_type: Optional[str] = None,
                        api_key: Optional[str] = None, base_url: Optional[str] = None) -> dict:
        """語意搜尋"""
        try:
            payload = {"query": query, "top_k": top_k}
            if doc_type:
                payload["doc_type"] = doc_type
            if api_key:
                payload["api_key"] = api_key
            if base_url:
                payload["base_url"] = base_url

            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                resp = client.post(f"{self.api_url}/search/semantic", json=payload, headers=self._build_headers())
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"語意搜尋失敗: {e}")
            return {"success": False, "results": []}

    def keyword_search(self, query: str, top_k: int = 5, doc_type: Optional[str] = None) -> dict:
        """關鍵字搜尋"""
        try:
            payload = {"query": query, "top_k": top_k}
            if doc_type:
                payload["doc_type"] = doc_type

            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                resp = client.post(f"{self.api_url}/search/keyword", json=payload, headers=self._build_headers())
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"關鍵字搜尋失敗: {e}")
            return {"success": False, "results": []}

    # ========== Auth 驗證 (v2.2.0 新增) ==========

    def verify_api_key(
        self,
        api_key: str,
        username: str = "",
        base_url: Optional[str] = None,
    ) -> dict:
        """
        驗證使用者的 API Key 是否有效（企業 API Proxy 統一端點）

        Args:
            api_key: API Key
            username: 可選的使用者名稱
            base_url: 企業 API Proxy 端點 URL

        Returns:
            dict: {"status": "valid"/"invalid", "user_hash": "...", "available_models": [...]}
        """
        try:
            payload = {
                "key": api_key,
                "username": username,
                "provider": "openai",  # 企業 API Proxy 統一使用 OpenAI 相容格式
            }
            if base_url:
                payload["base_url"] = base_url

            with httpx.Client(timeout=15.0) as client:
                resp = client.post(f"{self.api_url}/auth/verify", json=payload, headers=self._build_headers())
                resp.raise_for_status()
                return resp.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"API Key 驗證失敗: {e.response.status_code}")
            try:
                return e.response.json()
            except Exception:
                return {"status": "invalid", "message": f"驗證失敗: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"API Key 驗證請求失敗: {e}")
            return {"status": "error", "message": f"連線失敗: {str(e)}"}

    # ========== Chat History (v2.2.0 新增) ==========

    def get_sessions(self) -> dict:
        """取得當前用戶的所有對話 Session"""
        return self._request("GET", f"{self.api_url}/history/sessions")

    def create_session(self, title: str = "新對話", model_used: Optional[str] = None) -> dict:
        """建立新的對話 Session"""
        payload = {"title": title}
        if model_used:
            payload["model_used"] = model_used
        return self._request("POST", f"{self.api_url}/history/sessions", json=payload)

    def get_session_history(self, session_id: str) -> dict:
        """取得指定 Session 的對話歷史"""
        return self._request("GET", f"{self.api_url}/history/sessions/{session_id}")

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        model_used: Optional[str] = None,
        tokens_used: int = 0,
    ) -> dict:
        """
        儲存一筆對話訊息

        Args:
            session_id: Session ID
            role: "user" | "assistant"
            content: 訊息內容
            model_used: 使用的模型
            tokens_used: Token 用量
        """
        payload = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "model_used": model_used,
            "tokens_used": tokens_used,
        }
        return self._request("POST", f"{self.api_url}/history/messages", json=payload)

    def delete_session(self, session_id: str) -> dict:
        """刪除指定 Session 及其對話記錄"""
        return self._request("DELETE", f"{self.api_url}/history/sessions/{session_id}")

    def update_session_title(self, session_id: str, title: str) -> dict:
        """更新 Session 標題"""
        return self._request(
            "PATCH",
            f"{self.api_url}/history/sessions/{session_id}/title",
            params={"title": title},
        )
