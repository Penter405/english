"""
filter_wiktionary.py
--------------------
把 kaikki.org 的完整英文 Wiktionary 匯出檔 (約 3.4 GB) 串流過濾成只含本專案需要的字
(考試單字 + word_origins 裡的變體/原型 + 所有字首字尾詞條)，約 90 MB。

下載 + 過濾一次完成 (不必先把 3.4 GB 存到硬碟):
    curl -L https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl | py scripts/filter_wiktionary.py

或先下載再過濾:
    py scripts/filter_wiktionary.py --input kaikki.org-dictionary-English.jsonl

輸出: database/raw/wiktionary_en_filtered.jsonl
"""
import argparse
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE_DIR, "database")
OUT = os.path.join(DB, "raw", "wiktionary_en_filtered.jsonl")
AFFIX_POS = ("prefix", "suffix", "affix", "infix", "interfix", "root")


def word_set():
    ew = json.load(open(os.path.join(DB, "exam_words.json"), encoding="utf-8"))["words"]
    s = {w.lower() for w in ew}
    p = os.path.join(DB, "word_origins.json")
    if os.path.exists(p):
        wo = json.load(open(p, encoding="utf-8"))["words"]
        s |= {w.lower() for w in wo} | {v["origin"].lower() for v in wo.values()}
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="kaikki jsonl 檔；不給就讀 stdin")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    ws = word_set()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    src = open(args.input, encoding="utf-8") if args.input else sys.stdin
    n = k = 0
    with open(args.out, "w", encoding="utf-8") as out:
        for line in src:
            n += 1
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("lang_code") != "en":
                continue
            w = e.get("word", "")
            if w.lower() not in ws and e.get("pos") not in AFFIX_POS:
                continue
            keep = {x: e.get(x) for x in ("word", "pos", "etymology_text", "etymology_templates")}
            keep["senses"] = [{"glosses": s.get("glosses"), "tags": s.get("tags"), "form_of": s.get("form_of")}
                              for s in (e.get("senses") or [])][:6]
            keep["derived"] = [d.get("word") for d in (e.get("derived") or [])][:80]
            keep["forms"] = [{"form": f.get("form"), "tags": f.get("tags")} for f in (e.get("forms") or [])][:20]
            out.write(json.dumps(keep, ensure_ascii=False) + "\n")
            k += 1
            if n % 500000 == 0:
                print(f"  read {n:,}  kept {k:,}", file=sys.stderr, flush=True)
    print(f"done: read {n:,}, kept {k:,} -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
