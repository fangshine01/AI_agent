# 搜尋系統優化建議 - 快速摘要

## 🔍 問題診斷結果

### 資料庫狀態 ✅
- **有** 3 個 N706 相關文件，包括 `N706 蝴蝶Mura.pptx`
- 每個文件有 6 個向量切片
- keywords 欄位有完整資料

### 根本原因 ❌
**關鍵字搜尋使用完整查詢字串進行匹配**

當用戶查詢: `"N706 蝴蝶Mura.pptx 內容詳細解析"`

現在的搜尋邏輯:
```sql
WHERE filename LIKE '%N706 蝴蝶Mura.pptx  內容詳細解析%'
```
→ **找不到任何結果** (沒有文件包含這麼長的完整字串)

但如果分開搜尋:
- "N706" → ✅ 3 個文件
- "蝴蝶" → ✅ 1 個文件  
- "Mura" → ✅ 1 個文件

## 💡 優化方案

### 方案 1: 查詢分詞 + 多關鍵字 OR 搜尋 (推薦優先實施)

**改進後的邏輯**:
1. 將查詢拆分: `["N706", "蝴蝶", "Mura"]` (過濾停用詞如"內容"、"詳細"、"解析")
2. 使用 OR 邏輯:
   ```sql
   WHERE (filename LIKE '%N706%' OR filename LIKE '%蝴蝶%' OR filename LIKE '%Mura%')
   ```
3. 根據匹配關鍵字數量排序

**預期效果**: 關鍵字搜尋命中率從 **0% → 80%+**

### 方案 2: 利用 keywords 欄位

資料庫已有結構化關鍵字資料:
```
專案:N706,客戶:PTST,Defect Code:G Line Gap
```

新增對 `vec_chunks.keywords` 欄位的搜尋，提高精準度。

### 方案 3: 優化混合搜尋融合策略

使用 Reciprocal Rank Fusion (RRF) 取代簡單的加權平均，更公平地融合向量搜尋和關鍵字搜尋結果。

## 📋 實施建議

### 立即改善 (第一階段)
1. 創建分詞工具 `core/search/tokenizer.py`
2. 修改 `legacy_search.py` 支援多關鍵字 OR 搜尋
3. 添加匹配分數計算

### 進一步優化 (第二階段)  
1. 添加 keywords 欄位搜尋
2. 調整搜尋優先級

### 長期優化 (第三階段)
1. 實施 RRF 融合策略
2. 添加查詢擴展 (同義詞)

## 📊 測試驗證

建議的測試查詢:
- ✅ "N706 蝴蝶Mura.pptx 內容詳細解析" → 應找到蝴蝶Mura文件
- ✅ "N706 問題" → 應找到所有3個N706文件  
- ✅ "蝴蝶" → 應找到蝴蝶Mura文件
- ✅ "Oven Pin" → 應找到Oven Pin文件

## 🔗 詳細文檔

完整的技術方案和實現細節請參考: [implementation_plan.md](file:///C:/Users/User/.gemini/antigravity/brain/b597f2e5-de1e-4e5a-9535-83172a3770c7/implementation_plan.md)
