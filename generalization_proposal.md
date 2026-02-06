# AI Agent 通用化與查詢優化方案

## 🎯 目標
解決使用者輸入內容「雜亂」、「多樣化」的問題，並實現「先檢索關鍵字、再生成回答」的高級 RAG 流程。

## 核心概念：雙階段檢索 (Two-Stage Retrieval)

傳統 RAG 是 `User Query -> Vector Search -> LLM`。
為了應對雜亂輸入，我們引入一個 **"理解與校正"** 層。

### 架構圖
```mermaid
graph TD
    User[使用者輸入 (雜亂語句)] --> Router[語意理解層 (LLM/Rule)]
    Router -->|提取特徵| Extractor[關鍵字提取]
    
    subgraph "知識庫映射 (Knowledge Mapping)"
        Extractor -->|Fuzzy Match| KB_Keywords[資料庫關鍵字表]
        KB_Keywords -->|Return| Standardized_Tags[標準化標籤]
    end
    
    Standardized_Tags -->|注入| Enhanced_Query[增強型查詢]
    Enhanced_Query -->|搜尋| Search_Engine[混合搜尋引擎]
    Search_Engine -->|文檔 + 標籤| Generator[LLM 回答生成]
    
    Generator --> Final[最終回答]
```

---

## 🛠️ 具體解決方案

### 方案 1: 關鍵字映射 (Keyword Mapping & Injection) - *您提到的方法*

這就是您提到的「先檢索資料庫，把關鍵字融入語句」。

**流程：**
1. **建立關鍵字索引 (Keywords Index)**：
   - 掃描現有 DB 中的 `vec_chunks.keywords`，建立一個去重後的關鍵字清單（Glossary）。
   - 例如：`["Mura", "Particle", "Scratch", "N706", "PTST"]`。

2. **使用者意圖解析**：
   - 當使用者問：「那個螢幕有髒髒的東西怎麼辦？」
   - 系統先不查文件，而是先查「關鍵字索引」。
   - **LLM 輔助**：請 LLM 判斷「髒髒的東西」可能對應我們術語表中的哪些詞？ -> 輸出 `["Mura", "Particle", "Stain"]`。

3. **注入與重組 (Injection)**：
   - 系統自動將查詢改寫為：`"螢幕有髒髒的東西 (Mura OR Particle OR Stain)"`
   - 或者在 Prompt 中告訴 GPT：
     > 使用者問的是關於「髒髒的東西」。
     > 系統檢索到相關專業術語可能是：Mura, Particle。
     > 請參考這些術語相關的文件來回答。

**優點**：即使使用者不懂術語，也能搜到專業文件。

### 方案 2: 查詢路由與重寫 (Query Routing & Rewriting)

針對「使用者用法很雜」的通用解法。

**流程：**
在搜尋前，先經過一個輕量級的 LLM 節點（Router）：

- **輸入**：使用者原始問句
- **任務**：
  1. **標準化 (Normalize)**：把口語轉為書面語。
  2. **分類 (Classify)**：這是「查詢文件」、「尋求建議」還是「閒聊」？
  3. **擴展 (Expand)**：生成 3 個不同角度的搜尋關鍵字。

**範例**：
- User: "之前那個做某某客戶的案子，好像有破片的紀錄"
- **Router Output**:
  ```json
  {
    "intent": "document_search",
    "keywords": ["破片", "Crack", "Broken"],
    "filters": {"category": "Customer Issue"},
    "rewritten_query": "客戶案子 破片 Crack 紀錄"
  }
  ```
- 接著系統用 `rewritten_query` 去搜尋，準確率會遠高於原始語句。

### 方案 3: HyDE (Hypothetical Document Embeddings)

這是目前學界解決「問題與答案不匹配」的通用方法。

**原理**：
1. 使用者問一個問題。
2. LLM **先憑空寫一個「假想的完美答案」** (Hypothetical Answer)。
3. 拿這個「假想答案」去跟資料庫做向量搜尋，而不是拿「問題」去搜。

**為什麼有效？**
因為「假想答案」的向量空間跟「真實文件」的向量空間更接近。使用者的「問題」通常很短且向量空間距離答案較遠。

---

## 🚀 推薦實施路徑 (Roadmap)

根據我們目前的系統狀態 (`AI_agent_expert_system`)，建議優先順序如下：

### Phase 1: 建立「術語映射表」 (Term Matcher)
這是最快能實現您想法的方式。

1. **Extract**: 從 DB 導出所有 unique keywords。
2. **Match**: 寫一個簡單的 Python 函數，拿使用者的輸入句去跟 Keywords 做 Fuzzy Match (模糊比對)。
3. **Inject**: 搜到的 Keywords 直接加到 SQL LIKE 條件中 (我們剛實作的 OR Logic)。

### Phase 2: LLM 查詢預處理器 (Query Preprocessor)
如果 Phase 1 不夠聰明，就接上 LLM。

1. 定義一個新的 Prompt Template: `Prompt_Query_Optimization`。
2. 每次搜尋前，先 call 一次 LLM (可以用較便宜的模型如 GPT-3.5-turbo 或 Gemini Flash)。
3. 讓 LLM 輸出優化後的關鍵字 list。

---

## 範例：如何告訴 GPT (Prompt Engineering)

在最終生成回答階段，我們可以這樣設計 Prompt：

```markdown
# Role
你是專業的客服工程師 AI。

# Context
使用者問題："{raw_user_query}"
系統識別關鍵字：{injected_keywords} (這是從資料庫自動匹配的術語)

# Retrieved Documents
{search_results}

# Instruction
請參考上述文件回答問題。
注意：使用者用語可能不標準，請參考「系統識別關鍵字」來確認使用者可能意指的專業問題。
```
