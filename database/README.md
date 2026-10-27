# Database

## Files

### Source Data (PDF)
- `高中英文參考詞彙表(111學年度起適用).pdf` — 官方詞彙表 (Level 1–6, ~6100 words)
- `{year}-4y-00-e.pdf` — 歷屆學測英文試題 (104–115 學年)
- `{year}-4y-00-e-standard.pdf` — 歷屆學測標準答案

### Generated Data (JSON)

| File | Size | Description |
|------|------|-------------|
| **`exam_words.json`** | 3.4 MB | 主資料庫：6109 個單字，含等級、詞性、詞形、詞族、出題紀錄、中文釋義、主題情境 |
| **`exam_stats.json`** | 16 KB | 統計摘要：出題頻率、等級分佈、高頻字排行 |
| **`word_database.json`** | 53 KB | Root Explorer 引擎資料庫：90 字根、59 前綴、50 後綴、65 基礎字 |

### Topic Vocabulary (獨立，之後整合)
- `topic_vocabulary_5000.json` — 100 主題 × 50 單字
- `topic_vocabulary_graph.json` — 主題關聯圖

### External Data (not committed)
- `ecdict.csv` — ECDICT 英中辭典 (63 MB, listed in .gitignore)

## exam_words.json Schema

```json
{
  "meta": { "version", "created", "updated", "word_count", "level_counts" },
  "words": {
    "word": {
      "level": 1-6,
      "pos": ["v.", "n."],
      "forms": ["want", "wanted", "wanting", "wants"],
      "word_family": ["achievement"],
      "appear_year": [104, 108, 112],
      "appear_year_count": 3,
      "total_appear": 15,
      "sources": [{"year": 104, "count": 5}, ...],
      "situations": ["Economics", "Goals & Decisions"],
      "definitions": ["vt. 需要;想要", "n. 需要;缺乏"]
    }
  }
}
```

## word_database.json Schema

```json
{
  "roots": {
    "root": {
      "meaning": "English meaning",
      "meaning_zh": "中文意思",
      "origin_word": "simple English word",
      "rule": 1-6,
      "rule_name": "Sound change rule name",
      "explanation": "How origin word connects to root",
      "derived_words": ["word1", "word2", ...]
    }
  },
  "affixes": {
    "prefixes": { "prefix": {"meaning": "...", "meaning_zh": "..."} },
    "suffixes": { "suffix": {"meaning": "...", "meaning_zh": "..."} }
  },
  "simple_words": { "word": {"meaning": "...", "meaning_zh": "..."} }
}
```

## Scripts (in `scripts/`)

| Script | Purpose |
|--------|---------|
| `build_exam_words.py` | Phase 1: Extract words + levels from vocabulary PDF |
| `parse_exams.py` | Phase 2: Parse exam PDFs, populate appear_year/total_appear |
| `enrich_vocab.py` | Phase 3: Generate forms, word_family, situations |
| `import_definitions.py` | Import Chinese definitions from ECDICT |
| `generate_stats.py` | Generate exam_stats.json summary |
| `upgrade_word_db.py` | Expand word_database.json with more roots/affixes |

## Level Distribution

| Level | Words | Appeared in Exams | Rate | Avg Appearances |
|-------|-------|-------------------|------|-----------------|
| 1 | 1,013 | 828 | 81.7% | 20.5 |
| 2 | 1,035 | 646 | 62.4% | 4.3 |
| 3 | 1,012 | 370 | 36.6% | 3.0 |
| 4 | 1,022 | 308 | 30.1% | 2.3 |
| 5 | 1,007 | 112 | 11.1% | 2.3 |
| 6 | 1,020 | 50 | 4.9% | 1.5 |
