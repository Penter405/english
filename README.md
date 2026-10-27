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
- **100% 雙語釋義**：全數單字收錄精準 **英文解釋 (English Definition)** 與 **繁體中文釋義**。
- **拓撲空間導覽**：以 Root (Life) 為核心，外圍展開 9 大領域與 38 個主題；進入領域時，Root 節點自動維持於遠離方向的相對位置，空間視角清晰。點選主題直接按 Level 1–6 六大等級展開單字清單。
- **直覺互動分流**：
  - **左鍵單擊 / 手機輕點**：彈出**英文詳細釋義**（全英沈浸模式）。
  - **右鍵點選 / 雙擊 (Double Click)**：彈出**繁體中文釋義**與歷屆出題次數。
- **圖片記憶輔助**：支援單字專屬圖檔關聯，點選時即時展示。

### 2. 印歐語音變字根探索器 (Root Word Explorer)
> **原始碼目錄：** [`web/`](./web/) (前端) 與 [`api/`](./api/) (後端 FastAPI)

依據印歐語六大音變規律（唇音、齒音、舌音變換等）解析單字來源：
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
│   └── README.md
│
├── scripts/                    # ⚙️ 自動化處理與維護腳本
│   ├── build_exam_words.py     # PDF 官方詞彙擷取
│   ├── parse_exams.py          # 12 年歷屆試題 PDF 解析與統計
│   ├── add_english_definitions.py # ECDICT 英文定義整合
│   ├── build_web_graph.py      # 圖譜階層生成
│   ├── upload_word_image.py    # 單字圖片上傳與自動壓縮工具
│   └── README.md
│
├── web/                        # 🔤 Root Word Explorer 前端介面
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── api/                        # ⚡ Root Word Explorer 後端 (FastAPI)
│   ├── index.py                # FastAPI 入口
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

### 2. 為單字上傳關聯圖片

利用內建工具為單字新增記憶圖片：

```bash
# 互動式上傳
py scripts/upload_word_image.py

# 指定單字直接上傳
py scripts/upload_word_image.py -w apple -i path/to/apple.jpg
```

### 3. 運行字根探索器 API (Root Word Explorer)

```bash
# 安裝相依套件
pip install -r requirements.txt

# 啟動 FastAPI 伺服器
cd api
python index.py
# API 運行於 http://localhost:8000
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
