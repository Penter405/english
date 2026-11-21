"""
build_word_relations.py
-----------------------
產生「相近字 (synonyms) / 相反字 (antonyms)」資料：docs/data/word_relations.json

為了不讓 docs/data/vocab_data.json (已約 25 MB) 更重，這份資料寫成獨立檔案，
網站第一次打開單字視窗時才載入 (lazy load)，不影響首頁載入速度。
重跑 build_web_graph.py 也不會覆蓋這個檔案。

資料來源 (都是直接下載的現成資料庫)：
  1. Simple English Wiktionary (database/raw/simple_wiktionary.jsonl.gz, CC-BY-SA)
     依義項列出的 synonyms / antonyms，用字簡單，排序優先。
     下載: curl -L -o database/raw/simple_wiktionary.jsonl.gz https://kaikki.org/dictionary/downloads/simple/simple-extract.jsonl.gz
  2. WordNet 3.0 (Princeton, 經 NLTK 下載, WordNet License)
     同義詞集 (synset) 的其他詞 + 詞條直接反義詞。
     第一次執行會自動 nltk.download('wordnet')。

排序規則 (每個字最多 10 個相近字、8 個相反字)：
  網站裡查得到的字 > 查不到的；兩個來源都有 > 只有一個來源；等級簡單 > 難。
  排除：單字本身、同字族變化形、超過兩個字的片語、太罕見的字 (wordfreq Zipf < 2.5)。

輸出格式 (精簡以縮小檔案)：
  {"meta": {...}, "words": {"happy": {"s": [["glad", 1, "sw"], ...], "a": [["sad", 1, "sw"], ...]}}}
  每筆 = [字, 推估等級 (1-6, 7=超出高中, null=未知), 來源 s=Simple Wiktionary / w=WordNet / sw=兩者]

執行：
  py scripts/build_word_relations.py
"""
import gzip
import json
import os
import re
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "database"
VOCAB = BASE / "docs" / "data" / "vocab_data.json"
DIFF = DB / "word_difficulty.json"
SIMPLE = DB / "raw" / "simple_wiktionary.jsonl.gz"
OUT = BASE / "docs" / "data" / "word_relations.json"

MAX_SYN = 10
MAX_ANT = 8
MIN_ZIPF = 2.5
WORD_RE = re.compile(r"^[a-z][a-z'\-]*( [a-z][a-z'\-]*)?$")   # 單字或兩個字的片語

# vocab_data 的詞性標記 -> WordNet 詞性
POS_MAP = {"n.": "n", "v.": "v", "a.": "as", "adj.": "as", "ad.": "r", "adv.": "r"}
# Simple Wiktionary 詞性 -> WordNet 詞性 (只用來對齊，不對應的照收)
SW_POS = {"noun": "n", "verb": "v", "adj": "as", "adv": "r"}


def load_wordnet():
    try:
        import nltk
        from nltk.corpus import wordnet as wn
        try:
            wn.ensure_loaded()
        except LookupError:
            nltk.download("wordnet", quiet=True)
            from nltk.corpus import wordnet as wn  # noqa: F811
            wn.ensure_loaded()
        return wn
    except Exception as e:  # pragma: no cover
        print(f"  ! WordNet 無法載入 ({e})，只用 Simple Wiktionary")
        return None


def load_simple():
    """word -> {'syn': [(w, pos)], 'ant': [(w, pos)]}，依義項順序。"""
    out = defaultdict(lambda: {"syn": [], "ant": []})
    if not SIMPLE.exists():
        print(f"  ! 找不到 {SIMPLE}，略過 Simple Wiktionary")
        return out
    with gzip.open(SIMPLE, "rt", encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            if e.get("lang_code") != "en":
                continue
            w = (e.get("word") or "").lower()
            pos = SW_POS.get(e.get("pos"), "")
            blocks = [e] + list(e.get("senses") or [])[:3]   # 只看前 3 個義項
            for b in blocks:
                for key, dst in (("synonyms", "syn"), ("antonyms", "ant")):
                    for x in b.get(key) or []:
                        t = (x.get("word") or "").strip().lower()
                        if t:
                            out[w][dst].append((t, pos))
    return out


def wordnet_relations(wn, word, pos_filter):
    syn, ant = [], []
    if wn is None:
        return syn, ant
    synsets = wn.synsets(word)
    if pos_filter:
        filtered = [s for s in synsets if s.pos() in pos_filter]
        synsets = filtered or synsets
    # 每個詞性只取最常用的前 3 個義項，避免冷僻義項帶進奇怪的字
    per_pos = defaultdict(int)
    picked = []
    for s in synsets:
        p = "a" if s.pos() in "as" else s.pos()
        if per_pos[p] < 3:
            per_pos[p] += 1
            picked.append(s)
    seen_pos = defaultdict(int)
    for s in picked:
        p = "a" if s.pos() in "as" else s.pos()
        main_sense = seen_pos[p] < 2   # 相近字只取每個詞性最主要的 2 個義項，避免冷僻義項
        seen_pos[p] += 1
        for lem in s.lemmas():
            name = lem.name().replace("_", " ").lower()
            if lem.name().lower() == word:
                for a in lem.antonyms():
                    ant.append(a.name().replace("_", " ").lower())
            elif main_sense:
                syn.append(name)
        if main_sense and s.pos() in "as":   # 形容詞：similar_to 也算相近字
            for sim in s.similar_tos()[:4]:
                for lem in sim.lemmas()[:2]:
                    syn.append(lem.name().replace("_", " ").lower())
    # WordNet 的多字片語 / 連字號複合字 (computing machine, world-shaking…) 對學習者幫助不大，只留單字
    ok = lambda x: " " not in x and "-" not in x
    return [x for x in syn if ok(x)], [x for x in ant if ok(x)]


def main():
    print("Loading vocab / difficulty ...")
    vocab = json.load(open(VOCAB, encoding="utf-8"))
    diff = json.load(open(DIFF, encoding="utf-8"))["words"]
    try:
        from wordfreq import zipf_frequency
    except ImportError:
        zipf_frequency = None

    def level_of(w):
        d = diff.get(w)
        if d and d.get("est_level") is not None:
            return d["est_level"] or 1
        v = vocab.get(w)
        if v and v.get("diff") and (v["diff"].get("l") or v["diff"].get("e")):
            return v["diff"].get("l") or v["diff"].get("e")
        # 考試表外：依 wordfreq 常用度粗估 (切點參考 build_word_difficulty.py 的各級中位數)
        z = zipf(w)
        for cut, lv in ((5.0, 1), (4.5, 2), (4.15, 3), (3.95, 4), (3.75, 5), (3.3, 6)):
            if z >= cut:
                return lv
        return 7

    def zipf(w):
        d = diff.get(w)
        if d and d.get("zipf") is not None:
            return d["zipf"]
        return zipf_frequency(w, "en") if zipf_frequency else 3.0

    print("Loading Simple English Wiktionary ...")
    simple = load_simple()
    print("Loading WordNet ...")
    wn = load_wordnet()

    # 只替「原型」建資料；變化形 (is_variant_fallback) 在網站上會改查原型
    targets = [w for w, v in vocab.items() if not v.get("is_variant_fallback")]
    print(f"Building relations for {len(targets)} words ...")

    raw = {}
    for w in targets:
        v = vocab[w]
        pos_filter = "".join(POS_MAP.get(p, "") for p in (v.get("pos") or []))
        family = {w, (v.get("origin") or "").lower()}
        family |= {x.lower() for x in (v.get("forms") or [])}
        family |= {x["w"].lower() for x in (v.get("variants") or []) if x.get("w")}

        cands = {"syn": {}, "ant": {}}

        def add(kind, t, src, order):
            t = t.strip().lower()
            if not t or t in family or not WORD_RE.match(t):
                return
            if len(t) <= 4 and w.startswith(t):   # 縮寫 (computer -> com)
                return
            c = cands[kind].setdefault(t, {"src": set(), "order": order})
            c["src"].add(src)
            c["order"] = min(c["order"], order)

        sw = simple.get(w, {"syn": [], "ant": []})
        for kind in ("syn", "ant"):
            lst = sw[kind]
            # 只收和這個字的詞性相符的詞條 (例如 ancient 形容詞不收名詞「旗子」義)
            if pos_filter and any(p and p[0] in pos_filter for _t, p in lst):
                lst = [(t, p) for t, p in lst if not p or p[0] in pos_filter]
            for i, (t, _p) in enumerate(lst):
                add(kind, t, "s", i)
        wsyn, want = wordnet_relations(wn, w, pos_filter)
        for i, t in enumerate(wsyn):
            add("syn", t, "w", 100 + i)
        for i, t in enumerate(want):
            add("ant", t, "w", 100 + i)
        raw[w] = cands

    # 反義詞補成雙向 (A 是 B 的相反字，B 也是 A 的相反字)
    for w, cands in list(raw.items()):
        for t, c in list(cands["ant"].items()):
            if t in raw and w not in raw[t]["ant"]:
                raw[t]["ant"][w] = {"src": set(c["src"]), "order": 500}

    words_out = {}
    n_syn = n_ant = 0
    for w, cands in raw.items():
        rec = {}
        for kind, key, cap in (("syn", "s", MAX_SYN), ("ant", "a", MAX_ANT)):
            items = []
            for t, c in cands[kind].items():
                single = " " not in t
                if single and zipf(t) < (MIN_ZIPF if "s" in c["src"] else 3.0):
                    continue
                lv = level_of(t) if single else None
                items.append((t, lv, c))
            items.sort(key=lambda x: (
                0 if x[0] in vocab else 1,         # 網站查得到的字優先 (可以點)
                -len(x[2]["src"]),                 # 兩個來源都有優先
                x[1] if x[1] is not None else 8,   # 等級簡單優先
                x[2]["order"],
            ))
            items = items[:cap]
            if items:
                rec[key] = [[t, lv, "".join(sorted(c["src"], key="sw".index))] for t, lv, c in items]
        if rec:
            words_out[w] = rec
            n_syn += bool(rec.get("s"))
            n_ant += bool(rec.get("a"))

    out = {
        "meta": {
            "description": "相近字 / 相反字。每筆 = [字, 推估等級(7=超出高中), 來源 s=Simple Wiktionary w=WordNet]",
            "sources": {
                "s": "Simple English Wiktionary via kaikki.org (CC-BY-SA)",
                "w": "Princeton WordNet 3.0 via NLTK (WordNet License)",
            },
            "words_with_synonyms": n_syn,
            "words_with_antonyms": n_ant,
        },
        "words": words_out,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote {OUT} ({len(words_out)} words, syn {n_syn}, ant {n_ant}, "
          f"{os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    main()
