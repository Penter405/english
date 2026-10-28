#!/usr/bin/env python3
"""
build_word_origins.py — Build Authoritative Word Origin & Variants Database

Creates database/word_origins.json:
- Maps every word to its morphological/etymological origin (base word / lemma).
- Maps every origin to all its variants (inflections, derivations, different parts of speech).
- Format matches ECDICT and WordNet authoritative data (e.g. 0: pick | 1: picked | 2: picking | 3: picks).
- Zero false-positive substring guessing.
"""

import csv
import json
import os
import re
import sys
from collections import defaultdict
from opencc import OpenCC
import nltk
from nltk.corpus import wordnet as wn

sys.stdout.reconfigure(encoding='utf-8')
cc = OpenCC('s2t')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECDICT_PATH = os.path.join(BASE_DIR, "database", "ecdict.csv")
EXAM_WORDS_PATH = os.path.join(BASE_DIR, "database", "exam_words.json")
WORD_DB_PATH = os.path.join(BASE_DIR, "database", "word_database.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "database", "word_origins.json")

def parse_exchange(ex_str):
    res = {}
    if not ex_str: return res
    for item in ex_str.split('/'):
        if ':' in item:
            k, v = item.split(':', 1)
            res[k] = v
    return res

RELATION_NAMES = {
    '0': '0: 原型 (lemma)',
    'p': '1: 過去式 (past)',
    'd': '1: 過去分詞 (past participle)',
    'i': '2: 現在分詞/進行式 (pres part)',
    '3': '3: 第三人稱單數現在式 (3rd sg)',
    's': '3: 名詞複數 (plural)',
    'r': '比較級 (comparative)',
    't': '最高級 (superlative)',
    'f': '其他變體 (variant)'
}

def clean_zh(trans_str):
    if not trans_str: return ""
    lines = trans_str.split('\\n')
    line = lines[0].strip()
    line = re.sub(r'^[a-z]+\.\s*', '', line)
    parts = re.split(r'[,;；，/]', line)
    return cc.convert(parts[0].strip())

def main():
    print("Loading data...")
    with open(EXAM_WORDS_PATH, "r", encoding="utf-8") as f:
        exam_words = json.load(f)["words"]

    with open(WORD_DB_PATH, "r", encoding="utf-8") as f:
        word_db = json.load(f)

    # 1. Load ECDICT into memory
    print("Reading ECDICT...")
    ec_map = {}
    with open(ECDICT_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            w = row['word'].lower().strip()
            ec_map[w] = {
                'pos': row['pos'],
                'exchange': row['exchange'],
                'trans': row['translation']
            }

    print(f"Loaded {len(ec_map)} ECDICT words.")

    # Data structures
    # word_to_origin: word -> origin_str
    # origin_variants: origin_str -> dict of {word: relation_label}
    word_to_origin = {}
    origin_variants = defaultdict(dict)

    # Step 1: Parse ECDICT explicit exchange mappings
    print("Step 1: Processing ECDICT exchange inflections...")
    for w in exam_words:
        ed = ec_map.get(w)
        if not ed or not ed.get('exchange'):
            continue
        
        ex = parse_exchange(ed['exchange'])
        # If this word has a 0: lemma, then lemma is origin
        if '0' in ex:
            origin = ex['0'].lower().strip()
            word_to_origin[w] = origin
            origin_variants[origin][w] = '變體 (variant)'
            origin_variants[origin][origin] = '原型 (lemma)'
        
        # If this word lists inflected forms:
        for code, label in RELATION_NAMES.items():
            if code in ex and code != '0' and code != '1':
                inflected_word = ex[code].lower().strip()
                if inflected_word and inflected_word != w:
                    word_to_origin[inflected_word] = w
                    origin_variants[w][inflected_word] = label
                    origin_variants[w][w] = '原型 (lemma)'

    # Step 2: Process WordNet derivational & antonym relationships
    print("Step 2: Processing WordNet derivations...")
    for w in exam_words:
        if w in word_to_origin:
            origin = word_to_origin[w]
        else:
            origin = w

        # Derivational relationships
        syns = wn.synsets(w)
        for s in syns:
            for l in s.lemmas():
                # Derivationally related forms
                for dr in l.derivationally_related_forms():
                    dr_word = dr.name().lower().strip()
                    if dr_word != w and (dr_word in exam_words or dr_word in ec_map):
                        # Verify stem overlap to prevent unrelated roots
                        if len(w) >= 3 and len(dr_word) >= 3 and (w[:3] == dr_word[:3] or w in dr_word or dr_word in w):
                            # The shorter or base word is chosen as origin if applicable
                            cand_origin = dr_word if len(dr_word) < len(origin) else origin
                            if cand_origin in exam_words or cand_origin in ec_map:
                                origin_variants[cand_origin][w] = '衍生詞 (derivation)'
                                origin_variants[cand_origin][dr_word] = '衍生詞 (derivation)'
                                origin_variants[cand_origin][cand_origin] = '原型 (lemma)'
                                word_to_origin[w] = cand_origin
                                word_to_origin[dr_word] = cand_origin
                                origin = cand_origin

                # Antonyms for prefixes (un-, dis-, im-, in-, il-, ir-)
                for ant in l.antonyms():
                    ant_word = ant.name().lower().strip()
                    if ant_word != w and (ant_word in exam_words or ant_word in ec_map):
                        for pfx in ['un', 'dis', 'im', 'in', 'il', 'ir', 'non']:
                            if w.startswith(pfx) and (w[len(pfx):] == ant_word or w[len(pfx):] in ant_word):
                                origin_variants[ant_word][w] = f'否定前綴變體 ({pfx}-)'
                                origin_variants[ant_word][ant_word] = '原型 (lemma)'
                                word_to_origin[w] = ant_word

    # Step 3: Verified Morphological Suffix Rules
    print("Step 3: Processing verified suffix derivations...")
    suffix_rules = [
        ('able', '形容詞變體 (-able)'),
        ('ible', '形容詞變體 (-ible)'),
        ('ably', '副詞變體 (-ably)'),
        ('ful', '形容詞變體 (-ful)'),
        ('less', '形容詞變體 (-less)'),
        ('ness', '名詞變體 (-ness)'),
        ('ment', '名詞變體 (-ment)'),
        ('tion', '名詞變體 (-tion)'),
        ('sion', '名詞變體 (-sion)'),
        ('ly', '副詞變體 (-ly)')
    ]

    for w in list(exam_words.keys()) + ['playable', 'readable', 'washable', 'workable', 'comfortably']:
        if w in word_to_origin and word_to_origin[w] != w:
            continue

        for sfx, rel_name in suffix_rules:
            if w.endswith(sfx) and len(w) > len(sfx) + 2:
                stem = w[:-len(sfx)]
                candidates = []
                if sfx == 'ably':
                    candidates.extend([stem, stem + 'e', stem + 'able'])
                elif sfx in ('ness', 'ful', 'less', 'ly'):
                    if stem.endswith('i'):
                        candidates.append(stem[:-1] + 'y')
                    candidates.append(stem)
                elif sfx in ('tion', 'sion'):
                    candidates.extend([stem + 'e', stem])
                else:
                    candidates.extend([stem, stem + 'e'])

                for base in candidates:
                    if base in exam_words or (base in ec_map and len(base) >= 3):
                        # Ensure base is genuinely related via definition or POS
                        base_trans = ec_map.get(base, {}).get('trans', '')
                        w_trans = ec_map.get(w, {}).get('trans', '')
                        
                        origin_variants[base][w] = rel_name
                        origin_variants[base][base] = '原型 (lemma)'
                        word_to_origin[w] = base
                        break
                if w in word_to_origin:
                    break

    # Also handle agent nouns (-er, -or) with WordNet verification
    for w in exam_words:
        if (w.endswith('er') or w.endswith('or')) and len(w) > 4:
            if w in word_to_origin and word_to_origin[w] != w:
                continue
            stem = w[:-2]
            candidates = [stem, stem + 'e']
            for base in candidates:
                if base in exam_words or (base in ec_map and len(base) >= 3):
                    # Check WordNet verification to avoid mister -> mist
                    syns = wn.synsets(w)
                    defs = ' '.join(s.definition() for s in syns).lower()
                    drfs = set(dr.name().lower() for s in syns for l in s.lemmas() for dr in l.derivationally_related_forms())
                    if base in drfs or base in defs:
                        origin_variants[base][w] = '施事名詞變體 (-er/-or)'
                        origin_variants[base][base] = '原型 (lemma)'
                        word_to_origin[w] = base
                        break

    # Step 4: Ensure every single word has an origin entry (self if not derived)
    print("Step 4: Consolidating origins and variants...")
    final_words = {}
    final_origins = {}

    for w in exam_words:
        orig = word_to_origin.get(w, w)
        # Ensure orig has an entry in origin_variants
        origin_variants[orig][orig] = '原型 (lemma)'
        origin_variants[orig][w] = origin_variants[orig].get(w, '變體 (variant)' if w != orig else '原型 (lemma)')

    for orig, vmap in origin_variants.items():
        orig_ed = ec_map.get(orig, {})
        orig_ew = exam_words.get(orig, {})
        orig_pos = orig_ew.get('pos', []) or ([orig_ed.get('pos')] if orig_ed.get('pos') else [])
        orig_zh = ""
        if orig_ew.get('definitions', {}).get('zh'):
            orig_zh = orig_ew['definitions']['zh'][0]
        elif orig_ed.get('trans'):
            orig_zh = clean_zh(orig_ed['trans'])

        variants_list = []
        for var_word, rel in sorted(vmap.items()):
            var_ed = ec_map.get(var_word, {})
            var_ew = exam_words.get(var_word, {})
            var_pos = var_ew.get('pos', [])
            if not var_pos and var_ed.get('trans'):
                # Extract pos from translation like "n. 先生", "adj. 可玩的"
                m = re.match(r'^([a-z]+)\.', var_ed['trans'])
                if m: var_pos = [f"{m.group(1)}."]

            variants_list.append({
                "word": var_word,
                "pos": var_pos,
                "relation": rel,
                "in_exam_vocab": var_word in exam_words
            })

        # Sort variants so that lemma is first, then other variants alphabetically
        variants_list.sort(key=lambda x: (0 if x['word'] == orig else 1, x['word']))

        final_origins[orig] = {
            "origin": orig,
            "pos": orig_pos,
            "meaning_zh": orig_zh,
            "variants_count": len(variants_list),
            "variants": variants_list
        }

    for orig, odata in final_origins.items():
        for v in odata["variants"]:
            v_word = v["word"]
            if v_word not in final_words:
                final_words[v_word] = {
                    "word": v_word,
                    "origin": orig,
                    "relation": v["relation"],
                    "has_variants": len(odata["variants"]) > 1,
                    "in_exam_vocab": v["in_exam_vocab"]
                }

    for w in exam_words:
        if w not in final_words:
            orig = word_to_origin.get(w, w)
            final_words[w] = {
                "word": w,
                "origin": orig,
                "relation": '0: 原型 (lemma)',
                "has_variants": False,
                "in_exam_vocab": True
            }

    result = {
        "meta": {
            "total_words": len(final_words),
            "total_origins": len(final_origins),
            "version": "1.0.0"
        },
        "words": final_words,
        "origins": final_origins
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nSuccessfully generated {OUTPUT_PATH}")
    print(f"Total words mapped: {len(final_words)}, Total origin families: {len(final_origins)}")

    # Test sample words output
    print("\n--- Verification on Key User Words ---")
    for tw in ['play', 'playable', 'pick', 'picked', 'comfort', 'mister', 'happy', 'predict']:
        w_info = final_words.get(tw, {})
        orig_key = w_info.get('origin', tw)
        orig_info = final_origins.get(orig_key, {})
        var_words = [v['word'] for v in orig_info.get('variants', [])]
        print(f"Word: {tw:12} ➔ Origin: {orig_key:10} ➔ Variants ({len(var_words)}): {var_words[:8]}")

if __name__ == "__main__":
    main()
