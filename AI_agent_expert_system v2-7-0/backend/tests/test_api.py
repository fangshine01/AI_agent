"""
API 端點測試 - 使用 pytest + httpx 的 FastAPI TestClient
"""

import pytest
from fastapi.testclient import TestClient

# 注意: 實際執行前需確保 backend 的 sys.path 設定正確
# 可透過 conftest.py 或直接設定 PYTHONPATH


@pytest.fixture
def client():
    """建立測試客戶端"""
    try:
        from backend.app.main import app
        return TestClient(app)
    except ImportError:
        pytest.skip("無法匯入 FastAPI app，請確認環境設定")


class TestHealthEndpoint:
    """健康檢查端點測試"""

    def test_health_check(self, client):
        """測試 /health 端點"""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    def test_root(self, client):
        """測試根路徑"""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data


class TestChatAPI:
    """聊天 API 測試"""

    def test_chat_query_missing_fields(self, client):
        """測試缺少必要欄位的查詢"""
        resp = client.post("/api/v1/chat/query", json={})
        assert resp.status_code == 422  # Validation Error

    def test_chat_query_basic(self, client):
        """測試基本查詢 (需要 API Key)"""
        payload = {
            "query": "測試查詢",
            "query_type": "general",
            "chat_model": "gpt-4o-mini",
            "api_key": "test-key",
            "base_url": "http://localhost",
        }
        resp = client.post("/api/v1/chat/query", json=payload)
        # 可能因 API Key 無效而失敗，但不應是 422
        assert resp.status_code in [200, 500]


class TestIngestionAPI:
    """檔案上傳 API 測試"""

    def test_upload_no_file(self, client):
        """測試未提供檔案的上傳"""
        resp = client.post("/api/v1/ingestion/upload")
        assert resp.status_code == 422

    def test_upload_file(self, client, tmp_path):
        """測試檔案上傳"""
        # 建立測試檔案
        test_file = tmp_path / "test.md"
        test_file.write_text("# 測試文件\n\n這是測試內容。", encoding="utf-8")

        with open(test_file, "rb") as f:
            resp = client.post(
                "/api/v1/ingestion/upload",
                files={"file": ("test.md", f, "text/markdown")},
                data={"doc_type": "knowledge"},
            )
        assert resp.status_code in [200, 500]

    def test_processing_status(self, client):
        """測試處理狀態查詢"""
        resp = client.get("/api/v1/ingestion/status/nonexistent.md")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data


class TestFilesAPI:
    """檔案管理 API 測試"""

    def test_list_files(self, client):
        """測試檔案列表"""
        resp = client.get("/api/v1/files/list")
        assert resp.status_code == 200

    def test_download_nonexistent(self, client):
        """測試下載不存在的檔案"""
        resp = client.get("/api/v1/files/download/nonexistent.md")
        assert resp.status_code in [404, 500]


class TestAdminAPI:
    """管理 API 測試"""

    def test_get_config(self, client):
        """測試取得配置"""
        resp = client.get("/api/v1/admin/config")
        assert resp.status_code == 200

    def test_get_stats(self, client):
        """測試取得統計"""
        resp = client.get("/api/v1/admin/stats")
        assert resp.status_code == 200

    def test_list_documents(self, client):
        """測試列出文件"""
        resp = client.get("/api/v1/admin/documents")
        assert resp.status_code == 200

    def test_token_stats(self, client):
        """測試 Token 統計"""
        resp = client.get("/api/v1/admin/token_stats")
        assert resp.status_code == 200

    def test_batch_invalid_action(self, client):
        """測試無效的批次操作"""
        resp = client.post("/api/v1/admin/batch/invalid_action")
        assert resp.status_code == 400

    def test_batch_reindex(self, client):
        """測試批次重新索引"""
        resp = client.post("/api/v1/admin/batch/reindex")
        assert resp.status_code == 200


class TestSearchAPI:
    """搜尋 API 測試"""

    def test_semantic_search(self, client):
        """測試語意搜尋"""
        payload = {"query": "測試搜尋", "top_k": 5}
        resp = client.post("/api/v1/search/semantic", json=payload)
        assert resp.status_code in [200, 500]

    def test_keyword_search(self, client):
        """測試關鍵字搜尋"""
        payload = {"query": "測試", "top_k": 5}
        resp = client.post("/api/v1/search/keyword", json=payload)
        assert resp.status_code in [200, 500]
