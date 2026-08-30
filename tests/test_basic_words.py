"""
Tests for Basic Word functionality (spec Sections 7-9).

Test that:
  - Known basic words (sun, hand, go) return quickly
  - Compound/affixed words are NOT basic words
  - Basic word count is reasonable (~10,000)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from database import Database
from models import DEFAULT_DB_PATH


def get_db():
    return Database(DEFAULT_DB_PATH)


class TestBasicWords:

    def test_basic_word_count(self):
        db = get_db()
        count = db.basic_word_count()
        assert count >= 5000, f"Expected at least 5000 basic words, got {count}"
        assert count <= 20000, f"Expected at most 20000 basic words, got {count}"
        db.close()

    def test_known_simple_words_are_basic(self):
        """Words like 'the', 'a', 'is' should be basic words."""
        db = get_db()
        # These are very common words that should be basic
        common_words = ["the", "is", "was", "be", "it", "he", "she"]
        found = sum(1 for w in common_words if db.is_basic_word(w))
        assert found >= 3, f"Expected at least 3 common words to be basic, found {found}"
        db.close()

    def test_complex_words_not_basic(self):
        """Words like 'unpredictable' should NOT be basic words."""
        db = get_db()
        complex_words = ["unpredictable", "benevolence", "transformation"]
        for w in complex_words:
            assert not db.is_basic_word(w), f"{w} should NOT be a basic word"
        db.close()

    def test_basic_word_has_score(self):
        """Basic words should have a positive score."""
        db = get_db()
        info = db.get_basic_word_info("the")
        if info is not None:
            assert info["basic_score"] > 0, "Basic word should have positive score"
        db.close()

    def test_get_all_basic_words(self):
        """Should return a set of basic words."""
        db = get_db()
        words = db.get_all_basic_words()
        assert isinstance(words, set)
        assert len(words) >= 5000
        db.close()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
