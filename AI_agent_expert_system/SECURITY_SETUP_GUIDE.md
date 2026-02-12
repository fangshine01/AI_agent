# 🔐 安全設定完整指南

> **目的**: 保護你的 AI Expert System 避免未授權存取  
> **適用對象**: 所有使用局域網共享的使用者  
> **設定時間**: 約 5 分鐘

---

## 📋 目錄

1. [為什麼需要安全設定](#為什麼需要安全設定)
2. [防護層級說明](#防護層級説明)
3. [推薦設定方案](#推薦設定方案)
4. [逐步設定教學](#逐步設定教學)
5. [驗證與測試](#驗證與測試)
6. [常見問題](#常見問題)

---

## 為什麼需要安全設定

### 風險說明

當你使用 `0.0.0.0` 監聽時，系統會在局域網中開放服務：

```
前端 Streamlit: http://192.168.5.3:8501
後端 FastAPI:   http://192.168.5.3:8000
```

**潛在風險**:

| 風險類型 | 說明 | 風險等級 |
|---------|------|---------|
| 📁 **檔案下載** | 他人可透過 API 下載你的訓練文件 | ⚠️ **高** |
| 📊 **資料查詢** | 他人可查詢向量資料庫內容 | ⚠️ **中** |
| 🔧 **系統設定** | 他人可查看 API 文檔和系統資訊 | ⚠️ **中** |
| 💻 **程式碼** | 程式碼本身不會被下載（需實體存取） | ✅ **低** |

### 真實情境範例

```bash
# 場景 1: 同事知道你的 IP，可以這樣做
curl http://192.168.5.3:8000/api/v1/files/list
# 回應: 列出所有你的文件名稱

# 場景 2: 下載特定文件
curl http://192.168.5.3:8000/api/v1/files/download/機密報告.md -O
# 結果: 機密報告.md 被下載

# 場景 3: 查詢訓練資料
curl http://192.168.5.3:8000/api/v1/search?query=專案計畫
# 回應: 你的專案計畫內容片段
```

---

## 防護層級說明

### 層級 1: 無保護（預設狀態）

- ❌ 任何知道 IP 的人都能存取
- ⚠️ **不建議用於敏感資料**

### 層級 2: 防火牆限制（基本保護）

- ✅ 只允許特定 IP 範圍存取（如 192.168.0.0/16）
- ✅ 設定時間: 1 分鐘（一鍵腳本）
- ⚠️ 同網段使用者仍可存取

**適用場景**: 家用網路、小型辦公室（5-10 人）

### 層級 3: API Key 驗證（推薦）

- ✅ 需要正確的 API Key 才能存取
- ✅ 設定時間: 3 分鐘
- ✅ 防護所有 API 端點和檔案下載
- ⚠️ API Key 洩漏需更換密鑰

**適用場景**: 企業環境、多人共用網路

### 層級 4: 雙重保護（最高安全）

- ✅ 防火牆 + API Key 驗證
- ✅ 外層阻擋 IP，內層驗證身份
- ✅ 設定時間: 4 分鐘

**適用場景**: 處理機密資料、生產環境

---

## 推薦設定方案

### 方案 A: 家用網路 / 個人使用

```
防火牆限制 (層級 2)
```

**理由**: 家庭網路通常只有自己或家人，防火牆已足夠

**設定**: 執行 `setup_firewall.bat`

---

### 方案 B: 小型辦公室 (5-20 人)

```
API Key 驗證 (層級 3)
```

**理由**: 多人環境需要驗證機制，防止好奇同事存取

**設定**: 參考下方「逐步設定教學」

---

### 方案 C: 企業環境 / 機密資料

```
防火牆 + API Key 驗證 (層級 4)
```

**理由**: 雙重保護，最高安全等級

**設定**: 
1. 執行 `setup_firewall.bat`
2. 參考下方「逐步設定教學」啟用 API Key

---

## 逐步設定教學

### 🛡️ 設定防火牆 (層級 2)

#### Windows 一鍵設定

```batch
# 以系統管理員身分執行
setup_firewall.bat
```

**腳本會自動**:
- ✅ 建立兩條防火牆規則（Port 8501, 8000）
- ✅ 限制只允許局域網 IP 連接
- ✅ 驗證規則是否生效

**完成！** 現在外網和陌生 IP 無法連接你的服務。

---

### 🔐 啟用 API Key 驗證 (層級 3)

#### 步驟 1: 產生安全密鑰

開啟 **命令提示字元** 或 **PowerShell**:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

輸出範例:
```
XyZ9_AbC123-dEfGhI456jKlMnOpQ789rStUvWxYz
```

**複製這串字串**（每次執行會產生不同密鑰）

---

#### 步驟 2: 編輯環境變數

1. 開啟專案根目錄
2. 找到 `.env` 檔案（若無，複製 `.env.example` 並重新命名為 `.env`）
3. 編輯檔案，加入以下內容：

```env
# ============================================
# 安全性設定 (Security Settings)
# ============================================

# 啟用 API Key 驗證
ENABLE_API_AUTH=true

# 填入剛才產生的密鑰
SYSTEM_API_KEY=XyZ9_AbC123-dEfGhI456jKlMnOpQ789rStUvWxYz
```

**重要**: 將 `XyZ9_AbC123...` 替換成你剛產生的密鑰

---

#### 步驟 3: 重啟系統

關閉現有的服務（在命令視窗按 `Ctrl+C`），重新啟動：

```batch
start_v2.bat
```

**看到以下訊息代表成功**:
```
[2024-05-20 10:30:00] INFO: ✅ API Key 驗證已啟用
[2024-05-20 10:30:00] INFO: 🔒 受保護端點: /api/v1/*, /files/*, /docs
```

---

## 驗證與測試

### 測試 1: 防火牆規則驗證

```powershell
# 查看防火牆規則
netsh advfirewall firewall show rule name="AI-Expert-Streamlit-LAN"
netsh advfirewall firewall show rule name="AI-Expert-FastAPI-LAN"

# 預期: 顯示規則詳細資訊，RemoteIP 限制為 192.168.0.0/16 等
```

**實際測試**:
- ✅ 同網段電腦可以連接 `http://192.168.x.x:8501`
- ✅ 使用手機 4G 網路無法連接

---

### 測試 2: API Key 驗證測試

#### 準備工作
- 系統已啟動
- `.env` 已設定 `ENABLE_API_AUTH=true`
- 記下你的 `SYSTEM_API_KEY`

#### 測試指令

```bash
# 測試 1: 未授權請求（應該失敗）
curl http://192.168.5.3:8000/api/v1/files/list

# 預期回應:
# {"detail": "Unauthorized: Missing or invalid API Key"}

# 測試 2: 帶上正確 API Key（應該成功）
curl http://192.168.5.3:8000/api/v1/files/list \
  -H "X-API-Key: XyZ9_AbC123-dEfGhI456jKlMnOpQ789rStUvWxYz"

# 預期回應:
# {"status": "success", "files": ["file1.md", "file2.pdf"]}

# 測試 3: 前端瀏覽器存取（應該正常運作）
# 開啟瀏覽器: http://192.168.5.3:8501
# 前端會自動讀取 .env 的 SYSTEM_API_KEY，無需手動輸入
```

---

### 測試 3: 檢視未授權存取日誌

```bash
# 查看後端日誌（在 start_v2.bat 啟動的視窗）
# 當有人嘗試未授權存取時，會顯示：

[2024-05-20 15:30:00] WARNING: 🚫 未授權存取嘗試:
  - IP: 192.168.5.100
  - 端點: /api/v1/files/download/secret.pdf
  - 原因: Missing API Key
```

---

## 常見問題

### Q1: 啟用 API Key 後，前端無法使用怎麼辦？

**原因**: 前端的 `.env` 檔案沒有設定 `SYSTEM_API_KEY`

**解決方法**:
1. 確認 `backend/.env` 和專案根目錄的 `.env` 都有設定相同的 `SYSTEM_API_KEY`
2. 重啟系統: `start_v2.bat`

---

### Q2: 忘記 API Key 怎麼辦？

**解決方法**:
1. 查看 `.env` 檔案中的 `SYSTEM_API_KEY` 值
2. 如果遺失，重新產生新的密鑰並更新 `.env`

---

### Q3: API Key 是否會洩漏？

**風險點**:
- ✅ 網路傳輸: HTTPS 加密（生產環境建議使用）
- ⚠️ `.env` 檔案: 確保不要上傳到公開的 Git 儲存庫
- ⚠️ 日誌檔案: 系統不會記錄完整 API Key

**最佳實踐**:
```bash
# 將 .env 加入 .gitignore
echo ".env" >> .gitignore
```

---

### Q4: 如何更換 API Key？

**步驟**:
1. 產生新的密鑰: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. 更新所有 `.env` 檔案的 `SYSTEM_API_KEY`
3. 重啟系統: `start_v2.bat`

---

### Q5: 防火牆規則如何移除？

```powershell
# 移除防火牆規則
netsh advfirewall firewall delete rule name="AI-Expert-Streamlit-LAN"
netsh advfirewall firewall delete rule name="AI-Expert-FastAPI-LAN"
```

---

### Q6: 如何暫時關閉 API Key 驗證？

編輯 `.env`:
```env
# 改為 false
ENABLE_API_AUTH=false
```

重啟系統即可。開發除錯時建議關閉，正式使用時開啟。

---

### Q7: 多人使用如何管理不同的 API Key？

**當前版本**: 僅支援單一系統 API Key（所有人共用）

**未來版本**: 規劃支援多使用者 JWT Token 驗證（每人獨立帳號）

**暫時解決方案**: 
- 透過防火牆限制特定 IP 範圍
- 將 API Key 僅分享給信任的人員

---

## 📌 快速檢查清單

設定完成後，確認以下項目：

### 防火牆設定
- [ ] 執行過 `setup_firewall.bat`
- [ ] 規則出現在「Windows Defender 防火牆進階設定」
- [ ] 外網無法連接 Port 8501/8000

### API Key 驗證
- [ ] `.env` 已設定 `ENABLE_API_AUTH=true`
- [ ] `.env` 已設定 `SYSTEM_API_KEY`（32 字元以上）
- [ ] 啟動時看到「✅ API Key 驗證已啟用」訊息
- [ ] 未授權 API 請求回傳 401 錯誤
- [ ] 前端瀏覽器存取正常

### 測試驗證
- [ ] 手機 4G 網路無法連接（外網隔離）
- [ ] 同網段電腦可以連接
- [ ] curl 測試未授權請求失敗
- [ ] curl 測試授權請求成功

---

## 🎯 總結

| 防護層級 | 設定難度 | 保護程度 | 適用場景 |
|---------|---------|---------|---------|
| 無保護 | - | ⭐☆☆☆☆ | 僅測試 |
| 防火牆 | ⭐☆☆☆☆ | ⭐⭐⭐☆☆ | 家用網路 |
| API Key | ⭐⭐☆☆☆ | ⭐⭐⭐⭐☆ | 辦公室 |
| 雙重保護 | ⭐⭐☆☆☆ | ⭐⭐⭐⭐⭐ | 企業環境 |

**建議**: 至少啟用「防火牆」，處理敏感資料時啟用「API Key 驗證」。

---

## 📚 相關文件

- [SECURITY.md](SECURITY.md) - 完整安全分析與風險評估
- [QUICKSTART.md](QUICKSTART.md) - 快速啟動指南
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - 常見問題排解

---

**最後更新**: 2024-05-20  
**維護者**: AI Expert System Team
