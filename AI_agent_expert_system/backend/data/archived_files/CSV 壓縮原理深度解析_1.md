---
作者:
  - Peicheng.Fang
工作屬性:
  - 程式碼
  - 教學
目的簡述: CSV 壓縮原理深度解析
窗口:
  - 方培丞
tags:
  - parquet
  - csv
  - 壓縮原理
---
---
# CSV 壓縮原理深度解析 (The Physics of CSV Compression)

CSV (Comma-Separated Values) 是最常見的純文字資料格式。與 Parquet 這種專為電腦設計的「二進位欄式格式」不同，CSV 是「以列為單位 (Row-based)」且「人類可讀 (Human-readable)」的文字。

因此，CSV 的壓縮原理主要依賴**通用文字壓縮演算法** (Text Compression Algorithms)。

最核心的三大技術是：
1.  **LZ77 (找出重複的字串)**
2.  **Huffman Coding (常用字元用短編碼)**
3.  **BWT (Burrows-Wheeler Transform, 字元排列)**

---

## 1. 核心壓縮戰將：DEFLATE (Gzip 的心臟)

絕大多數的 CSV 壓縮 (.csv.gz, .zip) 都是使用 **Deflate** 演算法。Deflate = **LZ77** (去重複) + **Huffman** (變動長度編碼)。

### 1.1 第一步：LZ77 - 消除重複的字串 (Deduplication)

CSV 檔案充滿了重複，這是壓縮的黃金來源。

**CSV 特性**:
1.  **逗號重複**: 每行都有很多 `,`。
2.  **日期重複**: `2024-01-01` 可能連續出現幾千行。
3.  **類別重複**: `Consumer`, `Corporate` 等字串不斷重複。

**LZ77 原理**:
使用一個「滑動視窗 (Sliding Window)」(例如 32KB)，往回看「這個片段以前出現過嗎？」。如果有，就用 **`(距離, 長度)`** 來取代。

#### **詳細範例**

**原始 CSV 片段**:
```csv
2024-01-01,Apple,100
2024-01-01,Banana,200
```

**LZ77 壓縮過程**:

1.  讀取第一行: `"2024-01-01,Apple,100"` (沒有重複，原樣輸出)
2.  讀取第二行:
    *   看到 `2`: 前面有嗎？有！就在 24 個字元前。
    *   看到 `0`: 前面有嗎？有！
    *   ...一路比對...
    *   發現整個 `"2024-01-01,"` (11 個字元) 與前一行完全一樣。
    *   **取代為**: `(距離=24, 長度=11)`

**壓縮後結果 (概念)**:
```text
2024-01-01,Apple,100
(24, 11)Banana,200
```
> **結果**: 原本 `"2024-01-01,"` 佔了 11 Bytes，現在只需 2 Bytes (存這裡和長度) 就能代表。

---

### 1.2 第二步：Huffman Coding - 頻率編碼

經過 LZ77 處理後，主要剩下「還沒重複過的文字」和「連結標籤」。Huffman 針對**單個字元**的出現頻率進行壓縮。

**CSV 特性**:
*   **高頻符號**: `,` (逗號), `\n` (換行), `"` (引號), 數字 `0-9`。
*   **低頻符號**: `Q`, `Z`, `{`, `}`。

**Huffman 原理**:
給高頻字元**極短**的二進位碼 (Binary Code)，低頻字元給**長**的碼。

#### **詳細範例**

假設統計後的頻率：
*   `,` : 出現 1000 次
*   `\n`: 出現 1000 次
*   `A` : 出現 10 次
*   `Z` : 出現 1 次

**編碼表 (Mapping)**:
*   `,` -> `0` (1 bit)
*   `\n` -> `10` (2 bits)
*   `A` -> `11001` (5 bits)
*   `Z` -> `1110011` (7 bits)

**效果**:
在標準 ASCII 中，每個字元都要 8 bits。但在這裡，最常見的逗號只需要 1 bit。CSV 檔案裡光是逗號就佔了很大比例，這一步能省下大量空間。

---

## 2. 進階壓縮：Bzip2 與 BWT (Burrows-Wheeler Transform)

`.csv.bz2` 通常比 `.csv.gz` 壓縮得更小，但速度慢很多。秘密在於它多了一個 **BWT** 步驟。

### 2.1 BWT - 把相似的字元「吸」在一起

BWT **不是壓縮**，它是**轉換 (Transformation)**。它把原始順序的字串，重新排列，讓**相同的字元靠在一起**。

**為什麼這對 CSV 很重要？**
CSV 雖然有重複，但分布在不同行。LZ77 只能看附近的視窗 (32KB)。如果重複發生在很遠的地方，LZ77 就看不到。BWT 通過排序，把所有相同的東西聚在一起。

#### **詳細範例 (簡化版)**

假設字串是: `BANANA`

1.  **產生所有旋轉 (Rotations)**:
    ```
    BANANA
    ANANAB
    NANABA
    ANABAN
    NABANA
    ABANAN
    ```
2.  **排序這些行 (Sort)**:
    ```
    ABANAN
    ANABAN
    ANANAB
    BANANA
    NABANA
    NANABA
    ```
3.  **取最後一欄 (Last Column) 作為輸出**: `NNBAAA`

**觀察結果**:
原始 (`BANANA`) -> BWT轉換 (`NNBAAA`)。
原本 `A` 分散在各處，現在 `A` 全部聚在一起 (`AAA`)，`N` 也聚在一起 (`NN`)。

**這時候再用「Run-Length Encoding (RLE)」**:
`NNBAAA` -> `2N 1B 3A`。
瞬間壓縮率大增！

> **結論**: Bzip2 對於 CSV 這種包含大量重複單字 (但位置不固定) 的文本，壓縮率極高，因為 BWT 能把分散到各行的 "Apple" 裡的 'p' 全部聚攏。

---

## 3. 現代霸主：Xz (LZMA) 與 Zstd

### 3.1 Xz / 7-Zip (演算法: LZMA2)
*   **原理**: 擁有**極巨大**的字典視窗 (Dictionary Window)。Gzip 只能回頭看 32KB，LZMA 可以回頭看 **1GB** 甚至更多。
*   **CSV 應用**: 如果你的 CSV 檔案有 100GB，第 1 行的模式可能在第 5000 萬行才重複。Gzip 看不到，但 Xz 看得到。
*   **範例**: 壓縮率通常最高，但壓縮時間可能要 Gzip 的 10 倍以上。

### 3.2 Zstd (Zstandard)
*   **原理**: 結合了 LZ77 的變種 (FSE: Finite State Entropy) 以及巨大的字典。
*   **特點**: 它建立在 Gzip (Deflate) 的基礎上，但數學模型更優化。它有一個特殊功能是「訓練字典 (Dictionary Training)」，可以針對特定種類的 CSV (例如全是醫療數據) 預先訓練一個字典，即使是很小的檔案也能有極高壓縮率。

---

## 4. 總結比較表 - 針對 CSV

| 壓縮格式 | 工具 | 主要原理 | 壓縮率 | 壓縮速度 | 範例與適用性 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Gzip** | `gzip` | Deflate (LZ77 + Huffman) | 中 | 快 | 最通用。適合一般 Log 或不需要極致壓縮的 CSV。 |
| **Bzip2** | `bzip2` | BWT + Huffman + RLE | 高 | 慢 | 適合純文字且重複性高的 CSV。如果不在乎等待時間，這比 Gzip 省空間。 |
| **Xz** | `xz` | LZMA (Huge Dictionary) | **極高** | 極慢 | 封存用 (Archiving)。如果你要把一年的 CSV 封存起來十年不看，用這個。 |
| **Zstd** | `zstd` | LZ77 + FSE | 中高 | **極快** | **現代最佳平衡**。大數據處理 (Spark/Pandas) 推薦使用。 |

## 5. 為什麼 CSV 壓縮永遠比不過 Parquet？

即使把 CSV 壓到極限 (用 Xz)，通常還是比 Parquet (Snappy) 大，或者讀取更慢。

1.  **型別浪費**: CSV 的 `1000000` 是 7 個字元 (7 Bytes)。Parquet 存 `Int32` 只要 4 Bytes。
2.  **Row-based 限制**: CSV 壓縮是混著壓 (日期接字串接數字)。Parquet 把所有日期放在一起壓 (Delta Encoding)，所有字串放在一起壓 (Dictionary Encoding)。**同質性的資料壓縮率永遠比較高**。

> **一句話總結**: CSV 壓縮是靠「找重複的文字片段」；Parquet 壓縮是靠「理解資料的結構與型別」。
