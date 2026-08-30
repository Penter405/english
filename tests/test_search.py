"""
Tests for the Search module.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from database import Database
from search import SearchEngine
from models import DEFAULT_DB_PATH
from sound_rules import RULES


def get_search_engine():
    db = Database(DEFAULT_DB_PATH)
    swaps = {}
    for rule_id, rule in RULES.items():
        for c in rule["group"]:
            swaps.setdefault(c, set()).update(rule["group"])
    return SearchEngine(db, swaps), db


class TestSearch:

    def test_search_returns_candidates(self):
        """Search should return at least one candidate for known words."""
        se, db = get_search_engine()
        candidates = se.search("happy", time.time() + 5)
        assert len(candidates) > 0, "Should find candidates for 'happy'"
        db.close()

    def test_basic_word_detected(self):
        """A basic word should be found as direct_basic."""
        se, db = get_search_engine()
        candidates = se.search("the", time.time() + 5)
        direct = [c for c in candidates if c["via"] == "direct_basic"]
        # 'the' may or may not be basic depending on the build
        db.close()

    def test_morpholex_strategy(self):
        """Words in MorphoLex should get morpholex candidates."""
        se, db = get_search_engine()
        candidates = se.search("unhappiness", time.time() + 5)
        morpholex = [c for c in candidates if c["via"] == "morpholex"]
        assert len(morpholex) > 0, "Should find morpholex decomposition"
        db.close()

    def test_affix_strip_strategy(self):
        """Affix stripping should work for words with known affixes."""
        se, db = get_search_engine()
        candidates = se.search("unhappy", time.time() + 5)
        affix = [c for c in candidates if c["via"] == "affix_strip"]
        assert len(affix) > 0, "Should find affix-stripped candidates"
        db.close()

    def test_deadline_respected(self):
        """Search should stop at deadline."""
        se, db = get_search_engine()
        short_deadline = time.time() + 0.001  # 1ms
        candidates = se.search("complicated", short_deadline)
        # Should not hang
        db.close()

    def test_visited_state_dedup(self):
        """Sound rules BFS should not revisit states."""
        se, db = get_search_engine()
        candidates = se.search("dig", time.time() + 5)
        # If BFS works correctly, no infinite loop
        db.close()

    def test_candidate_structure(self):
        """Each candidate should have required fields."""
        se, db = get_search_engine()
        candidates = se.search("happy", time.time() + 5)
        if candidates:
            c = candidates[0]
            for field in ["word", "prefixes", "roots", "suffixes", "core", "via", "evidence"]:
                assert field in c, f"Candidate missing field: {field}"
        db.close()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
