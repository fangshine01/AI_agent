"""
E2E 測試共用 Fixtures (Playwright)

提供：
- 瀏覽器實例管理
- API 基礎 URL 配置
- 截圖工具
"""

import pytest
from playwright.sync_api import sync_playwright

# 預設測試伺服器 URL
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:8501"


@pytest.fixture(scope="session")
def browser():
    """Session 級瀏覽器實例（跨測試共用，加速執行）"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """每個測試獨立的頁面實例"""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="zh-TW",
    )
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def backend_url():
    """後端 API URL"""
    return BACKEND_URL


@pytest.fixture
def frontend_url():
    """前端 Streamlit URL"""
    return FRONTEND_URL
