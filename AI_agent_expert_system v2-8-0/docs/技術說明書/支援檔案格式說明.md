# AI Agent 知識庫檔案格式規範指南 (v1.5.0)

本文檔詳細說明 AI Expert System v1.5.0 支援的檔案類型、建議格式與撰寫規則，以確保 AI 能最精確地解析與索引您的文件。

## 📁 支援的檔案格式

目前 v1.5.0 版本支援以下檔案格式：

| 格式 | 副檔名 | 適用場景 | 解析方式 |
|------|--------|----------|----------|
| **PowerPoint** | `.pptx` | 教育訓練、簡報報告 | 提取每一頁投影片的文字內容、備忘稿與圖片 |
| **PDF** | `.pdf` | 規格書、手冊、掃描檔 | 提取頁面文字內容 (使用 PyMuPDF) |
| **Markdown** | `.md` | 技術文件、知識庫 | 支援結構化章節解析 (建議使用) |
| **Text** | `.txt` | 純文字筆記 | 作為單一內容區塊處理 |

> ✅ **更新**: v1.5.0 已正式支援 PDF 解析。

---

## 📚 文件類型與撰寫規範

系統將文件分為四大類，每種類型有不同的 AI 解析邏輯。遵循以下結構撰寫文件，可大幅提升 AI 的理解與回答準確度。

### 1. 異常解析 (Troubleshooting)

此類型用於記錄問題排查過程、8D 報告或維修記錄。

**AI 自動提取欄位**:
1. **Problem issue & loss** (問題議題與損失)
2. **Problem description** (問題描述)
3. **Analysis root cause** (根本原因分析)
4. **Containment action** (圍堵對策)
5. **Corrective action** (矯正對策)
6. **Preventive action** (預防對策)

**💡 撰寫建議**:
- 在文件中明確包含上述關鍵字標題。
- 描述越具體越好，包含具體的錯誤代碼 (Error Code) 或現象。

**📝 Markdown 範本**:

```markdown
# N706 蝴蝶 Mura 異常報告

## Problem Description
機台 N706 在製程中出現蝴蝶狀 Mura，造成良率下降 5%。

## Root Cause
經分析發現，塗佈噴嘴 (Nozzle) 壓力不穩，導致光阻厚度不均。

## Corrective Action
更換噴嘴氣壓閥，並重新校正壓力參數至 5.0 psi。

## Preventive Action
將氣壓閥檢查列入每週 PM 項目。
```

---

### 2. 知識庫 (Knowledge)

此類型用於技術原理、操作手冊或標準規範 (SOP)。

**AI 解析邏輯**:
- 會自動將文件拆解為多個「章節」。
- 每個章節會被提取為一張「知識卡片」，包含：主題、定義、核心內容、關鍵用語、應用範例。

**💡 撰寫建議**:
- **重要規則**: 請使用 `# ` (H1 標題) 或 `---` (分隔線) 來區分不同章節。
- 每個章節應專注於一個特定的主題。

**📝 Markdown 範本**:

```markdown
# 半導體微影製程 (Lithography)

微影製程是將電路圖形轉移到晶圓表面的關鍵步驟。

---

# 光阻劑 (Photoresist)

## 定義
光阻劑是一種對光敏感的有機高分子材料。

## 核心內容
光阻劑分為正光阻與負光阻。正光阻在曝光後會變得可溶於顯影液...

## 關鍵術語
- 正光阻 (Positive PR)
- 負光阻 (Negative PR)
- 顯影 (Developing)

---

# 曝光 (Exposure)

曝光是利用光源透過光罩照射光阻的過程...
```

---

### 3. 教育訓練 (Training)

此類型用於課程教材、新人訓練投影片。

**AI 自動提取欄位**:
1. **Target Audience** (適用對象)
2. **Learning Objectives** (學習目標)
3. **Prerequisites** (先備知識)
4. **Core Modules** (核心單元)
5. **Quiz/Assessment** (課後測驗)

**💡 撰寫建議 (針對 PPTX/PDF)**:
- 在首頁或前幾頁投影片明確列出「課程目標」與「適用對象」。
- 每一頁投影片標題應清晰。
- 結尾頁面可包含「隨堂測驗」或「重點複習」。

---

### 4. 日常手順 (Procedure)

此類型用於 SOP、操作步驟。

**AI 解析邏輯**:
- 重點在於步驟的順序性。

**💡 撰寫建議**:
- 使用有序列表 (1., 2., 3.) 描述步驟。

---

## 🏷️ 檔案命名規則

為了讓搜尋引擎更精準地找到文件，建議遵循以下命名規則：

`[機台/專案代號]_[主題]_[文件類型].副檔名`

**範例**:
- `N706_蝴蝶Mura改善_Troubleshooting.pptx`
- `SOP_微影製程規範_Knowledge.md`
- `NewHirer_工安教育訓練_Training.pdf`

---

## 🏗️ 資料庫欄位與元數據總覽 (Database Schema)

系統在解析文件時，會自動建立以下完整的資料結構。了解這些欄位有助於您進行進階的 API 整合或資料庫查詢。

### 1. 核心資訊 (Core Info)
| 欄位名稱 | 說明 | 來源 |
|----------|------|------|
| `filename` | 原始檔案名稱 | 系統自動取得 |
| `file_hash` | MD5 雜湊值 (用於重複檢測) | 系統自動計算 |
| `file_size` | 檔案大小 (Bytes) | 系統自動取得 |
| `upload_time` | 上傳時間戳記 | 系統自動生成 |
| `version` | 文件版本號 (預設 1) | 系統自動生成 |

### 2. 智慧分類 (AI Classification)
| 欄位名稱 | 說明 | 來源 |
|----------|------|------|
| `doc_type` | 文件類型 (Knowledge/Training 等) | 上傳時**手動選擇** |
| `category` | 次級分類 (如: Display, Process) | **AI 自動推薦** 或 手動指定 |
| `tags` | 關鍵標籤 (如: Mura, 黃光) | **AI 自動提取** (JSON 格式) |
| `language` | 文件語言 (zh-TW / en-US) | **AI 自動偵測** |

### 3. 內容摘要 (Content Analysis)
| 欄位名稱 | 說明 | 來源 |
|----------|------|------|
| `summary` | 文件重點摘要 (約 150 字) | **AI 自動生成** |
| `key_points` | 條列式重點 (Key Takeaways) | **AI 自動生成** (JSON 格式) |
| `chunk_count` | 切片數量 | 解析後自動計算 |

### 4. 管理元數據 (Administrative)
這些欄位支援 API 寫入，但在預設 Admin UI 中為選填或留空。
| 欄位名稱 | 說明 | 來源 |
|----------|------|------|
| `author` | 文件作者 | API 輸入 / 預設 NULL |
| `department` | 所屬部門 | API 輸入 / 預設 NULL |
| `factory` | 所屬廠區 | API 輸入 / 預設 NULL |
| `priority` | 優先級 (0-10, 影響搜尋排序) | API 輸入 / 預設 0 |
| `status` | 狀態 (active/archived) | 預設 active |

> **💡 關於「產品」資訊**: 
> 目前資料庫無獨立的 `product` 欄位。建議將產品名稱 (如 N706, Model X) 包含在 `filename` 中，或由 AI 自動提取至 `tags` 欄位，搜尋引擎即可自動索引。

### 5. 向量與切片數據 (Vector Data)
文件內容會被切分為多個 `chunks` 儲存於 `vec_chunks` 表：
- **Content**: 切片文字內容
- **Embedding**: 1536 維向量
- **Keywords**: 用於混合搜尋的關鍵字索引
- **Context**: 上下文資訊 (Context Window)
