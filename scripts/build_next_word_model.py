"""
build_next_word_model.py
------------------------
建立「下一個單字預測」用的 n-gram 機率表 (最多看前 2 個字)。

語料: Tatoeba 英文句子 (CC-BY 2.0 FR)
    https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences.tsv.bz2
    解壓後放在 database/raw/eng_sentences.tsv (已加入 .gitignore)

輸出: docs/data/next_word.json
{
  "meta": {...},
  "ctx": {
     "<s>":        [["i", 0.081], ["tom", 0.052], ...],   # 句首
     "<s> i":      [["don't", 0.06], ["have", 0.04], ...],
     "i like":     [["to", 0.21], ["the", 0.05], ...],
     "like":       [...]                                   # 1 字情境 (退回用)
  },
  "end": {"<s> i": 0.001, ...}   # 這個情境下「句子結束」的機率 (可選顯示)
}

機率 = 在這個情境出現後，下一個字是 X 的次數 / 這個情境的總次數 (最大概似估計)。
前端查詢順序: 「前 2 字」→ 不夠樣本就退回「前 1 字」→ 再退回「句首」。

用法:
    py scripts/build_next_word_model.py
    py scripts/build_next_word_model.py --corpus database/raw/eng_sentences.tsv --topk 8
"""
import argparse
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CORPUS = os.path.join(BASE_DIR, "database", "raw", "eng_sentences.tsv")
DEFAULT_OUT = os.path.join(BASE_DIR, "docs", "data", "next_word.json")
EXAM_WORDS = os.path.join(BASE_DIR, "database", "exam_words.json")

RAW_TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
NAME = "<name>"  # 專有名詞 (人名、地名) 合併成一個選項，避免 Tom/Mary 洗版


def raw_tokens(sentence):
    return RAW_TOKEN_RE.findall(sentence.replace("’", "'"))


def find_proper_nouns(path):
    """句中 (非句首) 出現時 95% 以上都大寫開頭的字 → 視為專有名詞"""
    cap, low = Counter(), Counter()
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            for t in raw_tokens(parts[2])[1:]:
                if t[0].isupper() and not t.isupper():
                    cap[t.lower()] += 1
                elif t.islower():
                    low[t.lower()] += 1
    return {w for w, n in cap.items() if n >= 5 and n / (n + low[w]) >= 0.95 and w != "i" and not w.startswith("i'")}


def tokenize(sentence, proper=frozenset()):
    toks = [t.lower() for t in raw_tokens(sentence)]
    return [NAME if t in proper else t for t in toks]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--topk", type=int, default=8, help="每個情境保留幾個候選字")
    ap.add_argument("--min-ctx1", type=int, default=30, help="1 字情境最少出現次數")
    ap.add_argument("--min-ctx2", type=int, default=60, help="2 字情境最少出現次數")
    ap.add_argument("--max-len", type=int, default=20, help="超過這個字數的句子略過")
    args = ap.parse_args()

    c1 = defaultdict(Counter)  # prev1 -> next
    c2 = defaultdict(Counter)  # prev2 prev1 -> next
    proper = frozenset(find_proper_nouns(args.corpus))
    print(f"proper nouns merged into {NAME}: {len(proper)}")
    n_sent = 0
    with open(args.corpus, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            toks = tokenize(parts[2], proper)
            if not toks or len(toks) > args.max_len:
                continue
            n_sent += 1
            seq = ["<s>", "<s>"] + toks + ["</s>"]
            for i in range(2, len(seq)):
                nxt = seq[i]
                p1 = seq[i - 1]
                p2 = seq[i - 2]
                c1[p1][nxt] += 1
                if p1 != "<s>":
                    key2 = f"{p2} {p1}"
                    c2[key2][nxt] += 1

    ctx = {}
    end = {}

    def pack(key, counter, min_total):
        total = sum(counter.values())
        if total < min_total:
            return
        items = [(w, n) for w, n in counter.most_common(args.topk + 1) if w != "</s>"][: args.topk]
        ctx[key] = [[w, round(n / total, 4)] for w, n in items]
        e = counter.get("</s>", 0) / total
        if e >= 0.01:
            end[key] = round(e, 4)

    for k, cnt in c1.items():
        pack(k, cnt, args.min_ctx1)
    n1 = len(ctx)
    for k, cnt in c2.items():
        pack(k, cnt, args.min_ctx2)

    # 標上考試等級 (前端可上色)
    levels = {}
    if os.path.exists(EXAM_WORDS):
        ew = json.load(open(EXAM_WORDS, encoding="utf-8"))["words"]
        cand = {w for lst in ctx.values() for w, _ in lst}
        for w in cand:
            e = ew.get(w)
            if e and e.get("level"):
                levels[w] = e["level"]

    out = {
        "meta": {
            "source": "Tatoeba English sentences (CC-BY 2.0 FR) https://tatoeba.org",
            "built": datetime.now().isoformat(timespec="seconds"),
            "sentences": n_sent,
            "contexts_1word": n1,
            "contexts_2word": len(ctx) - n1,
            "topk": args.topk,
            "note": "機率為該情境下的相對次數；查詢順序 2字→1字→句首；<name> = 人名/地名等專有名詞",
        },
        "ctx": ctx,
        "end": end,
        "level": levels,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"sentences={n_sent}  contexts={len(ctx)} (1-word {n1})  -> {args.out}  "
          f"{os.path.getsize(args.out)/1e6:.2f} MB")


if __name__ == "__main__":
    main()
