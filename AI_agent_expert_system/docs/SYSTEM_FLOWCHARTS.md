# AI Agent 系統架構流程圖

本文檔展示了 AI Agent 系統目前的架構流程與未來的擴展開發藍圖。

## 🏛️ 當前架構流程 (Current Architecture v1.5.0)

目前的系統以 RAG (檢索增強生成) 為核心，整合了 Admin 管理後台與 User 問答前台，並透過通用查詢引擎進行資料檢索。

```mermaid
flowchart TD
    %% 定義樣式
    classDef frontend fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef backend fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef ai fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef db fill:#e0f2f1,stroke:#00695c,stroke-width:2px;
    classDef file fill:#fff3e0,stroke:#e65100,stroke-width:2px;

    subgraph Frontend ["前端介面層"]
        direction TB
        AdminUI["Admin Console<br/>(Streamlit :8501)"]:::frontend
        ChatUI["Chat Expert<br/>(Streamlit :8502)"]:::frontend
    end

    subgraph Backend ["後端核心層"]
        direction TB
        Ingestion["文件攝取引擎<br/>(Ingestion v3)"]:::backend
        SearchEngine["通用查詢引擎<br/>(Universal Search)"]:::backend
        Router["查詢意圖路由<br/>(Query Router)"]:::backend
        Reranker["AI 重排序<br/>(Reranker)"]:::backend
        Parser["多格式解析器<br/>(Parsers)"]:::backend
    end

    subgraph AI_Services ["AI 運算層"]
        LLM["LLM 模型<br/>(GPT-4o / OneAPI)"]:::ai
        Embed["Embedding 模型<br/>(text-embedding-3)"]:::ai
    end

    subgraph Data_Layer ["資料儲存層"]
        SQLite[("SQLite Metadata")]:::db
        VectorDB[("Vector DB<br/>sqlite-vec")]:::db
        RawFiles["原始文件<br/>PPTX, PDF, MD"]:::file
    end

    %% 連線關係 - 上傳流程
    AdminUI -->|上傳文件| Ingestion
    Ingestion -->|讀取| RawFiles
    Ingestion -->|解析| Parser
    Parser -->|提取文字| Ingestion
    Ingestion -->|1. 生成向量| Embed
    Ingestion -->|2. 提取元數據| LLM
    Ingestion -->|3. 寫入資料| SQLite & VectorDB

    %% 連線關係 - 查詢流程
    ChatUI -->|使用者提問| SearchEngine
    SearchEngine -->|1. 分析意圖| Router
    Router -->|判斷| SearchEngine
    SearchEngine -->|2. 執行搜尋| VectorDB
    VectorDB -->|返回候選結果| SearchEngine
    SearchEngine -->|3. 語意重排序| Reranker
    Reranker -->|LLM 評分| LLM
    SearchEngine -->|4. 生成回答| LLM
    LLM -->|最終回應| ChatUI
```

---

## 🚀 未來架構藍圖 (Future Roadmap: SPC/EDC/Yield)

未來的系統將從單純的文件知識庫，擴展為整合生產數據 (SPC, EDC, Yield) 的全方位製造智慧平台。

```mermaid
flowchart TD
    %% 定義樣式
    classDef frontend fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef backend fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef ai fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef db fill:#e0f2f1,stroke:#00695c,stroke-width:2px;
    classDef future fill:#ffebee,stroke:#c62828,stroke-width:2px,stroke-dasharray: 5 5;

    subgraph Frontend ["前端介面層"]
        direction TB
        UnifiedUI["整合戰情室<br/>(Dashboard)"]:::frontend
        ChatUI2["智慧助手<br/>(Chat Expert v2)"]:::frontend
    end

    subgraph Backend ["後端核心層"]
        direction TB
        SearchEngine2["增強型查詢引擎"]:::backend
        DataAgent["數據分析 Agent"]:::future
        Exporter["資料匯出模組"]:::future
    end

    subgraph AI_Services ["AI 運算層"]
        LLM2["LLM (GPT-4o)"]:::ai
        AnalysisModel["數據分析模型<br/>(Python/Pandas/Scikit-learn)"]:::ai
    end

    subgraph Data_Hub ["資料中心"]
        KB_DB[("知識庫 DB")]:::db
        
        subgraph Manufacturing_Data ["製造數據庫 (New)"]
            SPC_DB[("SPC 資料庫")]:::future
            EDC_DB[("EDC 資料庫")]:::future
            YIELD_DB[("良率資料庫")]:::future
        end
    end

    %% 連線
    UnifiedUI -->|查詢/監控| SearchEngine2
    ChatUI2 -->|自然語言提問| SearchEngine2

    SearchEngine2 -->|文件檢索| KB_DB
    SearchEngine2 -->|數據請求| DataAgent

    %% 數據分析流程 (New)
    DataAgent -->|1. SQL 查詢| SPC_DB & EDC_DB & YIELD_DB
    DataAgent -->|2. 數據處理| AnalysisModel
    AnalysisModel -->|3. 分析結果| DataAgent
    DataAgent -->|4. 生成報告| LLM2
    DataAgent -->|5. 匯出 Excel/CSV| Exporter
    
    %% 回饋
    DataAgent -->|分析洞察| ChatUI2
    Exporter -->|檔案下載| ChatUI2
```

### 關鍵擴充模組說明

1.  **製造數據庫 (Manufacturing Data Hub)**:
    -   **SPC DB**: 統計製程控制數據 (CPK, Control Charts)。
    -   **EDC DB**: 機台工程數據 (Sensor logs, FDC)。
    -   **Yield DB**: 產品良率數據、Defect Map。

2.  **數據分析 Agent (Data Agent)**:
    -   具備 SQL 生成能力，能將自然語言轉為資料庫查詢。
    -   整合 Pandas/Scikit-learn 進行趨勢分析與異常偵測。

3.  **資料匯出模組 (Exporter)**:
    -   自動生成 Excel 報表或 CSV 檔案供使用者下載。
