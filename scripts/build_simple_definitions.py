#!/usr/bin/env python3
"""
build_simple_definitions.py  (v2)
---------------------------------
為每個考試單字挑一條「基礎英文解釋」：用到的字要盡量簡單，而且一定是完整的句子。

候選來源 (依序)
  1. 人工撰寫 (KNOWN_SIMPLE)
  2. Simple English Wiktionary  (刻意用基礎英文寫的字典，CC-BY-SA)
     database/raw/simple_wiktionary.jsonl.gz
     https://kaikki.org/dictionary/downloads/simple/simple-extract.jsonl.gz
  3. 英文 Wiktionary 定義         database/raw/wiktionary_en_filtered.jsonl
  4. ECDICT / WordNet 定義        exam_words.json 的 definitions.en

檢查 (每條候選都要過)
  - 完整：不是被截斷的句子、不是 "Plural of …" / "Alternative form of …"、不是古語 / 俚語義項
  - 不能只靠單字本身或同字族來解釋
  - 難度：用 word_difficulty (考試 Level，表外字依常用度推估) 算出解釋裡最難的字是幾級
        tier 0 = 全部 Level 1–2
        tier 1 = 有較難的字，但都比單字本身簡單
        tier 2 = 用到跟單字一樣難或更難的字 (最後手段，前端會標示)

挑選：考試表第一個詞性 → 該詞性第一個詞條 → 第 0 個義項 (主要意思) → tier 越低越好 → 來源 → 越短
      (意思對但有難字，勝過簡單但意思冷門；難字會列在 hard_words 讓前端標示)
      (tier 2 一律排在最後)

輸出 database/simple_definitions.json
{
  "meta": {...},
  "words": {
    "abandon": {"text": "If you abandon something, you go away from it with no plan to return.",
                "level": 2, "tier": 0, "hard_words": [], "source": "simple_wiktionary"},
    ...
  }
}
"""
import gzip
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_word_difficulty import Difficulty, FUNCTION_WORDS  # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE_DIR, "database")
EXAM_WORDS = os.path.join(DB, "exam_words.json")
ORIGINS = os.path.join(DB, "word_origins.json")
SIMPLE_WIKT = os.path.join(DB, "raw", "simple_wiktionary.jsonl.gz")
WIKT = os.path.join(DB, "raw", "wiktionary_en_filtered.jsonl")
OUT = os.path.join(DB, "simple_definitions.json")
REPORT = os.path.join(DB, "simple_definitions_report.md")

KNOWN_SIMPLE = {
    "a": "Used before a word for one person or thing, when it is not a special one.",
    "an": "The same as a; used before a word that starts with a, e, i, o, or u sounds.",
    "the": "Used before a word when the listener knows which one you mean.",
    "orchid": "A plant that has beautiful and special flowers.",
    "supercomputer": "A very big and fast computer that can do hard work quickly.",
    "scam": "A bad plan to trick people and take their money.",
    "summer": "The warmest season of the year, between spring and autumn.",
    "rainforest": "A thick green forest where it rains a lot.",
    "backpacker": "A person who travels with a bag on their back.",
    "firefly": "A small insect that can make light in the dark.",
    "blog": "A website where a person writes about their life or thoughts.",
    "brave": "Not afraid to do dangerous or difficult things.",
    "sunlight": "The light that comes from the sun during the day.",
    "birthday": "The day each year that is the same date as the day you were born.",
    "worldwide": "Happening in all parts of the world.",
    "lifestyle": "The way that a person or group of people lives.",
    "bystander": "A person who is standing near something that happens and watches it.",
    "buyer": "A person who buys something.",
    "winner": "A person or team that wins a game or prize.",
    "happiness": "The feeling of being happy.",
    "unlimited": "Without any end or limit.",
}

SOURCE_RANK = {"manual": 0, "simple_wiktionary": 1, "wiktionary": 2, "ecdict": 3}
BAD_TAGS = {"obsolete", "archaic", "dated", "rare", "slang", "vulgar", "offensive", "derogatory",
            "nonstandard", "dialectal", "historical", "figuratively", "idiomatic", "jargon"}
BAD_START = re.compile(r"^(plural of|past tense of|past participle of|present participle of|"
                       r"third-person|alternative (form|spelling) of|misspelling of|obsolete|"
                       r"archaic|abbreviation of|initialism of|synonym of|see |short for|"
                       r"comparative of|superlative of|simple past|the plural form|plural form|en-|\()", re.I)
TRUNC_END = re.compile(r"\b(a|an|the|of|to|in|and|or|with|for|by|at|from|on|as|that|which|is|are)$", re.I)
POS_MAP = {"n.": "noun", "v.": "verb", "vt.": "verb", "vi.": "verb", "adj.": "adj", "a.": "adj",
           "adv.": "adv", "ad.": "adv", "prep.": "prep", "conj.": "conj", "pron.": "pron",
           "art.": "article", "det.": "det", "int.": "intj", "interj.": "intj", "aux.": "verb",
           "num.": "num"}
# Wiktionary 的詞性名稱 -> 同一組
POS_NORM = {"noun": "noun", "verb": "verb", "adj": "adj", "adv": "adv", "prep": "prep",
            "conj": "conj", "pron": "pron", "article": "det", "det": "det", "intj": "intj",
            "num": "num", "name": "name"}


def clean(text):
    t = re.sub(r"^[a-z]+\.\s*", "", text.strip())            # n. / v. 前綴
    t = re.sub(r"^(n|v|vt|vi|adj|adv)\s+(?=[a-z])", "", t)   # ECDICT "n a child …" / "v dwell" 殘留 (不碰冠詞 A)
    t = re.sub(r"\s*\([^)]*\)", "", t)                        # 括號說明
    t = re.sub(r"\s+", " ", t).strip()
    # 只留第一句 (Simple Wiktionary 常在第二句寫 "A very similar word is …")
    m = re.match(r"(.+?[.!?])\s+[A-Z]", t)
    if m:
        t = m.group(1)
    t = t.split(";")[0].strip()
    t = t.rstrip(" .,:")
    return t


def tokens(text):
    return re.findall(r"[A-Za-z]+(?:'[a-z]+)?", text)


def main():
    diff = Difficulty()
    exam = json.load(open(EXAM_WORDS, encoding="utf-8"))["words"]
    family = {}
    if os.path.exists(ORIGINS):
        od = json.load(open(ORIGINS, encoding="utf-8"))
        for o, data in (od.get("origins") or {}).items():
            fam = {o.lower()} | {v["word"].lower() for v in data.get("variants", [])}
            for w in fam:
                family.setdefault(w, set()).update(fam)

    # ---- 收集候選
    cands = {w: [] for w in exam}

    entry_order = Counter()   # 同一個字在同一來源的第幾個詞條 (Wiktionary 第一個詞條通常是主要用法)

    def add(w, text, src, pos, idx, ent=0):
        if w in cands and text:
            cands[w].append((text, src, POS_NORM.get(pos, pos), idx, ent))

    for w, t in KNOWN_SIMPLE.items():
        add(w, t, "manual", None, 0)

    print("reading Simple English Wiktionary ...")
    with gzip.open(SIMPLE_WIKT, "rt", encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            w = (e.get("word") or "").lower()
            if w not in cands:
                continue
            k = (w, "s", POS_NORM.get(e.get("pos"), e.get("pos")))
            ent = entry_order[k]
            entry_order[k] += 1
            for i, s in enumerate(e.get("senses") or []):
                if set(s.get("tags") or []) & BAD_TAGS or s.get("form_of"):
                    continue
                for g in s.get("glosses") or []:
                    add(w, g, "simple_wiktionary", e.get("pos"), i, ent)

    print("reading Wiktionary ...")
    if os.path.exists(WIKT):
        with open(WIKT, encoding="utf-8") as f:
            for line in f:
                e = json.loads(line)
                w = (e.get("word") or "").lower()
                if w not in cands or e.get("pos") in ("name", "prefix", "suffix"):
                    continue
                k = (w, "w", POS_NORM.get(e.get("pos"), e.get("pos")))
                ent = entry_order[k]
                entry_order[k] += 1
                for i, s in enumerate(e.get("senses") or []):
                    if set(s.get("tags") or []) & BAD_TAGS or s.get("form_of"):
                        continue
                    g = (s.get("glosses") or [None])[-1]   # 最後一個 gloss 是最具體的子義項
                    add(w, g, "wiktionary", e.get("pos"), i, ent)

    for w, e in exam.items():
        for i, d in enumerate((e.get("definitions") or {}).get("en") or []):
            m = re.match(r"^([a-z]+\.)", d.strip())
            add(w.lower(), d, "ecdict", POS_MAP.get(m.group(1)) if m else None, i)

    # ---- 評分
    def evaluate(w, raw, src):
        t = clean(raw)
        if not t or BAD_START.search(t) or "..." in raw or "…" in raw:
            return None
        if re.search(r'["“”:/=<>\[\]{}]|\d', t):     # 引號、冒號、公式、數字 -> 多半不是好讀的解釋
            return None
        toks = tokens(t)
        # 截斷只發生在 ECDICT；Wiktionary 句子以介系詞結尾是正常的 ("… for you to read or write in.")
        if not (3 <= len(toks) <= 30) or (src == "ecdict" and TRUNC_END.search(t)):
            return None
        fam = family.get(w, {w}) | {w}
        content = [x for x in toks if x.lower() not in FUNCTION_WORDS]
        explain = [x for x in content if x.lower() not in fam and diff.lemma(x) not in fam]
        if not explain:
            return None                                      # 只用單字本身 / 同字族解釋
        hard, lv_max = [], 0
        first = toks[0]
        for x in explain:
            # 專有名詞 (Spain, Roman) 不算難字；但句首大寫的字不是專有名詞
            if x[0].isupper() and x is not first and x.lower() not in diff.level:
                continue
            lv = diff.est(x)
            lv_max = max(lv_max, lv)
            if lv > 2:
                hard.append((x.lower(), lv))
        head_lv = diff.est(w)
        tier = 0 if lv_max <= 2 else (1 if lv_max < head_lv else 2)
        text = t[0].upper() + t[1:] + "."
        return {"text": text, "level": lv_max, "tier": tier,
                "hard_words": sorted({h for h, _ in hard}, key=lambda h: -diff.est(h)), "n": len(toks)}

    result, stats, src_count = {}, Counter(), Counter()
    for w, lst in cands.items():
        e = exam.get(w) or {}
        exam_pos = [POS_NORM.get(POS_MAP.get(p), POS_MAP.get(p)) for p in (e.get("pos") or [])]
        primary = exam_pos[0] if exam_pos else None
        best, best_key = None, None
        for text, src, pos, idx, ent in lst:
            ev = evaluate(w, text, src)
            if not ev:
                continue
            # 0 = 考試表第一個詞性 (主要用法)；1 = 考試表其他詞性；2 = 考試表沒列的詞性
            if pos is None or primary is None or pos == primary:
                pos_pen = 0
            elif pos in exam_pos:
                pos_pen = 1
            else:
                pos_pen = 2
            # 主要義項優先 (前 2 個義項、詞性符合)，其次才比簡單程度；
            # 避免 "a" 被選成冷門義項 "an A is a very high grade"
            # 每個來源的第 0 個義項 = 主要意思；同一個義項層級裡再比誰最簡單
            # 主要意思優先：考試表第一個詞性 → 該詞性的第一個詞條 → 第 0 個義項；
            # 各來源的「第 0 個義項」之間再比誰最簡單 (意思對但有難字，勝過簡單但意思冷門)
            key = (pos_pen, ent > 0, idx > 0, ev["tier"], len(ev["hard_words"]),
                   SOURCE_RANK[src], ev["level"], idx, ev["n"])
            if best_key is None or key < best_key:
                best_key, best = key, dict(ev, source=src)
        if best:
            best.pop("n")
            result[w] = best
            stats[f"tier{best['tier']}"] += 1
            src_count[best["source"]] += 1
        else:
            stats["none"] += 1

    meta = {"built": datetime.now().isoformat(timespec="seconds"),
            "rule": "tier0=全部 Level1-2；tier1=有較難的字但都比單字本身簡單；tier2=用到不比單字簡單的字",
            "words": len(exam), "tiers": dict(stats), "sources": dict(src_count)}
    json.dump({"meta": meta, "words": result}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(f"# 基礎英文解釋報告\n\n建置時間: {meta['built']}\n\n")
        f.write("| 等級 | 字數 |\n|---|---:|\n")
        f.write(f"| 🟢 tier 0：全部用 Level 1–2 單字 | {stats['tier0']} |\n")
        f.write(f"| 🟡 tier 1：有較難的字，但都比單字本身簡單 | {stats['tier1']} |\n")
        f.write(f"| 🔴 tier 2：用到不比單字簡單的字 | {stats['tier2']} |\n")
        f.write(f"| ⚪ 沒有合格的解釋 | {stats['none']} |\n\n")
        f.write("來源：" + "、".join(f"{k} {v}" for k, v in src_count.most_common()) + "\n\n")
        f.write("## tier 2 清單 (需要人工或 AI 改寫)\n\n")
        for w, r in sorted(result.items()):
            if r["tier"] == 2:
                f.write(f"- **{w}** (Lv{diff.est(w)}): {r['text']}  — 較難: {', '.join(r['hard_words'])}\n")
    print(json.dumps(meta, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
