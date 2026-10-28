# Scripts Directory

此目錄包含英語單字庫建置、歷屆試題解析、字根字綴擴充、網頁圖譜生成與素材管理的自動化處理工具。

---

## 🛠️ 腳本清單與功能說明

### 1. 核心資料建置流程 (ETL Pipeline)

```
[官方詞彙 PDF] ──> build_exam_words.py ──> exam_words.json (基礎字庫)
                                                 │
[12年歷屆試題] ──> parse_exams.py ───────────────┤ (出題年份與次數統計)
                                                 │
                   enrich_vocab.py ──────────────┤ (單字變形、字族、情境分類)
                                                 │
[ECDICT 辭典]  ──> import_definitions.py ────────┤ (中文釋義匯入)
                                                 │
                   convert_to_traditional.py ────┤ (簡體轉繁體中文)
                                                 │
                   add_english_definitions.py ───┘ (英文定義匯入)
```

| 腳本名稱 | 功能說明 | 常用執行指令 |
|---|---|---|
| **`build_exam_words.py`** | 從官方《高中英文參考詞彙表》PDF 擷取 Level 1–6 單字與詞性 | `py scripts/build_exam_words.py` |
| **`parse_exams.py`** | 解析 104–115 學年度歷屆試題 PDF，運用 NLTK 詞形還原計算出題次數 | `py scripts/parse_exams.py` |
| **`enrich_vocab.py`** | 為單字補充詞形變化 (`forms`)、同字族延伸詞 (`word_family`) 與主題情境 | `py scripts/enrich_vocab.py` |
| **`import_definitions.py`** | 從 `ecdict.csv` 批次匯入中文釋義 | `py scripts/import_definitions.py` |
| **`convert_to_traditional.py`**| 使用 OpenCC 將中文釋義全面轉換為繁體中文（台灣習慣用詞） | `py scripts/convert_to_traditional.py` |
| **`add_english_definitions.py`**| 從 `ecdict.csv` 擷取結構化英文定義並補足完整雙語欄位 | `py scripts/add_english_definitions.py` |
| **`generate_stats.py`** | 統計單字出題率、各等級分佈與高頻字排行，輸出 `exam_stats.json` | `py scripts/generate_stats.py` |

---

### 2. 網頁圖譜與素材工具 (Web & Assets)

| 腳本名稱 | 功能說明 | 常用執行指令 |
|---|---|---|
| **`add_exam_oov_words.py`** | 針對歷屆考卷全面進行詞形還原與比對，將統測考題實際出現但不在 6,109 表內的 592 個高頻考字（如 orchid, supercomputer, scam, summer 等）補齊雙語釋義並加入字庫 | `py scripts/add_exam_oov_words.py` |
| **`build_root_breakdown.py`**| 依據 90 字根與 109 詞綴庫，產生確定性字根/字首/字尾拆解資料庫 `database/word_roots_breakdown.json` | `py scripts/build_root_breakdown.py` |
| **`build_sentence_examples.py`**| 從 104–115 統測 PDF 抽取真實試題句子（1,209 句），並補齊全字典標準例句輸出 `database/word_sentences.json` | `py scripts/build_sentence_examples.py` |
| **`build_simple_definitions.py`**| 生成完全限定使用 Level 1–2 單字解釋的精簡英文定義庫 `database/simple_definitions.json` | `py scripts/build_simple_definitions.py` |
| **`auto_fetch_images.py`** | 自動從維基百科 REST API 批次抓取具體名詞高畫質圖片並自動以 Pillow 壓縮至 Web 最適尺寸 | `py scripts/auto_fetch_images.py --count 30` |
| **`build_web_graph.py`** | 篩選「統測出現過或 Level 1–4」單字（共 4,842 字），使用雙語語義匹配分類至 9 大領域 38 主題，整合例句、字根與排序指標，輸出 `docs/data/graph.json` 與 `docs/data/vocab_data.json` | `py scripts/build_web_graph.py` |
| **`upload_word_image.py`** | 為單字上傳並自動壓縮處理圖片至 `docs/data/images/{word}.png` | `py scripts/upload_word_image.py` |

#### `auto_fetch_images.py` 使用範例：
```bash
# 自動為尚未有圖片的前 20 個高頻具體名詞抓取維基百科圖片
py scripts/auto_fetch_images.py --count 20

# 指定單字清單下載圖片
py scripts/auto_fetch_images.py --words orchid supercomputer rainforest scam
```

#### `upload_word_image.py` 使用範例：
```bash
# 互動模式（直接在提示中輸入單字與圖片檔案）
py scripts/upload_word_image.py

# 參數指定模式
py scripts/upload_word_image.py -w apple -i C:/path/to/apple.jpg

# 批次匯入資料夾內所有單字圖片
py scripts/upload_word_image.py --batch C:/path/to/image_folder

# 查看目前已有圖片的單字清單
py scripts/upload_word_image.py -l
```

---

### 3. 字根字綴引擎升級 (Root Database)

| 腳本名稱 | 功能說明 | 常用執行指令 |
|---|---|---|
| **`upgrade_word_db.py`** | 擴充詞根庫（90 字根、59 前綴、50 後綴）與衍生詞，同步更新 `database/` 與 `api/` | `py scripts/upgrade_word_db.py` |

