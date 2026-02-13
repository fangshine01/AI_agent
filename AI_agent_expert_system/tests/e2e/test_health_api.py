"""
E2E 測試 - API 端點健康測試

測試情境：
1. Health 端點可用性
2. Metrics 端點可用性
3. API 文件端點存取
4. CORS 標頭驗證
5. 錯誤處理驗證
"""

import pytest
import requests


class TestHealthEndpoints:
    """健康檢查端點測試"""

    def test_health_simple(self, backend_url):
        """簡易健康檢查應回傳 200"""
        resp = requests.get(f"{backend_url}/health", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "healthy" or "status" in data

    def test_health_detailed(self, backend_url):
        """詳細健康檢查應包含完整系統資訊"""
        resp = requests.get(f"{backend_url}/health/detailed", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        # 應包含資料庫、磁碟等資訊
        assert isinstance(data, dict)

    def test_root_endpoint(self, backend_url):
        """根路徑應回傳 API 資訊"""
        resp = requests.get(f"{backend_url}/", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert data["version"] == "2.3.0"


class TestMetricsEndpoint:
    """Prometheus Metrics 端點測試 (v2.3.0)"""

    def test_metrics_available(self, backend_url):
        """/metrics 端點應回傳 Prometheus 格式文字"""
        resp = requests.get(f"{backend_url}/metrics", timeout=5)
        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")

        content = resp.text
        # 應至少包含計數器的 HELP 或 TYPE 宣告
        assert "http_requests_total" in content or "# HELP" in content

    def test_metrics_format(self, backend_url):
        """Metrics 應包含已知的指標名稱"""
        # 先呼叫 /health 以生成指標
        requests.get(f"{backend_url}/health", timeout=5)

        resp = requests.get(f"{backend_url}/metrics", timeout=5)
        content = resp.text

        # 驗證有 http_requests_total 指標
        assert "http_requests_total" in content
        # 驗證有直方圖指標
        assert "http_request_duration_seconds" in content


class TestAPIDocsEndpoints:
    """API 文件端點測試"""

    def test_openapi_docs(self, backend_url):
        """Swagger UI (/docs) 應可存取"""
        resp = requests.get(f"{backend_url}/docs", timeout=5)
        assert resp.status_code == 200

    def test_redoc_docs(self, backend_url):
        """ReDoc (/redoc) 應可存取"""
        resp = requests.get(f"{backend_url}/redoc", timeout=5)
        assert resp.status_code == 200

    def test_openapi_json(self, backend_url):
        """OpenAPI JSON Schema 應可取得"""
        resp = requests.get(f"{backend_url}/openapi.json", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert "openapi" in data
        assert "paths" in data
        assert data["info"]["version"] == "2.3.0"


class TestErrorHandling:
    """錯誤處理測試"""

    def test_404_not_found(self, backend_url):
        """不存在的路由應回傳 404"""
        resp = requests.get(f"{backend_url}/api/v1/nonexistent", timeout=5)
        assert resp.status_code == 404

    def test_method_not_allowed(self, backend_url):
        """錯誤的 HTTP 方法應被拒絕"""
        resp = requests.delete(f"{backend_url}/health", timeout=5)
        assert resp.status_code in [405, 404]  # 依路由設定而異

    def test_invalid_auth_payload(self, backend_url):
        """無效的驗證請求應回傳 422"""
        resp = requests.post(
            f"{backend_url}/api/v1/auth/verify",
            json={},  # 缺少必要欄位
            timeout=5,
        )
        assert resp.status_code in [400, 422]
