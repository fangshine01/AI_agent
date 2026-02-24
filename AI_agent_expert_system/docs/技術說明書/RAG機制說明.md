# RAG 機制文件 (RAG Mechanism Documentation)

本文檔詳細說明本系統使用的 RAG (Retrieval-Augmented Generation) 核心機制，包含切片策略、資料隔離、向量運算與重排序邏輯。

## 1. 切片策略 (Chunking Strategy)

本系統根據**文件類型 (Doc Type)** 採用不同的切片策略，以確保語意完整性。

| 文件類型 | 解析器 | 切片邏輯 (Chunking Logic) |
| :--- | :--- | :--- |
| **Troubleshooting**<br>(異常解析) | `TroubleshootingParser` | **語意欄位提取**: 使用 LLM 將非結構化報告標準化為 6 大欄位：<br>1. Problem issue & loss<br>2. Problem description<br>3. Analysis root cause<br>4. Containment action<br>5. Corrective action<br>6. Preventive action |
| **Knowledge**<br>(知識庫) | `KnowledgeParser` | **章節結構化**: <br>1. 先依據 Markdown 標題 (`#`) 或分隔線 (`---`) 切分章節。<br>2. 再使用 LLM 將每章節結構化為「知識卡片」 (包含 Topic, Definition, Core Content, Key Terms, Examples)。 |
| **Training**<br>(教育訓練) | `TrainingParser` | **教學單元**: 類似知識庫，但側重於將長篇教材拆解為獨立的教學觀念單元。 |
| **Procedure**<br>(SOP/手順) | `ProcedureParser` | **步驟拆解**: 將 SOP 拆解為獨立的操作步驟 (Step-by-step)。 |
| **PPTX 檔案** | `ppt_parser` | **投影片**: 以每一頁投影片 (Slide) 為一個基本切片單位。 |
| **PDF 檔案** | `pdf_parser` | **頁面**: 以每一頁 (Page) 為一個基本切片單位。 |

---

## 2. 資料隔離 (Data Isolation)

系統採用**邏輯隔離 (Logical Isolation)** 策略，所有向量資料儲存於同一個 `vec_chunks` 表中，但在查詢時透過 Metadata 進行精確過濾。

### 隔離層級
1. **文件類型 (Doc Type)**: 最上層的隔離，例如查詢 SOP 時不會搜尋到 8D 報告。
2. **結構化過濾 (Structured Filters)**:
   - **Product (產品型號)**: 例如 `N706`, `N707`。
   - **Station (站點)**: 例如 `Oven`, `Exposure`。
   - **Topic (主題)**: 針對特定關鍵字過濾。

> **註**: 查詢時會執行 `AND` 邏輯運算，確保結果同時符合所有過濾條件。

---

## 3. 向量距離與相似度 (Vector Distance & Similarity)

### 向量模型
- **Model**: `text-embedding-3-small` (OpenAI)
- **Dimension**: `1536` 維

### 相似度計算
- **演算法**: **Cosine Similarity (餘弦相似度)**
- **實作方式**: 使用 `vec_distance_cosine` 函數計算距離。
- **分數轉換公式**:
  $$ \text{Similarity Score} = 1 - \text{Cosine Distance} $$
  *(範圍 0.0 ~ 1.0，越接近 1.0 表示越相似)*

### 閾值設定 (Similarity Thresholds)
系統在 `document_grouping.py` 中定義了動態選擇切片的閾值：

- **High (0.85)**: 高度相關，必定納入參考。
- **Medium (0.70)**: 中度相關，最多選取 3 個。
- **Low (0.50)**: 低度相關，若無更好結果則最多選取 1 個 (保底)。

---

## 4. Top-K 與檢索設定

| 參數 | 預設值 | 說明 |
| :--- | :--- | :--- |
| **Vector Search Top-K** | `5` | 單次向量檢索取回的最相關切片數。 |
| **Universal Search Top-K** | `10` | 最終返回給用戶的結果數量上限。 |
| **Rerank Candidate Size** | `20` | 進入重排序階段的候選結果數量。 |

---

## 5. 重排序機制 (Re-ranking)

為了提升檢索精準度，系統在向量檢索後引入了 **AI 語意重排序 (`semantic_rerank`)**。

### 運作流程
1. **候選生成**: 從向量檢索取出前 `20` 筆結果。
2. **AI 分析**: 使用 `gpt-4o-mini` 對候選結果進行評分排序。
3. **排序準則**:
   1. **關鍵實體匹配 (Key Entity Matching)**: 優先展示完全匹配「產品型號」、「錯誤代碼」的結果 (最高權重)。
   2. **排除不相關 (Exclusion)**: 降權或排除產品型號不符的結果 (例如查 N706 卻出現 N500)。
   3. **內容相關性 (Relevance)**: 根據解決方案的具體程度排序。

### 為什麼需要重排序？
向量檢索有時無法區分細微的實體差異 (例如 `N706` vs `N707` 在向量空間可能很近)，透過 LLM 進行二次確認可以大幅降低「張冠李戴」的幻覺風險。
