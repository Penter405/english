# 外部資料來源與重建方式

## 1. 字根 / 字首 / 字尾資料庫：`word_morphology_verified.json`

**規則：Wiktionary 和 MorphoLex-en 兩個來源說法一致才收錄。** 不一致或只有一邊有資料的字，會寫進 `morphology_conflicts.json`（附原因），不會顯示在網站上。

| 來源 | 內容 | 授權 |
|---|---|---|
| [Wiktionary](https://en.wiktionary.org)（經 [kaikki.org](https://kaikki.org/dictionary/English/) wiktextract 匯出） | 詞源模板（`af`、`prefix`、`suffix`、`surf` …）與詞源說明文字 | CC-BY-SA |
| [MorphoLex-en](https://github.com/hugomailhot/MorphoLex-en)（Sánchez-Gutiérrez et al., 2018） | 約 7 萬字的構詞切分 | CC-BY-NC-SA |
| ECDICT（本機 `ecdict.csv`） | 把 Wiktionary 的英文註解翻成中文（OpenCC 轉繁體） | MIT |

`status` 欄位：

- `verified`：兩邊都拆得出來，而且字首、字尾、字根都對得上。
  - `type: "root"`：拆到拉丁 / 希臘字根，例如 `predict = pre- + dict`
  - `type: "base"`：英文基礎字加詞綴，例如 `survival = survive + -al`
  - `type: "compound"`：複合字，例如 `sunlight = sun + light`
- `monomorphemic`：兩邊都說這是單一詞素、不能拆，例如 `corner`、`number`、`flower`

重建：

```bash
# 1) Wiktionary (串流過濾，約 10 分鐘，不需要先存 3.4 GB 原檔)
curl -L https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl | py scripts/filter_wiktionary.py

# 2) MorphoLex: 下載 MorphoLEX_en.xlsx 放到 database/raw/ (已附)
#    https://raw.githubusercontent.com/hugomailhot/MorphoLex-en/master/MorphoLEX_en.xlsx

# 3) 交叉比對
pip install opencc-python-reimplemented
py scripts/build_verified_morphology.py      # -> word_morphology_verified.json / morphology_conflicts.json / morphology_report.md

# 4) 更新網站資料
py scripts/build_web_graph.py
```

### 沒有共識的字：`word_etymology_wiktionary.json`（單一來源）

兩來源說法不同時（最常見是 MorphoLex 說 `accept` 不可拆，Wiktionary 卻拆到拉丁文），改列出 **Wiktionary 的古典語源拆解**，並寫出每個部件的意思：

```
accept  ← 拉丁文 ad-(朝向) + capiō(拿、取 / to take)
atom    ← 古希臘文 ἀ-(不) + τέμνω(切、割 / to cut) + -ος(名詞語尾)
above   ← 古英文 bī(在旁邊) + ufan(在上方)
```

- 網站上用黃色「Wiktionary 單一來源」標籤顯示，和綠色「雙來源確認」區分。
- 部件意思優先用 Wiktionary 的英文註解，再用 ECDICT 翻成中文；中英文並列，方便對照。
- 不收：帶 `*` 的重建形式（語言學家推測的原始語言）、解析殘留（Latin、verb 等說明用詞）、沒有字根的拆解，以及所有部件都沒有意思的拆解。
- 已知限制：ECDICT 偶爾挑錯義項（例如 sib "related" 被翻成「講述的」），所以網站同時顯示英文原意；少數字的語言標籤可能不準。

舊的 `word_roots_breakdown.json`（演算法推導）已不再被 `build_web_graph.py` 使用，只保留作為對照。

## 2. 下一個單字預測：`docs/data/next_word.json`

| 來源 | 內容 | 授權 |
|---|---|---|
| [Tatoeba](https://tatoeba.org) 英文句子 | 約 200 萬句真人撰寫的例句 | CC-BY 2.0 FR |

```bash
curl -O https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences.tsv.bz2
# 解壓成 database/raw/eng_sentences.tsv
py scripts/build_next_word_model.py
```

- 機率 = 某個情境出現後，下一個字是 X 的次數 ÷ 這個情境的總次數。
- 查詢順序：前 2 個字 → 前 1 個字 → 句首。
- Tatoeba 例句很常用 Tom、Mary 這類角色名，所以人名、地名會合併成一個「人名 / 地名」選項。

## 3. 難度分級與基礎英文解釋

### `word_difficulty.json`（`scripts/build_word_difficulty.py`）

- `level`：考試詞彙表等級（表外為 null；變化形會還原成原型再查，例如 letters → letter）
- `est_level`：判斷難度時實際使用的等級。考試表內的字就是考試 Level；表外的字依 [wordfreq](https://github.com/rspeer/wordfreq) 常用度推估，7 代表超出高中範圍
- `stars`：常用度 1–5 顆星，網站上顯示在等級旁邊

推估切點是用考試表內單字的常用度分布校準出來的：各等級常用度（Zipf）的中位數為 L1 5.01、L2 4.53、L3 4.14、L4 3.98、L5 3.95、L6 3.56。可以看出 Level 3–5 的常用度高度重疊，所以只看考試 Level 不夠準。

### `simple_definitions.json` v2（`scripts/build_simple_definitions.py`）

候選來源依序是：人工撰寫 → [Simple English Wiktionary](https://simple.wiktionary.org)（`database/raw/simple_wiktionary.jsonl.gz`）→ 英文 Wiktionary → ECDICT/WordNet。

挑選規則：
1. 主要意思優先：考試表的第一個詞性 → 該詞性的第一個詞條 → 第 0 個義項。
2. 同一層級裡，挑用字最簡單的。
3. 拒收：被截斷的句子、「Plural of…」這類定義、古語或俚語義項、只用單字本身或同字族來解釋的定義。

每條解釋都標上 `tier`：

| tier | 意思 | 網站標示 |
|---|---|---|
| 0 | 全部只用 Level 1–2 的字 | 🟢 只用 Level 1–2 單字 |
| 1 | 有較難的字，但都比單字本身簡單 | 🟡 |
| 2 | 用到不比單字本身簡單的字 | 🟠，並列出較難的字（可點擊查詢） |

完整統計和 tier 2 清單見 `simple_definitions_report.md`。tier 2 的字需要人工或 AI 改寫。

重建方式：

```bash
curl -L -o database/raw/simple_wiktionary.jsonl.gz https://kaikki.org/dictionary/downloads/simple/simple-extract.jsonl.gz
py scripts/build_word_difficulty.py
py scripts/build_simple_definitions.py
py scripts/build_web_graph.py
```

## 4. 相近字 / 相反字：`docs/data/word_relations.json`

| 來源 | 內容 | 授權 |
|---|---|---|
| [Simple English Wiktionary](https://simple.wiktionary.org)（`database/raw/simple_wiktionary.jsonl.gz`，和第 3 節同一個檔） | 依義項列出的 synonyms / antonyms，用字簡單 | CC-BY-SA |
| [Princeton WordNet 3.0](https://wordnet.princeton.edu)（經 NLTK 自動下載） | 同義詞集的其他詞、詞條直接反義詞 | WordNet License |

```bash
py scripts/build_word_relations.py      # 第一次會自動 nltk.download('wordnet')
```

- **獨立檔案、不覆蓋 `vocab_data.json`**：主資料檔已約 25 MB，所以相近字 / 相反字另存一個約 300 KB 的檔案。網站首頁顯示後才在背景載入，重跑 `build_web_graph.py` 也不會動到它。
- 每個字最多 10 個相近字、8 個相反字。排序：網站查得到的字（可以點）→ 兩個資料庫都列出（網站上打 ✓）→ 等級簡單。
- 過濾：只收和這個字詞性相符的義項；WordNet 只用每個詞性最主要的 2 個義項找相近字；不收同字族變化形、縮寫、WordNet 的多字片語與連字號複合字、太罕見的字。
- 變化形（例如 happier）沒有單獨資料，網站會改顯示原型 happy 的資料。
- 已知限制：資料庫本身偶有怪的配對（例如 happy 的相反字有 moving），需要的話可以在腳本裡加人工排除清單。
