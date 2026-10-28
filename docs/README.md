# Interactive Exam Vocabulary Graph (Web App)

> **GitHub Pages:** [https://penter405.github.io/english/](https://penter405.github.io/english/)

專為台灣高中/高職統測及學測設計的**互動式單字知識圖譜**（基於 Cytoscape.js 與純靜態前端架構）。

---

## 🌟 核心特色 (Option A 架構)

1. **4,842 個核心考試單字**：
   - 篩選標準：**歷屆試題曾出題 OR Level 1–4**，精準鎖定考試重點（含歷屆統測考題高頻詞如 orchid, supercomputer, scam, rainforest, backpacker 等）。
   - **3 軌多模態釋義**：
     - **🟢 基礎英釋 (Level 1–2)**：完全限制在國中小 Level 1–2 單字範圍撰寫的簡明英文解釋，降低閱讀門檻。
     - **📘 詳細英釋 (Advanced)**：完整 ECDICT 權威英文定義。
     - **🇹🇼 繁體中文**：精準台灣慣用詞性與中文對譯。
2. **確定性字根/字首/字尾拆解 (Deterministic Root & Affix Breakdown)**：
   - 直接依據 `database/word_roots_breakdown.json` 資料庫查詢，無啟發式演算法猜測。
   - 結構化呈現 `Prefix` (前綴)、`Root` (詞根)、`Suffix` (後綴) 及中英文造詞邏輯（例：`predict` ➔ `pre-(事先) + dict(說/講)`）。
3. **詞源原型 (Origin) 與時態/詞性衍生變體互通 (Clickable Origin & Family Variants)**：
   - 每個單字皆關聯至其原始原型（如 `playable` ➔ `play`、`picked` ➔ `pick`、`comfortably` ➔ `comfort`）。
   - 彈窗直接展開所有同源衍生詞與動詞時態變化（如 `0: pick (原型)`, `1: picked (過去式/分詞)`, `2: picking (現在分詞)`, `3: picks (三單)`, `picker (施事名詞)`）。
   - **所有變體與原型按鈕 100% 可點選**：點擊立即切換至該單字進行深層查詢，內建「← 返回上一個單字」歷史堆疊。
   - **頂部路徑防無限延伸 (Single-slot Additional Search)**：進入延伸查詢時，頂部路徑只會顯示 `... › 🔍 Additional Search: {word}`，連續點選變體時就地替換該標籤，永不無限延伸路徑。
4. **統測真題與標準例句 (Authentic Sentence Examples)**：
   - 整合 104–115 統測歷屆考題真題原句與權威例句，關鍵單字高亮顯示。
4. **多維出題排序與特定年份調整 (Multi-criteria Adjust Buttons)**：
   - **全域調整工具列 (Global Adjust Bar)**：
     - `🔥 依出題次數降序` (預設高頻先排)
     - `📅 依出題年數降序` (歷年常考指標)
     - `⏱️ 最新出題年份先排` (近期趨勢)
     - `🔤 依字母 A-Z`
     - `🎯 歷年特定年份過濾`（如 114 統測、113 統測... 只看該年出現的字）
   - **分區獨立下拉選單 (Per-section Adjust)**：Level 1 至 Level 6 每個難度區塊皆可獨立自訂排序。
5. **構詞複合即時搜尋 (Compound Affix Search Modal)**：
   - 點擊右上角「🔍 構詞複合搜尋」，支援同時輸入：
     - **字首 (Prefix)**：如 `com*`, `pre*`, `un*`
     - **字尾 (Postfix)**：如 `*te`, `*tion`, `*able`
     - **詞性 (POS)**：動詞 (Verb)、名詞 (Noun)、形容詞 (Adjective)、副詞 (Adverb)
   - 支援即時在 4,842 單字中精準過濾（例如：`com*` + `*te` + `verb` 即時找出 `complete`, `compete`, `communicate` 等）。
6. **9 大核心領域 × 38 個直觀子主題**：
   - **人物與特質 (People & Character)**：個性品質（如 brave, honest）、外貌體態、身分人際、家庭生命歷程。
   - **心智與情緒 (Mind & Emotions)**：情緒感受、思維判斷、態度動機目標、溝通言論。
   - **身體與動作 (Body & Actions)**：器官與健康、肢體位移動作、肢體操作、感官知覺。
   - **日常與生活 (Daily Life & Living)**：飲食餐飲、居住家居、服飾穿搭、消費金融。
   - **學習與教育 (School & Learning)**：校園課堂、閱讀寫作、考試學術、語言文字。
   - **職場與社會 (Work & Society)**：職業工作、商業經濟、政府政治、法律正義、文化社會。
   - **科技與交通 (Tech & Transport)**：電腦網路、通訊影音、陸上交通、航空航海、旅行物流。
   - **自然與科學 (Nature & Science)**：動物世界、植物生態、氣候地理、理化宇宙。
   - **邏輯與修飾 (Logic & Modifiers)**：時間頻率、空間方向、程度比較、變化因果。
7. **無連線碰撞幾何排版（Zero Line-Node Collisions）**：
   - **Root View**：中央為 `Life`，外圍環繞 9 個核心領域，純放射狀連線。
   - **Domain View**：進入領域後，該領域置中（`0, 0`），**父節點（Root）以反向角度（`ROOT_LINK_DIST = 520`）呈現在對應位置**（虛線連接、縮小呈現為 Breadcrumb）。
   - **子節點外展扇形（Outward Fan）**：子主題節點集中於**遠離 Root 的外側扇形（夾角差距 > 105°）**展開，**連線絕對不會碰觸或穿過其他任何節點**。
8. **取消圖中 Basic/Medium/Hard 節點，點入直接呈現 6 個等級**：
   - 點選任何主題節點，立即開啟該主題的單字列表頁面，直接按 **Level 1 至 Level 6** 六大難度清晰分區呈現單字晶片。
9. **圖片輔助記憶**：
   - 支援單字圖片關聯，彈窗自動加載對應圖像（位於 `data/images/{word}.png`）。
   - 提供自動批次抓圖工具 [`scripts/auto_fetch_images.py`](../scripts/auto_fetch_images.py)。

---

## 📁 檔案架構

```
docs/
├── index.html           # 前端首頁（Cytoscape.js 畫布、返回按鈕與單字彈窗）
├── app.js               # 核心邏輯：防碰撞幾何拓撲、視角切換、6 等級渲染與彈窗分流
├── style.css            # 深色太空主題、Level 1–6 色彩、彈窗與響應式排版
└── data/
    ├── graph.json       # 48 節點（1 Root + 9 Domains + 38 Topics）圖形拓撲結構
    ├── vocab_data.json  # 4,842 個單字的完整釋義、出題紀錄、詞形等資料
    └── images/          # 單字專屬圖片（格式為 {word}.png）
```

---

## 🧭 操作指南

### 1. 本地啟動預覽

```bash
# 在專案根目錄下執行
py -m http.server 8000 --directory docs

# 瀏覽器開啟 http://localhost:8000
```

### 2. 圖譜瀏覽與操作方式

- **拖曳畫布**：按住滑鼠左鍵空白處拖曳移動視野。
- **縮放視野**：滾動滑鼠滾輪，或點選右下角 `+` / `-` 按鈕。
- **進入領域**：點選任一外圍領域節點（如 `People & Character`, `Daily Life`, `Nature & Science`）。
- **查看主題單字**：點選主題節點（如 `Personality & Traits`），立即進入 6 等級單字清單。
- **返回圖譜**：點擊右上角「← Back to Graph」或點選圖譜上的 Root 父節點。
- **單字釋義**：
  - **左鍵點擊單字晶片**：查看英文定義與考試資訊。
  - **右鍵點擊或雙擊**：查看繁體中文釋義。
