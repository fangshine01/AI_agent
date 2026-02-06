# 搜尋系統優化方案

## 問題分析

### 現象
從日誌可以看到：
```
2026-02-06 16:42:07,854 - core.search.legacy_search - WARNING - ❌ 無搜尋結果: 'N706 蝴蝶Mura.pptx  內容詳細解析'
```

### 根本原因
經過資料庫分析發現：

1. **資料確實存在**
   - 資料庫有 **3個N706相關文件**，包括 `N706 蝴蝶Mura.pptx`
   - 每個文件都有 6 個向量切片
   - keywords 欄位有完整的關鍵字資料

2. **關鍵字搜尋邏輯問題**
   - 當前搜尋使用完整查詢字串進行 `LIKE '%N706 蝴蝶Mura.pptx  內容詳細解析%'`
   - 沒有任何文件/內容包含這個**完整長字串**
   - 但單個關鍵字都能成功匹配：
     - "N706" → 3 個文件
     - "蝴蝶" → 1 個文件  
     - "Mura" → 1 個文件

3. **未利用已有資源**
   - `vec_chunks` 表的 `keywords` 欄位已有結構化關鍵字資料
   - 例如: `專案:N706,客戶:PTST,Defect Code:G Line Gap`
   - 目前搜尋完全沒有利用這個欄位

## 優化方案

### 方案 1: 查詢分詞 + 多關鍵字 OR 搜尋 (推薦)

**原理**: 將用戶查詢拆分成多個關鍵字，使用 OR 邏輯搜尋

**優點**:
- 大幅提高召回率
- 符合用戶實際搜尋習慣
- 可以根據匹配關鍵字數量排序

**實現方式**:

#### 1.1 創建分詞工具函數

新增 [`core/search/tokenizer.py`](file:///d:/Github/AI_agent/AI_agent_expert_system/core/search/tokenizer.py):

```python
import re
from typing import List, Set

def tokenize_query(query: str) -> List[str]:
    """
    將查詢字串分詞，提取有意義的關鍵字
    
    規則:
    1. 移除檔案副檔名 (.pptx, .pdf 等)
    2. 以空格、標點符號分割
    3. 過濾過短的詞 (< 2 字元)
    4. 過濾停用詞
    """
    # 移除副檔名
    query = re.sub(r'\.(pptx|pdf|xlsx|docx|txt)', '', query, flags=re.IGNORECASE)
    
    # 分詞: 以空格、逗號、句號等分割
    tokens = re.split(r'[\s,。、]+', query)
    
    # 停用詞表 (可根據實際情況擴充)
    stopwords = {'的', '了', '和', '與', '或', '在', '是', '有', '為', '以', '及',
                 '內容', '詳細', '解析', '說明', '介紹', '資料', '文件'}
    
    # 過濾
    keywords = []
    for token in tokens:
        token = token.strip()
        if len(token) >= 2 and token not in stopwords:
            keywords.append(token)
    
    return keywords
```

#### 1.2 修改 legacy_search.py

修改 [`_search_filename`](file:///d:/Github/AI_agent/AI_agent_expert_system/core/search/legacy_search.py#L15-L59) 和 [`_search_content_text`](file:///d:/Github/AI_agent/AI_agent_expert_system/core/search/legacy_search.py#L62-L115) 函數:

```python
def _search_filename_multi_keyword(
    cursor: sqlite3.Cursor,
    keywords: List[str],
    file_types: Optional[List[str]],
    top_k: int
) -> List[Dict]:
    """使用多關鍵字 OR 邏輯搜尋檔名"""
    
    # 建立多個 LIKE 條件 (OR 連接)
    like_conditions = ' OR '.join(['filename LIKE ?' for _ in keywords])
    params = [f'%{kw}%' for kw in keywords]
    
    type_condition = ""
    if file_types:
        placeholders = ','.join(['?'] * len(file_types))
        type_condition = f"AND doc_type IN ({placeholders})"
        params.extend(file_types)
    
    params.append(top_k)
    
    # 計算匹配分數
    sql = f"""
        SELECT 
            id,
            filename as file_name,
            doc_type as file_type,
            upload_date as upload_time,
            'File Match' as raw_content,
            'System' as author,
            (
                {' + '.join([f"(filename LIKE ? COLLATE NOCASE)" for _ in keywords])}
            ) as match_score
        FROM documents
        WHERE ({like_conditions})
        {type_condition}
        ORDER BY match_score DESC, upload_date DESC
        LIMIT ?
    """
    
    # 合併參數: LIKE 條件 + match_score 計算 + 類型過濾 + LIMIT
    all_params = [f'%{kw}%' for kw in keywords] * 2  # LIKE 和 match_score 各用一次
    if file_types:
        all_params.extend(file_types)
    all_params.append(top_k)
    
    cursor.execute(sql, all_params)
    # ... 處理結果
```

類似方式修改 `_search_content_text`。

### 方案 2: 利用 keywords 欄位進行精準搜尋

**原理**: 直接搜尋 `vec_chunks.keywords` 欄位

**優點**:
- 更精準，關鍵字已經提取好
- 搜尋速度快

**實現方式**:

新增搜尋階段在 [`search_documents_v2`](file:///d:/Github/AI_agent/AI_agent_expert_system/core/search/legacy_search.py#L118-L161):

```python
def _search_keywords(
    cursor: sqlite3.Cursor,
    keywords: List[str],
    file_types: Optional[List[str]],
    top_k: int
) -> List[Dict]:
    """搜尋 keywords 欄位"""
    
    like_conditions = ' OR '.join(['v.keywords LIKE ?' for _ in keywords])
    params = [f'%{kw}%' for kw in keywords]
    
    type_condition = ""
    if file_types:
        placeholders = ','.join(['?'] * len(file_types))
        type_condition = f"AND d.doc_type IN ({placeholders})"
        params.extend(file_types)
    
    params.append(top_k)
    
    sql = f"""
        SELECT 
            d.id,
            d.filename as file_name,
            d.doc_type as file_type,
            d.upload_date as upload_time,
            v.keywords as raw_content,
            'System' as author,
            COUNT(*) as match_count
        FROM vec_chunks v
        JOIN documents d ON v.doc_id = d.id
        WHERE ({like_conditions})
        {type_condition}
        GROUP BY d.id
        ORDER BY match_count DESC, d.upload_date DESC
        LIMIT ?
    """
    
    cursor.execute(sql, params)
    # ... 處理結果
```

然後在 `search_documents_v2` 中調整搜尋順序:
```python
def search_documents_v2(query: str, ...):
    # 分詞
    keywords = tokenize_query(query)
    
    # 1. 搜尋檔名 (多關鍵字)
    results = _search_filename_multi_keyword(cursor, keywords, file_types, top_k)
    if results:
        return results
    
    # 2. 搜尋 keywords 欄位
    results = _search_keywords(cursor, keywords, file_types, top_k)
    if results:
        return results
    
    # 3. 搜尋內容 (多關鍵字)
    results = _search_content_text_multi_keyword(cursor, keywords, file_types, top_k)
    return results
```

### 方案 3: 優化混合搜尋的融合策略

**問題**: 當前混合搜尋在關鍵字搜尋為 0 時，最終結果只依賴向量搜尋

**改進方向**:

1. **調整權重** - 根據實際效果調整 `vector_weight` 和 `keyword_weight`
2. **使用 BM25 或 TF-IDF** 作為關鍵字搜尋的評分方法
3. **Reciprocal Rank Fusion (RRF)** - 更公平的融合方法

修改 [`hybrid_search`](file:///d:/Github/AI_agent/AI_agent_expert_system/core/search/hybrid_search.py#L15-L118):

```python
def reciprocal_rank_fusion(
    vector_results: List[Dict],
    keyword_results: List[Dict],
    k: int = 60
) -> List[Dict]:
    """
    RRF 融合演算法
    score(d) = sum(1 / (k + rank_i))
    """
    scores = {}
    
    # Vector results
    for rank, result in enumerate(vector_results, 1):
        chunk_id = result['chunk_id']
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
    
    # Keyword results  
    for rank, result in enumerate(keyword_results, 1):
        # 需要找到對應的 chunk_id
        doc_id = result['id']
        chunks = database.get_chunks_by_doc_id(doc_id)
        for chunk in chunks:
            chunk_id = chunk['chunk_id']
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
    
    # 排序
    sorted_chunks = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    # ...
```

### 方案 4: 添加查詢擴展 (Query Expansion)

**原理**: 自動擴展用戶查詢，增加相關詞

**實現**:
```python
def expand_query(query: str, keywords_db: List[str]) -> List[str]:
    """
    查詢擴展
    - 添加同義詞
    - 添加常見組合
    """
    keywords = tokenize_query(query)
    
    # 同義詞映射
    synonyms = {
        'Mura': ['斑點', '不均勻'],
        '問題': ['issue', 'problem'],
        # ...
    }
    
    expanded = keywords.copy()
    for kw in keywords:
        if kw in synonyms:
            expanded.extend(synonyms[kw])
    
    return expanded
```

## 推薦實施順序

### 第一階段 (立即改善)
1. ✅ **實施方案 1** - 查詢分詞 + 多關鍵字 OR 搜尋
   - 創建 `tokenizer.py`
   - 修改 `legacy_search.py` 的兩個搜尋函數
   - **預期效果**: 關鍵字搜尋命中率從 0% 提升到 80%+

### 第二階段 (進一步優化)
2. ✅ **實施方案 2** - 利用 keywords 欄位
   - 添加 `_search_keywords` 函數
   - 調整搜尋優先級
   - **預期效果**: 提高精準度，降低噪音

### 第三階段 (長期優化)
3. 📋 **實施方案 3** - 優化融合策略 (RRF)
4. 📋 **實施方案 4** - 查詢擴展

## 驗證計畫

### 自動化測試

創建測試腳本 [`tests/test_search_improvements.py`](file:///d:/Github/AI_agent/AI_agent_expert_system/tests/test_search_improvements.py):

```python
import pytest
from core.search.legacy_search import search_documents_v2
from core.search.tokenizer import tokenize_query

def test_tokenizer():
    """測試分詞功能"""
    query = "N706 蝴蝶Mura.pptx  內容詳細解析"
    tokens = tokenize_query(query)
    
    assert "N706" in tokens
    assert "蝴蝶" in tokens
    assert "Mura" in tokens
    assert "pptx" not in tokens  # 應被移除
    assert "內容" not in tokens  # 停用詞
    assert "詳細" not in tokens  # 停用詞

def test_multi_keyword_search():
    """測試多關鍵字搜尋"""
    results = search_documents_v2("N706 蝴蝶 Mura")
    
    # 應該找到至少 1 筆結果
    assert len(results) > 0
    
    # 第一筆結果應該是 N706 蝴蝶Mura.pptx
    assert "N706" in results[0]['file_name']
    assert "蝴蝶" in results[0]['file_name']

def test_partial_match():
    """測試部分匹配"""
    results = search_documents_v2("N706 內容解析")
    
    # 即使 "內容解析" 不在文件名中，"N706" 也應該匹配
    assert len(results) > 0
```

執行測試:
```bash
pytest tests/test_search_improvements.py -v
```

### 手動驗證

1. **啟動 chat_app.py**
   ```bash
   streamlit run chat_app.py
   ```

2. **測試查詢列表**:
   - ✅ "N706 蝴蝶Mura.pptx 內容詳細解析" → 應找到蝴蝶Mura文件
   - ✅ "N706 問題" → 應找到所有3個N706文件
   - ✅ "蝴蝶" → 應找到蝴蝶Mura文件
   - ✅ "Oven Pin" → 應找到Oven Pin文件
   - ✅ "ITO issue" → 應找到ITO issue文件

3. **檢查日誌輸出**
   - 確認關鍵字搜尋不再返回 0 筆
   - 檢查搜尋結果排序是否合理

## 其他建議

### 1. 添加搜尋日誌分析
記錄搜尋失敗的查詢，定期分析:
```python
def log_search_query(query: str, results_count: int):
    """記錄搜尋查詢供分析"""
    # 可以寫入專門的日誌文件或資料庫
```

### 2. 考慮使用 FTS (Full-Text Search)
SQLite 支援 FTS5 擴展，可以提供更好的全文搜尋:
```sql
CREATE VIRTUAL TABLE fts_content USING fts5(
    doc_id, 
    filename, 
    content
);
```

### 3. 調整向量搜尋的 top_k
當前混合搜尋會取 `top_k * 2` 的結果，可能需要根據實際情況調整。

### 4. 添加搜尋建議功能
當搜尋無結果時，提供建議:
- "您是不是要找: N706 蝴蝶Mura?"
- 顯示最相似的文件名
