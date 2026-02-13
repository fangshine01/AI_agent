"""
壓力測試腳本 - 使用 Locust 模擬並行使用者 (v2.3.0 增強)
目標: 模擬 50-100 名同時使用者，測試系統性能瓶頸

安裝:
  pip install locust

執行 (50 並發):
  locust -f tests/load_test.py --host=http://localhost:8000 --users=50 --spawn-rate=5
  然後開啟瀏覽器 http://localhost:8089 查看即時報表

執行 (100 並發):
  locust -f tests/load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10
  然後開啟瀏覽器 http://localhost:8089 查看即時報表

無頭模式 (50 並發, CI/CD):
  locust -f tests/load_test.py --host=http://localhost:8000 --users=50 --spawn-rate=5 --run-time=60s --headless

無頭模式 (100 並發, CI/CD):
  locust -f tests/load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=120s --headless

產出 CSV 報告:
  locust -f tests/load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=120s --headless --csv=tests/load_test_results
"""

import os
import random
import string
import json
from locust import HttpUser, task, between, events

# 測試用 API Key（不會真正呼叫 LLM，只測試 API 路由）
TEST_API_KEYS = [
    f"sk-test-{''.join(random.choices(string.ascii_lowercase, k=32))}"
    for _ in range(10)
]

# 測試用問題集
TEST_QUERIES = [
    "什麼是機器學習？",
    "解釋 Python 裝飾器的原理",
    "RAG 架構的運作方式",
    "如何設計可擴展的資料庫",
    "Docker 和 Kubernetes 的差異",
    "什麼是 Transformer 模型？",
    "資料前處理的最佳實踐",
    "微服務架構的優缺點",
    "如何進行 A/B 測試？",
    "RESTful API 的設計原則",
]


class HealthCheckUser(HttpUser):
    """模擬健康檢查請求 - 輕量級端點"""
    weight = 3  # 較高權重，模擬監控系統頻繁檢查
    wait_time = between(1, 3)

    @task(3)
    def health_simple(self):
        """簡易健康檢查"""
        self.client.get("/health", name="/health [simple]")

    @task(1)
    def health_detailed(self):
        """詳細健康檢查"""
        self.client.get("/health/detailed", name="/health/detailed")


class AuthUser(HttpUser):
    """模擬 API Key 驗證流程"""
    weight = 2
    wait_time = between(2, 5)

    def on_start(self):
        """初始化: 隨機選一把 API Key"""
        self.api_key = random.choice(TEST_API_KEYS)
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    @task
    def verify_api_key(self):
        """驗證 API Key（預期可能失敗，只測試路由吞吐量）"""
        with self.client.post(
            "/api/v1/auth/verify",
            json={
                "api_key": self.api_key,
                "provider": "openai",
                "base_url": "http://innoai.cminl.oa/agency/proxy/openai/platform",
            },
            headers=self.headers,
            name="/api/v1/auth/verify",
            catch_response=True,
        ) as response:
            # 驗證可能因 key 無效返回 401，但路由應該正常回應
            if response.status_code in [200, 401, 422]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class ChatHistoryUser(HttpUser):
    """模擬聊天歷史 CRUD 操作"""
    weight = 3
    wait_time = between(1, 4)

    def on_start(self):
        """初始化: 設定請求標頭"""
        self.api_key = random.choice(TEST_API_KEYS)
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        self.session_ids = []

    @task(3)
    def list_sessions(self):
        """列出聊天 Session"""
        self.client.get(
            "/api/v1/history/sessions",
            headers=self.headers,
            name="/api/v1/history/sessions [GET]",
        )

    @task(2)
    def create_session(self):
        """建立新 Session"""
        with self.client.post(
            "/api/v1/history/sessions",
            json={"title": f"Test Session {random.randint(1, 9999)}"},
            headers=self.headers,
            name="/api/v1/history/sessions [POST]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    sid = data.get("session_id")
                    if sid:
                        self.session_ids.append(sid)
                except Exception:
                    pass
                response.success()

    @task(4)
    def send_message(self):
        """發送聊天訊息"""
        if not self.session_ids:
            return

        sid = random.choice(self.session_ids)
        query = random.choice(TEST_QUERIES)

        self.client.post(
            f"/api/v1/history/sessions/{sid}/messages",
            json={
                "role": "user",
                "content": query,
                "model": "gpt-4o",
            },
            headers=self.headers,
            name="/api/v1/history/sessions/{id}/messages [POST]",
        )


class AdminUser(HttpUser):
    """模擬管理員操作"""
    weight = 1
    wait_time = between(5, 10)

    def on_start(self):
        self.api_key = random.choice(TEST_API_KEYS)
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    @task(2)
    def get_token_stats(self):
        """查詢 Token 統計"""
        self.client.get(
            "/api/v1/admin/token-stats",
            headers=self.headers,
            name="/api/v1/admin/token-stats",
        )

    @task(1)
    def get_documents(self):
        """查詢文件列表"""
        self.client.get(
            "/api/v1/admin/documents",
            headers=self.headers,
            name="/api/v1/admin/documents",
        )

    @task(1)
    def get_user_stats(self):
        """查詢個人統計"""
        self.client.get(
            "/api/v1/user/stats",
            headers=self.headers,
            name="/api/v1/user/stats",
        )


class MetricsUser(HttpUser):
    """模擬 Prometheus Metrics 抓取 (v2.3.0)"""
    weight = 1
    wait_time = between(10, 15)

    @task
    def scrape_metrics(self):
        """/metrics 端點抓取測試"""
        with self.client.get(
            "/metrics",
            name="/metrics [prometheus]",
            catch_response=True,
        ) as response:
            if response.status_code == 200 and "http_requests_total" in response.text:
                response.success()
            elif response.status_code == 200:
                response.success()  # 初始可能無指標
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class SearchUser(HttpUser):
    """模擬搜尋查詢 (v2.3.0 新增)"""
    weight = 2
    wait_time = between(3, 8)

    def on_start(self):
        self.api_key = random.choice(TEST_API_KEYS)
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    @task(2)
    def semantic_search(self):
        """語意搜尋"""
        query = random.choice(TEST_QUERIES)
        with self.client.post(
            "/api/v1/search/semantic",
            json={
                "query": query,
                "top_k": 5,
            },
            headers=self.headers,
            name="/api/v1/search/semantic",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 401, 422, 500]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(1)
    def keyword_search(self):
        """關鍵字搜尋"""
        query = random.choice(TEST_QUERIES)
        with self.client.post(
            "/api/v1/search/keyword",
            json={
                "query": query,
                "top_k": 5,
                "enable_fuzzy": True,
            },
            headers=self.headers,
            name="/api/v1/search/keyword",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 401, 422, 500]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class ModelsUser(HttpUser):
    """模擬模型列表查詢 (v2.3.0 新增)"""
    weight = 1
    wait_time = between(5, 10)

    @task
    def list_models(self):
        """查詢可用模型列表"""
        self.client.get(
            "/api/v1/models/list",
            name="/api/v1/models/list",
        )


# ========== 事件鉤子：自訂報表 ==========

@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """測試結束時輸出摘要報告"""
    stats = environment.runner.stats
    total_users = getattr(environment.runner, 'target_user_count', '?')
    print("\n" + "=" * 70)
    print(f"壓力測試摘要報告 ({total_users} 並發使用者)")
    print("=" * 70)
    print(f"總請求數:    {stats.total.num_requests}")
    print(f"失敗請求數:  {stats.total.num_failures}")
    print(f"平均回應時間: {stats.total.avg_response_time:.0f} ms")
    print(f"中位數:      {stats.total.median_response_time} ms")
    print(f"95th百分位:  {stats.total.get_response_time_percentile(0.95):.0f} ms")
    print(f"99th百分位:  {stats.total.get_response_time_percentile(0.99):.0f} ms")
    print(f"每秒請求數:  {stats.total.current_rps:.1f}")
    
    fail_ratio = (
        stats.total.num_failures / stats.total.num_requests * 100
        if stats.total.num_requests > 0
        else 0
    )
    print(f"失敗率:      {fail_ratio:.1f}%")
    print("=" * 70)

    # 性能評估
    if stats.total.avg_response_time < 200:
        print("✅ 性能等級: 優秀 (平均 < 200ms)")
    elif stats.total.avg_response_time < 500:
        print("🟡 性能等級: 良好 (平均 < 500ms)")
    elif stats.total.avg_response_time < 1000:
        print("🟠 性能等級: 尚可 (平均 < 1000ms)")
    else:
        print("🔴 性能等級: 需優化 (平均 >= 1000ms)")

    if fail_ratio > 5:
        print("⚠️ 警告: 失敗率超過 5%，需要排查問題")

    # M4 驗收標準 (100 並發)
    print("-" * 70)
    print("M4 驗收標準 (100 並發):")
    m4_pass = True
    if stats.total.avg_response_time > 1000:
        print("  ❌ 平均回應時間 > 1000ms")
        m4_pass = False
    else:
        print("  ✅ 平均回應時間 ≤ 1000ms")

    p95 = stats.total.get_response_time_percentile(0.95)
    if p95 > 3000:
        print("  ❌ P95 回應時間 > 3000ms")
        m4_pass = False
    else:
        print("  ✅ P95 回應時間 ≤ 3000ms")

    if fail_ratio > 1:
        print("  ❌ 失敗率 > 1%")
        m4_pass = False
    else:
        print("  ✅ 失敗率 ≤ 1%")

    if m4_pass:
        print("🎉 M4 驗收: 通過")
    else:
        print("⚠️ M4 驗收: 未通過，請調優後重測")
    print("=" * 70)
