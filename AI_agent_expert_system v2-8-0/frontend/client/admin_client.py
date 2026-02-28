"""
Admin Client — 管理後台 API 操作

繼承 BaseClient，負責：
- /admin/config — 系統配置
- /admin/stats — 統計
- /admin/documents — 文件管理
- /admin/token_stats — Token 統計
- /ingestion/* — 檔案上傳與處理
- /files/* — 檔案列表 / 下載
- /user/* — GDPR 合規
"""

import logging
from typing import Optional, Dict, Any, List

import httpx

from client.base_client import BaseClient, DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)


class AdminClient(BaseClient):
    """Admin 相關 API 操作"""

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
        """取得 Token 統計"""
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{self.api_url}/admin/token_stats",
                    params={"days": days},
                    headers=self._build_headers(),
                )
                resp.raise_for_status()
                result = resp.json()
                return result.get("data", result)
        except Exception as e:
            logger.error(f"取得 Token 統計失敗: {e}")
            return {}

    # ========== Ingestion ==========

    def upload_file(self, file_content: bytes, filename: str, doc_type: str = "Knowledge") -> dict:
        """上傳檔案"""
        try:
            files = {"file": (filename, file_content)}
            data = {"doc_type": doc_type}
            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                resp = client.post(
                    f"{self.api_url}/ingestion/upload",
                    files=files, data=data,
                    headers=self._build_headers(),
                )
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
                resp = client.post(
                    f"{self.api_url}/ingestion/upload_multiple",
                    files=files, data=data,
                    headers=self._build_headers(),
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"批次上傳失敗: {e}")
            return {"success": False, "message": str(e)}

    def get_processing_status(self, filename: str) -> dict:
        """查詢檔案處理狀態"""
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{self.api_url}/ingestion/status/{filename}",
                    headers=self._build_headers(),
                )
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
        """上傳檔案並立即處理（使用使用者的 API Key）"""
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
                    files=files, data=data,
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
                resp = client.get(
                    f"{self.api_url}/files/list",
                    params={"source": source},
                    headers=self._build_headers(),
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"列出檔案失敗: {e}")
            return {"success": False, "data": {"files": []}}

    # ========== GDPR 合規 ==========

    def export_user_data(self) -> dict:
        """匯出當前使用者的所有資料（GDPR 合規）"""
        return self._request("GET", "/user/export")

    def delete_user_data(self, confirm: bool = False) -> dict:
        """刪除當前使用者的所有資料（GDPR 合規）"""
        return self._request(
            "DELETE",
            "/user/data",
            params={"confirm": str(confirm).lower()},
        )

    def get_user_stats(self) -> dict:
        """取得當前使用者的個人統計"""
        return self._request("GET", "/user/stats")
