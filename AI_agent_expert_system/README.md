# AI Expert System v2.3.0

歡迎使用 AI 專家系統！本專案已將說明文件全面整理並繁體中文化。請參考以下目錄尋找您需要的資訊。

## 📚 說明文件索引

所有詳細文件皆位於 `docs/` 目錄下：

### 🚀 1. 程式使用說明書 (User Guide)
> 適合：終端使用者、系統管理員

- [快速入門指南](docs/程式使用說明書/快速入門指南.md) - 從零開始安裝與啟動
- [啟動範例](docs/程式使用說明書/啟動範例.md) - 多平台啟動指令參考
- [系統部署指南](docs/程式使用說明書/系統部署指南.md) - 正式環境部署與服務化設定
- [新手上路指南](docs/程式使用說明書/新手上路指南.md) - 第一次使用系統的教學
- [API使用手冊](docs/程式使用說明書/API使用手冊.md) - Backend API 呼叫方式詳解
- [專案首頁](docs/程式使用說明書/專案首頁.md) - 原始 README

### ⚙️ 2. 技術說明書 (Technical Guide)
> 適合：開發人員、架構師

- **架構設計**:
  - [架構總覽](docs/技術說明書/架構總覽.md)
  - [系統架構詳解](docs/技術說明書/系統架構詳解.md)
  - [系統流程圖](docs/技術說明書/系統流程圖.md)
- **核心機制**:
  - [RAG機制說明](docs/技術說明書/RAG機制說明.md)
  - [向量資料庫簡介](docs/技術說明書/向量資料庫簡介.md)
  - [支援檔案格式說明](docs/技術說明書/支援檔案格式說明.md)
- **進階主題**:
  - [網路與認證指南](docs/技術說明書/網路與認證指南.md)
  - [SQLite並發處理指南](docs/技術說明書/SQLite並發處理指南.md)
  - [排程器設定說明](docs/技術說明書/排程器設定說明.md)
  - [安全性政策](docs/技術說明書/安全性政策.md)
- **維護與報告**:
  - [上線觀察清單](docs/技術說明書/上線觀察清單.md)
  - [系統審計報告](docs/技術說明書/系統審計報告.md)
  - [舊版程式碼清理報告](docs/技術說明書/舊版程式碼清理報告.md)

### ❓ 3. 疑難排解 (Troubleshooting)
> 適合：維運人員、開發者

- [常見問題與故障排除](docs/疑難排解/常見問題與故障排除.md)
- [待辦事項](docs/疑難排解/待辦事項.md)

---

## 🛠️ 快速啟動

1. **安裝依賴**:
   ```bash
   pip install -r requirements.txt
   pip install -r backend/requirements.txt
   pip install -r frontend/requirements.txt
   ```

2. **設定環境變數**:
   複製 `.env.example` 為 `.env` 並填入 API Key。

3. **啟動系統** (Windows):
   - 後端: `scripts\start_backend.bat`
   - 前端: `scripts\start_frontend.bat`
