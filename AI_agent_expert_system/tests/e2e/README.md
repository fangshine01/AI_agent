# E2E 測試 - Playwright 設定與使用指南

## 安裝

```bash
pip install playwright pytest-playwright
playwright install chromium
```

## 執行測試

```bash
# 全部 E2E 測試
pytest tests/e2e/ -v

# 僅 Chat 流程
pytest tests/e2e/test_chat_flow.py -v

# 僅 Admin 流程
pytest tests/e2e/test_admin_flow.py -v

# 帶截圖（失敗時自動截圖）
pytest tests/e2e/ -v --screenshot=only-on-failure --output=tests/e2e/results

# 無頭模式（CI/CD）
pytest tests/e2e/ -v --headed=false
```

## 前置條件

1. 後端服務須在 `http://localhost:8000` 執行
2. 前端 Streamlit 須在 `http://localhost:8501` 執行
3. 至少需要一把有效的 API Key

## 測試架構

```
tests/e2e/
├── conftest.py                 # Playwright fixtures
├── test_chat_flow.py           # Chat UI 端到端測試
├── test_admin_flow.py          # Admin UI 端到端測試
└── test_health_api.py          # API 端點健康測試
```
