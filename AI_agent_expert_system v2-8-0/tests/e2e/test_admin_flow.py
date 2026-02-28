"""
E2E 測試 - Admin UI 流程

測試情境：
1. Admin 頁面載入
2. 系統設定 tab 功能
3. 模型選擇器
4. 分析模式設定
5. 文件管理 tab
"""

import pytest
from playwright.sync_api import expect


class TestAdminPageLoad:
    """Admin 頁面基礎載入測試"""

    def test_admin_page_loads(self, page, frontend_url):
        """Admin 頁面應該能正常載入"""
        page.goto(f"{frontend_url}/📁_Admin")
        page.wait_for_load_state("networkidle", timeout=15000)

        content = page.content()
        assert "Admin" in content or "管理" in content or "📁" in content

    def test_sidebar_visible(self, page, frontend_url):
        """側邊欄應該可見"""
        page.goto(f"{frontend_url}/📁_Admin")
        page.wait_for_load_state("networkidle", timeout=15000)

        sidebar = page.locator('[data-testid="stSidebar"]')
        expect(sidebar).to_be_visible(timeout=10000)


class TestAdminSidebar:
    """Admin 側邊欄功能測試"""

    def test_no_provider_dropdown(self, page, frontend_url):
        """不應有 API 提供者選擇器"""
        page.goto(f"{frontend_url}/📁_Admin")
        page.wait_for_load_state("networkidle", timeout=15000)

        content = page.content()
        assert "API 提供者" not in content
        assert "API提供者" not in content

    def test_analysis_mode_visible(self, page, frontend_url):
        """應有分析模式選擇器 (v2.3.0)"""
        page.goto(f"{frontend_url}/📁_Admin")
        page.wait_for_load_state("networkidle", timeout=15000)

        content = page.content()
        # 檢查分析模式相關文字
        has_analysis = any(
            text in content
            for text in ["分析模式", "純文字", "含圖", "analysis_mode"]
        )
        assert has_analysis, "頁面上應存在分析模式選擇器"

    def test_version_footer(self, page, frontend_url):
        """頁面應顯示正確版本號"""
        page.goto(f"{frontend_url}/📁_Admin")
        page.wait_for_load_state("networkidle", timeout=15000)

        content = page.content()
        assert "v2.3.0" in content or "2.3.0" in content


class TestAdminTabs:
    """Admin 頁籤功能測試"""

    def test_system_config_tab_exists(self, page, frontend_url):
        """應有系統設定頁籤"""
        page.goto(f"{frontend_url}/📁_Admin")
        page.wait_for_load_state("networkidle", timeout=15000)

        content = page.content()
        assert "系統設定" in content or "設定" in content

    def test_documents_tab_exists(self, page, frontend_url):
        """應有文件管理頁籤"""
        page.goto(f"{frontend_url}/📁_Admin")
        page.wait_for_load_state("networkidle", timeout=15000)

        content = page.content()
        assert "文件" in content or "知識庫" in content
