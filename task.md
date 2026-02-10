# AI Agent 優化任務清單

## 0. 資料庫架構擴充 🗄️ (優先執行) ✅
- [x] 建立 `document_raw_data` 表及索引
- [x] 建立 `document_keywords` 表及索引
- [x] 建立 `troubleshooting_metadata` 表及索引
- [x] 建立 `procedure_metadata` 表及索引
- [x] 建立 `document_versions` 表及索引
- [x] 建立 `search_analytics` 表及索引
- [x] 建立 `chunk_metadata` 表
- [x] 遷移現有 documents 表的專屬欄位到新表
- [x] 建立新的資料庫操作模組(keyword_ops.py, metadata_ops.py, raw_data_ops.py)
- [ ] 測試所有新表的 CRUD 操作

## 1. 關鍵字映射功能整合 ✅
- [x] 分析 keyword_mappings 的讀取流程
- [x] 實作 keyword_ops.py (save/get/search 關鍵字)
- [x] 修改 ingestion 流程以讀取並儲存關鍵字到 document_keywords 表
- [x] 實作 AI 自動提取關鍵字功能
- [x] 整合到搜尋流程(支援關鍵字過濾)

## 2. Troubleshooting Chunking 策略改善 ✅
- [x] 分析目前 8D 欄位切片問題
- [x] 設計新的 unified chunk 策略
- [x] 修改 TroubleshootingParser 生成單一整合 chunk
- [x] 將 8D 欄位結構儲存到 chunk_metadata 表
- [x] 更新 troubleshooting_metadata 表儲存產品/Defect Code 等資訊

## 3. Troubleshooting 精準查詢強化 ✅
- [x] 實作產品+Defect Code 精準匹配邏輯
- [x] 在 query_router 加入 exact_match 模式
- [x] 建立 troubleshooting 專用查詢模板
- [x] 實作 8D 格式 Markdown 產生器
- [x] 整合 yield loss 資訊顯示
- [x] 提供 .md 檔案下載功能

## 4. SOP 查詢 Token 消耗優化 ✅
- [x] 分析目前 SOP 查詢的 GPT 總結流程
- [x] 實作 `_should_skip_llm` 判斷邏輯
- [x] 在 query_router 加入 'direct' 回傳模式
- [x] 修改 chat_app 支援直接回傳(跳過 GPT)
- [ ] 驗證 token 消耗降低

## 5. Raw Data 保存與重新訓練機制 ✅
- [x] 修改 ingestion 流程儲存 raw_content 到 document_raw_data
- [x] 實作 raw_data_ops.py 操作模組
- [x] 建立 retraining.py 重新訓練模組
- [x] 實作 retrain_all_documents 函數
- [x] 整合 document_versions 記錄重訓歷史
- [ ] 測試重新訓練流程
