# AI Agent 知識庫系統 v1.5.0 - API 使用文檔

## 概述

AI Agent 知識庫系統 v1.5.0 提供了強大的智慧搜尋和文件管理功能。本文檔介紹如何使用核心 API。

---

## 核心模組

### 1. 搜尋模組 (`core.search`)

#### 1.1 通用查詢引擎 (推薦使用)

```python
from core.search import universal_search

# 基本使用
result = universal_search(
    query="N706 蝴蝶Mura 問題",
    top_k=10
)

# 進階使用 (指定類型與策略)
result = universal_search(
    query="如何更換濾心",
    query_type="procedure",  # 明確指定查詢類型 (general, troubleshooting, procedure, knowledge)
    auto_strategy=True,      # 讓系統自動選擇最佳策略
    filters={"station": "黃光"}, # 結構化過濾條件
    top_k=5
)

# 結果結構
{
    'query': str,              # 原始查詢
    'intent': str,             # 查詢意圖 (factual/procedural/troubleshooting/comparative/document_lookup)
    'strategy': str,           # 使用的策略 (vector/keyword/hybrid/document_name/semantic_deep)
    'results': List[Dict],     # 搜尋結果列表
    'meta': {
        'total_found': int,    # 找到的總數
        'search_time': float,  # 搜尋時間(秒)
        'confidence': float,   # 信心度 (0-1)
        'skip_llm': bool       # 是否建議跳過 LLM 直接顯示內容 (直讀模式)
    }
}
```

**查詢意圖類型 (Intent)**:
- `factual`: 事實查詢 (例: "什麼是...")
- `procedural`: 步驟查詢 (例: "如何...")
- `troubleshooting`: 問題排查 (例: "為什麼...、怎麼修...")
- `comparative`: 比較查詢 (例: "A和B的差異")
- `document_lookup`: 文件查找 (例: "找到XX文件")

**搜尋策略 (Strategy)**:
- `vector`: 純向量搜尋 (語意理解)
- `keyword`: 純關鍵字搜尋 (精確匹配)
- `hybrid`: 混合搜尋 (向量+關鍵字)
- `document_name`: 檔名優先搜尋
- `semantic_deep`: 深度語意搜尋 (向量 + AI 重排序)

#### 1.2 其他搜尋函數

```python
from core.search import (
    hybrid_search,        # 混合搜尋
    search_by_vector,     # 純向量搜尋
    search_documents_v2,  # 關鍵字搜尋
    semantic_rerank,      # 語意重排序
    expand_query          # 查詢擴展
)

# 混合搜尋
results = hybrid_search(
    query="ITO issue",
    top_k=5,
    api_key="your-api-key"
)

# 語意重排序
reranked = semantic_rerank(
    results=search_results,
    query="N706 問題"
)

# 查詢擴展
expanded_queries = expand_query(
    query="如何安裝",
    max_variants=3
)
# 返回: ["如何安裝", "安裝步驟", "安裝流程"]
```

---

### 2. 資料庫模組 (`core.database`)

#### 2.1 文件操作

```python
from core.database import (
    create_document_enhanced,  # 創建文件 (增強版)
    get_document,              # 取得文件
    get_document_by_hash,      # 根據 hash 取得文件
    update_document,           # 更新文件
    delete_document,           # 刪除文件
    increment_access_count     # 增加訪問次數
)

# 創建文件 (增強版)
doc_id = create_document_enhanced(
    filename="N706_蝴蝶Mura.pptx",
    doc_type="Troubleshooting",
    category="Display",
    tags='["Mura", "蝴蝶", "品質"]',
    file_hash="abc123...",
    summary="蝴蝶狀 Mura 缺陷分析報告",
    priority=5
)

# 根據 hash 檢查文件是否已存在
existing_doc = get_document_by_hash("abc123...")
if existing_doc:
    print(f"文件已存在: {existing_doc['filename']}")

# 增加訪問次數
increment_access_count(doc_id)
```

#### 2.2 向量操作

```python
from core.database import (
    save_chunk_embedding,  # 儲存 chunk 和向量
    get_chunks_by_doc_id   # 取得文件的所有 chunks
)

# 儲存 chunk
save_chunk_embedding(
    doc_id=1,
    source_type="slide",
    title="問題描述",
    content="蝴蝶狀的 Mura 缺陷...",
    embedding=embedding_vector,
    keywords="Mura,蝴蝶,品質"
)

# 取得文件的所有 chunks
chunks = get_chunks_by_doc_id(doc_id=1)
```

#### 2.3 搜尋歷史

```python
from core.database import log_search_history

# 記錄搜尋歷史
log_search_history(
    query="N706 蝴蝶Mura",
    intent="troubleshooting",
    strategy="hybrid",
    result_count=5,
    search_time=0.35
)
```

---

### 3. 文件處理模組 (`core.ingestion_v3`)

```python
from core.ingestion_v3 import process_document_v3

# 處理文件 (自動提取元數據)
result = process_document_v3(
    file_path="path/to/document.pptx", # 支援 pptx, pdf, md, txt
    doc_type="Troubleshooting",
    auto_extract_metadata=True,  # 使用 AI 提取元數據
    category="Display",
    department="製造部",
    factory="台中廠",
    priority=5
)

# 結果
{
    'success': True,
    'doc_id': 123,
    'chunks': 15,
    'message': '成功處理 document.pptx'
}
```

---

### 4. 元數據提取模組 (`core.metadata_extractor`)

```python
from core.metadata_extractor import (
    calculate_file_hash,
    extract_document_metadata
)

# 計算檔案 hash
file_hash = calculate_file_hash("path/to/file.pptx")

# 提取元數據
metadata = extract_document_metadata(
    content="文件內容...",
    doc_type="Troubleshooting"
)

# 返回
{
    'summary': "一段式摘要...",
    'key_points': '["重點1", "重點2"]',
    'category': "Display",
    'tags': '["Mura", "品質"]',
    'language': "zh-TW"
}
```

---

## 完整範例

### 範例 1: 上傳並處理新文件 (含 PDF)

```python
from core.ingestion_v3 import process_document_v3

# 上傳 PDF 文件
result = process_document_v3(
    file_path="D:/documents/Spec_Sheet.pdf",
    doc_type="Knowledge",
    auto_extract_metadata=True,
    department="研發部",
    priority=8
)

if result['success']:
    print(f"✅ 文件處理成功!")
    print(f"   文件 ID: {result['doc_id']}")
    print(f"   切片數: {result['chunks']}")
```

### 範例 2: 智慧搜尋

```python
from core.search import universal_search

# 執行智慧搜尋
result = universal_search(
    query="如何解決蝴蝶 Mura 問題",
    top_k=5
)

print(f"查詢意圖: {result['intent']}")
print(f"搜尋策略: {result['strategy']}")
print(f"搜尋時間: {result['meta']['search_time']:.2f}秒")
print(f"信心度: {result['meta']['confidence']:.0%}")
print(f"\n找到 {len(result['results'])} 筆結果:")

for i, doc in enumerate(result['results'], 1):
    print(f"{i}. {doc['file_name']}")
```

---

## 最佳實踐

### 1. 搜尋優化

- **使用 `universal_search`**: 自動選擇最佳策略，無需手動判斷。
- **適當的 `top_k`**: 一般查詢使用 5-10，深度研究使用 20+。
- **利用查詢意圖**: 根據返回的 `intent` 調整 UI 顯示。

### 2. 文件上傳

- **啟用元數據提取**: `auto_extract_metadata=True` 可大幅提升搜尋準確度。
- **檢查重複**: 使用 `get_document_by_hash()` 避免重複上傳。
- **設定優先級**: 重要文件設定較高的 `priority` 值。

### 3. 效能優化

- **批次處理**: 使用 `process_directory_v3()` 批次處理多個文件。
- **限制內容長度**: 元數據提取時限制內容長度避免 token 過多。
- **使用索引**: 資料庫已建立索引，查詢時善用 `category`, `status` 等欄位。

---

## 版本歷史

- **v1.5.0** (2026-02): 通用查詢引擎、智慧元數據提取、資料庫結構增強、PDF 支援
