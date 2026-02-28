"""
Chat Client — 問答、Auth 驗證、對話歷史 CRUD

繼承 BaseClient，負責：
- /chat/query — 問答查詢
- /auth/verify — API Key 驗證
- /history/* — Session / Message CRUD
"""

import logging
from typing import Optional, Dict, Any, List

import httpx

from client.base_client import BaseClient, DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)


class ChatClient(BaseClient):
    """Chat 相關 API 操作"""

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

    # ========== Auth 驗證 ==========

    def verify_api_key(
        self,
        api_key: str,
        username: str = "",
        base_url: Optional[str] = None,
    ) -> dict:
        """驗證使用者的 API Key 是否有效"""
        try:
            payload = {
                "key": api_key,
                "username": username,
                "provider": "openai",
            }
            if base_url:
                payload["base_url"] = base_url

            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    f"{self.api_url}/auth/verify",
                    json=payload,
                    headers=self._build_headers(),
                )
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

    # ========== Chat History ==========

    def get_sessions(self) -> dict:
        """取得當前用戶的所有對話 Session"""
        return self._request("GET", "/history/sessions")

    def create_session(self, title: str = "新對話", model_used: Optional[str] = None) -> dict:
        """建立新的對話 Session"""
        payload = {"title": title}
        if model_used:
            payload["model_used"] = model_used
        return self._request("POST", "/history/sessions", json=payload)

    def get_session_history(self, session_id: str) -> dict:
        """取得指定 Session 的對話歷史"""
        return self._request("GET", f"/history/sessions/{session_id}")

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        model_used: Optional[str] = None,
        tokens_used: int = 0,
    ) -> dict:
        """儲存一筆對話訊息"""
        payload = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "model_used": model_used,
            "tokens_used": tokens_used,
        }
        return self._request("POST", "/history/messages", json=payload)

    def delete_session(self, session_id: str) -> dict:
        """刪除指定 Session 及其對話記錄"""
        return self._request("DELETE", f"/history/sessions/{session_id}")

    def update_session_title(self, session_id: str, title: str) -> dict:
        """更新 Session 標題"""
        return self._request(
            "PATCH",
            f"/history/sessions/{session_id}/title",
            params={"title": title},
        )

    # ========== Search ==========

    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        doc_type: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> dict:
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
                resp = client.post(
                    f"{self.api_url}/search/semantic",
                    json=payload,
                    headers=self._build_headers(),
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"語意搜尋失敗: {e}")
            return {"success": False, "results": []}

    def keyword_search(
        self,
        query: str,
        top_k: int = 5,
        doc_type: Optional[str] = None,
    ) -> dict:
        """關鍵字搜尋"""
        try:
            payload = {"query": query, "top_k": top_k}
            if doc_type:
                payload["doc_type"] = doc_type

            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                resp = client.post(
                    f"{self.api_url}/search/keyword",
                    json=payload,
                    headers=self._build_headers(),
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"關鍵字搜尋失敗: {e}")
            return {"success": False, "results": []}
