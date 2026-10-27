# Interactive Exam Vocabulary Graph (Web App)

> **GitHub Pages:** [https://penter405.github.io/english/](https://penter405.github.io/english/)

專為台灣高中/高職統測及學測設計的**互動式單字知識圖譜**（基於 Cytoscape.js 與純靜態前端架構）。

---

## 🌟 核心特色 (Option A 架構)

1. **4,842 個核心考試單字**：
   - 篩選標準：**歷屆試題曾出題 OR Level 1–4**，精準鎖定考試重點（含歷屆統測考題高頻詞如 orchid, supercomputer, scam, rainforest, backpacker 等）。
   - 100% 具備 **English Definition** 與 **繁體中文釋義**。
2. **9 大核心領域 × 38 個直觀子主題**：
   - **人物與特質 (People & Character)**：個性品質（如 brave, honest）、外貌體態、身分人際、家庭生命歷程。
   - **心智與情緒 (Mind & Emotions)**：情緒感受、思維判斷、態度動機目標、溝通言論。
   - **身體與動作 (Body & Actions)**：器官與健康、肢體位移動作、肢體操作、感官知覺。
   - **日常與生活 (Daily Life & Living)**：飲食餐飲、居住家居、服飾穿搭、消費金融。
   - **學習與教育 (School & Learning)**：校園課堂、閱讀寫作、考試學術、語言文字。
   - **職場與社會 (Work & Society)**：職業工作、商業經濟、政府政治、法律正義、文化社會。
   - **科技與交通 (Tech & Transport)**：電腦網路、通訊影音、陸上交通、航空航海、旅行物流。
   - **自然與科學 (Nature & Science)**：動物世界、植物生態、氣候地理、理化宇宙。
   - **邏輯與修飾 (Logic & Modifiers)**：時間頻率、空間方向、程度比較、變化因果。
3. **無連線碰撞幾何排版（Zero Line-Node Collisions）**：
   - **Root View**：中央為 `Life`，外圍環繞 9 個核心領域，純放射狀連線。
   - **Domain View**：進入領域後，該領域置中（`0, 0`），**父節點（Root）以反向角度（`ROOT_LINK_DIST = 520`）呈現在對應位置**（虛線連接、縮小呈現為 Breadcrumb）。
   - **子節點外展扇形（Outward Fan）**：子主題節點集中於**遠離 Root 的外側扇形（夾角差距 > 105°）**展開，**連線絕對不會碰觸或穿過其他任何節點**。
   - 點擊父節點立即平滑返回上一層或根節點。
4. **取消圖中 Basic/Medium/Hard 節點，點入直接呈現 6 個等級**：
   - 圖形畫布內不設置雜亂的難度子節點。
   - 點選任何主題節點，立即開啟該主題的單字列表頁面。
   - 頁面直接按 **Level 1 至 Level 6** 六大官方難度清晰分區呈現單字晶片。
5. **雙模態釋義交互**：
   - **左鍵單擊 / 手機輕點**：彈出詳細**英文解釋**（全英閱讀模式）。
   - **右鍵點選 / 雙擊（Double Click）**：彈出**繁體中文釋義**。
   - 彈窗內建切換按鈕，可隨時在英中雙語間切換，並顯示出題紀錄與詞性。
6. **圖片輔助記憶**：
   - 支援單字圖片關聯，彈窗自動加載對應圖像（位於 `data/images/{word}.png`）。
   - 提供 Python 上傳工具 [`scripts/upload_word_image.py`](../scripts/upload_word_image.py) 進行維護。

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
