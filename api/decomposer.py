"""
Root Explorer — Engine Orchestrator (v2)

Coordinates the database, search engine, and scoring modules to analyze words.
This is the refactored decomposer that uses real linguistic data instead of
just a hand-crafted JSON file.

Preserved: The original sound-rules BFS as one search strategy.
Added: MorphoLex decompositions, etymological relationships, affix stripping.

Architecture (spec Section 27):
  DATABASE → "What linguistic facts are known?"
  ENGINE   → "Which known facts form the best path?"
  FRONTEND → "How should the result be shown?"
"""

import json
import os
import sys
import time
from typing import List, Dict, Optional, Set

# Ensure api/ directory is in path
sys.path.insert(0, os.path.dirname(__file__))

from database import Database
from search import SearchEngine
from scoring import score_candidate, classify_confidence, select_best_candidate, LOW_THRESHOLD
from sound_rules import RULES
from models import DEFAULT_DB_PATH

# Also keep the legacy JSON database for backward compatibility
LEGACY_DB_PATH = os.path.join(os.path.dirname(__file__), "word_database.json")


class Decomposer:
    """Root Explorer Engine — word analysis orchestrator."""

    ENGINE_VERSION = "2.0"

    def __init__(self, db_path: str = None):
        # Try to use the new SQLite database
        if db_path is None:
            db_path = DEFAULT_DB_PATH

        self._use_new_db = os.path.exists(db_path)

        if self._use_new_db:
            self.db = Database(db_path)
            # Build sound-rule swap map for the search engine
            swaps = {}
            for rule_id, rule in RULES.items():
                for c in rule["group"]:
                    swaps.setdefault(c, set()).update(rule["group"])
            self.search_engine = SearchEngine(self.db, swaps)
        else:
            self.db = None
            self.search_engine = None

        # Also load legacy JSON for fallback and compatibility
        self._legacy_db = None
        self._legacy_roots = {}
        self._legacy_prefixes = {}
        self._legacy_suffixes = {}
        self._legacy_simple_words = {}
        self._legacy_basic_words = set()
        self._legacy_origin_to_roots = {}

        legacy_path = db_path if db_path.endswith(".json") else LEGACY_DB_PATH
        if os.path.exists(legacy_path) and legacy_path.endswith(".json"):
            self._load_legacy(legacy_path)

    def _load_legacy(self, path: str):
        """Load legacy JSON database for backward compatibility."""
        with open(path, "r", encoding="utf-8") as f:
            self._legacy_db = json.load(f)
        self._legacy_roots = self._legacy_db.get("roots", {})
        self._legacy_prefixes = self._legacy_db.get("affixes", {}).get("prefixes", {})
        self._legacy_suffixes = self._legacy_db.get("affixes", {}).get("suffixes", {})
        self._legacy_simple_words = self._legacy_db.get("simple_words", {})
        for sw in self._legacy_simple_words:
            self._legacy_basic_words.add(sw.lower())
        for rk, rd in self._legacy_roots.items():
            ow = rd.get("origin_word", "").lower()
            if ow:
                self._legacy_basic_words.add(ow)
                self._legacy_origin_to_roots.setdefault(ow, []).append(rk)

    # ================================================================== #
    #  PUBLIC API                                                         #
    # ================================================================== #

    def decompose(self, word: str) -> Dict:
        """Main entry point: analyze a word and return structured results.

        Uses the new database-driven engine if available,
        falls back to legacy JSON engine otherwise.
        """
        wl = word.lower().strip()
        start_time = time.time()
        deadline = start_time + 5.0  # spec Section 18

        if self._use_new_db and self.db:
            result = self._decompose_v2(word, wl, deadline)
        else:
            result = self._decompose_legacy(word, wl, deadline)

        search_time = time.time() - start_time
        result["search_time"] = round(search_time, 3)

        # Log unknown words (spec Section 24)
        if not result.get("found") and self.db:
            reason = "TIMEOUT" if search_time >= 4.9 else "NO_CANDIDATE"
            self.db.log_unknown_word(wl, reason, search_time, 0.0)

        return result

    def _decompose_v2(self, word: str, wl: str, deadline: float) -> Dict:
        """New database-driven decomposition engine."""

        # Check if it's a simple word / basic word first
        is_basic = self.db.is_basic_word(wl)
        word_info = self.db.get_word(wl)

        # Run search engine
        candidates = self.search_engine.search(wl, deadline)

        if not candidates:
            return self._too_hard_response(word)

        # Score all candidates
        best = select_best_candidate(candidates, self.db)

        if best is None:
            return self._too_hard_response(word)

        # Build structured response
        return self._build_v2_response(word, wl, best, candidates, is_basic, deadline)

    def _build_v2_response(self, word: str, wl: str, best: Dict,
                            all_candidates: List[Dict], is_basic: bool,
                            deadline: float = None) -> Dict:
        """Build the structured API response from the best candidate."""

        components = []
        origin_trace = []
        word_family = {}

        # Add prefixes
        for p in best.get("prefixes", []):
            info = self.db.get_affix_info(p, "prefix") if self.db else None
            components.append({
                "type": "prefix", "text": p,
                "meaning": info["meaning"] if info else "(prefix)",
                "meaning_zh": info.get("meaning_zh", "") if info else ""
            })

        # Add roots / core
        roots = best.get("roots", [])
        core = best.get("core", "")

        if not roots and core:
            roots = [core]

        for r in roots:
            root_info_list = self.db.get_roots_for_form(r) if self.db else []
            if root_info_list:
                ri = root_info_list[0]
                components.append({
                    "type": "root", "text": r,
                    "meaning": ri["meaning"] or r,
                    "meaning_zh": ri.get("meaning_zh", ""),
                    "language": ri.get("language", ""),
                })
                origin_trace.append({
                    "root": r,
                    "meaning": ri["meaning"],
                    "language": ri.get("language", ""),
                    "origin_word": best.get("basic_word", ""),
                    "explanation": ri.get("description", ""),
                    "reconstructed": ri.get("reconstructed", False)
                })
            elif r in self._legacy_roots:
                rd = self._legacy_roots[r]
                components.append({
                    "type": "root", "text": r,
                    "meaning": rd["meaning"],
                    "meaning_zh": rd.get("meaning_zh", ""),
                    "origin_word": rd.get("origin_word", ""),
                    "rule": rd.get("rule", ""),
                    "rule_name": rd.get("rule_name", ""),
                    "explanation": rd.get("explanation", "")
                })
                origin_trace.append({
                    "root": r, "meaning": rd["meaning"],
                    "origin_word": rd.get("origin_word", ""),
                    "rule": rd.get("rule", ""),
                    "rule_name": rd.get("rule_name", ""),
                    "explanation": rd.get("explanation", "")
                })
                word_family[r] = {
                    "meaning": rd["meaning"],
                    "derived_words": rd.get("derived_words", [])
                }
            else:
                # Root found but no detailed info
                comp_data = {"type": "root", "text": r, "meaning": r, "meaning_zh": ""}
                if is_basic or r == wl:
                    comp_data["type"] = "simple_word"
                    if self.db:
                        wi = self.db.get_word(r)
                        if wi and wi.get("definition"):
                            comp_data["meaning"] = wi["definition"]
                components.append(comp_data)

        # Add suffixes
        for s in best.get("suffixes", []):
            info = self.db.get_affix_info(s, "suffix") if self.db else None
            components.append({
                "type": "suffix", "text": s,
                "meaning": info["meaning"] if info else "(suffix)",
                "meaning_zh": info.get("meaning_zh", "") if info else ""
            })

        # Friend words from legacy data
        for r in roots:
            if r in self._legacy_roots:
                rd = self._legacy_roots[r]
                if r not in word_family:
                    word_family[r] = {
                        "meaning": rd["meaning"],
                        "derived_words": rd.get("derived_words", [])
                    }
            # Also check origin_to_roots
            basic = best.get("basic_word", "")
            if basic:
                for rk in self._legacy_origin_to_roots.get(basic, []):
                    if rk not in word_family:
                        rd = self._legacy_roots[rk]
                        word_family[rk] = {
                            "meaning": rd["meaning"],
                            "derived_words": rd.get("derived_words", [])
                        }

        # ============================================================
        # ROOT-LEVEL FRIEND WORD SEARCH
        # Run BFS on EACH root/component to find real English friend words
        # e.g. uniform → uni+form → BFS("uni") finds "one"
        # ============================================================
        friend_words = []
        seen_friends = set()
        if deadline is None:
            deadline = time.time() + 3.0
        remaining_time = deadline - time.time()

        if self.search_engine and remaining_time > 0.5:
            # Collect all components to search (roots + prefixes that look like roots)
            components_to_search = []
            for r in roots:
                if len(r) >= 2:
                    components_to_search.append(r)
            for p in best.get("prefixes", []):
                if len(p) >= 2:
                    components_to_search.append(p)

            # Budget time equally across components
            per_component_budget = max(0.3, remaining_time / max(len(components_to_search), 1))

            for component in components_to_search:
                component_deadline = time.time() + per_component_budget
                component_deadline = min(component_deadline, deadline)

                # Run BFS on this individual root/component
                root_friends = self.search_engine.find_root_friend_words(
                    component, component_deadline
                )

                for rf in root_friends:
                    friend = rf["friend"]
                    if friend not in seen_friends and friend != wl:
                        seen_friends.add(friend)
                        friend_words.append({
                            "basic_word": friend,
                            "from_root": rf["from_root"],
                            "path": rf["path"],
                            "path_display": rf["path_display"],
                            "rules_used": rf["rules_used"],
                            "score": rf["score"]
                        })

        # Also add friend words from curated database
        if self.db:
            friends = self.db.get_friend_words(wl)
            for fw in friends:
                if fw["friend"] not in seen_friends:
                    seen_friends.add(fw["friend"])
                    friend_words.append({
                        "basic_word": fw["friend"],
                        "from_root": fw.get("shared_root", ""),
                        "path": [wl, fw["friend"]],
                        "path_display": f"{wl} → {fw['friend']}",
                        "rules_used": f"shared root: {fw['shared_root']}",
                        "score": fw["confidence"] * 100
                    })

        # Sort by score (best first), limit to 30
        friend_words.sort(key=lambda x: -x.get("score", 0))

        return {
            "word": word,
            "found": True,
            "status": "FOUND",
            "confidence": best.get("confidence", "MEDIUM_CONFIDENCE"),
            "is_simple_word": is_basic,
            "components": components,
            "origin_trace": origin_trace,
            "word_family": word_family,
            "friend_words": friend_words[:30],
            "basic_word": best.get("basic_word", ""),
            "affixes": best.get("prefixes", []) + best.get("suffixes", []),
            "roots": best.get("roots", []),
            "explanation": self._build_explanation(word, best, components)
        }

    def _build_explanation(self, word: str, best: Dict, components: List[Dict]) -> str:
        """Build a human-readable explanation."""
        parts = []
        for c in components:
            if c["type"] == "prefix":
                parts.append(f"{c['text']}- (prefix: {c['meaning']})")
            elif c["type"] == "root" or c["type"] == "simple_word":
                parts.append(f"{c['text']} (root: {c['meaning']})")
            elif c["type"] == "suffix":
                parts.append(f"-{c['text']} (suffix: {c['meaning']})")

        if parts:
            structure = " + ".join(parts)
            return f'"{word}" = {structure}'
        return f'"{word}" analyzed via {best.get("via", "unknown")} strategy'

    def _too_hard_response(self, word: str) -> Dict:
        """Return a TOO_HARD response (spec Section 20)."""
        return {
            "word": word,
            "found": False,
            "status": "TOO_HARD",
            "confidence": "TOO_HARD",
            "is_simple_word": False,
            "components": [],
            "origin_trace": [],
            "word_family": {},
            "friend_words": [],
            "basic_word": "",
            "affixes": [],
            "roots": [],
            "explanation": "",
            "message": (
                "This word is too complex for the deterministic Root Engine "
                "to analyze reliably. Try an AI assistant for a deeper "
                "etymological explanation."
            )
        }

    # ================================================================== #
    #  LEGACY ENGINE (backward compatibility)                             #
    # ================================================================== #

    def _decompose_legacy(self, word: str, wl: str, deadline: float) -> Dict:
        """Legacy decomposition using word_database.json only."""
        from collections import deque
        from sound_rules import are_interchangeable

        sorted_prefixes = sorted(self._legacy_prefixes, key=len, reverse=True)
        sorted_suffixes = sorted(self._legacy_suffixes, key=len, reverse=True)
        sorted_roots = sorted(self._legacy_roots, key=len, reverse=True)

        # Build swap map
        swaps = {}
        for rule_id, rule in RULES.items():
            for c in rule["group"]:
                swaps.setdefault(c, set()).update(rule["group"])

        # Strip affixes
        cores = [([], wl, [])]
        for p in sorted_prefixes:
            if wl.startswith(p) and len(wl) > len(p) + 1:
                rem = wl[len(p):]
                cores.append(([p], rem, []))
                for s in sorted_suffixes:
                    if rem.endswith(s) and len(rem) > len(s) + 1:
                        cores.append(([p], rem[:-len(s)], [s]))
        for s in sorted_suffixes:
            if wl.endswith(s) and len(wl) > len(s) + 1:
                cores.append(([], wl[:-len(s)], [s]))

        all_found = []

        for pfxs, core, sfxs in cores:
            if core in self._legacy_basic_words:
                all_found.append({
                    "basic_word": core, "core": core,
                    "path": [core], "transforms": [],
                    "prefixes": pfxs, "suffixes": sfxs,
                    "score": 100, "via": "direct"
                })
            if core in self._legacy_roots:
                rd = self._legacy_roots[core]
                all_found.append({
                    "basic_word": rd["origin_word"].lower(), "core": core,
                    "path": [core, rd["origin_word"].lower()],
                    "transforms": [{"from_word": core, "to_word": rd["origin_word"].lower(),
                                    "rule": rd["rule"], "rule_name": rd.get("rule_name", ""),
                                    "explanation": rd["explanation"]}],
                    "prefixes": pfxs, "suffixes": sfxs,
                    "score": 95, "via": "root"
                })
            # Compound roots
            for r1 in sorted_roots:
                if core.startswith(r1) and len(core) > len(r1):
                    rem = core[len(r1):]
                    if rem in self._legacy_roots:
                        rd1, rd2 = self._legacy_roots[r1], self._legacy_roots[rem]
                        all_found.append({
                            "basic_word": rd1["origin_word"].lower(), "core": r1,
                            "path": [r1, rd1["origin_word"].lower()],
                            "transforms": [{"from_word": r1, "to_word": rd1["origin_word"].lower(),
                                            "rule": rd1["rule"], "rule_name": rd1.get("rule_name", ""),
                                            "explanation": rd1["explanation"]}],
                            "prefixes": pfxs, "suffixes": sfxs, "score": 93, "via": "root"
                        })
                        all_found.append({
                            "basic_word": rd2["origin_word"].lower(), "core": rem,
                            "path": [rem, rd2["origin_word"].lower()],
                            "transforms": [{"from_word": rem, "to_word": rd2["origin_word"].lower(),
                                            "rule": rd2["rule"], "rule_name": rd2.get("rule_name", ""),
                                            "explanation": rd2["explanation"]}],
                            "prefixes": pfxs, "suffixes": sfxs, "score": 93, "via": "root"
                        })

            # BFS sound search
            queue = deque([(core, [core], [])])
            visited = {core}
            max_depth = 3
            while queue and time.time() < deadline:
                current, path, transforms = queue.popleft()
                if len(path) > max_depth + 1:
                    continue
                for i, ch in enumerate(current):
                    for new_ch in swaps.get(ch, set()):
                        if new_ch == ch:
                            continue
                        neighbor = current[:i] + new_ch + current[i+1:]
                        if neighbor in visited:
                            continue
                        visited.add(neighbor)
                        new_path = path + [neighbor]
                        rules = are_interchangeable(ch, new_ch)
                        swap_info = {"from_word": current, "to_word": neighbor,
                                     "position": i, "from_char": ch, "to_char": new_ch,
                                     "rules": rules,
                                     "rule_names": [RULES[r]["name"] for r in rules]}
                        new_transforms = transforms + [swap_info]
                        depth = len(new_path) - 1
                        score = max(0, 85 - depth * 15)
                        if neighbor in self._legacy_basic_words:
                            all_found.append({
                                "basic_word": neighbor, "core": core,
                                "path": new_path, "transforms": new_transforms,
                                "prefixes": pfxs, "suffixes": sfxs,
                                "score": score, "via": "sound_rule"
                            })
                        if neighbor in self._legacy_roots:
                            rd = self._legacy_roots[neighbor]
                            all_found.append({
                                "basic_word": rd["origin_word"].lower(), "core": core,
                                "path": new_path + [rd["origin_word"].lower()],
                                "transforms": new_transforms + [{
                                    "from_word": neighbor, "to_word": rd["origin_word"].lower(),
                                    "rule": rd["rule"], "rule_name": rd.get("rule_name", ""),
                                    "explanation": rd["explanation"]}],
                                "score": score, "via": "sound_rule_to_root"
                            })
                        if depth < max_depth:
                            queue.append((neighbor, new_path, new_transforms))
            if time.time() >= deadline:
                break

        if not all_found:
            return self._too_hard_response(word)

        # Deduplicate
        seen = {}
        for hit in all_found:
            bw = hit["basic_word"]
            if bw not in seen or hit["score"] > seen[bw]["score"]:
                seen[bw] = hit
        unique = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
        best = unique[0]

        if best["score"] >= 80:
            confidence = "HIGH_CONFIDENCE"
        elif best["score"] >= 50:
            confidence = "MEDIUM_CONFIDENCE"
        elif best["score"] > 0:
            confidence = "LOW_CONFIDENCE"
        else:
            confidence = "TOO_HARD"

        return self._build_legacy_response(word, unique, best, confidence)

    def _build_legacy_response(self, word, results, best, confidence):
        """Build response in the legacy format (compatible with existing frontend)."""
        components = []
        origin_trace = []
        word_family = {}

        for p in best.get("prefixes", []):
            d = self._legacy_prefixes.get(p, {})
            components.append({
                "type": "prefix", "text": p,
                "meaning": d["meaning"] if isinstance(d, dict) else str(d),
                "meaning_zh": d.get("meaning_zh", "") if isinstance(d, dict) else ""
            })

        core = best["core"]
        if core in self._legacy_roots:
            rd = self._legacy_roots[core]
            components.append({
                "type": "root", "text": core, "meaning": rd["meaning"],
                "meaning_zh": rd.get("meaning_zh", ""),
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
        elif core in self._legacy_basic_words:
            sd = self._legacy_simple_words.get(core, {"meaning": core})
            components.append({
                "type": "simple_word", "text": core,
                "meaning": sd.get("meaning", core),
                "meaning_zh": sd.get("meaning_zh", "")
            })
            for rk in self._legacy_origin_to_roots.get(core, []):
                rd = self._legacy_roots[rk]
                origin_trace.append({
                    "root": rk, "meaning": rd["meaning"], "origin_word": core,
                    "rule": rd["rule"], "rule_name": rd.get("rule_name", ""),
                    "explanation": rd["explanation"]
                })
                word_family[rk] = {"meaning": rd["meaning"], "derived_words": rd.get("derived_words", [])}
        else:
            components.append({"type": "core", "text": core, "meaning": f"→ {best['basic_word']}", "meaning_zh": ""})

        for s in best.get("suffixes", []):
            d = self._legacy_suffixes.get(s, {})
            components.append({
                "type": "suffix", "text": s,
                "meaning": d["meaning"] if isinstance(d, dict) else str(d),
                "meaning_zh": d.get("meaning_zh", "") if isinstance(d, dict) else ""
            })

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
                "basic_word": bw, "path": r["path"],
                "path_display": path_display, "rules_used": rules_used,
                "score": r["score"]
            })
            for rk in self._legacy_origin_to_roots.get(bw, []):
                if rk not in word_family:
                    rd = self._legacy_roots[rk]
                    word_family[rk] = {"meaning": rd["meaning"], "derived_words": rd.get("derived_words", [])}

        return {
            "word": word, "found": True, "status": "FOUND",
            "confidence": confidence,
            "is_simple_word": best.get("via") == "direct",
            "components": components, "origin_trace": origin_trace,
            "word_family": word_family, "friend_words": friend_words,
            "basic_word": best.get("basic_word", ""),
            "affixes": best.get("prefixes", []) + best.get("suffixes", []),
            "roots": [best.get("core", "")],
            "explanation": ""
        }

    # ================================================================== #
    #  SUPPORTING API (backward compatible)                               #
    # ================================================================== #

    def get_word_family(self, root_key: str) -> Dict:
        """Get word family for a root."""
        if root_key in self._legacy_roots:
            rd = self._legacy_roots[root_key]
            return {
                "root": root_key, "found": True,
                "meaning": rd["meaning"], "meaning_zh": rd.get("meaning_zh", ""),
                "origin_word": rd["origin_word"], "rule": rd["rule"],
                "explanation": rd["explanation"],
                "derived_words": rd.get("derived_words", [])
            }
        # Try database
        if self.db:
            roots = self.db.get_roots_for_form(root_key)
            if roots:
                ri = roots[0]
                derived = self.db.get_derived_words(root_key)
                return {
                    "root": root_key, "found": True,
                    "meaning": ri["meaning"], "meaning_zh": ri.get("meaning_zh", ""),
                    "origin_word": "", "rule": "",
                    "explanation": ri.get("description", ""),
                    "derived_words": [d["word"] for d in derived[:20]]
                }
        return {"found": False, "message": f"Root '{root_key}' not found"}

    def search_by_root(self, query: str) -> List[Dict]:
        """Search for roots matching a query."""
        q = query.lower().strip()
        out = []
        for rk, rd in self._legacy_roots.items():
            if q in rk or q in rd["meaning"].lower() or q == rd["origin_word"].lower():
                out.append({
                    "root": rk, "meaning": rd["meaning"],
                    "meaning_zh": rd.get("meaning_zh", ""),
                    "origin_word": rd["origin_word"],
                    "derived_words": rd.get("derived_words", []),
                    "rule": rd["rule"], "explanation": rd["explanation"]
                })
        return out
