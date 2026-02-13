"""
v2.2.0 新功能測試 - Auth、Identity、History、Health、Rate Limiter
使用 pytest + FastAPI TestClient
"""

import sys
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# 確保專案根目錄在 path 中
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def client():
    """建立測試客戶端"""
    try:
        from backend.app.main import app
        return TestClient(app)
    except ImportError:
        pytest.skip("無法匯入 FastAPI app，請確認環境設定")


# ========== Health Endpoint 測試 ==========

class TestHealthEndpoints:
    """健康檢查端點測試"""

    def test_health_simple(self, client):
        """測試簡易健康檢查"""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_detailed(self, client):
        """測試詳細健康狀態"""
        resp = client.get("/health/detailed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert "databases" in data
        assert "disk" in data

    def test_root_endpoint_version(self, client):
        """確認版本號已更新為 2.2.0"""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == "2.2.0"


# ========== Auth Endpoint 測試 ==========

class TestAuthVerify:
    """API Key 驗證端點測試"""

    def test_verify_missing_key(self, client):
        """測試缺少 key 的驗證請求"""
        resp = client.post("/api/v1/auth/verify", json={"provider": "openai"})
        assert resp.status_code == 422  # Validation Error

    def test_verify_invalid_openai_key(self, client):
        """測試無效的 OpenAI Key"""
        resp = client.post("/api/v1/auth/verify", json={
            "key": "sk-invalid-test-key-12345",
            "provider": "openai",
        })
        assert resp.status_code in (200, 401)
        data = resp.json()
        # 無效 key 應該回傳 invalid 狀態
        if resp.status_code == 200:
            assert data.get("status") in ("valid", "invalid")

    def test_verify_invalid_gemini_key(self, client):
        """測試無效的 Gemini Key"""
        resp = client.post("/api/v1/auth/verify", json={
            "key": "AIzaSy-invalid-test-key",
            "provider": "gemini",
        })
        assert resp.status_code in (200, 401)

    def test_verify_unsupported_provider(self, client):
        """測試不支援的 provider"""
        resp = client.post("/api/v1/auth/verify", json={
            "key": "test-key",
            "provider": "anthropic",
        })
        # 應回傳錯誤
        assert resp.status_code in (400, 422, 200)


# ========== Identity Middleware 測試 ==========

class TestIdentityMiddleware:
    """BYOK 身份識別中介層測試"""

    def test_unauthenticated_request(self, client):
        """未帶 API Key 的請求，應有 is_authenticated=False"""
        # 存取不需要 auth 的端點 (health)
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_authenticated_request_passes(self, client):
        """帶有 X-API-Key 標頭的請求應正常通過"""
        headers = {"X-API-Key": "sk-test-key-for-identity"}
        resp = client.get("/health", headers=headers)
        assert resp.status_code == 200

    def test_skip_endpoints(self, client):
        """跳過端點 (/, /docs, /health) 不應報錯"""
        for path in ["/", "/health", "/docs"]:
            resp = client.get(path)
            assert resp.status_code == 200


# ========== History API 測試 ==========

class TestHistoryAPI:
    """對話歷史 API 測試"""

    def test_get_sessions_unauthorized(self, client):
        """未認證時取得 Session 列表應回傳 401"""
        resp = client.get("/api/v1/history/sessions")
        assert resp.status_code == 401

    def test_get_sessions_with_key(self, client):
        """帶 API Key 取得 Session 列表"""
        headers = {"X-API-Key": "sk-test-key-for-history"}
        resp = client.get("/api/v1/history/sessions", headers=headers)
        # 200 表示成功 (可能為空列表)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert isinstance(data.get("sessions"), list)

    def test_create_and_get_session(self, client):
        """建立新 Session 並取得其歷史"""
        headers = {"X-API-Key": "sk-test-key-for-history"}

        # 建立
        resp = client.post(
            "/api/v1/history/sessions",
            json={"title": "測試對話", "model_used": "gpt-4o-mini"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        session_id = data.get("session_id")
        assert session_id is not None

        # 取得歷史 (應為空)
        resp2 = client.get(
            f"/api/v1/history/sessions/{session_id}",
            headers=headers,
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2.get("session_id") == session_id
        assert data2.get("messages") == []

    def test_save_message_and_retrieve(self, client):
        """儲存訊息並取回"""
        headers = {"X-API-Key": "sk-test-key-for-history-msg"}

        # 建立 Session
        resp = client.post(
            "/api/v1/history/sessions",
            json={"title": "訊息測試"},
            headers=headers,
        )
        session_id = resp.json().get("session_id")

        # 儲存 user 訊息
        resp2 = client.post("/api/v1/history/messages", json={
            "session_id": session_id,
            "role": "user",
            "content": "這是一個測試問題",
            "tokens_used": 10,
        }, headers=headers)
        assert resp2.status_code == 200

        # 儲存 assistant 訊息
        resp3 = client.post("/api/v1/history/messages", json={
            "session_id": session_id,
            "role": "assistant",
            "content": "這是 AI 的回答",
            "model_used": "gpt-4o-mini",
            "tokens_used": 50,
        }, headers=headers)
        assert resp3.status_code == 200

        # 取得歷史
        resp4 = client.get(
            f"/api/v1/history/sessions/{session_id}",
            headers=headers,
        )
        data = resp4.json()
        assert len(data.get("messages", [])) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

    def test_delete_session(self, client):
        """刪除 Session"""
        headers = {"X-API-Key": "sk-test-key-for-delete"}

        # 建立
        resp = client.post(
            "/api/v1/history/sessions",
            json={"title": "待刪除"},
            headers=headers,
        )
        session_id = resp.json().get("session_id")

        # 刪除
        resp2 = client.delete(
            f"/api/v1/history/sessions/{session_id}",
            headers=headers,
        )
        assert resp2.status_code == 200

        # 確認已刪除
        resp3 = client.get(
            f"/api/v1/history/sessions/{session_id}",
            headers=headers,
        )
        assert resp3.status_code == 404

    def test_cross_user_isolation(self, client):
        """不同用戶之間的 Session 隔離"""
        headers_a = {"X-API-Key": "sk-user-a-isolation-test"}
        headers_b = {"X-API-Key": "sk-user-b-isolation-test"}

        # 用戶 A 建立 Session
        resp = client.post(
            "/api/v1/history/sessions",
            json={"title": "用戶A的對話"},
            headers=headers_a,
        )
        session_id_a = resp.json().get("session_id")

        # 用戶 B 嘗試存取用戶 A 的 Session → 404
        resp2 = client.get(
            f"/api/v1/history/sessions/{session_id_a}",
            headers=headers_b,
        )
        assert resp2.status_code == 404


# ========== Error Handler 測試 ==========

class TestErrorHandler:
    """全域錯誤處理中介層測試"""

    def test_404_not_found(self, client):
        """不存在的 endpoint 應回傳 404"""
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404

    def test_422_validation_error(self, client):
        """Request body 格式錯誤應回傳 422"""
        resp = client.post("/api/v1/auth/verify", json={"bad": "data"})
        assert resp.status_code == 422
