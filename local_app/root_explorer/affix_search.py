#!/usr/bin/env python3
"""
affix_search.py — Morphological & Syntactic Compound Search Engine

Allows searching vocabulary by combining:
  1. Prefix (e.g. 'com*', 'pre*', 'un*')
  2. Postfix / Suffix (e.g. '*te', '*tion', '*able', '*ly')
  3. Part of Speech (e.g. 'verb', 'noun', 'adj', 'adv')
  4. Level constraint (e.g. 1-4, or 1-6)

Example:
    search_words(prefix='com', postfix='te', pos='verb')
    ➔ ['complete', 'compete', 'complicate', 'compensate']
"""

import json
import os
import re
from typing import List, Dict, Optional, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXAM_WORDS_PATH = os.path.join(PROJECT_ROOT, "database", "exam_words.json")
ROOTS_PATH = os.path.join(PROJECT_ROOT, "database", "word_roots_breakdown.json")

# POS mapping normalization
POS_MAP = {
    "v": ["v.", "vi.", "vt.", "verb"],
    "verb": ["v.", "vi.", "vt.", "verb"],
    "n": ["n.", "noun"],
    "noun": ["n.", "noun"],
    "adj": ["adj.", "a.", "adjective"],
    "a": ["adj.", "a.", "adjective"],
    "adv": ["adv.", "r.", "adverb"],
    "r": ["adv.", "r.", "adverb"],
    "prep": ["prep.", "preposition"],
    "conj": ["conj.", "conjunction"],
    "pron": ["pron.", "pronoun"]
}

class AffixSearchEngine:
    def __init__(self, exam_words_path: str = EXAM_WORDS_PATH, roots_path: str = ROOTS_PATH):
        self.words = {}
        self.roots = {}
        
        if os.path.exists(exam_words_path):
            with open(exam_words_path, "r", encoding="utf-8") as f:
                self.words = json.load(f)["words"]
        
        if os.path.exists(roots_path):
            with open(roots_path, "r", encoding="utf-8") as f:
                self.roots = json.load(f)

    def match_pos(self, entry: Dict[str, Any], target_pos: str) -> bool:
        if not target_pos:
            return True
        norm_key = target_pos.lower().strip().rstrip('.')
        accepted_tags = POS_MAP.get(norm_key, [norm_key])

        # 1. Check entry['pos']
        word_pos_list = [p.lower().strip() for p in entry.get("pos", [])]
        for tag in accepted_tags:
            if any(tag in wp for wp in word_pos_list):
                return True

        # 2. Check definition text if pos list empty
        zh_defs = entry.get("definitions", {}).get("zh", [])
        if isinstance(zh_defs, list):
            for d in zh_defs:
                for tag in accepted_tags:
                    if d.lower().startswith(tag) or f"[{tag}" in d.lower():
                        return True

        return False

    def search(
        self,
        prefix: Optional[str] = None,
        postfix: Optional[str] = None,
        pos: Optional[str] = None,
        min_level: int = 1,
        max_level: int = 6,
        only_exam: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute compound query.
        Both prefix and postfix can be specified simultaneously.
        """
        pfx = prefix.lower().rstrip('*').strip() if prefix else ""
        sfx = postfix.lower().lstrip('*').strip() if postfix else ""

        results = []

        for w, entry in self.words.items():
            # Level filter
            lv = entry.get("level", 0)
            if not (min_level <= lv <= max_level):
                continue

            # Exam only filter
            cnt = entry.get("total_appear", 0)
            if only_exam and cnt == 0:
                continue

            # Prefix filter
            if pfx and not w.startswith(pfx):
                continue

            # Postfix filter
            if sfx and not w.endswith(sfx):
                continue

            # Ensure word is long enough to have both prefix and postfix without overlap
            if pfx and sfx and len(w) < len(pfx) + len(sfx) - 1:
                continue

            # POS filter
            if pos and not self.match_pos(entry, pos):
                continue

            zh_defs = entry.get("definitions", {}).get("zh", [])
            en_defs = entry.get("definitions", {}).get("en", [])

            results.append({
                "word": w,
                "level": lv,
                "pos": entry.get("pos", []),
                "total_appear": cnt,
                "appear_years": entry.get("appear_year", []),
                "zh": zh_defs[:2] if zh_defs else [],
                "en": en_defs[:2] if en_defs else [],
                "root_breakdown": self.roots.get(w)
            })

        # Sort results: level ascending, then appearance count descending, then alphabetical
        results.sort(key=lambda x: (x["level"], -x["total_appear"], x["word"]))
        return results

# Singleton engine instance
_engine = None

def get_engine() -> AffixSearchEngine:
    global _engine
    if _engine is None:
        _engine = AffixSearchEngine()
    return _engine

def search_words(**kwargs) -> List[Dict[str, Any]]:
    return get_engine().search(**kwargs)

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    engine = get_engine()
    print("Testing Affix Search Engine:")
    print("1. Query: prefix='com', pos='verb':")
    res1 = engine.search(prefix="com", pos="verb")
    for r in res1[:10]:
        print(f"   • {r['word']:14} [Lv{r['level']}] {r['pos']} -> {r['zh'][0] if r['zh'] else ''}")

    print("\n2. Query: prefix='com', postfix='te', pos='verb':")
    res2 = engine.search(prefix="com", postfix="te", pos="verb")
    for r in res2[:10]:
        print(f"   • {r['word']:14} [Lv{r['level']}] {r['pos']} -> {r['zh'][0] if r['zh'] else ''}")

    print("\n3. Query: prefix='un', postfix='able', pos='adj':")
    res3 = engine.search(prefix="un", postfix="able", pos="adj")
    for r in res3[:10]:
        print(f"   • {r['word']:14} [Lv{r['level']}] {r['pos']} -> {r['zh'][0] if r['zh'] else ''}")
