# AI Expert System - 故障排除指南

> **最後更新**: 2026-02-12

---

## 🔧 常見問題與解決方案

### 1. WebSocket 連接錯誤

#### 錯誤訊息
```
tornado.websocket.WebSocketClosedError
StreamClosedError: Stream is closed
```

#### 原因分析
這是 **正常的行為**，不會影響系統功能。當以下情況發生時會出現：

| 情況 | 說明 | 嚴重性 |
|------|------|--------|
| **用戶關閉頁面** | 瀏覽器頁面被關閉或刷新 | ✅ 正常 |
| **網路不穩定** | 網路連接短暫中斷 | ⚠️ 檢查網路 |
| **連接超時** | 長時間無操作導致 WebSocket 超時 | ✅ 正常 |
| **並發連接過多** | 多人同時使用時的競爭狀態 | ⚠️ 需優化 |

#### 解決方案

**方案 1: 更新配置檔** (已自動完成)
```toml
# .streamlit/config.toml
[server]
maxMessageSize = 200
enableWebsocketCompression = true
websocketPingInterval = 20
websocketPingTimeout = 20
```

**方案 2: 使用更穩定的網路連接**
- 優先使用有線網路而非 WiFi
- 確保路由器與電腦之間訊號良好
- 避免在網路尖峰時段使用

**方案 3: 調整瀏覽器設定**
- 清除瀏覽器快取
- 禁用瀏覽器擴充套件（如廣告阻擋器）
- 使用無痕模式測試

**方案 4: 檢查防火牆/防毒軟體**
- 確認防火牆未阻擋 WebSocket 連接
- 暫時停用防毒軟體測試

#### 何時需要擔心？

❌ **不需要擔心的情況**：
- 偶爾出現（1-2 次/小時）
- 頁面刷新或關閉時出現
- 不影響正常使用

⚠️ **需要檢查的情況**：
- 頻繁出現（每分鐘多次）
- 導致頁面無法載入
- Chat/Admin 功能無法使用
- 上傳檔案時頻繁斷線

---

### 2. 模組導入錯誤

#### 錯誤訊息
```
ModuleNotFoundError: No module named 'frontend'
ModuleNotFoundError: No module named 'backend'
```

#### 解決方案
✅ **已修復**: 使用 `start_v2.bat` 啟動即可，腳本會自動設定 `PYTHONPATH`

如果手動啟動，請執行：
```batch
set PYTHONPATH=%cd%\AI_agent_expert_system
streamlit run frontend/Home.py
```

---

### 3. 防火牆連接問題

#### 症狀
- 本機可以連接 (http://localhost:8501)
- 局域網無法連接 (http://192.168.x.x:8501)

#### 解決方案
```batch
# 執行防火牆設定腳本（以系統管理員身分）
setup_firewall.bat
```

或手動設定：
```powershell
netsh advfirewall firewall add rule name="AI-Expert-Streamlit-LAN" dir=in action=allow protocol=TCP localport=8501 remoteip=192.168.0.0/16 profile=private
```

---

### 4. 後端 API 連接失敗

#### 症狀
- Chat/Admin 頁面顯示 "API 連接失敗"
- 統計頁面無資料

#### 檢查步驟
1. **確認後端已啟動**
   ```bash
   # 訪問健康檢查端點
   curl http://localhost:8000/health
   # 預期回應: {"status": "healthy"}
   ```

2. **檢查 Port 是否被佔用**
   ```powershell
   netstat -ano | findstr "8000"
   ```

3. **查看後端日誌**
   - 檢查後端 Terminal 視窗的錯誤訊息

4. **重新啟動後端**
   - 關閉後端 Terminal 視窗
   - 重新執行 `start_v2.bat`

---

### 5. Gemini API 錯誤

#### 錯誤訊息
```
google.generativeai.types.GenerateContentError: API key not valid
```

#### 解決方案
1. **檢查 .env 檔案**
   ```bash
   # 確認 GEMINI_API_KEY 已設定
   GEMINI_API_KEY=AIza...
   ```

2. **驗證 API Key**
   - 訪問 https://aistudio.google.com/app/apikey
   - 檢查 API Key 是否有效
   - 確認配額未超限

3. **測試連接**
   ```python
   import google.generativeai as genai
   genai.configure(api_key="YOUR_API_KEY")
   model = genai.GenerativeModel("gemini-2.0-flash-exp")
   response = model.generate_content("Hello")
   print(response.text)
   ```

---

### 6. 檔案上傳失敗

#### 症狀
- 上傳後檔案未處理
- 檔案被移至 `failed_files/`

#### 檢查步驟
1. **查看後端日誌**
   - 檢查 Watcher 是否觸發
   - 查看錯誤原因

2. **檢查檔案格式**
   - 支援格式: `.md`, `.txt`, `.pptx`, `.pdf`, `.png`, `.jpg`, `.jpeg`
   - 檔案大小 < 50MB

3. **檢查資料目錄權限**
   ```powershell
   # 確認目錄存在且可寫入
   icacls backend\data\raw_files
   ```

4. **手動測試處理**
   ```python
   from core.ingestion_v3 import process_document_v3
   result = process_document_v3(
       file_path="test.pptx",
       doc_type="Knowledge",
       enable_gemini_vision=True
   )
   print(result)
   ```

---

### 7. Token 用量異常

#### 症狀
- Token 消耗速度異常快
- 成本超出預期

#### 檢查步驟
1. **查看 Token 統計**
   - 進入 Stats 頁面查看用量圖表
   - 檢查哪個操作消耗最多

2. **檢查模型設定**
   ```python
   # 確認使用正確的模型
   # GPT-4o: 較貴但效果好
   # GPT-4o-mini: 便宜但可能需要多次查詢
   ```

3. **優化策略**
   - 使用快取機制（待實作）
   - 減少 chunk 大小
   - 使用更便宜的模型進行初步篩選

---

### 8. 資料庫錯誤

#### 錯誤訊息
```
sqlite3.OperationalError: database is locked
sqlite3.OperationalError: no such table: documents
```

#### 解決方案

**情況 1: 資料庫被鎖定**
```powershell
# 關閉所有存取資料庫的程式
# 重新啟動系統
```

**情況 2: 資料表不存在**
```bash
# 重新初始化資料庫
python scripts/init_db.py
```

**情況 3: 資料庫損壞**
```bash
# 備份舊資料庫
copy backend\data\documents\knowledge_v2.db backend\data\documents\knowledge_v2.db.backup

# 重新建立
python scripts/init_db.py
```

---

### 9. 效能問題

#### 症狀
- 查詢速度過慢 (>10 秒)
- 頁面載入緩慢
- CPU/記憶體使用率過高

#### 診斷步驟

1. **檢查資料庫大小**
   ```powershell
   # 查看資料庫檔案大小
   dir backend\data\documents\*.db
   ```

2. **檢查文件數量**
   ```sql
   -- 在 Stats 頁面查看
   -- 或直接查詢資料庫
   SELECT COUNT(*) FROM documents;
   SELECT COUNT(*) FROM vec_chunks;
   ```

3. **系統資源監控**
   ```powershell
   # 開啟工作管理員
   taskmgr
   # 查看 Python 程序的 CPU/記憶體使用
   ```

#### 優化建議

| 問題 | 解決方案 |
|------|---------|
| 文件數過多 (>1000) | 定期清理舊文件、分批處理 |
| 向量數過多 (>10000) | 減少 chunk 大小、使用索引優化 |
| 記憶體不足 | 增加系統記憶體、使用分頁查詢 |
| 網路延遲高 | 使用本地模型、啟用快取 |

---

### 10. 系統更新後問題

#### 症狀
- 更新程式碼後無法啟動
- 新功能無法使用

#### 解決方案

1. **重新安裝依賴**
   ```bash
   pip install -r backend/requirements.txt --upgrade
   pip install -r frontend/requirements.txt --upgrade
   ```

2. **清除 Python 快取**
   ```batch
   # 刪除 __pycache__ 目錄
   for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"
   ```

3. **重新初始化資料庫** (如果資料表結構變更)
   ```bash
   python scripts/init_db.py
   ```

4. **清除 Streamlit 快取**
   ```bash
   # 刪除 .streamlit/cache
   rmdir /s /q .streamlit\cache
   ```

---

## 🛠️ 除錯工具

### 查看系統日誌
```powershell
# 後端日誌
Get-Content backend\data\logs\*.log -Tail 50

# Streamlit 日誌（Terminal 輸出）
```

### 測試 API 端點
```powershell
# 健康檢查
curl http://localhost:8000/health

# 查看 API 文檔
start http://localhost:8000/docs
```

### 資料庫查詢
```bash
# 使用 DB Browser for SQLite
# 或直接使用 sqlite3
sqlite3 backend\data\documents\knowledge_v2.db
```

---

## 📞 取得協助

如果上述方案都無法解決問題：

1. **收集錯誤資訊**
   - 完整的錯誤訊息
   - 系統環境 (Python 版本、OS 版本)
   - 發生錯誤前的操作步驟

2. **檢查已知問題**
   - 查看 `TODO.md` 中的「已知限制」
   - 查看 `ARCHITECTURE_OVERVIEW.md` 中的「已知限制與改進方向」

3. **查看相關文檔**
   - `QUICKSTART.md` - 快速啟動指南
   - `ARCHITECTURE_OVERVIEW.md` - 完整架構文檔
   - API 文檔: http://localhost:8000/docs

---

## 🔍 預防性維護

### 定期檢查清單

- [ ] 每週備份資料庫
- [ ] 每月檢查磁碟空間 (`backend/data/`)
- [ ] 每月清理舊日誌檔案
- [ ] 每月檢查 Token 用量與成本
- [ ] 每季更新依賴套件
- [ ] 每季檢查 API Key 有效性

### 備份腳本範例

```batch
@echo off
REM 備份資料庫
set BACKUP_DIR=backup_%date:~0,4%%date:~5,2%%date:~8,2%
mkdir %BACKUP_DIR%
copy backend\data\documents\*.db %BACKUP_DIR%\
echo 備份完成: %BACKUP_DIR%
```

---

**提示**: 大部分問題都可以透過重新啟動系統解決！
