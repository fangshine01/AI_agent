"""
API Client - 封裝所有後端 HTTP 請求
前端透過此模組與 FastAPI 後端通訊
"""

import logging
import os
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60.0


class APIClient:
    """FastAPI 後端 API 客戶端"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1"
        
        # 讀取 API Key (如果有設定)
        self.api_key = os.getenv("SYSTEM_API_KEY", "")
        self.headers = {}
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key

    # ========== 通用請求方法 ==========

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """通用 HTTP 請求方法，供內部或進階呼叫使用"""
        try:
            url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.api_url}/{path}"
            
            # 合併 API Key header
            headers = kwargs.get("headers", {})
            headers.update(self.headers)
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
            headers = self.headers.copy()
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

            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                resp = client.post(f"{self.api_url}/chat/query", json=payload)
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
                resp = client.post(f"{self.api_url}/ingestion/upload", files=files, data=data)
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
                resp = client.post(f"{self.api_url}/ingestion/upload_multiple", files=files, data=data)
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"批次上傳失敗: {e}")
            return {"success": False, "message": str(e)}

    def get_processing_status(self, filename: str) -> dict:
        """查詢檔案處理狀態"""
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.api_url}/ingestion/status/{filename}")
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

        Returns:
            dict: 處理結果 (含 doc_id, chunks 等)
        """
        try:
            files = {"file": (filename, file_content)}
            data = {"doc_type": doc_type}
            if api_key:
                data["api_key"] = api_key
            if base_url:
                data["base_url"] = base_url

            with httpx.Client(timeout=DEFAULT_TIMEOUT * 3) as client:
                resp = client.post(
                    f"{self.api_url}/ingestion/upload_and_process",
                    files=files,
                    data=data,
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
                resp = client.get(f"{self.api_url}/files/list", params={"source": source})
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
                resp = client.get(f"{self.api_url}/admin/config")
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
                resp = client.post(f"{self.api_url}/admin/config", json=payload)
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"更新配置失敗: {e}")
            return {"success": False, "message": str(e)}

    def get_stats(self) -> dict:
        """取得統計資訊"""
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.api_url}/admin/stats")
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
                resp = client.get(f"{self.api_url}/admin/documents", params=params)
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"列出文件失敗: {e}")
            return {"success": False, "data": {"documents": []}}

    def delete_document(self, doc_id: int) -> dict:
        """刪除文件"""
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.delete(f"{self.api_url}/admin/documents/{doc_id}")
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"刪除文件失敗: {e}")
            return {"success": False, "message": str(e)}

    def get_token_stats(self, days: int = 30) -> dict:
        """取得 Token 統計"""
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.api_url}/admin/token_stats", params={"days": days})
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"取得 Token 統計失敗: {e}")
            return {"success": False, "data": {}}

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
                resp = client.post(f"{self.api_url}/search/semantic", json=payload)
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
                resp = client.post(f"{self.api_url}/search/keyword", json=payload)
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            logger.error(f"關鍵字搜尋失敗: {e}")
            return {"success": False, "results": []}
