"""
English Root Explorer — Graph Search Module

Per spec Section 14, treats decomposition as a graph search problem.
Explores multiple possible paths and selects the strongest supported explanation.

Search strategies:
  1. Database-driven: use MorphoLex decompositions + etymology relationships
  2. Affix stripping: recursive prefix/suffix removal
  3. Sound rules BFS: letter-swap search (from original engine)
  4. Root+Root compounds: detect compound words

All strategies operate under a 5-second deadline (spec Section 18).
"""

import time
import json
from typing import List, Dict, Set, Optional, Tuple
from collections import deque


class SearchEngine:
    """Graph search engine for word decomposition."""

    def __init__(self, db, sound_rules_swaps: Dict = None):
        """
        Args:
            db: Database instance
            sound_rules_swaps: char -> set of swappable chars (from sound_rules.py)
        """
        self.db = db
        self._swaps = sound_rules_swaps or {}

        # Cache frequently-used data
        self._basic_words: Set[str] = None
        self._prefixes: List[Dict] = None
        self._suffixes: List[Dict] = None

    @property
    def basic_words(self) -> Set[str]:
        if self._basic_words is None:
            self._basic_words = self.db.get_all_basic_words()
        return self._basic_words

    @property
    def prefixes(self) -> List[Dict]:
        if self._prefixes is None:
            self._prefixes = self.db.get_all_prefixes()
        return self._prefixes

    @property
    def suffixes(self) -> List[Dict]:
        if self._suffixes is None:
            self._suffixes = self.db.get_all_suffixes()
        return self._suffixes

    def search(self, word: str, deadline: float) -> List[Dict]:
        """Run all search strategies and collect candidates.

        Args:
            word: the input word (lowercase, stripped)
            deadline: time.time() deadline (5 seconds from start)

        Returns:
            List of candidate dicts, each with:
                - word, prefixes, roots, suffixes, core, basic_word
                - path, evidence, via, score (scored later)
        """
        candidates = []

        # Strategy 1: Check if word IS a basic word (instant)
        if word in self.basic_words:
            candidates.append(self._make_candidate(
                word=word, core=word, basic_word=word,
                via="direct_basic", evidence={"coverage": 1.0}
            ))

        if time.time() >= deadline:
            return candidates

        # Strategy 2: Database-driven morphological decomposition
        candidates.extend(self._search_morpholex(word, deadline))

        if time.time() >= deadline:
            return candidates

        # Strategy 3: Affix stripping + root lookup
        candidates.extend(self._search_affix_strip(word, deadline))

        if time.time() >= deadline:
            return candidates

        # Strategy 4: Etymology-based search
        candidates.extend(self._search_etymology(word, deadline))

        if time.time() >= deadline:
            return candidates

        # Strategy 5: Sound rules BFS (from original engine)
        candidates.extend(self._search_sound_rules(word, deadline))

        return candidates

    # ================================================================== #
    #  STRATEGY 1: MorphoLex database lookup                              #
    # ================================================================== #

    def _search_morpholex(self, word: str, deadline: float) -> List[Dict]:
        """Use MorphoLex decompositions from the database."""
        candidates = []

        decomps = self.db.get_morphological_decomposition(word)
        for decomp in decomps:
            if time.time() >= deadline:
                break

            morphemes = decomp["morphemes"]
            structure = decomp["structure"]

            # Classify each morpheme
            pfxs, roots, sfxs = self._classify_morphemes(morphemes)

            # Try to find a basic word among the roots
            basic = ""
            for r in roots:
                if r in self.basic_words:
                    basic = r
                    break

            candidates.append(self._make_candidate(
                word=word, prefixes=pfxs, roots=roots, suffixes=sfxs,
                core=roots[0] if roots else word,
                basic_word=basic, via="morpholex",
                evidence={
                    "morpholex_match": True,
                    "coverage": sum(len(m) for m in morphemes) / max(len(word), 1),
                    "structure": structure
                }
            ))

        return candidates

    def _classify_morphemes(self, morphemes: List[str]) -> Tuple[List[str], List[str], List[str]]:
        """Classify morphemes into prefixes, roots, suffixes."""
        pfxs = []
        roots = []
        sfxs = []

        for m in morphemes:
            if self.db.is_known_affix(m, "prefix"):
                pfxs.append(m)
            elif self.db.is_known_affix(m, "suffix"):
                sfxs.append(m)
            else:
                roots.append(m)

        return pfxs, roots, sfxs

    # ================================================================== #
    #  STRATEGY 2: Affix stripping                                        #
    # ================================================================== #

    def _search_affix_strip(self, word: str, deadline: float) -> List[Dict]:
        """Strip known prefixes/suffixes to find root candidates."""
        candidates = []
        seen_cores = set()

        for stripped in self._generate_stripped_forms(word):
            if time.time() >= deadline:
                break

            pfxs, core, sfxs = stripped

            if core in seen_cores:
                continue
            seen_cores.add(core)

            # Skip if core is too short
            if len(core) < 2:
                continue

            evidence = {"coverage": (len(word) - len(core) + len(core)) / max(len(word), 1)}

            # Check if core is a basic word
            basic = core if core in self.basic_words else ""

            # Check if core is a known root
            root_info = self.db.get_roots_for_form(core)
            if root_info:
                evidence["known_root"] = True

            # Check etymological relationships
            ancestors = self.db.get_etymological_ancestors(core)
            if ancestors:
                evidence["etymological_relationship"] = True

            if basic or root_info or ancestors:
                candidates.append(self._make_candidate(
                    word=word, prefixes=pfxs, roots=[core], suffixes=sfxs,
                    core=core, basic_word=basic, via="affix_strip",
                    evidence=evidence
                ))

            # Also try: core is two roots (compound words, spec Section 13)
            if len(core) >= 4:
                compound_hits = self._check_compound(core, pfxs, sfxs, deadline)
                candidates.extend(compound_hits)

        return candidates

    def _generate_stripped_forms(self, word: str) -> List[Tuple[List[str], str, List[str]]]:
        """Generate all possible prefix+core+suffix combinations."""
        results = [([], word, [])]

        for pfx_info in self.prefixes:
            pfx = pfx_info["text"]
            if word.startswith(pfx) and len(word) > len(pfx) + 1:
                remainder = word[len(pfx):]
                results.append(([pfx], remainder, []))
                for sfx_info in self.suffixes:
                    sfx = sfx_info["text"]
                    if remainder.endswith(sfx) and len(remainder) > len(sfx) + 1:
                        results.append(([pfx], remainder[:-len(sfx)], [sfx]))

        for sfx_info in self.suffixes:
            sfx = sfx_info["text"]
            if word.endswith(sfx) and len(word) > len(sfx) + 1:
                results.append(([], word[:-len(sfx)], [sfx]))

        return results

    def _check_compound(self, core: str, pfxs: List[str], sfxs: List[str],
                         deadline: float) -> List[Dict]:
        """Check if core is a compound of two roots (spec Section 13)."""
        candidates = []

        for split_pos in range(2, len(core) - 1):
            if time.time() >= deadline:
                break

            part1 = core[:split_pos]
            part2 = core[split_pos:]

            # Both parts must have evidence (not just string splitting)
            p1_is_root = self.db.is_known_root(part1) or part1 in self.basic_words
            p2_is_root = self.db.is_known_root(part2) or part2 in self.basic_words

            if p1_is_root and p2_is_root:
                candidates.append(self._make_candidate(
                    word=core, prefixes=pfxs, roots=[part1, part2], suffixes=sfxs,
                    core=core, basic_word=part1 if part1 in self.basic_words else part2,
                    via="compound",
                    evidence={
                        "compound": True,
                        "coverage": 1.0,
                        "known_root": True
                    }
                ))

        return candidates

    # ================================================================== #
    #  STRATEGY 3: Etymology search                                       #
    # ================================================================== #

    def _search_etymology(self, word: str, deadline: float) -> List[Dict]:
        """Search for etymological ancestors."""
        candidates = []

        ancestors = self.db.get_etymological_ancestors(word)
        for anc in ancestors:
            if time.time() >= deadline:
                break

            candidates.append(self._make_candidate(
                word=word, roots=[anc["term"]], core=anc["term"],
                basic_word="",
                via="etymology",
                evidence={
                    "etymological_relationship": True,
                    "ancestor_language": anc["language"],
                    "relationship_type": anc["relationship"],
                    "coverage": 0.8
                }
            ))

        return candidates

    # ================================================================== #
    #  STRATEGY 4: Sound rules BFS                                        #
    # ================================================================== #

    def _search_sound_rules(self, word: str, deadline: float) -> List[Dict]:
        """BFS letter-swap search using Indo-European sound change rules."""
        if not self._swaps:
            return []

        candidates = []
        queue = deque([(word, [word], 0)])
        visited = {word}
        max_depth = 3

        while queue and time.time() < deadline:
            current, path, depth = queue.popleft()
            if depth > max_depth:
                continue

            for neighbor in self._sound_neighbors(current):
                if neighbor in visited:
                    continue
                visited.add(neighbor)

                new_path = path + [neighbor]
                new_depth = depth + 1

                # Hit a basic word?
                if neighbor in self.basic_words:
                    candidates.append(self._make_candidate(
                        word=word, core=word,
                        basic_word=neighbor,
                        via="sound_rule",
                        evidence={
                            "sound_path": new_path,
                            "bfs_depth": new_depth,
                            "coverage": 0.7
                        },
                        path=new_path
                    ))

                # Hit a known root?
                if self.db.is_known_root(neighbor):
                    candidates.append(self._make_candidate(
                        word=word, core=word,
                        basic_word=neighbor,
                        via="sound_rule_to_root",
                        evidence={
                            "sound_path": new_path,
                            "bfs_depth": new_depth,
                            "known_root": True,
                            "coverage": 0.6
                        },
                        path=new_path
                    ))

                if new_depth < max_depth:
                    queue.append((neighbor, new_path, new_depth))

        return candidates

    def _sound_neighbors(self, word: str) -> List[str]:
        """Generate single-letter-swap neighbors using sound rules."""
        results = []
        for i, ch in enumerate(word):
            for new_ch in self._swaps.get(ch, set()):
                if new_ch == ch:
                    continue
                new_word = word[:i] + new_ch + word[i+1:]
                results.append(new_word)
        return results

    # ================================================================== #
    #  HELPERS                                                            #
    # ================================================================== #

    def _make_candidate(self, word: str, core: str = "",
                         prefixes: List[str] = None, roots: List[str] = None,
                         suffixes: List[str] = None, basic_word: str = "",
                         via: str = "", evidence: Dict = None,
                         path: List[str] = None) -> Dict:
        """Create a standardized candidate dict."""
        return {
            "word": word,
            "prefixes": prefixes or [],
            "roots": roots or [],
            "suffixes": suffixes or [],
            "core": core,
            "basic_word": basic_word,
            "via": via,
            "evidence": evidence or {},
            "path": path or [],
            "score": 0.0,
            "confidence": "TOO_HARD"
        }

    # ================================================================== #
    #  ROOT-LEVEL FRIEND WORD SEARCH                                      #
    # ================================================================== #

    def find_root_friend_words(self, root: str, deadline: float,
                                max_depth: int = 3) -> List[Dict]:
        """BFS from a single root/component to find real English friend words.

        This is the key feature: after decomposing 'uniform' into 'uni'+'form',
        we BFS each root separately:
          - 'uni' → BFS → finds 'one' (u→o, n→n, i→e)
          - 'form' → BFS → finds 'from' (metathesis-like)

        Only returns hits that are real English words (basic words or words
        in the database with frequency data).

        Args:
            root: the root string to search from (e.g. "uni", "form")
            deadline: time.time() deadline
            max_depth: max BFS depth (default 3)

        Returns:
            List of friend word dicts with:
                - friend: the friend word found
                - path: list of BFS steps from root to friend
                - path_display: "uni → une → one"
                - depth: BFS depth
                - rules_used: description of sound changes
        """
        if not self._swaps:
            return []

        from sound_rules import are_interchangeable, RULES

        results = []
        seen_friends = set()
        queue = deque([(root, [root], [], 0)])
        visited = {root}

        while queue and time.time() < deadline:
            current, path, transforms, depth = queue.popleft()
            if depth > max_depth:
                continue

            for i, ch in enumerate(current):
                for new_ch in self._swaps.get(ch, set()):
                    if new_ch == ch:
                        continue

                    neighbor = current[:i] + new_ch + current[i+1:]
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)

                    new_path = path + [neighbor]
                    new_depth = depth + 1

                    # Record the sound change
                    rules = are_interchangeable(ch, new_ch)
                    rule_names = [RULES[r]["name"] for r in rules] if rules else []
                    swap_info = {
                        "from_char": ch, "to_char": new_ch,
                        "position": i, "rules": rules,
                        "rule_names": rule_names
                    }
                    new_transforms = transforms + [swap_info]

                    # Is this neighbor a REAL English word?
                    is_real_word = (
                        neighbor in self.basic_words or
                        self._is_real_english_word(neighbor)
                    )

                    if is_real_word and neighbor not in seen_friends and neighbor != root:
                        seen_friends.add(neighbor)

                        # Build rules_used description
                        rules_desc = " → ".join(
                            f"{t['from_char']}↔{t['to_char']} ({', '.join(t['rule_names'])})"
                            for t in new_transforms if t.get("rule_names")
                        )

                        results.append({
                            "friend": neighbor,
                            "from_root": root,
                            "path": new_path,
                            "path_display": " → ".join(new_path),
                            "depth": new_depth,
                            "rules_used": rules_desc,
                            "transforms": new_transforms,
                            "score": max(0, 90 - new_depth * 20)
                        })

                    if new_depth < max_depth:
                        queue.append((neighbor, new_path, new_transforms, new_depth))

        # Sort by score (shorter paths first)
        results.sort(key=lambda x: (-x["score"], x["depth"]))
        return results

    def _is_real_english_word(self, word: str) -> bool:
        """Check if a word is a real English word (has frequency or is in WordNet)."""
        w = self.db.get_word(word)
        if w and w.get("frequency", 0) > 0:
            return True
        return False

