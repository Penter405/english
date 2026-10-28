# English Vocabulary & Root Explorer 🔤

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live%20Demo-brightgreen)](https://penter405.github.io/english/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Cytoscape.js](https://img.shields.io/badge/Cytoscape.js-3.28-orange)](https://js.cytoscape.org/)

本專案整合了**台灣高中英文參考詞彙（Level 1–6）**、**12 年歷屆學測/統測出題分析大數據**、**印歐語音變規律字根拆解引擎**，以及**多層次互動式單字知識圖譜 Web 應用**。

---

## 🚀 專案兩大核心功能 (Applications)

### 1. 互動式考試單字知識圖譜 (Interactive Exam Vocabulary Graph)
> **線上體驗網址：** [https://penter405.github.io/english/](https://penter405.github.io/english/)  
> **原始碼目錄：** [`docs/`](./docs/)

專為台灣高中職學生量身打造的視覺化單字導覽地圖：
- **精選 4,842 個核心單字**：涵蓋「統測歷屆曾出題 OR Level 1–4」重點範圍（含統測歷屆高頻詞如 orchid, supercomputer, scam, rainforest 等）。
- **3 軌雙語釋義與 Level 1–2 簡化英釋**：
  - **🟢 基礎英釋 (Level 1–2)**：全數單字收錄完全由國中小 Level 1–2 基礎單字撰寫之極簡釋義，初學者零負擔。
  - **📘 詳細英釋 (Advanced)**：完整 ECDICT 權威英文定義。
  - **🇹🇼 繁體中文**：精準詞性與中文對譯。
- **確定性字根/字首/字尾拆解 (Deterministic Root & Affix Breakdown)**：直接查表自字根資料庫，清晰標示 `Prefix` (前綴)、`Root` (詞根)、`Suffix` (後綴) 及造詞中英合成邏輯（例：`predict` ➔ `pre-(事先) + dict(說/講)`），杜絕演算法隨機猜測。
- **統測歷屆真題與標準例句 (Authentic Sentence Examples)**：收錄 104–115 統測真題實際句子與標準例句，目標字自動發光標註。
- **多維出題排序與特定年份調整 (Multi-criteria Adjust Buttons)**：
  - **全域調整工具列 (Global Adjust Bar)**：支援「🔥 出現次數」、「📅 出現年數」、「⏱️ 最新出題年份」、「🔤 字母 A-Z」，以及「🎯 歷年特定年份過濾」（如僅看 114 統測考題單字）。
  - **各等級分區調整 (Per-section Adjust)**：Level 1 至 Level 6 獨立下拉選單，依個人複習步調靈活排序。
- **構詞複合即時搜尋 (Compound Affix Search)**：點擊導覽列「🔍 構詞複合搜尋」，支援同時輸入 Prefix（如 `com*`）、Postfix（如 `*te`）及詞性（如 `verb`）即時在 4,842 單字中精準過濾（如找出 `comfort`, `complete`, `compete`, `communicate`）。
- **拓撲空間導覽**：以 Root (Life) 為核心，外圍展開 9 大領域與 38 個主題；進入領域時，Root 節點自動維持於遠離方向的相對位置，連線絕不碰撞節點。點選主題直接按 Level 1–6 六大等級展開單字清單。
- **圖片記憶輔助**：支援單字專屬圖檔關聯，內建維基百科自動抓圖工具，點選時即時展示。

### 2. 印歐語音變字根探索器 (Root Word Explorer)
> **原始碼目錄：** [`local_app/`](./local_app/) (CLI/核心), [`web/`](./web/) (前端) 與 [`api/`](./api/) (FastAPI 後端)

依據印歐語六大音變規律（唇音、齒音、舌音變換等）解析單字來源：
- **複合構詞搜尋 CLI 與 API**：
  - 本地命令列：`py local_app/root_explorer/main.py search com* *te verb`
  - 後端 API：`GET /api/v1/words/search?prefix=com&postfix=te&pos=verb`
- 輸入任何單字，即時拆解出核心字根（Root）、前綴（Prefix）與後綴（Suffix）。
- 建立字根與基礎英語單字（Simple English Words）之間的同源連鎖。
- 展示完整詞族網絡（Word Family Network）。

---

## 📁 專案目錄結構 (Project Structure)

```
english/
├── docs/                       # 🌟 考試單字知識圖譜（GitHub Pages 靜態網站發布目錄）
│   ├── index.html              # 圖譜導覽介面
│   ├── app.js                  # 核心圖譜邏輯與無限層級狀態機
│   ├── style.css               # 深色太空主題與響應式排版
│   ├── data/                   # 圖譜結構與單字資料
│   │   ├── graph.json          # Cytoscape 拓撲節點與連線
│   │   ├── vocab_data.json     # 4,842 詞條完整雙語資料
│   │   └── images/             # 單字關聯圖片庫
│   └── README.md
│
├── database/                   # 📚 核心資料庫與歷屆試題來源
│   ├── exam_words.json         # 6,701 單字主資料庫 (含 111 詞彙表 + 統測實際出現之考題字)
│   ├── exam_stats.json         # 歷屆試題出題率與頻次統計
│   ├── word_database.json      # 90 字根、109 詞綴資料庫
│   ├── word_roots_breakdown.json # 確定性字根/字首/字尾拆解與中英造詞邏輯庫
│   ├── word_sentences.json     # 歷屆試題真實例句與標準例句庫
│   ├── simple_definitions.json # Level 1-2 嚴格限制之簡明英釋庫
│   └── README.md
│
├── scripts/                    # ⚙️ 自動化處理與維護腳本
│   ├── build_exam_words.py     # PDF 官方詞彙擷取
│   ├── parse_exams.py          # 12 年歷屆試題 PDF 解析與統計
│   ├── build_root_breakdown.py # 確定性字根拆解資料庫建置
│   ├── build_sentence_examples.py # 統測真題與標準例句擷取
│   ├── build_simple_definitions.py # Level 1-2 簡明英釋生成
│   ├── auto_fetch_images.py    # 自動從維基百科抓取高畫質圖片並優化
│   ├── build_web_graph.py      # 圖譜階層與單字資料整合生成
│   ├── upload_word_image.py    # 單字圖片手動上傳工具
│   └── README.md
│
├── local_app/                  # 💻 本地端 Python 核心應用 (CLI & Search)
│   └── root_explorer/
│       ├── affix_search.py     # 字首/字尾/詞性複合搜尋引擎
│       └── main.py             # 命令列入口 (CLI)
│
├── web/                        # 🔤 Root Word Explorer 前端介面
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── api/                        # ⚡ Root Word Explorer 後端 (FastAPI)
│   ├── index.py                # FastAPI 入口 (含 /api/v1/words/search)
│   ├── decomposer.py           # 構詞分析與拆解引擎
│   ├── sound_rules.py          # 6 大音變轉換引擎
│   ├── graph_engine.py         # BFS 圖形引擎
│   └── requirements.txt
│
└── requirements.txt            # 專案 Python 相依套件
```

---

## ⚡ 快速開始 (Quick Start)

### 1. 運行單字知識圖譜 (Docs Web App)

純前端靜態架構，可直接使用 Python 內建伺服器啟動：

```bash
# 啟動伺服器
py -m http.server 8000 --directory docs

# 瀏覽器開啟 http://localhost:8000
```

### 2. 構詞複合搜尋 (CLI / Local App)

查詢符合字首、字尾與詞性條件的單字：

```bash
# 查詢 prefix: com*, postfix: *te, pos: verb
py local_app/root_explorer/main.py search com* *te verb

# 僅查字首與詞性 (com* + verb)
py local_app/root_explorer/main.py search com* "" verb
```

### 3. 自動抓取單字高畫質圖片 (Auto Image Fetcher)

```bash
# 自動為未有圖片的高頻詞抓取 Wikipedia 圖片 (預設 20 張)
py scripts/auto_fetch_images.py --count 20

# 指定單字自動抓取圖片
py scripts/auto_fetch_images.py --words orchid supercomputer rainforest scam
```

### 4. 為單字手動上傳關聯圖片

利用內建工具為單字新增記憶圖片：

```bash
# 互動式上傳
py scripts/upload_word_image.py

# 指定單字直接上傳
py scripts/upload_word_image.py -w apple -i path/to/apple.jpg
```

### 5. 運行字根探索器 API (FastAPI)

```bash
# 安裝相依套件
pip install -r requirements.txt

# 啟動 FastAPI 伺服器
cd api
python index.py
# API 運行於 http://localhost:8000
# 測試複合搜尋：http://localhost:8000/api/v1/words/search?prefix=com&postfix=te&pos=verb
```

---

## 📊 歷屆學測/統測出題數據速覽

| 等級 (Level) | 收錄單字數 | 歷屆出題單字數 | 出題涵蓋率 | 平均單字出題次數 |
|:---:|:---:|:---:|:---:|:---:|
| **Level 1** | 1,013 | 828 | **81.7%** | 20.5 次 |
| **Level 2** | 1,035 | 646 | **62.4%** | 4.3 次 |
| **Level 3** | 1,012 | 370 | **36.6%** | 3.0 次 |
| **Level 4** | 1,022 | 308 | **30.1%** | 2.3 次 |
| **Level 5** | 1,007 | 112 | **11.1%** | 2.3 次 |
| **Level 6** | 1,020 | 50 | **4.9%** | 1.5 次 |
| **總計** | **6,109** | **2,314** | **37.9%** | — |

---

## 🤝 致敬與參考資料 (Thanks & References)
- 大學入學考試中心 (CEEC) — 高中英文參考詞彙表
- 技專校院入學測驗中心 — 歷屆四技二專統一入學測驗英文科試題
- [ECDICT](https://github.com/skywind3000/ECDICT) — Free English-Chinese Dictionary Database
- 音變學習參考：[YouTube 英語詞根與語音轉變](https://m.youtube.com/watch?v=AFgZbU3AhlY&t=1s)
