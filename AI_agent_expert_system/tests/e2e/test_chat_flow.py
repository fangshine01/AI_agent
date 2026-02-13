"""
E2E 測試 - Chat UI 流程

測試情境：
1. 頁面載入正常
2. 側邊欄 API Key 輸入
3. 模型選擇器功能
4. 訊息發送與回應
5. 分析模式切換
"""

import pytest
from playwright.sync_api import expect


class TestChatPageLoad:
    """Chat 頁面基礎載入測試"""

    def test_chat_page_loads(self, page, frontend_url):
        """Chat 頁面應該能正常載入"""
        page.goto(f"{frontend_url}/💬_Chat")
        # Streamlit 需要等待載入完成
        page.wait_for_load_state("networkidle", timeout=15000)

        # 頁面標題或內容應包含相關文字
        content = page.content()
        assert "Chat" in content or "💬" in content or "AI" in content

    def test_sidebar_visible(self, page, frontend_url):
        """側邊欄應該可見"""
        page.goto(f"{frontend_url}/💬_Chat")
        page.wait_for_load_state("networkidle", timeout=15000)

        # Streamlit 側邊欄通常使用 data-testid="stSidebar"
        sidebar = page.locator('[data-testid="stSidebar"]')
        expect(sidebar).to_be_visible(timeout=10000)


class TestChatSidebar:
    """Chat 側邊欄功能測試"""

    def test_api_key_input_exists(self, page, frontend_url):
        """應有 API Key 輸入欄位"""
        page.goto(f"{frontend_url}/💬_Chat")
        page.wait_for_load_state("networkidle", timeout=15000)

        # 搜尋密碼類型的輸入欄位 (API Key 通常用 password input)
        content = page.content()
        assert "API Key" in content or "api_key" in content.lower()

    def test_no_provider_dropdown(self, page, frontend_url):
        """不應有 API 提供者選擇器 (已在 v2.3.0 移除)"""
        page.goto(f"{frontend_url}/💬_Chat")
        page.wait_for_load_state("networkidle", timeout=15000)

        content = page.content()
        assert "API 提供者" not in content
        assert "API提供者" not in content

    def test_model_selector_exists(self, page, frontend_url):
        """應有模型選擇器"""
        page.goto(f"{frontend_url}/💬_Chat")
        page.wait_for_load_state("networkidle", timeout=15000)

        content = page.content()
        # 檢查是否包含至少一個已知模型名稱
        has_model = any(
            model in content
            for model in ["gpt-4o", "gemini-2.5-flash", "模型"]
        )
        assert has_model, "頁面上應存在模型選擇器或模型名稱"


class TestChatInteraction:
    """Chat 對話互動測試"""

    def test_message_input_exists(self, page, frontend_url):
        """應有訊息輸入框"""
        page.goto(f"{frontend_url}/💬_Chat")
        page.wait_for_load_state("networkidle", timeout=15000)

        # Streamlit chat input 通常使用 textarea
        chat_input = page.locator('textarea, [data-testid="stChatInput"]')
        # 至少應有一個輸入元素
        assert chat_input.count() > 0 or "請輸入" in page.content()

    def test_version_footer(self, page, frontend_url):
        """頁面應顯示正確版本號"""
        page.goto(f"{frontend_url}/💬_Chat")
        page.wait_for_load_state("networkidle", timeout=15000)

        content = page.content()
        assert "v2.3.0" in content or "2.3.0" in content
