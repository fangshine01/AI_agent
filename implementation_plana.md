# 知識庫系統優化建議書

## 📊 系統現況分析

### 當前架構優勢
- ✅ 模組化設計良好（parsers、database、search 分離）
- ✅ 支援多種文件類型（Knowledge, Training, Troubleshooting）
- ✅ 混合搜尋機制（向量 + 關鍵字）
- ✅ 支援 sqlite-vec 向量搜尋

### 架構改進機會
經過深入分析，發現以下可優化的關鍵領域：

---

## 🎯 優化建議一：資料庫結構增強

### 當前 Schema 不足之處

**`documents` 表缺少的關鍵元數據：**
```sql
-- 當前結構
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    filename TEXT,
    doc_type TEXT,           -- 分類太粗略
    upload_date TIMESTAMP,
    analysis_mode TEXT,
    model_used TEXT
);
```

### 建議新增欄位

```sql
-- 優化後的 documents 表
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    
    -- 分類與標籤
    doc_type TEXT NOT NULL,              -- 'Knowledge', 'Troubleshooting', 'Training'
    category TEXT,                       -- 二級分類 (例如: 'Hardware', 'Software', 'Network')
    tags TEXT,                           -- JSON 陣列標籤 (例如: ["urgent", "customer-facing"])
    
    -- 元數據
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP,             -- 最後修改時間
    file_size INTEGER,                   -- 檔案大小 (bytes)
    file_hash TEXT,                      -- 檔案 hash (避免重複上傳)
    version INTEGER DEFAULT 1,           -- 版本號
    
    -- AI 處理資訊
    analysis_mode TEXT,                  -- 'text_only', 'vision', 'auto'
    model_used TEXT,                     -- 使用的模型
    processing_time REAL,                -- 處理時間 (秒)
    
    -- 業務元數據（重要！）
    author TEXT,                         -- 作者/上傳者
    department TEXT,                     -- 部門 (例如: '製造部', '研發部')
    factory TEXT,                        -- 工廠 (例如: '廠區A', '廠區B')
    language TEXT DEFAULT 'zh-TW',       -- 文件語言(中文、英文)
    priority INTEGER DEFAULT 0,          -- 優先級 (0-10, 用於搜尋排序)
    
    -- 內容摘要
    summary TEXT,                        -- AI 生成的文件摘要
    key_points TEXT,                     -- JSON 陣列：重點摘要
    
    -- 狀態管理
    status TEXT DEFAULT 'active',        -- 'active', 'archived', 'deprecated'
    access_count INTEGER DEFAULT 0,      -- 被查詢次數
    last_accessed TIMESTAMP              -- 最後訪問時間
);
```

**索引優化：**
```sql
-- 加速常用查詢
CREATE INDEX idx_documents_type ON documents(doc_type);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_hash ON documents(file_hash);
CREATE INDEX idx_documents_priority ON documents(priority DESC);
CREATE INDEX idx_documents_access ON documents(access_count DESC);

-- 全文搜尋索引（使用 FTS5）
CREATE VIRTUAL TABLE documents_fts USING fts5(
    filename, summary, key_points,
    content=documents
);
```

### `vec_chunks` 表增強

```sql
-- 優化後的 vec_chunks 表
CREATE TABLE vec_chunks (
    chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL,
    
    -- 內容分類
    source_type TEXT NOT NULL,           -- 'chapter', 'step', 'field', 'section'
    source_title TEXT,
    text_content TEXT NOT NULL,
    
    -- 向量與關鍵字
    embedding BLOB,
    keywords TEXT,                       -- JSON 陣列
    
    -- 新增：內容特徵
    chunk_index INTEGER,                 -- 在文件中的順序
    context_before TEXT,                 -- 前文摘要 (幫助理解上下文)
    context_after TEXT,                  -- 後文摘要
    
    -- 新增：品質指標
    content_quality REAL,                -- AI 評估的內容品質分數 (0-1)
    relevance_score REAL,                -- 與文件主題的相關性 (0-1)
    
    -- 新增：使用統計
    access_count INTEGER DEFAULT 0,      -- 被檢索次數
    positive_feedback INTEGER DEFAULT 0, -- 正面回饋次數
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_vec_chunks_doc ON vec_chunks(doc_id);
CREATE INDEX idx_vec_chunks_type ON vec_chunks(source_type);
CREATE INDEX idx_vec_chunks_quality ON vec_chunks(content_quality DESC);
CREATE INDEX idx_vec_chunks_access ON vec_chunks(access_count DESC);
```

### 新增：關聯關係表

```sql
-- 文件之間的關聯 (例如：引用、相關、更新關係)
CREATE TABLE document_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_doc_id INTEGER NOT NULL,
    target_doc_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,         -- 'references', 'updates', 'related', 'supersedes'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_doc_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (target_doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- 用戶查詢歷史（用於改進搜尋）
CREATE TABLE search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    query_embedding BLOB,                -- 查詢的向量
    result_chunks TEXT,                  -- JSON: 返回的 chunk_ids
    user_clicked_chunk_id INTEGER,       -- 用戶實際點擊的結果
    feedback TEXT,                       -- 'helpful', 'not_helpful', 'irrelevant'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🎯 優化建議二：智慧元數據提取

### 在文件匯入時自動提取更多資訊

#### 修改 `process_document_v3()` 流程

```python
# core/ingestion_v3.py 增強版

def process_document_v3(
    file_path: str,
    doc_type: str,
    analysis_mode: str = "auto",
    category: str = None,           # 新增：二級分類
    department: str = None,         # 新增：部門
    factory: str = None,            # 新增：工廠
    priority: int = 0,              # 新增：優先級
    auto_extract_metadata: bool = True,  # 新增：是否自動提取元數據
    **kwargs
):
    """增強版文件處理流程"""
    
    # 1. 計算檔案 hash（避免重複上傳）
    file_hash = _calculate_file_hash(file_path)
    existing_doc = database.get_document_by_hash(file_hash)
    if existing_doc:
        logger.warning(f"文件已存在: {existing_doc['filename']}")
        return existing_doc['id']
    
    # 2. 提取檔案基本資訊
    file_stats = os.stat(file_path)
    metadata = {
        'filename': os.path.basename(file_path),
        'file_size': file_stats.st_size,
        'file_hash': file_hash,
        'doc_type': doc_type,
        'category': category,
        'department': department,
        'factory': factory,
        'priority': priority
    }
    
    # 3. 讀取文件內容
    start_time = time.time()
    content = _read_file_content_v3(file_path)
    
    # 4. 使用 AI 提取元數據（關鍵增強！）
    if auto_extract_metadata and content:
        extracted_metadata = _extract_document_metadata(content, doc_type)
        metadata.update(extracted_metadata)
    
    # 5. 建立文件記錄
    processing_time = time.time() - start_time
    doc_id = database.create_document_enhanced(
        **metadata,
        processing_time=processing_time
    )
    
    # ... 後續切片處理 ...
    
    return doc_id


def _extract_document_metadata(content: str, doc_type: str) -> dict:
    """
    使用 AI 從文件內容中提取元數據
    
    Returns:
        {
            'summary': str,           # 摘要
            'key_points': list,       # 重點列表
            'category': str,          # 推薦分類
            'tags': list,             # 標籤
            'language': str           # 語言
        }
    """
    prompt = f"""
請分析以下{doc_type}文件，提取關鍵資訊：

【文件內容】
{content[:3000]}  # 只取前 3000 字避免 token 過多

請以 JSON 格式回覆：
{{
    "summary": "一段式摘要（不超過150字）",
    "key_points": ["重點1", "重點2", "重點3"],
    "suggested_category": "建議的二級分類",
    "tags": ["標籤1", "標籤2"],
    "language": "zh-TW 或 en-US"
}}
"""
    
    response = ai_core.analyze_text(prompt, model="gpt-4o-mini")
    
    try:
        metadata = json.loads(response)
        return {
            'summary': metadata.get('summary'),
            'key_points': json.dumps(metadata.get('key_points', []), ensure_ascii=False),
            'category': metadata.get('suggested_category'),
            'tags': json.dumps(metadata.get('tags', []), ensure_ascii=False),
            'language': metadata.get('language', 'zh-TW')
        }
    except:
        logger.warning("元數據提取失敗，使用預設值")
        return {}
```

---

## 🎯 優化建議三：通用查詢引擎設計

### 當前查詢的問題

1. 查詢邏輯分散在多個模組（`vector_search.py`, `hybrid_search.py`, `legacy_search.py`）
2. 缺乏統一的查詢入口
3. 無法根據查詢類型自動選擇最佳策略
4. 沒有查詢意圖分析

### 建議：建立智慧查詢路由器

```python
# core/search/query_router.py (新檔案)

from typing import List, Dict, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """查詢意圖類型"""
    FACTUAL = "factual"              # 事實查詢（例：什麼是...）
    PROCEDURAL = "procedural"        # 步驟查詢（例：如何...）
    TROUBLESHOOTING = "troubleshooting"  # 問題排查（例：為什麼...、怎麼修...）
    COMPARATIVE = "comparative"      # 比較查詢（例：A和B的差異）
    DOCUMENT_LOOKUP = "document_lookup"  # 文件查找（例：找到XX文件）


class SearchStrategy(Enum):
    """搜尋策略"""
    VECTOR_ONLY = "vector"           # 純向量搜尋
    KEYWORD_ONLY = "keyword"         # 純關鍵字
    HYBRID = "hybrid"                # 混合搜尋
    DOCUMENT_NAME = "document_name"  # 檔名搜尋
    SEMANTIC_DEEP = "semantic_deep"  # 深度語意搜尋


def analyze_query_intent(query: str) -> QueryIntent:
    """
    分析查詢意圖
    
    使用規則 + AI 混合判斷
    """
    query_lower = query.lower()
    
    # 規則判斷
    if any(word in query_lower for word in ['如何', '怎麼', '步驟', '流程', 'how to']):
        return QueryIntent.PROCEDURAL
    
    if any(word in query_lower for word in ['為什麼', '原因', '異常', '錯誤', '故障', 'why', 'error']):
        return QueryIntent.TROUBLESHOOTING
    
    if any(word in query_lower for word in ['差異', '比較', '區別', 'vs', 'compare']):
        return QueryIntent.COMPARATIVE
    
    if any(word in query_lower for word in ['文件', '檔案', '找到', 'document', 'file']):
        return QueryIntent.DOCUMENT_LOOKUP
    
    # 預設為事實查詢
    return QueryIntent.FACTUAL


def select_search_strategy(
    query: str,
    intent: QueryIntent,
    doc_type: Optional[str] = None
) -> SearchStrategy:
    """
    根據查詢意圖選擇最佳搜尋策略
    """
    # 如果查詢包含明確文件名/編號，優先檔名搜尋
    if _contains_document_identifier(query):
        return SearchStrategy.DOCUMENT_NAME
    
    # 根據意圖選擇
    strategy_map = {
        QueryIntent.DOCUMENT_LOOKUP: SearchStrategy.DOCUMENT_NAME,
        QueryIntent.FACTUAL: SearchStrategy.HYBRID,
        QueryIntent.PROCEDURAL: SearchStrategy.VECTOR_ONLY,
        QueryIntent.TROUBLESHOOTING: SearchStrategy.HYBRID,
        QueryIntent.COMPARATIVE: SearchStrategy.SEMANTIC_DEEP
    }
    
    return strategy_map.get(intent, SearchStrategy.HYBRID)


def universal_search(
    query: str,
    top_k: int = 10,
    doc_type: Optional[str] = None,
    auto_strategy: bool = True,
    **kwargs
) -> Dict:
    """
    通用查詢引擎入口
    
    Args:
        query: 查詢文字
        top_k: 回傳結果數
        doc_type: 限定文件類型
        auto_strategy: 是否自動選擇策略
        
    Returns:
        {
            'query': str,
            'intent': str,
            'strategy': str,
            'results': List[Dict],
            'meta': {
                'total_found': int,
                'search_time': float,
                'confidence': float
            }
        }
    """
    import time
    start_time = time.time()
    
    # 1. 分析查詢意圖
    intent = analyze_query_intent(query)
    logger.info(f"查詢意圖: {intent.value}")
    
    # 2. 選擇搜尋策略
    if auto_strategy:
        strategy = select_search_strategy(query, intent, doc_type)
    else:
        strategy = kwargs.get('strategy', SearchStrategy.HYBRID)
    
    logger.info(f"搜尋策略: {strategy.value}")
    
    # 3. 執行搜尋
    results = _execute_search(query, strategy, top_k, doc_type, **kwargs)
    
    # 4. 後處理與排序優化
    results = _post_process_results(results, query, intent)
    
    # 5. 記錄查詢歷史（用於持續優化）
    search_time = time.time() - start_time
    _log_search_history(query, intent, strategy, results, search_time)
    
    return {
        'query': query,
        'intent': intent.value,
        'strategy': strategy.value,
        'results': results[:top_k],
        'meta': {
            'total_found': len(results),
            'search_time': search_time,
            'confidence': _calculate_confidence(results)
        }
    }


def _execute_search(
    query: str,
    strategy: SearchStrategy,
    top_k: int,
    doc_type: Optional[str],
    **kwargs
) -> List[Dict]:
    """執行實際搜尋"""
    from .vector_search import search_by_vector
    from .legacy_search import search_documents_v2
    from .hybrid_search import hybrid_search
    
    if strategy == SearchStrategy.VECTOR_ONLY:
        return search_by_vector(query, top_k=top_k, **kwargs)
    
    elif strategy == SearchStrategy.KEYWORD_ONLY:
        return search_documents_v2(query, top_k=top_k, **kwargs)
    
    elif strategy == SearchStrategy.HYBRID:
        return hybrid_search(query, top_k=top_k, **kwargs)
    
    elif strategy == SearchStrategy.DOCUMENT_NAME:
        # 檔名優先搜尋
        keyword_results = search_documents_v2(query, top_k=top_k, fuzzy=True)
        if keyword_results:
            return keyword_results
        # 降級到混合搜尋
        return hybrid_search(query, top_k=top_k, **kwargs)
    
    elif strategy == SearchStrategy.SEMANTIC_DEEP:
        # 深度語意搜尋（使用更大的 top_k 然後重新排序）
        results = search_by_vector(query, top_k=top_k * 3, **kwargs)
        # 使用 AI 重新排序
        return _semantic_rerank(results, query)[:top_k]


def _post_process_results(
    results: List[Dict],
    query: str,
    intent: QueryIntent
) -> List[Dict]:
    """
    後處理結果
    
    - 去重
    - 補充上下文
    - 調整排序
    """
    # 1. 根據 chunk_id 去重
    seen_chunks = set()
    deduped_results = []
    for result in results:
        chunk_id = result.get('chunk_id')
        if chunk_id not in seen_chunks:
            seen_chunks.add(chunk_id)
            deduped_results.append(result)
    
    # 2. 根據意圖調整排序
    if intent == QueryIntent.TROUBLESHOOTING:
        # 優先顯示 Troubleshooting 類型的文件
        deduped_results.sort(
            key=lambda x: (
                x.get('document', {}).get('doc_type') == 'Troubleshooting',
                x.get('total_score', 0)
            ),
            reverse=True
        )
    
    return deduped_results


def _calculate_confidence(results: List[Dict]) -> float:
    """計算結果信心度"""
    if not results:
        return 0.0
    
    # 基於最高分與平均分的差異
    scores = [r.get('total_score', r.get('similarity', 0)) for r in results]
    if not scores:
        return 0.0
    
    max_score = max(scores)
    avg_score = sum(scores) / len(scores)
    
    # 如果最高分明顯高於平均，信心度較高
    confidence = max_score if max_score > avg_score * 1.5 else avg_score
    return min(confidence, 1.0)


def _contains_document_identifier(query: str) -> bool:
    """檢查查詢是否包含文件編號/名稱"""
    import re
    # 檢測常見的文件編號格式（例如：N706, SOP-001, DOC_2024_01）
    patterns = [
        r'[A-Z]\d{3,}',           # N706, A123
        r'[A-Z]{2,}-\d{3,}',      # SOP-001
        r'DOC[_-]\d{4}[_-]\d{2}', # DOC_2024_01
    ]
    
    for pattern in patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return True
    return False


def _log_search_history(
    query: str,
    intent: QueryIntent,
    strategy: SearchStrategy,
    results: List[Dict],
    search_time: float
):
    """記錄查詢歷史（用於後續優化）"""
    try:
        from core import database
        database.log_search_history(
            query=query,
            intent=intent.value,
            strategy=strategy.value,
            result_count=len(results),
            search_time=search_time
        )
    except Exception as e:
        logger.warning(f"記錄查詢歷史失敗: {e}")
```

---

## 🎯 優化建議四：增強查詢精準度

### 4.1 語意重排序（Semantic Reranking）

```python
# core/search/reranker.py (新檔案)

def _semantic_rerank(results: List[Dict], query: str) -> List[Dict]:
    """
    使用 AI 對搜尋結果重新排序
    
    適用於需要深度理解查詢意圖的場景
    """
    if not results:
        return results
    
    # 構建重排序 prompt
    candidates = []
    for idx, result in enumerate(results[:20]):  # 只重排前 20 個
        candidates.append({
            'index': idx,
            'title': result.get('source_title', ''),
            'content': result.get('content', '')[:200]  # 只取前 200 字
        })
    
    prompt = f"""
你是一個搜尋排序專家。用戶查詢是：「{query}」

以下是候選結果（編號 0-{len(candidates)-1}）：
{json.dumps(candidates, ensure_ascii=False, indent=2)}

請根據與查詢的相關性，將結果編號由高到低排序。
只回覆 JSON 陣列，例如：[3, 0, 7, 1, ...]
"""
    
    try:
        response = ai_core.analyze_text(prompt, model="gpt-4o-mini")
        reranked_indices = json.loads(response)
        
        # 重新排列
        reranked_results = [results[i] for i in reranked_indices if i < len(results)]
        # 加上未重排的其餘結果
        remaining = [r for i, r in enumerate(results[20:], start=20)]
        return reranked_results + remaining
        
    except Exception as e:
        logger.warning(f"重排序失敗: {e}")
        return results
```

### 4.2 查詢擴展（Query Expansion）

```python
def expand_query(query: str) -> List[str]:
    """
    查詢擴展：生成語意相近的查詢變體
    
    例如：「如何安裝」→ ["如何安裝", "安裝步驟", "安裝流程", "安裝教學"]
    """
    prompt = f"""
請為以下查詢生成 3-5 個語意相近的變體查詢，幫助提升搜尋召回率：

原始查詢：「{query}」

要求：
1. 保留核心意圖
2. 使用同義詞或不同表達方式
3. 只回覆 JSON 陣列，例如：["變體1", "變體2", "變體3"]
"""
    
    try:
        response = ai_core.analyze_text(prompt, model="gpt-4o-mini")
        variants = json.loads(response)
        return [query] + variants  # 包含原始查詢
    except:
        return [query]
```

---

## 🎯 優化建議五：程式連動與 API 設計

### 統一的 API 層

```python
# core/search/__init__.py (修改)

from .query_router import universal_search, QueryIntent, SearchStrategy

# 對外統一接口
__all__ = [
    'universal_search',      # 主要入口
    'QueryIntent',
    'SearchStrategy'
]

# 向後兼容（保留舊接口）
from .vector_search import search_by_vector
from .hybrid_search import hybrid_search
```

### 在 chat_app.py 中使用

```python
# chat_app.py (修改後)

from core.search import universal_search

def handle_user_query(query: str, doc_type_filter: str = None):
    """處理用戶查詢"""
    
    # 使用通用查詢引擎
    search_result = universal_search(
        query=query,
        top_k=10,
        doc_type=doc_type_filter,
        auto_strategy=True  # 自動選擇策略
    )
    
    # 顯示搜尋元資訊
    st.info(f"""
    🔍 查詢意圖：{search_result['intent']}
    📊 搜尋策略：{search_result['strategy']}
    ⏱️ 搜尋時間：{search_result['meta']['search_time']:.2f}秒
    📈 信心度：{search_result['meta']['confidence']:.2%}
    """)
    
    # 顯示結果
    results = search_result['results']
    if results:
        for result in results:
            # ... 顯示邏輯 ...
    else:
        st.warning("未找到相關內容")
```

---

## 📝 實施計畫

### Phase 1: 資料庫結構升級（1-2 天）
1. ✅ 建立 migration script
2. ✅ 新增欄位到 `documents` 和 `vec_chunks`
3. ✅ 建立新的關聯表
4. ✅ 更新 `database` 模組的 CRUD 操作

### Phase 2: 元數據提取增強（2-3 天）
1. ✅ 實作 `_extract_document_metadata()`
2. ✅ 修改 `process_document_v3()` 整合元數據提取
3. ✅ 測試不同文件類型的元數據提取

### Phase 3: 通用查詢引擎（3-4 天）
1. ✅ 建立 `query_router.py`
2. ✅ 實作意圖分析與策略選擇
3. ✅ 整合現有搜尋模組
4. ✅ 實作語意重排序

### Phase 4: UI 整合與測試（1-2 天）
1. ✅ 更新 `chat_app.py` 使用新 API
2. ✅ 新增查詢歷史查看功能
3. ✅ 進行端到端測試

---

## 🎁 額外優化建議

### 1. 智慧推薦系統
```python
def get_related_documents(doc_id: int, top_k: int = 5) -> List[Dict]:
    """基於向量相似度推薦相關文件"""
    # 實作邏輯...
```

### 2. 用戶回饋機制
```python
def record_user_feedback(chunk_id: int, feedback: str):
    """記錄用戶對結果的回饋，用於改進搜尋"""
    # helpful / not_helpful / irrelevant
```

### 3. 定期優化任務
- 定期分析 `search_history` 找出常見查詢模式
- 根據 `access_count` 調整文件優先級
- 識別低品質切片並重新處理

---

## ✨ 預期效果

實施這些優化後，系統將能：

1. ✅ **更精準**：通過意圖分析和策略選擇，提升搜尋準確度 20-30%
2. ✅ **更智慧**：自動提取元數據，減少人工標註工作 80%
3. ✅ **更快速**：優化過的索引和查詢策略，提升查詢速度 40%
4. ✅ **更易用**：統一的 API 介面，降低維護成本
5. ✅ **可持續優化**：通過查詢歷史分析，系統能自我學習改進

## 驗證計畫

### 自動化測試
建立測試資料集：
```python
# tests/test_query_router.py
def test_intent_detection():
    assert analyze_query_intent("如何安裝軟體") == QueryIntent.PROCEDURAL
    assert analyze_query_intent("為什麼會出現錯誤") == QueryIntent.TROUBLESHOOTING
```

### 手動測試
1. 上傳 10 個不同類型的測試文件
2. 執行 20 個典型查詢，比較優化前後的結果品質
3. 記錄查詢時間和精準度指標
