#!/usr/bin/env python3
"""
build_root_breakdown.py — Enhanced Deterministic Affix & Root Breakdown Builder

Builds database/word_roots_breakdown.json by:
1. Mapping all 90 roots and 627+ derived words from word_database.json.
2. Mapping prefix-derived words (e.g. un-happy, re-write, dis-agree, im-possible).
3. Mapping suffix-derived words (e.g. care-ful, care-less, move-ment, friend-ly).
4. Generating clean bilingual synthesis strings:
   "pre-(事先) + dict(說) → 預測"
   "un-(不) + happy(快樂) → 不快樂、悲傷"
5. Storing completely deterministic JSON data with zero guesswork at runtime.
"""

import json
import os
import re
import sys
from opencc import OpenCC

sys.stdout.reconfigure(encoding='utf-8')
cc = OpenCC("s2t")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORD_DB_PATH = os.path.join(BASE_DIR, "database", "word_database.json")
EXAM_WORDS_PATH = os.path.join(BASE_DIR, "database", "exam_words.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "database", "word_roots_breakdown.json")

PREFIXES = {
    "un": {"en": "not, opposite of", "zh": "不、相反"},
    "re": {"en": "again, back", "zh": "再次、向後、重新"},
    "in": {"en": "in, into, or not", "zh": "向內、進入 或 否定(不)"},
    "im": {"en": "in, into, or not", "zh": "向內 或 否定(不)"},
    "ir": {"en": "not", "zh": "否定(不)"},
    "il": {"en": "not", "zh": "否定(不)"},
    "dis": {"en": "away, apart, not", "zh": "分離、除去、否定"},
    "mis": {"en": "wrong, badly", "zh": "錯誤、不當"},
    "pre": {"en": "before, in front of", "zh": "在...之前、事先"},
    "pro": {"en": "forward, in favor of", "zh": "向前、贊同"},
    "post": {"en": "after, behind", "zh": "在...之後"},
    "ex": {"en": "out, former", "zh": "向外、出、前任"},
    "sub": {"en": "under, below, secondary", "zh": "在...之下、次要"},
    "sup": {"en": "under, supporting", "zh": "在...之下、支撐"},
    "sur": {"en": "over, above", "zh": "在...之上、超過"},
    "trans": {"en": "across, beyond", "zh": "跨越、轉移"},
    "con": {"en": "together, completely", "zh": "共同、完全"},
    "com": {"en": "together, completely", "zh": "共同、完全、加強"},
    "col": {"en": "together, with", "zh": "共同、一起"},
    "cor": {"en": "together, thoroughly", "zh": "共同、完全"},
    "co": {"en": "together, joint", "zh": "共同、聯合"},
    "ad": {"en": "to, toward, near", "zh": "向、朝向、加強"},
    "ac": {"en": "to, toward", "zh": "朝向、加強"},
    "ap": {"en": "to, toward", "zh": "朝向、加強"},
    "as": {"en": "to, toward", "zh": "朝向、加強"},
    "at": {"en": "to, toward", "zh": "朝向、加強"},
    "de": {"en": "down, away, completely", "zh": "向下、離開、完全"},
    "inter": {"en": "between, among", "zh": "在...之間、互相"},
    "super": {"en": "above, beyond, over", "zh": "超級、在...之上"},
    "over": {"en": "too much, above", "zh": "過度、在...之上"},
    "under": {"en": "beneath, insufficient", "zh": "在...下方、不足"},
    "anti": {"en": "against, opposing", "zh": "反對、抗、抗衡"},
    "counter": {"en": "against, opposite", "zh": "相反、對抗"},
    "auto": {"en": "self, same", "zh": "自身、自動"},
    "tele": {"en": "far, distant", "zh": "遠距離"},
    "micro": {"en": "small", "zh": "微小"},
    "multi": {"en": "many, multiple", "zh": "多元、多數"},
    "bi": {"en": "two, twice", "zh": "二、雙重"},
    "tri": {"en": "three", "zh": "三"},
    "en": {"en": "make, put into", "zh": "使成為、置入"},
    "em": {"en": "make, put into", "zh": "使成為、置入"},
    "fore": {"en": "before, front", "zh": "預先、前方"},
    "non": {"en": "not, absence of", "zh": "非、不"},
    "extra": {"en": "outside, beyond", "zh": "額外、在...之外"},
    "semi": {"en": "half, partly", "zh": "半、部分"}
}

SUFFIXES = {
    "tion": {"en": "noun: action, condition", "zh": "名詞：動作、狀態"},
    "sion": {"en": "noun: action, condition", "zh": "名詞：動作、狀態"},
    "ation": {"en": "noun: process, result", "zh": "名詞：過程、結果"},
    "ition": {"en": "noun: action, state", "zh": "名詞：動作、狀態"},
    "ment": {"en": "noun: action, resulting state", "zh": "名詞：行為、結果"},
    "ness": {"en": "noun: state, quality", "zh": "名詞：性質、狀態"},
    "ity": {"en": "noun: state, quality", "zh": "名詞：狀態、特質"},
    "ty": {"en": "noun: condition, state", "zh": "名詞：情況、性質"},
    "ance": {"en": "noun: state, quality of", "zh": "名詞：性質、情況"},
    "ence": {"en": "noun: state, quality of", "zh": "名詞：性質、情況"},
    "ship": {"en": "noun: state, relationship", "zh": "名詞：身分、關係"},
    "hood": {"en": "noun: state, period", "zh": "名詞：時期、狀態"},
    "er": {"en": "noun: person or thing that does", "zh": "名詞：從事者、器具"},
    "or": {"en": "noun: person or thing that does", "zh": "名詞：從事者、器具"},
    "ist": {"en": "noun: person who practices", "zh": "名詞：專業人士、主義者"},
    "ee": {"en": "noun: recipient of action", "zh": "名詞：受動者"},
    "ism": {"en": "noun: doctrine, belief", "zh": "名詞：主義、學說"},
    "al": {"en": "adj/noun: related to", "zh": "形容詞/名詞：相關的"},
    "ive": {"en": "adj: tending to, performing", "zh": "形容詞：具...特性的"},
    "ous": {"en": "adj: full of", "zh": "形容詞：充滿...的"},
    "ious": {"en": "adj: full of", "zh": "形容詞：充滿...的"},
    "able": {"en": "adj: capable of being", "zh": "形容詞：能夠...的"},
    "ible": {"en": "adj: capable of being", "zh": "形容詞：能夠...的"},
    "ful": {"en": "adj: full of", "zh": "形容詞：充滿...的"},
    "less": {"en": "adj: without, lacking", "zh": "形容詞：沒有...的、缺乏的"},
    "ic": {"en": "adj: having quality of", "zh": "形容詞：相關的"},
    "ical": {"en": "adj: related to", "zh": "形容詞：有關...的"},
    "ish": {"en": "adj: somewhat", "zh": "形容詞：稍具...特質的"},
    "ly": {"en": "adv: in manner of", "zh": "副詞：...地"},
    "ward": {"en": "adv/adj: in direction of", "zh": "副詞/形容詞：朝...方向"},
    "ize": {"en": "verb: make, become", "zh": "動詞：使成為、化"},
    "ise": {"en": "verb: make, become", "zh": "動詞：使成為、化"},
    "ate": {"en": "verb/adj: cause to become", "zh": "動詞/形容詞：造成、使具備"},
    "en": {"en": "verb/adj: make / made of", "zh": "動詞/形容詞：使變為 / ...製的"},
    "ify": {"en": "verb: make, cause to be", "zh": "動詞：使成為"}
}

def load_data():
    with open(WORD_DB_PATH, "r", encoding="utf-8") as f:
        word_db = json.load(f)
    with open(EXAM_WORDS_PATH, "r", encoding="utf-8") as f:
        exam_words = json.load(f)["words"]
    return word_db, exam_words

def build():
    word_db, exam_words = load_data()
    roots = word_db.get("roots", {})
    simple_words = word_db.get("simple_words", {})

    breakdowns = {}

    # 1. Linguistic Roots from word_database.json
    for root_key, rdata in roots.items():
        root_mean_en = rdata.get("meaning", "")
        root_mean_zh = cc.convert(rdata.get("meaning_zh", ""))
        root_origin = rdata.get("origin_word", "")
        rule_name = rdata.get("rule_name", "")
        explanation = cc.convert(rdata.get("explanation", ""))

        for w in rdata.get("derived_words", []):
            w_lower = w.lower().strip()
            
            matched_prefix = None
            stem = w_lower
            for pfx in sorted(PREFIXES.keys(), key=lambda x: -len(x)):
                if w_lower.startswith(pfx) and len(w_lower) > len(pfx) + 2:
                    rem = w_lower[len(pfx):]
                    if root_key in rem or rem[:2] in root_key or root_key[:2] in rem:
                        matched_prefix = pfx
                        stem = rem
                        break
            
            matched_suffix = None
            for sfx in sorted(SUFFIXES.keys(), key=lambda x: -len(x)):
                if stem.endswith(sfx) and len(stem) > len(sfx) + 1:
                    matched_suffix = sfx
                    break

            prefix_info = {
                "text": f"{matched_prefix}-",
                "meaning_en": PREFIXES[matched_prefix]["en"],
                "meaning_zh": PREFIXES[matched_prefix]["zh"]
            } if matched_prefix else None

            suffix_info = {
                "text": f"-{matched_suffix}",
                "meaning_en": SUFFIXES[matched_suffix]["en"],
                "meaning_zh": SUFFIXES[matched_suffix]["zh"]
            } if matched_suffix else None

            root_info = {
                "text": root_key,
                "meaning_en": root_mean_en,
                "meaning_zh": root_mean_zh,
                "origin": root_origin
            }

            parts_zh = []
            if prefix_info:
                parts_zh.append(f"{prefix_info['text']}({prefix_info['meaning_zh']})")
            parts_zh.append(f"{root_info['text']}({root_info['meaning_zh']})")
            if suffix_info:
                parts_zh.append(f"{suffix_info['text']}({suffix_info['meaning_zh']})")

            parts_en = []
            if prefix_info:
                parts_en.append(f"{prefix_info['text']} ({prefix_info['meaning_en']})")
            parts_en.append(f"{root_info['text']} ({root_info['meaning_en']})")
            if suffix_info:
                parts_en.append(f"{suffix_info['text']} ({suffix_info['meaning_en']})")

            breakdowns[w_lower] = {
                "word": w_lower,
                "has_affix": True,
                "prefix": prefix_info,
                "root": root_info,
                "suffix": suffix_info,
                "synthesis_zh": " + ".join(parts_zh),
                "synthesis_en": " + ".join(parts_en),
                "rule_name": rule_name,
                "explanation": explanation
            }

    # 2. Regular Prefix Decompositions against known vocabulary
    for w in exam_words:
        if w in breakdowns or len(w) < 4:
            continue
        
        for pfx in sorted(PREFIXES.keys(), key=lambda x: -len(x)):
            if len(pfx) >= 2 and w.startswith(pfx):
                base = w[len(pfx):]
                if base in exam_words and len(base) >= 3:
                    base_zh = exam_words[base].get("definitions", {}).get("zh", [""])[0]
                    base_clean = re.sub(r'^[a-z]+\.\s*', '', base_zh).split(',')[0].split(';')[0].split('；')[0].split(' ')[0][:6]
                    if not base_clean:
                        base_clean = base

                    p_data = PREFIXES[pfx]
                    prefix_info = {"text": f"{pfx}-", "meaning_en": p_data["en"], "meaning_zh": p_data["zh"]}
                    root_info = {"text": base, "meaning_en": f"base word: {base}", "meaning_zh": base_clean, "is_base_word": True}
                    
                    breakdowns[w] = {
                        "word": w,
                        "has_affix": True,
                        "prefix": prefix_info,
                        "root": root_info,
                        "suffix": None,
                        "synthesis_zh": f"{prefix_info['text']}({prefix_info['meaning_zh']}) + {base}({base_clean})",
                        "synthesis_en": f"{prefix_info['text']} ({prefix_info['meaning_en']}) + {base}"
                    }
                    break

    # 3. Regular Suffix Decompositions against known vocabulary
    for w in exam_words:
        if w in breakdowns or len(w) < 5:
            continue
        
        for sfx in sorted(SUFFIXES.keys(), key=lambda x: -len(x)):
            if len(sfx) >= 2 and w.endswith(sfx):
                stem = w[:-len(sfx)]
                candidates = [stem]
                if not stem.endswith('e'):
                    candidates.append(stem + 'e')
                if stem.endswith('i'):
                    candidates.append(stem[:-1] + 'y')
                if len(stem) >= 3 and stem[-1] == stem[-2]:
                    candidates.append(stem[:-1])
                
                matched_base = None
                for c in candidates:
                    if c in exam_words and len(c) >= 3:
                        matched_base = c
                        break
                
                if matched_base:
                    base_zh = exam_words[matched_base].get("definitions", {}).get("zh", [""])[0]
                    base_clean = re.sub(r'^[a-z]+\.\s*', '', base_zh).split(',')[0].split(';')[0].split('；')[0].split(' ')[0][:6]
                    if not base_clean:
                        base_clean = matched_base

                    s_data = SUFFIXES[sfx]
                    suffix_info = {"text": f"-{sfx}", "meaning_en": s_data["en"], "meaning_zh": s_data["zh"]}
                    root_info = {"text": matched_base, "meaning_en": f"base word: {matched_base}", "meaning_zh": base_clean, "is_base_word": True}

                    breakdowns[w] = {
                        "word": w,
                        "has_affix": True,
                        "prefix": None,
                        "root": root_info,
                        "suffix": suffix_info,
                        "synthesis_zh": f"{matched_base}({base_clean}) + {suffix_info['text']}({suffix_info['meaning_zh']})",
                        "synthesis_en": f"{matched_base} + {suffix_info['text']} ({suffix_info['meaning_en']})"
                    }
                    break

    # 4. Simple Words mapping
    for sw, sdata in simple_words.items():
        sw_lower = sw.lower().strip()
        if sw_lower not in breakdowns:
            breakdowns[sw_lower] = {
                "word": sw_lower,
                "has_affix": False,
                "is_simple_word": True,
                "meaning_en": sdata.get("meaning", ""),
                "meaning_zh": cc.convert(sdata.get("meaning_zh", "")),
                "cognate_roots": sdata.get("related_roots", []),
                "explanation": cc.convert(sdata.get("explanation", ""))
            }

    print(f"Total structured root/affix breakdowns created: {len(breakdowns)}")
    matched_in_exam = sum(1 for w in exam_words if w in breakdowns)
    print(f"Matching exam words: {matched_in_exam} / {len(exam_words)} words ({matched_in_exam/len(exam_words)*100:.1f}%)")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(breakdowns, f, ensure_ascii=False, indent=2)

    print(f"Saved: {OUTPUT_PATH}")

    # Preview samples
    print("\nSamples:")
    test_samples = ["predict", "unhappy", "careful", "movement", "visible", "rewrite", "export", "happiness", "disagree", "supercomputer"]
    for w in test_samples:
        if w in breakdowns:
            b = breakdowns[w]
            print(f"  {w:14} ➔ {b.get('synthesis_zh')}")

if __name__ == "__main__":
    build()

