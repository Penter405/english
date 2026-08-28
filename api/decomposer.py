"""
Root Explorer — Graph Search Engine

1. User inputs a word
2. Check if it's a basic word → add to results
3. Strip prefixes/suffixes → get core(s)
4. For each core: apply 6 sound rules to swap letters (BFS)
5. Each neighbor matching a basic word or root → add to results
6. 5-second deadline → return best results with confidence
7. Nothing found → TOO_HARD
"""

import json
import os
import time
from typing import List, Dict, Optional, Tuple, Set
from collections import deque

from sound_rules import RULES, are_interchangeable


class Decomposer:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "word_database.json")

        with open(db_path, "r", encoding="utf-8") as f:
            self.db = json.load(f)

        self.roots: Dict = self.db["roots"]
        self.prefixes: Dict = self.db["affixes"]["prefixes"]
        self.suffixes: Dict = self.db["affixes"]["suffixes"]
        self.simple_words: Dict = self.db.get("simple_words", {})

        # Basic word set: all simple/origin words
        self.basic_words: Set[str] = set()
        for sw in self.simple_words:
            self.basic_words.add(sw.lower())
        for rk, rd in self.roots.items():
            ow = rd.get("origin_word", "").lower()
            if ow:
                self.basic_words.add(ow)

        # origin_word -> root keys
        self.origin_to_roots: Dict[str, List[str]] = {}
        for rk, rd in self.roots.items():
            ow = rd.get("origin_word", "").lower()
            if ow:
                self.origin_to_roots.setdefault(ow, []).append(rk)

        self._sorted_prefixes = sorted(self.prefixes, key=len, reverse=True)
        self._sorted_suffixes = sorted(self.suffixes, key=len, reverse=True)
        self._sorted_roots = sorted(self.roots, key=len, reverse=True)

        # Precompute: char -> set of chars it can swap with
        self._swaps: Dict[str, Set[str]] = {}
        for rule_id, rule in RULES.items():
            for c in rule["group"]:
                self._swaps.setdefault(c, set()).update(rule["group"])

    # ================================================================== #
    #  PUBLIC API                                                         #
    # ================================================================== #

    def decompose(self, word: str) -> Dict:
        """Main entry. Graph-search the word to find related basic words."""
        wl = word.lower().strip()
        deadline = time.time() + 5.0

        # --- Step 1: Strip affixes to get cores ---
        cores = self._strip_affixes(wl)

        # --- Step 2: Graph search from each core ---
        all_found = []

        for pfxs, core, sfxs in cores:
            # Is core a basic word?
            if core in self.basic_words:
                all_found.append({
                    "basic_word": core, "core": core,
                    "path": [core], "transforms": [],
                    "prefixes": pfxs, "suffixes": sfxs,
                    "score": 100, "via": "direct"
                })

            # Is core a known root?
            if core in self.roots:
                rd = self.roots[core]
                all_found.append({
                    "basic_word": rd["origin_word"].lower(), "core": core,
                    "path": [core, rd["origin_word"].lower()],
                    "transforms": [{
                        "from_word": core, "to_word": rd["origin_word"].lower(),
                        "rule": rd["rule"], "rule_name": rd.get("rule_name", ""),
                        "explanation": rd["explanation"]
                    }],
                    "prefixes": pfxs, "suffixes": sfxs,
                    "score": 95, "via": "root"
                })

            # Is core two roots? (e.g. "unicorn" core after no stripping)
            for r1 in self._sorted_roots:
                if core.startswith(r1) and len(core) > len(r1):
                    rem = core[len(r1):]
                    if rem in self.roots:
                        rd1 = self.roots[r1]
                        rd2 = self.roots[rem]
                        all_found.append({
                            "basic_word": rd1["origin_word"].lower(),
                            "core": r1, "path": [r1, rd1["origin_word"].lower()],
                            "transforms": [{"from_word": r1, "to_word": rd1["origin_word"].lower(),
                                            "rule": rd1["rule"], "rule_name": rd1.get("rule_name", ""),
                                            "explanation": rd1["explanation"]}],
                            "prefixes": pfxs, "suffixes": sfxs,
                            "score": 93, "via": "root"
                        })
                        all_found.append({
                            "basic_word": rd2["origin_word"].lower(),
                            "core": rem, "path": [rem, rd2["origin_word"].lower()],
                            "transforms": [{"from_word": rem, "to_word": rd2["origin_word"].lower(),
                                            "rule": rd2["rule"], "rule_name": rd2.get("rule_name", ""),
                                            "explanation": rd2["explanation"]}],
                            "prefixes": pfxs, "suffixes": sfxs,
                            "score": 93, "via": "root"
                        })

            # BFS: swap letters using sound rules
            bfs_hits = self._bfs_sound_search(core, deadline)
            for hit in bfs_hits:
                hit["prefixes"] = pfxs
                hit["suffixes"] = sfxs
            all_found.extend(bfs_hits)

            if time.time() >= deadline:
                break

        # --- Step 3: Build response ---
        if not all_found:
            return {
                "word": word, "found": False,
                "confidence": "TOO_HARD",
                "components": [], "origin_trace": [],
                "word_family": {}, "friend_words": [],
                "message": "The Root Engine could not reliably analyze this word. We recommend using an AI for deeper analysis."
            }

        # Deduplicate by basic_word, keep highest score
        seen = {}
        for hit in all_found:
            bw = hit["basic_word"]
            if bw not in seen or hit["score"] > seen[bw]["score"]:
                seen[bw] = hit

        unique_results = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
        best = unique_results[0]

        # Confidence
        if best["score"] >= 80:
            confidence = "HIGH_CONFIDENCE"
        elif best["score"] >= 50:
            confidence = "MEDIUM_CONFIDENCE"
        elif best["score"] > 0:
            confidence = "LOW_CONFIDENCE"
        else:
            confidence = "TOO_HARD"

        return self._build_response(word, unique_results, best, confidence)

    # ================================================================== #
    #  BFS SOUND SEARCH                                                   #
    # ================================================================== #

    def _bfs_sound_search(self, start: str, deadline: float) -> List[Dict]:
        """BFS: swap letters using sound rules, find basic words/roots."""
        results = []
        queue = deque([(start, [start], [])])
        visited = {start}
        max_depth = 3

        while queue and time.time() < deadline:
            current, path, transforms = queue.popleft()
            if len(path) > max_depth + 1:
                continue

            for neighbor, swap in self._neighbors(current):
                if neighbor in visited:
                    continue
                visited.add(neighbor)

                new_path = path + [neighbor]
                new_transforms = transforms + [swap]
                depth = len(new_path) - 1
                score = max(0, 85 - depth * 15)

                # Hit a basic word?
                if neighbor in self.basic_words:
                    results.append({
                        "basic_word": neighbor, "core": start,
                        "path": new_path, "transforms": new_transforms,
                        "score": score, "via": "sound_rule"
                    })

                # Hit a known root?
                if neighbor in self.roots:
                    rd = self.roots[neighbor]
                    results.append({
                        "basic_word": rd["origin_word"].lower(), "core": start,
                        "path": new_path + [rd["origin_word"].lower()],
                        "transforms": new_transforms + [{
                            "from_word": neighbor, "to_word": rd["origin_word"].lower(),
                            "rule": rd["rule"], "rule_name": rd.get("rule_name", ""),
                            "explanation": rd["explanation"]
                        }],
                        "score": score, "via": "sound_rule_to_root"
                    })

                if depth < max_depth:
                    queue.append((neighbor, new_path, new_transforms))

        return results

    def _neighbors(self, word: str) -> List[Tuple[str, Dict]]:
        """Generate all single-letter-swap neighbors using the 6 rules."""
        result = []
        for i, ch in enumerate(word):
            for new_ch in self._swaps.get(ch, set()):
                if new_ch == ch:
                    continue
                new_word = word[:i] + new_ch + word[i+1:]
                rules = are_interchangeable(ch, new_ch)
                result.append((new_word, {
                    "from_word": word, "to_word": new_word,
                    "position": i, "from_char": ch, "to_char": new_ch,
                    "rules": rules,
                    "rule_names": [RULES[r]["name"] for r in rules]
                }))
        return result

    # ================================================================== #
    #  AFFIX STRIPPING                                                    #
    # ================================================================== #

    def _strip_affixes(self, word: str) -> List[Tuple[List[str], str, List[str]]]:
        """Strip known prefixes/suffixes. Returns (pfx_list, core, sfx_list) candidates."""
        results = [([], word, [])]

        for p in self._sorted_prefixes:
            if word.startswith(p) and len(word) > len(p) + 1:
                rem = word[len(p):]
                results.append(([p], rem, []))
                for s in self._sorted_suffixes:
                    if rem.endswith(s) and len(rem) > len(s) + 1:
                        results.append(([p], rem[:-len(s)], [s]))

        for s in self._sorted_suffixes:
            if word.endswith(s) and len(word) > len(s) + 1:
                results.append(([], word[:-len(s)], [s]))

        return results

    # ================================================================== #
    #  BUILD RESPONSE                                                     #
    # ================================================================== #

    def _build_response(self, word: str, results: List[Dict], best: Dict, confidence: str) -> Dict:
        components = []
        origin_trace = []
        word_family = {}

        # Prefixes
        for p in best.get("prefixes", []):
            components.append(self._affix_comp(p, True))

        # Core / root
        core = best["core"]
        if core in self.roots:
            rd = self.roots[core]
            components.append({
                "type": "root", "text": core,
                "meaning": rd["meaning"], "meaning_zh": rd.get("meaning_zh", ""),
                "origin_word": rd["origin_word"],
                "rule": rd["rule"], "rule_name": rd.get("rule_name", ""),
                "explanation": rd["explanation"]
            })
            origin_trace.append({
                "root": core, "meaning": rd["meaning"],
                "origin_word": rd["origin_word"],
                "rule": rd["rule"], "rule_name": rd.get("rule_name", ""),
                "explanation": rd["explanation"]
            })
            word_family[core] = {"meaning": rd["meaning"], "derived_words": rd.get("derived_words", [])}
        elif core in self.basic_words:
            sd = self.simple_words.get(core, {"meaning": core})
            components.append({
                "type": "simple_word", "text": core,
                "meaning": sd.get("meaning", core), "meaning_zh": sd.get("meaning_zh", "")
            })
            for rk in self.origin_to_roots.get(core, []):
                rd = self.roots[rk]
                origin_trace.append({
                    "root": rk, "meaning": rd["meaning"], "origin_word": core,
                    "rule": rd["rule"], "rule_name": rd.get("rule_name", ""),
                    "explanation": rd["explanation"]
                })
                word_family[rk] = {"meaning": rd["meaning"], "derived_words": rd.get("derived_words", [])}
        else:
            components.append({"type": "core", "text": core, "meaning": f"→ {best['basic_word']}", "meaning_zh": ""})

        # Suffixes
        for s in best.get("suffixes", []):
            components.append(self._affix_comp(s, False))

        # Friend words: all basic words found via graph search
        friend_words = []
        seen_bw = set()
        for r in results:
            bw = r["basic_word"]
            if bw in seen_bw:
                continue
            seen_bw.add(bw)
            path_display = " → ".join(r["path"])
            rules_used = ", ".join(
                f"{t['from_char']}↔{t['to_char']} (Rule {t['rules'][0]})"
                for t in r.get("transforms", []) if "from_char" in t
            )
            if not rules_used:
                for t in r.get("transforms", []):
                    if "explanation" in t:
                        rules_used = t["explanation"]
                        break
            friend_words.append({
                "basic_word": bw,
                "path": r["path"],
                "path_display": path_display,
                "rules_used": rules_used,
                "score": r["score"]
            })
            # Add word families for this basic word's roots
            for rk in self.origin_to_roots.get(bw, []):
                if rk not in word_family:
                    rd = self.roots[rk]
                    word_family[rk] = {"meaning": rd["meaning"], "derived_words": rd.get("derived_words", [])}

        return {
            "word": word, "found": True, "confidence": confidence,
            "components": components, "origin_trace": origin_trace,
            "word_family": word_family, "friend_words": friend_words
        }

    def _affix_comp(self, seg: str, is_prefix: bool) -> Dict:
        src = self.prefixes if is_prefix else self.suffixes
        kind = "prefix" if is_prefix else "suffix"
        if seg in src:
            d = src[seg]
            return {"type": kind, "text": seg,
                    "meaning": d["meaning"] if isinstance(d, dict) else d,
                    "meaning_zh": d.get("meaning_zh", "") if isinstance(d, dict) else ""}
        return {"type": kind, "text": seg, "meaning": f"({kind})", "meaning_zh": ""}

    # ================================================================== #
    #  SUPPORTING API                                                     #
    # ================================================================== #

    def get_word_family(self, root_key: str) -> Dict:
        if root_key not in self.roots:
            return {"found": False, "message": f"Root '{root_key}' not found"}
        rd = self.roots[root_key]
        return {
            "root": root_key, "found": True,
            "meaning": rd["meaning"], "meaning_zh": rd.get("meaning_zh", ""),
            "origin_word": rd["origin_word"], "rule": rd["rule"],
            "explanation": rd["explanation"],
            "derived_words": rd.get("derived_words", [])
        }

    def search_by_root(self, query: str) -> List[Dict]:
        q = query.lower().strip()
        out = []
        for rk, rd in self.roots.items():
            if q in rk or q in rd["meaning"].lower() or q == rd["origin_word"].lower():
                out.append({
                    "root": rk, "meaning": rd["meaning"],
                    "meaning_zh": rd.get("meaning_zh", ""),
                    "origin_word": rd["origin_word"],
                    "derived_words": rd.get("derived_words", []),
                    "rule": rd["rule"], "explanation": rd["explanation"]
                })
        return out
