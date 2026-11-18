"""
build_word_difficulty.py
------------------------
單字難度分級：考試 Level + 常用度 (wordfreq Zipf)。

為什麼需要：
  - 考試詞彙表只有 6,701 字。表外的字 (dwell、alphabet …) 以前一律被當成「不合格」或無法判斷。
  - 考試 Level 3–5 的常用度其實高度重疊 (中位數 4.14 / 3.98 / 3.95)，只看 Level 不夠。

輸出 database/word_difficulty.json
{
  "meta": {...},
  "words": {
     "dwell": {"level": null, "est_level": 6, "zipf": 3.57, "stars": 2, "lemma": "dwell"},
     "apple": {"level": 1, "est_level": 1, "zipf": 4.9, "stars": 4, "lemma": "apple"},
     ...
  }
}
  level      : 考試詞彙表的等級 (表外為 null)
  est_level  : 實際用來判斷難度的等級。考試表內 = level；表外 = 依常用度推估 (7 = 超出高中範圍)
  zipf       : 常用度 (wordfreq Zipf，約 1–7，越大越常見)
  stars      : 常用度 1–5 顆星 (給前端顯示)

其他程式可以 import 這支的 Difficulty 類別直接查任何字 (含變化形)。
"""
import json
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE_DIR, "database")
EXAM_WORDS = os.path.join(DB, "exam_words.json")
ORIGINS = os.path.join(DB, "word_origins.json")
OUT = os.path.join(DB, "word_difficulty.json")

# 依考試表內單字的常用度分布校準 (各等級中位數之間取切點)
#   Level 1 中位 5.01 / Level 2 4.53 / Level 3 4.14 / Level 4 3.98 / Level 5 3.95 / Level 6 3.56
ZIPF_CUTS = [(4.80, 1), (4.35, 2), (4.05, 3), (3.85, 4), (3.65, 5), (3.30, 6)]

# 功能詞 / 代名詞：考試表沒收，但當然是最基礎的字
FUNCTION_WORDS = set("""
a an the of in to for with on at from by about as into like through after over between out
against during without before under around among and but or so because when if that which who
whom whose what where why how is am are was were be being been have has had having do does did
doing done can could will would shall should may might must i you he she it we they me him her us
them my your his its our their mine yours hers ours theirs this these those not no yes very more
most much many all some any each every both few little other another such only own same than too
there here then now also just up down off away back again one two three four five six seven eight
nine ten something someone somebody anything anyone nothing everything everyone thing things
way ways s t etc ok
""".split())


def zipf_to_level(z):
    for cut, lv in ZIPF_CUTS:
        if z >= cut:
            return lv
    return 7


def stars(z):
    # 5: 極常見 (>=5.5) 4: 常見 3: 一般 2: 少見 1: 罕見
    return 5 if z >= 5.5 else 4 if z >= 4.7 else 3 if z >= 4.0 else 2 if z >= 3.3 else 1


INFLECTION_TAGS = ("1:", "2:", "3:", "比較級", "最高級")


class Difficulty:
    """查任何字的難度 (會先還原變化形：letters -> letter, cried -> cry)"""

    def __init__(self):
        from wordfreq import zipf_frequency
        self._zipf = lambda w: zipf_frequency(w, "en")
        ew = json.load(open(EXAM_WORDS, encoding="utf-8"))["words"]
        self.level = {w.lower(): e.get("level") for w, e in ew.items() if e.get("level")}
        self.lemma_of = {}
        if os.path.exists(ORIGINS):
            wo = json.load(open(ORIGINS, encoding="utf-8"))["words"]
            for w, v in wo.items():
                rel = v.get("relation", "")
                if rel.startswith(INFLECTION_TAGS):
                    self.lemma_of[w.lower()] = v["origin"].lower()
        self._cache = {}

    def lemma(self, w):
        w = w.lower()
        if w in self.level or w in FUNCTION_WORDS:
            return w
        if w in self.lemma_of:
            return self.lemma_of[w]
        for suf, rep in (("ies", "y"), ("ied", "y"), ("ier", "y"), ("iest", "y"), ("es", ""), ("s", ""),
                         ("ed", ""), ("ed", "e"), ("ing", ""), ("ing", "e"), ("er", ""), ("est", ""),
                         ("'s", "")):
            if w.endswith(suf) and len(w) - len(suf) >= 2:
                b = w[: -len(suf)] + rep
                if b in self.level:
                    return b
                if len(b) >= 3 and b[-1] == b[-2] and b[:-1] in self.level:   # stopped -> stop
                    return b[:-1]
        return w

    def info(self, w):
        w = w.lower()
        if w in self._cache:
            return self._cache[w]
        lem = self.lemma(w)
        z = round(max(self._zipf(w), self._zipf(lem)), 2)
        if lem in FUNCTION_WORDS:
            lv, est = None, 0
        elif lem in self.level:
            lv = self.level[lem]
            est = lv
        else:
            lv, est = None, zipf_to_level(z)
        r = {"level": lv, "est_level": est, "zipf": z, "stars": stars(z), "lemma": lem}
        self._cache[w] = r
        return r

    def est(self, w):
        return self.info(w)["est_level"]


def main():
    d = Difficulty()
    words = set(d.level)
    if os.path.exists(ORIGINS):
        words |= {w.lower() for w in json.load(open(ORIGINS, encoding="utf-8"))["words"]}
    out = {w: d.info(w) for w in sorted(words)}
    from collections import Counter
    dist = Counter(v["est_level"] for v in out.values())
    meta = {"built": datetime.now().isoformat(timespec="seconds"),
            "zipf_cuts": ZIPF_CUTS,
            "note": "est_level: 考試表內=考試 Level；表外=依 wordfreq 常用度推估 (7=超出高中範圍)",
            "est_level_counts": {str(k): v for k, v in sorted(dist.items())}}
    json.dump({"meta": meta, "words": out}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False,
              separators=(",", ":"))
    print(json.dumps(meta, ensure_ascii=False))
    for w in ["dwell", "alphabet", "perform", "letters", "cried", "orchid", "the", "abbreviate"]:
        print(w, d.info(w))


if __name__ == "__main__":
    main()
