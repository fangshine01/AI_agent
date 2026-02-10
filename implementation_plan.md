# AI Agent 系統優化實作計劃

## 概述

本計劃針對目前 AI Agent 專家系統的五個主要問題,提出改善方案並規劃實作步驟。

---

## 📊 資料庫架構設計討論

### 現有資料庫結構分析

#### 📋 目前的 Tables

**1. documents 表**
- **用途**: 儲存文件的元數據(metadata)
- **主要欄位**:
  - `id`: 主鍵
  - `filename`: 檔案名稱
  - `doc_type`: 文件類型(Knowledge/Troubleshooting/Training/Procedure)
  - `upload_date`: 上傳時間
  - `analysis_mode`: 分析模式(text_only/vision/auto)
  - `model_used`: 使用的 AI 模型
  - **v3.0 新增欄位**:
    - `file_hash`: 檔案雜湊值(用於去重)
    - `file_size`: 檔案大小
    - `category`, `tags`: 分類與標籤
    - `processing_time`: 處理時間
    - `author`, `department`, `factory`: 組織相關資訊
    - `language`: 語言(預設 zh-TW)
    - `priority`: 優先級
    - `summary`, `key_points`: AI 產生的摘要與重點
    - `status`: 狀態(active/archived/deleted)
    - **Troubleshooting 專用欄位**:
      - `product_model`: 產品型號(如 N706, N707)
      - `defect_code`: 缺陷代碼(如 Oven Pin, 蝴蝶Mura)
      - `station`: 檢出站點
      - `yield_loss`: 產量損失

**2. vec_chunks 表**
- **用途**: 儲存文件切片(chunks)與向量 embeddings
- **主要欄位**:
  - `chunk_id`: 主鍵
  - `doc_id`: 外鍵,關聯到 documents 表
  - `source_type`: 切片類型(chapter/step/field/section)
  - `source_title`: 切片標題
  - `text_content`: 實際文字內容
  - `embedding`: 向量資料(BLOB,使用 sqlite-vec 擴充)
  - `keywords`: 關鍵字(TEXT,目前為 JSON 或逗號分隔字串)
  - `created_at`: 建立時間

#### 🔍 現有結構的優缺點

**優點:**
- 基本資料模型完整,支援核心的檢索功能
- documents 表已包含豐富的 metadata 欄位
- 使用外鍵約束(ON DELETE CASCADE),維持資料一致性
- 已建立索引加速查詢

**缺點:**
- **缺少原始資料保存**: 沒有儲存原始文字內容(raw_content),無法重新訓練
- **關鍵字結構不佳**: vec_chunks.keywords 欄位為文字,不利於結構化查詢
- **資料正規化不足**: Troubleshooting 專屬欄位直接放在 documents 表,導致表結構膨脹
- **缺少稽核追蹤**: 沒有記錄文件修改歷史
- **缺少使用統計**: 無法追蹤文件被查詢的次數與效果

---

### 💡 資料庫擴充建議


#### 方案 2: 建立獨立的 document_raw_data 表 ⭐⭐ (推薦-擴展性方案)

**做法**:
```sql
CREATE TABLE IF NOT EXISTS document_raw_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER UNIQUE NOT NULL,
    raw_content TEXT NOT NULL,
    content_type TEXT,           -- 'text', 'markdown', 'html'
    encoding TEXT DEFAULT 'utf-8',
    compressed BOOLEAN DEFAULT 0, -- 是否經過壓縮
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_raw_data_doc_id ON document_raw_data(doc_id);
```

**優點**:
- ✅ 符合資料庫正規化原則(關注點分離)
- ✅ 可支援內容壓縮(節省儲存空間)
- ✅ 可支援多版本管理(移除 UNIQUE 約束即可)
- ✅ 查詢 documents 表時不會被大型 raw_content 拖慢
- ✅ 未來可輕鬆遷移到其他儲存方案(如 S3, MinIO)

**缺點**:
- ❌ 需要額外的 JOIN 才能取得 raw_content
- ❌ 實作稍微複雜

**適用情境**:
- 文件數量 > 1000 或預期會成長
- 單一文件大小可能 > 500KB
- 需要版本管理或內容壓縮
- 未來可能遷移到物件儲存

> [!NOTE]
> **建議**: 若專案規模預期會成長,或需要支援大型文件(如長 PDF、大型 PPT),建議採用方案 2

---

### 🏗️ 完整的資料庫架構建議

基於你的需求與目前專案規模,建議採用以下架構:

#### 新增的 Tables

**1. document_raw_data 表** (方案 2)
```sql
CREATE TABLE IF NOT EXISTS document_raw_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER UNIQUE NOT NULL,
    raw_content TEXT NOT NULL,
    content_type TEXT DEFAULT 'text',
    encoding TEXT DEFAULT 'utf-8',
    compressed BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);
```

**2. document_keywords 表** (已選擇)
```sql
CREATE TABLE IF NOT EXISTS document_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL,
    category TEXT NOT NULL,      -- 產品/Defect Code/機台/站點/廠別
    keyword TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,  -- AI 提取的信心度
    source TEXT DEFAULT 'manual', -- 'manual'(手動) or 'ai'(AI 提取)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(doc_id, category, keyword)
);

CREATE INDEX IF NOT EXISTS idx_doc_keywords_doc_id ON document_keywords(doc_id);
CREATE INDEX IF NOT EXISTS idx_doc_keywords_category ON document_keywords(category);
CREATE INDEX IF NOT EXISTS idx_doc_keywords_keyword ON document_keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_doc_keywords_composite ON document_keywords(category, keyword);
```

**3. document_versions 表** 
```sql
CREATE TABLE IF NOT EXISTS document_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    change_type TEXT,             -- 'create', 'update', 'reprocess'
    changed_by TEXT,              -- 操作者
    change_description TEXT,
    snapshot JSON,                -- 該版本的 metadata 快照
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(doc_id, version)
);
```

**4. search_analytics 表** 
```sql
CREATE TABLE IF NOT EXISTS search_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    intent TEXT,                  -- 'procedural', 'troubleshooting', etc.
    strategy TEXT,                -- 'vector', 'hybrid', 'exact_match'
    result_count INTEGER,
    search_time_ms REAL,
    user_clicked_chunk_id INTEGER,
    user_rating INTEGER,          -- 1-5 評分
    feedback TEXT,
    session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_search_analytics_query ON search_analytics(query);
CREATE INDEX IF NOT EXISTS idx_search_analytics_created_at ON search_analytics(created_at);
```

**5. chunk_metadata 表** 

目前 vec_chunks 若要儲存複雜的 metadata(如 Troubleshooting 的 8D 結構化欄位),只能用 JSON 字串。
建立獨立的 metadata 表可以更靈活:

```sql
CREATE TABLE IF NOT EXISTS chunk_metadata (
    chunk_id INTEGER PRIMARY KEY,
    metadata JSON NOT NULL,       -- 結構化 metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES vec_chunks(chunk_id) ON DELETE CASCADE
);
```

---

### 📐 資料庫正規化策略

#### 目前的正規化程度

- **documents 表**: 部分違反第三正規化(3NF)
  - 問題:Troubleshooting 專用欄位(product_model, defect_code 等)只有部分文件使用
  - 建議:可考慮拆分到 `troubleshooting_metadata` 表

#### 建議的正規化方案


**方案 B: 拆分專屬欄位** (適合中大型專案)

```sql
-- Troubleshooting 專屬 metadata
CREATE TABLE IF NOT EXISTS troubleshooting_metadata (
    doc_id INTEGER PRIMARY KEY,
    product_model TEXT,
    defect_code TEXT,
    station TEXT,
    yield_loss TEXT,
    severity TEXT,              -- 嚴重程度
    occurrence_date DATE,       -- 發生日期
    resolution_date DATE,       -- 解決日期
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Procedure 專屬 metadata
CREATE TABLE IF NOT EXISTS procedure_metadata (
    doc_id INTEGER PRIMARY KEY,
    procedure_type TEXT,        -- 'SOP', 'WI', 'Checklist'
    applicable_station TEXT,    -- 適用站點
    revision TEXT,              -- 版本號
    approval_status TEXT,       -- 簽核狀態
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);
```

優點:
- ✅ 符合正規化原則
- ✅ 節省儲存空間
- ✅ 擴充性更好

缺點:
- ❌ 查詢時需要額外 JOIN
- ❌ 實作複雜度增加

---

### 🎯 建議的資料庫架構總結

根據你的專案需求與規模,我建議採用以下架構:

#### 核心表(必要)
1. ✅ **documents** - 文件元數據(保持現狀)
2. ✅ **vec_chunks** - 向量切片(保持現狀)
3. ✅ **document_raw_data** - 原始文字內容(新增 - 方案 2)
4. ✅ **document_keywords** - 關鍵字關聯(新增 - 已選擇)

#### 增強表(建議新增)
5. ⭐ **search_analytics** - 搜尋分析與優化
6. ⭐ **document_versions** - 版本管理(若需要稽核追蹤)

#### 進階表(增加)
7. 🔸 **troubleshooting_metadata** - Troubleshooting 專屬欄位(若需要嚴格正規化)
8. 🔸 **procedure_metadata** - Procedure 專屬欄位
9. 🔸 **chunk_metadata** - Chunk 的結構化 metadata

#### 已存在的其他表
- **Token 相關表**: 已存在於 `tokenrecord.db` 中(獨立資料庫)

---

### 📊 資料庫拆分建議

#### 目前狀況
- 主資料庫:`knowledge.db` (documents + vec_chunks)
- Token 資料庫:`tokenrecord.db` (token 使用統計)

#### 建議

**選項 1: 單一資料庫** (推薦 - 簡單方案)
- 將所有新表都加入 `knowledge.db`
- 優點:簡單、事務一致性好
- 缺點:資料庫檔案會變大

---

### ✅ 使用者確認的架構方案

> [!NOTE]
> **使用者已完成架構選擇,以下為最終確認方案**

1. **✅ raw_content 儲存方案**: 
   - **已選擇:方案 2 - 建立獨立的 document_raw_data 表**
   - 符合擴展性需求,支援未來成長

2. **✅ 資料庫正規化程度**:
   - **已選擇:方案 B - 拆分專屬欄位**
   - 建立 `troubleshooting_metadata` 表
   - 建立 `procedure_metadata` 表

3. **✅ 進階功能需求**:
   - **已確認新增**:
     - ✅ `document_versions` - 版本管理
     - ✅ `search_analytics` - 搜尋分析
     - ✅ `chunk_metadata` - Chunk 結構化 metadata

4. **✅ 資料庫拆分**:
   - **已選擇:單一資料庫(knowledge.db)**
   - 採用多表(multi-sheet)架構
   - 保持事務一致性與簡單性

---

### 🎯 最終確認的完整資料庫架構

#### 核心資料表
```
knowledge.db (單一資料庫)
├── documents                    # 文件元數據(主表)
├── vec_chunks                   # 向量切片與 embeddings
├── document_raw_data           # 原始文字內容 ✨新增
└── document_keywords           # 關鍵字關聯表 ✨新增
```

#### 專屬 Metadata 表(正規化拆分)
```
├── troubleshooting_metadata    # Troubleshooting 專屬欄位 ✨新增
└── procedure_metadata          # Procedure 專屬欄位 ✨新增
```

#### 進階功能表
```
├── document_versions           # 版本管理與稽核 ✨新增
├── search_analytics            # 搜尋分析與優化 ✨新增
└── chunk_metadata              # Chunk 結構化 metadata ✨新增
```

#### 外部資料庫(已存在)
```
tokenrecord.db                  # Token 使用統計
```

---

### 📋 完整資料表 Schema 定義

#### 1. document_raw_data (新增)
```sql
CREATE TABLE IF NOT EXISTS document_raw_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER UNIQUE NOT NULL,
    raw_content TEXT NOT NULL,           -- 原始文字內容
    content_type TEXT DEFAULT 'text',    -- 'text', 'markdown', 'html'
    encoding TEXT DEFAULT 'utf-8',
    compressed BOOLEAN DEFAULT 0,        -- 是否壓縮
    file_extension TEXT,                 -- 原始檔案副檔名
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX idx_raw_data_doc_id ON document_raw_data(doc_id);
```

#### 2. document_keywords (新增)
```sql
CREATE TABLE IF NOT EXISTS document_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL,
    category TEXT NOT NULL,              -- '產品'/'Defect Code'/'機台'/'站點'/'廠別'
    keyword TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,         -- AI 提取的信心度(0-1)
    source TEXT DEFAULT 'manual',        -- 'manual'(手動) or 'ai'(AI提取)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(doc_id, category, keyword)
);

CREATE INDEX idx_keywords_doc_id ON document_keywords(doc_id);
CREATE INDEX idx_keywords_category ON document_keywords(category);
CREATE INDEX idx_keywords_keyword ON document_keywords(keyword);
CREATE INDEX idx_keywords_composite ON document_keywords(category, keyword);
```

#### 3. troubleshooting_metadata (新增 - 正規化拆分)
```sql
CREATE TABLE IF NOT EXISTS troubleshooting_metadata (
    doc_id INTEGER PRIMARY KEY,
    product_model TEXT,                  -- 產品型號 (如 N706, N707)
    defect_code TEXT,                    -- 缺陷代碼 (如 Oven Pin, 蝴蝶Mura)
    station TEXT,                        -- 檢出站點 (如 PTST, A3LR)
    yield_loss TEXT,                     -- 產量損失 (如 8%, 7.2%)
    severity TEXT,                       -- 嚴重程度 (Critical/Major/Minor)
    occurrence_date DATE,                -- 發生日期
    resolution_date DATE,                -- 解決日期
    responsible_dept TEXT,               -- 負責部門
    status TEXT DEFAULT 'active',        -- 'active', 'resolved', 'closed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX idx_ts_product ON troubleshooting_metadata(product_model);
CREATE INDEX idx_ts_defect ON troubleshooting_metadata(defect_code);
CREATE INDEX idx_ts_station ON troubleshooting_metadata(station);
CREATE INDEX idx_ts_composite ON troubleshooting_metadata(product_model, defect_code);
```

#### 4. procedure_metadata (新增 - 正規化拆分)
```sql
CREATE TABLE IF NOT EXISTS procedure_metadata (
    doc_id INTEGER PRIMARY KEY,
    procedure_type TEXT,                 -- 'SOP', 'WI', 'Checklist', 'Flow'
    applicable_station TEXT,             -- 適用站點
    applicable_product TEXT,             -- 適用產品
    revision TEXT,                       -- 版本號 (如 Rev.A, v1.2)
    approval_status TEXT,                -- 'draft', 'pending', 'approved'
    approved_by TEXT,                    -- 簽核者
    approved_date DATE,                  -- 簽核日期
    effective_date DATE,                 -- 生效日期
    expiry_date DATE,                    -- 到期日期
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX idx_proc_type ON procedure_metadata(procedure_type);
CREATE INDEX idx_proc_station ON procedure_metadata(applicable_station);
CREATE INDEX idx_proc_status ON procedure_metadata(approval_status);
```

#### 5. document_versions (新增)
```sql
CREATE TABLE IF NOT EXISTS document_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL,
    version INTEGER NOT NULL,            -- 版本號 (1, 2, 3...)
    change_type TEXT NOT NULL,           -- 'create', 'update', 'reprocess', 'delete'
    changed_by TEXT,                     -- 操作者
    change_description TEXT,             -- 變更描述
    snapshot JSON,                       -- 該版本的 metadata 快照
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(doc_id, version)
);

CREATE INDEX idx_versions_doc_id ON document_versions(doc_id);
CREATE INDEX idx_versions_created ON document_versions(created_at);
```

#### 6. search_analytics (新增)
```sql
CREATE TABLE IF NOT EXISTS search_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,                 -- 查詢字串
    intent TEXT,                         -- 'procedural', 'troubleshooting', 'factual'
    strategy TEXT,                       -- 'vector', 'hybrid', 'exact_match'
    result_count INTEGER,                -- 結果數量
    search_time_ms REAL,                 -- 搜尋時間(毫秒)
    top_chunk_id INTEGER,                -- 最相關的 chunk_id
    user_clicked_chunk_id INTEGER,       -- 使用者點擊的 chunk_id
    user_rating INTEGER,                 -- 使用者評分(1-5)
    feedback TEXT,                       -- 使用者回饋
    session_id TEXT,                     -- Session ID
    user_id TEXT,                        -- 使用者 ID(可選)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_analytics_query ON search_analytics(query);
CREATE INDEX idx_analytics_intent ON search_analytics(intent);
CREATE INDEX idx_analytics_created ON search_analytics(created_at);
CREATE INDEX idx_analytics_session ON search_analytics(session_id);
```

#### 7. chunk_metadata (新增)
```sql
CREATE TABLE IF NOT EXISTS chunk_metadata (
    chunk_id INTEGER PRIMARY KEY,
    metadata JSON NOT NULL,              -- 結構化 metadata
    -- Troubleshooting 的 metadata 範例:
    -- {
    --   "fields": {"Problem issue & loss": "...", ...},
    --   "yield_loss": "8%",
    --   "product": "N706",
    --   "defect_code": "蝴蝶Mura"
    -- }
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES vec_chunks(chunk_id) ON DELETE CASCADE
);
```

---

### 📊 資料表關聯圖

```mermaid
erDiagram
    documents ||--o{ vec_chunks : "1:N"
    documents ||--o| document_raw_data : "1:1"
    documents ||--o{ document_keywords : "1:N"
    documents ||--o| troubleshooting_metadata : "1:0..1"
    documents ||--o| procedure_metadata : "1:0..1"
    documents ||--o{ document_versions : "1:N"
    vec_chunks ||--o| chunk_metadata : "1:0..1"
    
    documents {
        int id PK
        string filename
        string doc_type
        timestamp upload_date
        string analysis_mode
        string model_used
    }
    
    vec_chunks {
        int chunk_id PK
        int doc_id FK
        string source_type
        string source_title
        text text_content
        blob embedding
        string keywords
    }
    
    document_raw_data {
        int id PK
        int doc_id FK
        text raw_content
        string content_type
        boolean compressed
    }
    
    document_keywords {
        int id PK
        int doc_id FK
        string category
        string keyword
        real confidence
    }
    
    troubleshooting_metadata {
        int doc_id PK-FK
        string product_model
        string defect_code
        string station
        string yield_loss
    }
    
    procedure_metadata {
        int doc_id PK-FK
        string procedure_type
        string applicable_station
        string revision
    }
```

---

### 🔧 Migration 策略

#### 步驟 1: 建立新表
- 執行所有新表的 CREATE TABLE 語句
- 建立所有索引

#### 步驟 2: 資料遷移
```sql
-- 將 documents 表中的 Troubleshooting 專屬欄位遷移到 troubleshooting_metadata
INSERT INTO troubleshooting_metadata (doc_id, product_model, defect_code, station, yield_loss)
SELECT id, product_model, defect_code, station, yield_loss
FROM documents
WHERE doc_type = 'troubleshooting' AND product_model IS NOT NULL;

-- 類似遷移 Procedure metadata...
```

#### 步驟 3: 清理舊欄位(可選)
```sql
-- SQLite 不支援 DROP COLUMN,需要重建表
-- 若要保持向後相容,可保留舊欄位但不再使用
```

#### 步驟 4: 更新應用程式碼
- 修改 `schema.py` 加入新表定義
- 建立新的 ops 模組(keyword_ops.py, metadata_ops.py 等)
- 更新 ingestion 流程
- 更新查詢流程


## 問題 1: 關鍵字映射未整合到資料庫

### 📋 問題分析

目前在 `data/keyword_mappings/` 目錄下已建立關鍵字參數檔案:
- `產品.json`
- `Defect Code.json`
- `機台.json`
- `站點.json`
- `廠別.json`

雖然有 `KeywordManager` 模組可以讀取這些檔案,但在訓練資料時並未將關鍵字寫入資料庫,導致:
1. 無法追蹤哪些文件包含哪些關鍵字
2. 無法基於關鍵字進行精準過濾
3. 搜尋時無法利用關鍵字增強檢索

### ✅ 解決方案

**✅ 方案 B: 建立獨立的 document_keywords 關聯表** (已選擇)
- 優點:結構化,支援複雜查詢,可統計關鍵字出現頻率,符合正規化原則
- 缺點:需要多表 JOIN(但效能影響不大,可透過索引優化)

### 🔧 實作步驟

#### 1.1 擴展資料庫 Schema
修改檔案:`core/database/schema.py`

```python
# 新增關鍵字關聯表
CREATE TABLE IF NOT EXISTS document_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL,
    category TEXT NOT NULL,      -- 類別:產品/Defect Code/機台/站點/廠別
    keyword TEXT NOT NULL,        -- 關鍵字值
    confidence REAL DEFAULT 1.0,  -- 信心度(AI 提取時使用)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(doc_id, category, keyword)
);

-- 建立索引以加速查詢
CREATE INDEX IF NOT EXISTS idx_doc_keywords_doc_id ON document_keywords(doc_id);
CREATE INDEX IF NOT EXISTS idx_doc_keywords_category ON document_keywords(category);
CREATE INDEX IF NOT EXISTS idx_doc_keywords_keyword ON document_keywords(keyword);
```

#### 1.2 新增資料庫操作函數
新增檔案:`core/database/keyword_ops.py`

```python
def save_document_keywords(doc_id: int, keywords: Dict[str, List[str]]):
    """儲存文件關鍵字"""
    
def get_document_keywords(doc_id: int) -> Dict[str, List[str]]:
    """取得文件的所有關鍵字"""
    
def search_by_keywords(filters: Dict[str, str]) -> List[int]:
    """根據關鍵字過濾查詢文件 ID"""
```

#### 1.3 整合到 Ingestion 流程
修改檔案:`core/ingestion_v3.py`

在 `process_document_v3` 函數中:
1. 使用 AI 從文件內容中提取關鍵字(產品名、Defect Code 等)
2. 與 `keyword_mappings` 中的標準關鍵字進行匹配
3. 呼叫 `save_document_keywords` 儲存到資料庫

#### 1.4 整合到搜尋流程
修改檔案:`core/search/query_router.py`

在 `universal_search` 函數中:
- 支援 `filters` 參數傳入關鍵字篩選條件
- 先用 `search_by_keywords` 取得符合的 doc_id 清單
- 在 vector/hybrid search 時限定只搜尋這些文件

---

## 問題 2: Troubleshooting 被切成 6 個獨立 Chunks

### 📋 問題分析

目前 `TroubleshootingParser` 將 8D 格式的 6 個欄位切成 6 個獨立的 chunk:
1. Problem issue & loss
2. Problem description
3. Analysis root cause
4. Containment action
5. Corrective action
6. Preventive action

**問題:**
- 每個 chunk 獨立檢索時缺乏上下文
- 使用者詢問完整解決方案時,只能取得部分資訊
- Top-K 限制導致無法取得同一份報告的所有欄位

### ✅ 解決方案

**將 6 個欄位合併為單一 Chunk,但在 metadata 中保留欄位結構**

優點:
- 保持資訊完整性
- 檢索時能取得完整的 8D 報告
- metadata 仍保留結構化資訊供後續處理

### 🔧 實作步驟

#### 2.1 修改 TroubleshootingParser
修改檔案:`core/parsers/troubleshooting_parser.py`

```python
def parse(self, raw_data: str) -> List[Dict]:
    # ... (AI 分析獲得 extracted 字典)
    
    # 生成整合的 Markdown 內容
    md_content = self._generate_8d_markdown(extracted)
    
    # 回傳單一 chunk,但保留結構化 metadata
    return [{
        'type': 'troubleshooting_full',
        'title': extracted.get('Problem issue & loss', '異常報告'),
        'content': md_content,  # 完整的 Markdown 格式
        'metadata': {
            'fields': extracted,  # 保留所有欄位
            'yield_loss': self._extract_yield_loss(extracted),
            'product': self._extract_product(extracted),
            'defect_code': self._extract_defect_code(extracted)
        }
    }]

def _generate_8d_markdown(self, data: Dict) -> str:
    """生成 8D 格式的 Markdown"""
    md = []
    md.append(f"# 【8D 異常報告】{data.get('Problem issue & loss', '')}\n")
    
    for field in self.STANDARD_FIELDS:
        if field in data:
            md.append(f"## {field}\n")
            md.append(f"{data[field]}\n")
    
    return "\n".join(md)
```

#### 2.2 更新資料庫 Schema
確保 `chunks` 表的 `metadata` 欄位(JSON 類型)能儲存結構化的欄位資訊。

---

## 問題 3: Troubleshooting 精準查詢未直接提供步驟

### 📋 問題分析

目前詢問 Troubleshooting 時,即使使用者精準問到「產品 + Defect Code」,系統仍然:
1. 進行語義搜尋
2. 可能返回不夠精準的結果
3. 沒有直接提供 8D 格式的完整報告和 .md 下載

**需求:**
- 類似 SOP 查詢,當精準匹配到產品+Defect Code 時,直接提供訓練好的 8D 報告
- 提供 Markdown 檔案下載

### ✅ 解決方案

**在 query_router 中新增 Troubleshooting 精準匹配邏輯**

### 🔧 實作步驟

#### 3.1 在 query_router 新增精準匹配函數
修改檔案:`core/search/query_router.py`

```python
def _try_exact_troubleshooting_match(query: str, filters: Dict) -> Optional[Dict]:
    """
    嘗試精準匹配 Troubleshooting 文件
    
    條件:
    1. filters 中有 product 和 defect_code
    2. 或從 query 中可以解析出產品和 Defect Code
    
    Returns:
        找到則回傳完整的 8D 報告,否則回傳 None
    """
    product = filters.get('product')
    defect_code = filters.get('defect_code')
    
    if not (product and defect_code):
        # 嘗試從 query 解析
        product, defect_code = _parse_product_defect(query)
    
    if product and defect_code:
        # 從 document_keywords 精準查詢
        results = database.query("""
            SELECT DISTINCT d.id, d.filename, c.content, c.metadata
            FROM documents d
            JOIN chunks c ON c.doc_id = d.id
            JOIN document_keywords k1 ON k1.doc_id = d.id
            JOIN document_keywords k2 ON k2.doc_id = d.id
            WHERE d.doc_type = 'troubleshooting'
              AND k1.category = 'product' AND k1.keyword = ?
              AND k2.category = 'Defect Code' AND k2.keyword = ?
              AND c.type = 'troubleshooting_full'
        """, (product, defect_code))
        
        if results:
            return {
                'exact_match': True,
                'content': results[0]['content'],
                'metadata': results[0]['metadata'],
                'filename': results[0]['filename']
            }
    
    return None
```

#### 3.2 整合到 universal_search
```python
def universal_search(...):
    # 在進行 vector search 之前,先嘗試精準匹配
    if doc_type == 'troubleshooting' or query_type == 'troubleshooting':
        exact_match = _try_exact_troubleshooting_match(query, filters)
        if exact_match:
            return {
                'results': [exact_match],
                'strategy': 'exact_match',
                'intent': QueryIntent.TROUBLESHOOTING,
                'mode': 'direct'  # 標記為直接回傳模式
            }
    
    # 否則執行一般搜尋流程
    ...
```

#### 3.3 修改 Chat App 處理邏輯
修改檔案:`chat_app.py`

在接收到搜尋結果後:
```python
if search_result.get('mode') == 'direct':
    # 直接回傳,不經過 GPT 總結
    exact_result = search_result['results'][0]
    response = exact_result['content']
    
    # 提供下載按鈕
    st.download_button(
        label="📥 下載 8D 報告",
        data=response,
        file_name=f"{exact_result.get('filename', '8D_report')}.md",
        mime="text/markdown"
    )
```

---

## 問題 4: SOP 查詢會經過 GPT 總結浪費 Token

### 📋 問題分析

目前詢問 SOP 時:
1. 搜尋返回完整的步驟內容
2. 系統再把步驟丟給 GPT 做總結
3. 理論上應該只消耗 embedding token,但實際上還消耗了 GPT completion token

**原因分析:**
可能在 `chat_app.py` 或 `query_router.py` 的後處理中,對所有結果都進行了 GPT 總結。

### ✅ 解決方案

**對 SOP 類型的查詢,直接回傳檢索結果,跳過 GPT 總結步驟**

### 🔧 實作步驟

#### 4.1 在搜尋結果中標記回傳模式
修改檔案:`core/search/query_router.py`

```python
def universal_search(...):
    ...
    
    # 判斷是否需要 GPT 總結
    need_gpt_summary = _should_use_gpt_summary(intent, doc_type, query_type)
    
    return {
        'results': results,
        'strategy': strategy,
        'intent': intent,
        'mode': 'direct' if not need_gpt_summary else 'summary'
    }

def _should_use_gpt_summary(intent, doc_type, query_type) -> bool:
    """判斷是否需要 GPT 總結"""
    # SOP 查詢直接回傳
    if intent == QueryIntent.PROCEDURAL or doc_type == 'procedure' or query_type == 'procedure':
        return False
    
    # Troubleshooting 精準匹配直接回傳
    if query_type == 'troubleshooting':
        return False
    
    # 其他情況需要總結
    return True
```

#### 4.2 修改 Chat App 的處理邏輯
修改檔案:`chat_app.py`

找到目前處理搜尋結果的部分(大約在 line 283-400):

```python
# 執行搜尋
search_result = universal_search(
    query=prompt,
    top_k=search_limit,
    doc_type=selected_types,
    query_type=query_type,
    filters=search_filters,
    ...
)

# 根據 mode 決定是否使用 GPT
if search_result.get('mode') == 'direct':
    # 直接回傳模式
    if search_result['results']:
        response = search_result['results'][0]['content']
        usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        
        st.markdown(response)
        st.caption("💡 本次使用: 0 tokens (直接回傳)")
        
        # 提供下載
        if 'filename' in search_result['results'][0]:
            st.download_button(...)
    else:
        response = "未找到相關資料"
        usage = {'total_tokens': 0}
else:
    # 原有的 GPT 總結流程
    context = "\n\n".join([r['content'] for r in search_result['results']])
    response = ai_core.generate_response(prompt, context, model=chat_model)
    usage = {...}
```

---

## 問題 5: Raw Data 是否需要保存

### 📋 問題分析

目前系統只儲存:
- 解析後的 chunks(embedding 向量 + 文字內容)
- 文件 metadata

**沒有保存原始文字內容**,導致:
1. 若資料庫升版(schema 變更),無法重新訓練
2. 若 AI 模型優化(更好的 chunking 策略),需要重新上傳原始檔案
3. 無法進行資料審計或除錯

### ✅ 解決方案

**在 documents 表新增 `raw_content` 欄位,儲存原始文字**

優點:
- 完整保留原始資料
- 支援重新訓練
- 方便除錯與審計

缺點:
- 增加資料庫大小(但相對於向量,文字壓縮率高)

> [!IMPORTANT]
> 建議保存 raw data,這是資料治理的最佳實踐

### 🔧 實作步驟

#### 5.1 擴展資料庫 Schema
修改檔案:`core/database/schema.py`

```sql
ALTER TABLE documents ADD COLUMN raw_content TEXT;
```

或在新建時直接包含:
```sql
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    ...
    raw_content TEXT,  -- 新增:原始文字內容
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 5.2 修改 document_ops
修改檔案:`core/database/document_ops.py`

在 `create_document_enhanced` 函數中新增參數:
```python
def create_document_enhanced(
    filename: str,
    doc_type: str,
    raw_content: str = None,  # 新增
    ...
):
    cursor.execute("""
        INSERT INTO documents 
        (filename, doc_type, raw_content, ...)
        VALUES (?, ?, ?, ...)
    """, (filename, doc_type, raw_content, ...))
```

#### 5.3 修改 Ingestion 流程
修改檔案:`core/ingestion_v3.py`

在 `process_document_v3` 中:
```python
# 讀取原始內容
raw_content = _read_file_content_v3(file_path)

# 建立文件記錄時傳入 raw_content
doc_id = database.create_document_enhanced(
    filename=Path(file_path).name,
    doc_type=doc_type,
    raw_content=raw_content,  # 儲存原始內容
    ...
)
```

#### 5.4 實作重新訓練函數
新增檔案:`core/retraining.py`

```python
def retrain_all_documents(doc_type: str = None):
    """
    從 raw_content 重新訓練文件
    
    Args:
        doc_type: 限定文件類型,None 表示全部重新訓練
    """
    # 1. 取得所有文件
    docs = database.get_all_documents(doc_type=doc_type)
    
    for doc in docs:
        if not doc['raw_content']:
            logger.warning(f"文件 {doc['filename']} 無原始內容,跳過")
            continue
        
        # 2. 刪除舊的 chunks 和 embeddings
        database.delete_chunks_by_doc_id(doc['id'])
        
        # 3. 重新解析與 embedding
        # 相當於重新執行 ingestion,但直接從 raw_content 讀取
        process_raw_content(
            doc_id=doc['id'],
            raw_content=doc['raw_content'],
            doc_type=doc['doc_type']
        )
```

---

## 驗證計劃

### 測試案例

#### 測試 1: 關鍵字整合
1. 上傳包含「產品: N706」的 troubleshooting 文件
2. 檢查 `document_keywords` 表是否正確記錄
3. 使用 `filters={'product': 'N706'}` 搜尋,驗證能精準過濾

#### 測試 2: Troubleshooting 單一 Chunk
1. 上傳 8D 報告
2. 檢查是否只產生 1 個 chunk(而非 6 個)
3. 檢查 chunk 的 metadata 是否包含完整欄位結構
4. 搜尋並驗證能取得完整報告

#### 測試 3: Troubleshooting 精準匹配
1. 詢問:「N706 蝴蝶Mura 異常報告」
2. 驗證是否直接回傳 8D 報告(不經過 GPT)
3. 檢查是否提供 .md 下載

#### 測試 4: SOP Token 優化
1. 詢問 SOP:「黃光站點操作步驟」
2. 檢查 token 統計,completion_tokens 應為 0
3. 驗證直接回傳步驟內容

#### 測試 5: Raw Data 保存
1. 上傳文件後,檢查 `documents.raw_content` 欄位
2. 修改 chunking 策略
3. 呼叫 `retrain_all_documents()` 並驗證重新訓練成功

### 效能指標

- **關鍵字查詢速度**: 應在 100ms 內
- **Token 節省率**: SOP 查詢應節省 80%+ completion tokens
- **精準匹配準確率**: Troubleshooting 精準匹配應達 95%+
- **資料庫大小**: raw_content 增加的大小應 < 原始檔案大小的 50%(因文字壓縮)
