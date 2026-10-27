# Interactive Exam Vocabulary Graph (Web App)

> **GitHub Pages:** [https://penter405.github.io/english/](https://penter405.github.io/english/)

專為台灣高中/高職統測及學測設計的**互動式單字知識圖譜**（基於 Cytoscape.js 與純靜態前端架構）。

---

## 🌟 核心特色

1. **4,200+ 核心考試單字**：
   - 篩選標準：**歷屆試題曾出題 OR Level 1–4**，精準鎖定考試重點。
   - 100% 具備 **English Definition** 與 **繁體中文釋義**。
2. **10 大領域 × 100 個主題分類**：
   - 10 大核心領域：Home & Daily Life, Food, Transport, Technology, Education, Work, Society, Thought & Concepts, Science, Nature。
   - 100 個情境主題完整對應試題語境，圖形排版具備精確極座標角度與位置。
3. **經典拓撲導覽邏輯（遠離 Root 相對視角）**：
   - **Root View**：中心為 `Life`，外圍環繞 10 個核心領域。
   - **Domain View**：進入領域後，該領域置中（`0, 0`），**父節點（Root）以反向角度（`ROOT_LINK_DIST = 500`）呈現在對應位置**（虛線連接、縮小呈現為 Breadcrumb），主題節點（Topics）依角度環繞展開。
   - 點擊父節點立即平滑返回上一層或根節點。
4. **取消圖中 Basic/Medium/Hard 節點，點入直接呈現 6 個等級**：
   - 圖形畫布內不設置雜亂的難度子節點。
   - 點選任何主題（Topic）節點，立即開啟該主題的單字列表頁面。
   - 頁面直接按 **Level 1 至 Level 6** 六大官方難度清晰分區呈现單字晶片。
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
├── app.js               # 核心邏輯：拓撲座標定位、視角切換、6 等級渲染與彈窗分流
├── style.css            # 深色太空主題、Level 1–6 色彩、彈窗與響應式排版
└── data/
    ├── graph.json       # 111 節點（1 Root + 10 Domains + 100 Topics）圖形拓撲結構
    ├── vocab_data.json  # 4,244 個單字的完整釋義、出題紀錄、詞形等資料
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
- **進入領域**：點選任一外圍領域節點（如 `Food`, `Technology`, `Home & Daily Life`）。
- **查看主題單字**：點選主題節點，立即進入 6 等級單字清單。
- **返回圖譜**：點擊右上角「← Back to Graph」或點選圖譜上的 Root 父節點。
- **單字釋義**：
  - **左鍵點擊單字晶片**：查看英文定義與考試資訊。
  - **右鍵點擊或雙擊**：查看繁體中文釋義。
