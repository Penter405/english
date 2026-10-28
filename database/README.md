# Database

English vocabulary databases and exam analysis data for Taiwanese high school students (高中英文參考詞彙表 Level 1–6 & 歷屆統測/學測分析).

---

## Files Overview

### 1. Source Data (PDF)
- `高中英文參考詞彙表(111學年度起適用).pdf` — 官方詞彙表（Level 1–6，約 6,100 單字）
- `{year}-4y-00-e.pdf` — 歷屆學測/統測英文試題（104–115 學年度）
- `{year}-4y-00-e-standard.pdf` — 歷屆試題標準答案

### 2. Core Databases (JSON)

| File | Size | Records | Description |
|---|---|---|---|
| **`exam_words.json`** | ~5.3 MB | 6,701 words | 主單字庫：等級 (1–6)、詞性、詞形變化 (`forms`)、字族 (`word_family`)、出題紀錄、雙語釋義 (`definitions.en`, `definitions.zh`)、主題情境 (`situations`)。涵蓋官方 111 詞彙表 6,109 字 + 592 個統測歷屆試題實際出現之核心詞彙（如 orchid, supercomputer, scam, summer, sunlight 等） |
| **`exam_stats.json`** | 16 KB | Summary | 統計摘要：等級分佈、出題率、年度高頻排行、詞性分佈統計 |
| **`word_database.json`** | 53 KB | 90 roots / 109 affixes | Root Explorer 詞根詞綴資料庫：90 個字根、59 個前綴、50 個後綴、65 個基礎英語字 |
| **`word_roots_breakdown.json`** | ~920 KB | 1,976 entries | 確定性字根/字首/字尾拆解庫：包含 prefix, root, suffix 及其英繁釋義、合成邏輯 (`synthesis_zh`, `synthesis_en`) 與語音轉變規則 |
| **`word_sentences.json`** | ~1.4 MB | 6,701 words | 例句資料庫：優先整合 104–115 統測歷屆真題原句（1,209 句、涵蓋 2,579 個考字），其餘由權威標準例句補足 |
| **`simple_definitions.json`** | ~480 KB | 6,701 words | Level 1–2 簡明英釋庫：以國中小基礎字彙為限制生成的精簡英文定義 |

### 3. External / Local Data (not committed)
- `ecdict.csv` — ECDICT 英漢/英英字典（約 63 MB，已加入 `.gitignore`）

---

## Data Schemas

### `exam_words.json` Schema

```json
{
  "meta": {
    "version": 4,
    "created": "2026-10-27T...",
    "updated": "2026-10-27T...",
    "word_count": 6109,
    "level_counts": { "1": 1013, "2": 1035, "3": 1012, "4": 1022, "5": 1007, "6": 1020 }
  },
  "words": {
    "apple": {
      "level": 1,
      "pos": ["n."],
      "forms": {
        "plural": "apples"
      },
      "word_family": [],
      "appear_year": [105, 109],
      "appear_year_count": 2,
      "total_appear": 4,
      "sources": [
        { "year": 105, "count": 2 },
        { "year": 109, "count": 2 }
      ],
      "situations": ["Fruits", "Food & Cooking"],
      "definitions": {
        "en": [
          "n. fruit with red or yellow or green skin and sweet to tart crisp whitish flesh"
        ],
        "zh": [
          "n. 蘋果, 蘋果樹"
        ]
      }
    }
  }
}
```

### `word_database.json` Schema

```json
{
  "roots": {
    "port": {
      "meaning": "carry",
      "meaning_zh": "拿、運、帶",
      "origin_word": "fare",
      "rule": 1,
      "rule_name": "唇音變換 (p ↔ b ↔ f ↔ v)",
      "explanation": "拉丁語 portare (運送) 與古英語 faran (旅行、前進) 同源",
      "derived_words": ["export", "import", "transport", "portable", "support"]
    }
  },
  "affixes": {
    "prefixes": {
      "trans-": {
        "meaning": "across, beyond",
        "meaning_zh": "跨越、超越"
      }
    },
    "suffixes": {
      "-able": {
        "meaning": "capable of, fit for",
        "meaning_zh": "能夠...的、可以...的"
      }
    }
  },
  "simple_words": {
    "bear": {
      "meaning": "carry, produce",
      "meaning_zh": "攜帶、承受、生育"
    }
  }
}
```

---

## 歷屆試題等級與出題分佈統計

| 等級 (Level) | 總單字量 | 出現在歷屆試題單字量 | 出題涵蓋率 | 平均單字出題次數 |
|:---:|:---:|:---:|:---:|:---:|
| **Level 1** | 1,013 | 828 | **81.7%** | 20.5 次 |
| **Level 2** | 1,035 | 646 | **62.4%** | 4.3 次 |
| **Level 3** | 1,012 | 370 | **36.6%** | 3.0 次 |
| **Level 4** | 1,022 | 308 | **30.1%** | 2.3 次 |
| **Level 5** | 1,007 | 112 | **11.1%** | 2.3 次 |
| **Level 6** | 1,020 | 50 | **4.9%** | 1.5 次 |
| **總計** | **6,109** | **2,314** | **37.9%** | — |

> **說明**：
> - 統測與學測題目強烈偏重 **Level 1–4** 單字（總出題涵蓋率高達 80% 以上）。
> - Web 視覺化圖形系統即依據此特性，精選收錄「**歷屆曾出題 OR Level 1–4**」之共 4,244 個單字。
