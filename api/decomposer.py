"""
Morphological Decomposer

Takes any English word and decomposes it into:
- Prefix(es)
- Root(s)
- Suffix(es)

Then for each root, finds the simple English word it originated from
via the sound-change rules.

Uses a candidate-scoring approach: generates multiple possible decompositions
and picks the one that explains the most characters with known roots.
"""

import json
import os
from typing import List, Dict, Optional, Tuple


class Decomposer:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "word_database.json")

        with open(db_path, "r", encoding="utf-8") as f:
            self.db = json.load(f)

        self.roots = self.db["roots"]
        self.prefixes = self.db["affixes"]["prefixes"]
        self.suffixes = self.db["affixes"]["suffixes"]

        # Build reverse index: derived_word -> root(s)
        self.derived_to_roots: Dict[str, List[str]] = {}
        for root_key, root_data in self.roots.items():
            for word in root_data.get("derived_words", []):
                word_lower = word.lower()
                if word_lower not in self.derived_to_roots:
                    self.derived_to_roots[word_lower] = []
                self.derived_to_roots[word_lower].append(root_key)

        # Sort by length (longest first) for greedy matching
        self._sorted_prefixes = sorted(self.prefixes.keys(), key=len, reverse=True)
        self._sorted_suffixes = sorted(self.suffixes.keys(), key=len, reverse=True)
        self._sorted_roots = sorted(self.roots.keys(), key=len, reverse=True)

        # Build a set of strings that are BOTH a prefix/suffix AND a root
        self._ambiguous_prefixes = set(self.prefixes.keys()) & set(self.roots.keys())

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def decompose(self, word: str) -> Dict:
        """
        Decompose a word into its morphological components.

        Returns a dict with:
        - word: the original word
        - components: list of {type, text, meaning, meaning_zh, ...}
        - origin_trace: for each root, the simple word it came from
        - word_family: for each root, other words sharing that root
        """
        word_lower = word.lower().strip()

        # Strategy 1: Check if this word is directly in our derived_words index
        if word_lower in self.derived_to_roots:
            return self._decompose_known_word(word_lower)

        # Strategy 2: Check if this word IS a root
        if word_lower in self.roots:
            return self._decompose_as_root(word_lower)

        # Strategy 3: Check if this word is a simple/origin word
        simple_words = self.db.get("simple_words", {})
        if word_lower in simple_words:
            return self._decompose_simple_word(word_lower)

        # Strategy 4: Try morphological decomposition (prefix + root + suffix)
        result = self._decompose_by_morphology(word_lower)
        if result and result.get("components"):
            return result

        # Strategy 5: Fallback — find any matching roots as substrings
        result = self._decompose_by_substring(word_lower)
        if result and result.get("components"):
            return result

        # Nothing found
        return {
            "word": word,
            "found": False,
            "components": [],
            "origin_trace": [],
            "word_family": {},
            "message": f"Could not find root word decomposition for '{word}'. Try a different word."
        }

    def get_word_family(self, root_key: str) -> Dict:
        """Get all dictionary words derived from a specific root."""
        if root_key not in self.roots:
            return {"found": False, "message": f"Root '{root_key}' not found"}

        root_data = self.roots[root_key]
        return {
            "root": root_key,
            "found": True,
            "meaning": root_data["meaning"],
            "meaning_zh": root_data.get("meaning_zh", ""),
            "origin_word": root_data["origin_word"],
            "rule": root_data["rule"],
            "explanation": root_data["explanation"],
            "derived_words": root_data.get("derived_words", [])
        }

    def search_by_root(self, query: str) -> List[Dict]:
        """Search for roots matching a query string."""
        query = query.lower().strip()
        results = []

        for root_key, root_data in self.roots.items():
            if (query in root_key
                    or query in root_data["meaning"].lower()
                    or query == root_data["origin_word"].lower()):
                results.append({
                    "root": root_key,
                    "meaning": root_data["meaning"],
                    "meaning_zh": root_data.get("meaning_zh", ""),
                    "origin_word": root_data["origin_word"],
                    "derived_words": root_data.get("derived_words", []),
                    "rule": root_data["rule"],
                    "explanation": root_data["explanation"]
                })

        return results

    # ------------------------------------------------------------------ #
    #  Candidate-based decomposition for known words                      #
    # ------------------------------------------------------------------ #

    def _decompose_known_word(self, word: str) -> Dict:
        """
        Decompose a word that exists in our derived_words index.
        Generates multiple candidate decompositions and picks the best.
        """
        root_keys = self.derived_to_roots[word]

        # Generate candidates: try with/without each possible prefix
        candidates = []

        # Candidate A: no prefix — try to match roots directly in the word
        candidates.append(self._try_decompose(word, root_keys, skip_prefix=True))

        # Candidate B: with prefix stripping
        candidates.append(self._try_decompose(word, root_keys, skip_prefix=False))

        # Pick the candidate with the highest score (most chars explained by roots)
        best = max(candidates, key=lambda c: c["score"])
        return best["result"]

    def _try_decompose(self, word: str, root_keys: List[str], skip_prefix: bool) -> Dict:
        """
        Try one decomposition approach. Returns {"score": int, "result": dict}.
        Score = total characters covered by identified roots.
        """
        remaining = word
        found_prefixes = []
        found_suffixes = []
        score = 0

        # --- Prefix phase ---
        if not skip_prefix:
            for prefix in self._sorted_prefixes:
                if remaining.startswith(prefix) and len(remaining) > len(prefix):
                    # Skip if this prefix is also a root and the remainder also starts
                    # with a known root (root interpretation is usually better)
                    if prefix in self._ambiguous_prefixes:
                        continue
                    after_prefix = remaining[len(prefix):]
                    if self._contains_root(after_prefix) or any(
                            after_prefix.startswith(r) for r in root_keys):
                        found_prefixes.append(prefix)
                        remaining = after_prefix
                        break

        # --- Suffix phase ---
        for suffix in self._sorted_suffixes:
            if remaining.endswith(suffix) and len(remaining) > len(suffix):
                after_suffix = remaining[:-len(suffix)]
                if self._contains_root(after_suffix) or any(
                        r in after_suffix or after_suffix in r for r in root_keys):
                    found_suffixes.append(suffix)
                    remaining = after_suffix
                    break

        # --- Root matching phase ---
        matched_roots = self._find_roots_in_string(remaining, root_keys)
        if not matched_roots:
            for rk in root_keys:
                matched_roots.append((rk, ""))

        # Calculate score: chars covered by roots
        score = sum(len(r[0]) for r in matched_roots)
        # Bonus for roots that are in the expected root_keys
        score += sum(3 for r, _ in matched_roots if r in root_keys)

        # Build result
        components = []
        origin_trace = []
        word_family = {}

        for prefix in found_prefixes:
            components.append(self._make_prefix_component(prefix))

        for root_key, leftover in matched_roots:
            if root_key in self.roots:
                comp, trace, family = self._make_root_components(root_key)
                components.append(comp)
                origin_trace.append(trace)
                word_family.update(family)

        for suffix in found_suffixes:
            components.append(self._make_suffix_component(suffix))

        result = {
            "word": word,
            "found": True,
            "components": components,
            "origin_trace": origin_trace,
            "word_family": word_family
        }

        return {"score": score, "result": result}

    # ------------------------------------------------------------------ #
    #  Strategy: word IS a root                                           #
    # ------------------------------------------------------------------ #

    def _decompose_as_root(self, word: str) -> Dict:
        """Decompose a word that is itself a root."""
        comp, trace, family = self._make_root_components(word)
        return {
            "word": word,
            "found": True,
            "components": [comp],
            "origin_trace": [trace],
            "word_family": family
        }

    # ------------------------------------------------------------------ #
    #  Strategy: word is a simple/origin word                             #
    # ------------------------------------------------------------------ #

    def _decompose_simple_word(self, word: str) -> Dict:
        """Handle when the input is a simple/origin word."""
        simple_data = self.db["simple_words"][word]

        related_roots = []
        word_family = {}
        for root_key, root_data in self.roots.items():
            if root_data["origin_word"].lower() == word:
                related_roots.append({
                    "root": root_key,
                    "meaning": root_data["meaning"],
                    "origin_word": word,
                    "rule": root_data["rule"],
                    "rule_name": root_data.get("rule_name", ""),
                    "explanation": root_data["explanation"]
                })
                word_family[root_key] = {
                    "meaning": root_data["meaning"],
                    "derived_words": root_data.get("derived_words", [])
                }

        return {
            "word": word,
            "found": True,
            "is_simple_word": True,
            "components": [{
                "type": "simple_word",
                "text": word,
                "meaning": simple_data["meaning"],
                "meaning_zh": simple_data.get("meaning_zh", "")
            }],
            "origin_trace": related_roots,
            "word_family": word_family,
            "message": f"'{word}' is a simple root word. It evolved into the following roots through sound changes."
        }

    # ------------------------------------------------------------------ #
    #  Strategy: full morphological decomposition                         #
    # ------------------------------------------------------------------ #

    def _decompose_by_morphology(self, word: str) -> Optional[Dict]:
        """Try systematic prefix/root/suffix decomposition with scoring."""
        best_result = None
        best_score = 0

        prefix_options = [("", word)]
        for prefix in self._sorted_prefixes:
            if word.startswith(prefix) and len(word) > len(prefix) + 1:
                prefix_options.append((prefix, word[len(prefix):]))

        for prefix, after_prefix in prefix_options:
            suffix_options = [("", after_prefix)]
            for suffix in self._sorted_suffixes:
                if after_prefix.endswith(suffix) and len(after_prefix) > len(suffix) + 1:
                    suffix_options.append((suffix, after_prefix[:-len(suffix)]))

            for suffix, core in suffix_options:
                root_matches = self._find_roots_in_string(core)
                if root_matches:
                    score = sum(len(r[0]) for r in root_matches)
                    # Prefer decompositions where roots are in the roots DB
                    if prefix in self._ambiguous_prefixes and prefix in self.roots:
                        # If prefix is also a root, try it as root instead
                        alt_matches = [(prefix, "")] + self._find_roots_in_string(
                            after_prefix[:-len(suffix)] if suffix else after_prefix)
                        alt_score = sum(len(r[0]) for r in alt_matches)
                        if alt_score > score:
                            score = alt_score
                            root_matches = alt_matches
                            prefix = ""

                    if score > best_score:
                        best_score = score
                        best_result = self._build_result(word, prefix, root_matches, suffix)

        return best_result

    # ------------------------------------------------------------------ #
    #  Strategy: substring fallback                                       #
    # ------------------------------------------------------------------ #

    def _decompose_by_substring(self, word: str) -> Optional[Dict]:
        """Fallback: find any root that appears as a substring."""
        found_roots = []

        for root_key in self._sorted_roots:
            if root_key in word and len(root_key) >= 3:
                found_roots.append(root_key)

        if not found_roots:
            return None

        components = []
        origin_trace = []
        word_family = {}

        for root_key in found_roots:
            comp, trace, family = self._make_root_components(root_key)
            components.append(comp)
            origin_trace.append(trace)
            word_family.update(family)

        return {
            "word": word,
            "found": True,
            "components": components,
            "origin_trace": origin_trace,
            "word_family": word_family
        }

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #

    def _contains_root(self, text: str) -> bool:
        """Check if text contains any known root."""
        for root_key in self.roots:
            if root_key in text:
                return True
        return False

    def _find_roots_in_string(self, text: str, preferred_roots: List[str] = None) -> List[Tuple[str, str]]:
        """Find root(s) within a string. Returns list of (root_key, leftover)."""
        results = []

        if preferred_roots:
            for root_key in preferred_roots:
                if root_key in text or text.startswith(root_key[:len(text)]):
                    results.append((root_key, text.replace(root_key, "", 1)))
                    return results

        if text in self.roots:
            return [(text, "")]

        for root_key in self._sorted_roots:
            if text.startswith(root_key):
                leftover = text[len(root_key):]
                results.append((root_key, leftover))
                if leftover and len(leftover) >= 3:
                    sub_roots = self._find_roots_in_string(leftover)
                    results.extend(sub_roots)
                return results
            elif root_key in text and len(root_key) >= 3:
                results.append((root_key, text.replace(root_key, "", 1)))
                return results

        return results

    def _make_prefix_component(self, prefix: str) -> Dict:
        """Build a prefix component dict."""
        data = self.prefixes[prefix]
        if isinstance(data, dict):
            return {"type": "prefix", "text": prefix, "meaning": data["meaning"],
                    "meaning_zh": data.get("meaning_zh", "")}
        return {"type": "prefix", "text": prefix, "meaning": data, "meaning_zh": ""}

    def _make_suffix_component(self, suffix: str) -> Dict:
        """Build a suffix component dict."""
        data = self.suffixes[suffix]
        if isinstance(data, dict):
            return {"type": "suffix", "text": suffix, "meaning": data["meaning"],
                    "meaning_zh": data.get("meaning_zh", "")}
        return {"type": "suffix", "text": suffix, "meaning": data, "meaning_zh": ""}

    def _make_root_components(self, root_key: str) -> Tuple[Dict, Dict, Dict]:
        """Build root component, origin trace, and word family dicts."""
        root_data = self.roots[root_key]
        comp = {
            "type": "root",
            "text": root_key,
            "meaning": root_data["meaning"],
            "meaning_zh": root_data.get("meaning_zh", ""),
            "origin_word": root_data["origin_word"],
            "rule": root_data["rule"],
            "rule_name": root_data.get("rule_name", ""),
            "explanation": root_data["explanation"]
        }
        trace = {
            "root": root_key,
            "meaning": root_data["meaning"],
            "origin_word": root_data["origin_word"],
            "rule": root_data["rule"],
            "rule_name": root_data.get("rule_name", ""),
            "explanation": root_data["explanation"]
        }
        family = {
            root_key: {
                "meaning": root_data["meaning"],
                "derived_words": root_data.get("derived_words", [])
            }
        }
        return comp, trace, family

    def _build_result(self, word: str, prefix: str, root_matches: List[Tuple[str, str]], suffix: str) -> Dict:
        """Build a complete result dict from decomposition parts."""
        components = []
        origin_trace = []
        word_family = {}

        if prefix:
            components.append(self._make_prefix_component(prefix))

        for root_key, leftover in root_matches:
            if root_key in self.roots:
                comp, trace, family = self._make_root_components(root_key)
                components.append(comp)
                origin_trace.append(trace)
                word_family.update(family)

        if suffix:
            components.append(self._make_suffix_component(suffix))

        return {
            "word": word,
            "found": True,
            "components": components,
            "origin_trace": origin_trace,
            "word_family": word_family
        }
