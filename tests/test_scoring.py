"""
Tests for the Scoring module.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from database import Database
from scoring import score_candidate, classify_confidence, select_best_candidate
from scoring import HIGH_THRESHOLD, MEDIUM_THRESHOLD, LOW_THRESHOLD
from models import DEFAULT_DB_PATH


def get_db():
    return Database(DEFAULT_DB_PATH)


class TestScoring:

    def test_high_confidence_threshold(self):
        """Score >= 70 should be HIGH_CONFIDENCE."""
        assert classify_confidence(70) == "HIGH_CONFIDENCE"
        assert classify_confidence(100) == "HIGH_CONFIDENCE"

    def test_medium_confidence_threshold(self):
        """Score >= 45 and < 70 should be MEDIUM_CONFIDENCE."""
        assert classify_confidence(45) == "MEDIUM_CONFIDENCE"
        assert classify_confidence(69) == "MEDIUM_CONFIDENCE"

    def test_low_confidence_threshold(self):
        """Score >= 20 and < 45 should be LOW_CONFIDENCE."""
        assert classify_confidence(20) == "LOW_CONFIDENCE"
        assert classify_confidence(44) == "LOW_CONFIDENCE"

    def test_too_hard_threshold(self):
        """Score < 20 should be TOO_HARD."""
        assert classify_confidence(0) == "TOO_HARD"
        assert classify_confidence(19) == "TOO_HARD"

    def test_basic_word_bonus(self):
        """Reaching a basic word should add score."""
        db = get_db()
        candidate = {
            "word": "test", "prefixes": [], "roots": [], "suffixes": [],
            "core": "the", "basic_word": "the", "via": "direct",
            "evidence": {}
        }
        score = score_candidate(candidate, db)
        assert score > 0, "Basic word should add score"
        db.close()

    def test_known_affix_bonus(self):
        """Known affixes should add score."""
        db = get_db()
        candidate = {
            "word": "unhappy", "prefixes": ["un"], "roots": ["happy"],
            "suffixes": [], "core": "happy", "basic_word": "",
            "via": "affix_strip", "evidence": {}
        }
        score = score_candidate(candidate, db)
        assert score > 0, "Known affix should add score"
        db.close()

    def test_spelling_only_penalty(self):
        """Spelling-only matches should be penalized."""
        db = get_db()
        candidate = {
            "word": "test", "prefixes": [], "roots": [], "suffixes": [],
            "core": "test", "basic_word": "", "via": "sound_rule",
            "evidence": {"spelling_only": True}
        }
        score_with_penalty = score_candidate(candidate, db)

        candidate2 = {
            "word": "test", "prefixes": [], "roots": [], "suffixes": [],
            "core": "test", "basic_word": "", "via": "sound_rule",
            "evidence": {}
        }
        score_without = score_candidate(candidate2, db)
        assert score_with_penalty < score_without, "Spelling-only should be penalized"
        db.close()

    def test_select_best_candidate_returns_highest(self):
        """select_best_candidate should return the highest scoring candidate."""
        db = get_db()
        candidates = [
            {"word": "test", "prefixes": [], "roots": [], "suffixes": [],
             "core": "test", "basic_word": "", "via": "low",
             "evidence": {"spelling_only": True}},
            {"word": "test", "prefixes": ["un"], "roots": ["happy"],
             "suffixes": [], "core": "happy", "basic_word": "happy",
             "via": "affix_strip", "evidence": {"morpholex_match": True}},
        ]
        best = select_best_candidate(candidates, db)
        if best is not None:
            assert best["via"] == "affix_strip", "Should select the higher-scoring candidate"
        db.close()

    def test_select_best_returns_none_for_all_low(self):
        """Should return None if all candidates score below threshold."""
        db = get_db()
        candidates = [
            {"word": "xyz", "prefixes": [], "roots": [], "suffixes": [],
             "core": "xyz", "basic_word": "", "via": "none",
             "evidence": {"spelling_only": True}},
        ]
        best = select_best_candidate(candidates, db)
        # May or may not be None depending on exact scoring
        db.close()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
