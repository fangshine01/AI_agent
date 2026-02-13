# 並行運行觀察期檢查清單 (v2.3.0)

> 本文件用於 v2.3.0 部署上線後的 2 週觀察期間，逐項確認系統穩定度。

## 觀察期間

| 項目 | 預計時間 |
|------|---------|
| 開始日期 | 部署當天 |
| 結束日期 | 部署後 2 週 |
| 檢查頻率 | 第 1 週：每日 / 第 2 週：隔日 |

---

## 每日檢查清單

### 1. 系統健康 (Health Check)

- [ ] `/health` 端點回應正常 (HTTP 200)
- [ ] `/health/detailed` 無錯誤旗標
- [ ] `/metrics` 端點可正常抓取
- [ ] 記憶體使用量 < 1GB (Windows 工作管理員)
- [ ] 磁碟空間 > 5GB 可用

```bash
# 快速檢查指令
curl http://localhost:8000/health
curl http://localhost:8000/health/detailed
curl http://localhost:8000/metrics
```

### 2. 效能指標 (Performance)

- [ ] 平均回應時間 < 500ms (`/metrics` 中的 `http_request_duration_seconds`)
- [ ] 錯誤率 < 1% (`http_errors_total` / `http_requests_total`)
- [ ] 無 5xx 錯誤堆積
- [ ] SQLite WAL 檔案大小 < 100MB

```bash
# 檢查 WAL 檔案大小
dir backend\data\documents\knowledge_v2.db-wal
```

### 3. 功能驗證 (Functional)

- [ ] Chat UI 可正常對話
- [ ] Admin UI 系統設定可讀取/儲存
- [ ] 模型選擇器 13 模型全數顯示
- [ ] 分析模式 (純文字/含圖/自動) 切換正常
- [ ] 檔案上傳 + 處理完整流程正常
- [ ] 搜尋功能 (語意 + 關鍵字) 正常回傳

### 4. 安全性 (Security)

- [ ] BYOK Identity 隔離正常 (不同 Key 看不到彼此歷史)
- [ ] Rate Limiter 正常運作 (429 回應)
- [ ] API Key 驗證正常
- [ ] 無異常存取日誌

### 5. 資料完整性 (Data Integrity)

- [ ] 知識庫文件數量無異常減少
- [ ] Token 統計持續累計
- [ ] Chat History 正常保存
- [ ] 備份腳本運行正常

```bash
# 備份資料庫
scripts\backup_db.bat
```

---

## 每週深度檢查

### Week 1 額外項目

- [ ] 執行 50 並發壓力測試，確認基線
- [ ] 檢查 `data/logs/` 日誌無 ERROR 級別堆積
- [ ] 確認搜尋快取命中率 (Embedding Cache Hit Rate)
- [ ] 驗證 Prometheus 指標可被 Grafana/外部系統抓取

```bash
# 50 並發壓力測試
locust -f tests/load_test.py --host=http://localhost:8000 --users=50 --spawn-rate=5 --run-time=60s --headless
```

### Week 2 額外項目

- [ ] 執行 100 並發壓力測試 (M4 驗收標準)
- [ ] 確認平均回應 < 1000ms, P95 < 3000ms, 失敗率 < 1%
- [ ] 長時間運行穩定性 (24hr 連續無當機)
- [ ] SQLite VACUUM (如 DB 大小膨脹)
- [ ] 確認 E2E 測試全數通過

```bash
# 100 並發壓力測試 (M4 驗收)
locust -f tests/load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=120s --headless --csv=tests/load_test_results

# E2E 測試
pytest tests/e2e/ -v
```

---

## 觀察期結論模板

| 指標 | Week 1 結果 | Week 2 結果 | 判定 |
|------|------------|------------|------|
| 可用性 (uptime) | ___% | ___% | ✅/❌ |
| 平均回應時間 | ___ms | ___ms | ✅/❌ |
| 錯誤率 | ___% | ___% | ✅/❌ |
| 100 並發通過 | N/A | ✅/❌ | ✅/❌ |
| 資料完整性 | ✅/❌ | ✅/❌ | ✅/❌ |
| 安全性 | ✅/❌ | ✅/❌ | ✅/❌ |

### 結論
- [ ] **通過**: 所有指標達標，正式發布 v2.3.0
- [ ] **有條件通過**: 需修復 ___ 後再觀察 1 週
- [ ] **未通過**: 需回退至 v2.2.0 並重新排查

---

*文件版本: v2.3.0 | 最後更新: Phase 5 完成時*
