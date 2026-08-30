"""
Tests for the Decomposer engine.

Test decomposable words with known expected outputs:
  - unpredictable: prefix + root + suffix
  - benevolence: prefix + root + suffix
  - innovation: prefix + root + suffix  
  - philosophy: root + root
  - asdfghjkl: TOO_HARD
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from decomposer import Decomposer


def get_decomposer():
    return Decomposer()


class TestDecomposer:

    def test_found_status(self):
        """Known English words should return FOUND."""
        d = get_decomposer()
        for word in ["happy", "predict", "light", "transport"]:
            result = d.decompose(word)
            assert result["status"] == "FOUND", f"{word} should be FOUND, got {result['status']}"

    def test_too_hard_for_gibberish(self):
        """Gibberish should return TOO_HARD."""
        d = get_decomposer()
        result = d.decompose("asdfghjkl")
        assert result["status"] == "TOO_HARD", f"Expected TOO_HARD for gibberish"
        assert result["confidence"] == "TOO_HARD"

    def test_has_components(self):
        """Found words should have components."""
        d = get_decomposer()
        result = d.decompose("unpredictable")
        assert result["status"] == "FOUND"
        assert len(result["components"]) > 0, "Should have components"

    def test_prefix_detection(self):
        """Words with prefixes should detect them."""
        d = get_decomposer()
        result = d.decompose("unhappy")
        assert result["status"] == "FOUND"
        prefixes = [c for c in result["components"] if c["type"] == "prefix"]
        assert len(prefixes) > 0, "Should detect prefix 'un'"
        assert any(c["text"] == "un" for c in prefixes), "Should detect 'un' prefix"

    def test_suffix_detection(self):
        """Words with suffixes should detect them."""
        d = get_decomposer()
        result = d.decompose("happiness")
        assert result["status"] == "FOUND"
        suffixes = [c for c in result["components"] if c["type"] == "suffix"]
        assert len(suffixes) > 0, "Should detect suffix 'ness'"

    def test_confidence_levels(self):
        """Confidence should be one of the valid levels."""
        d = get_decomposer()
        valid = {"HIGH_CONFIDENCE", "MEDIUM_CONFIDENCE", "LOW_CONFIDENCE", "TOO_HARD"}
        for word in ["happy", "unpredictable", "asdfghjkl"]:
            result = d.decompose(word)
            assert result["confidence"] in valid, f"Invalid confidence: {result['confidence']}"

    def test_search_time_under_5_seconds(self):
        """No query should exceed 5 seconds (spec Section 18)."""
        d = get_decomposer()
        for word in ["unpredictable", "benevolence", "philosophy", "asdfghjkl"]:
            start = time.time()
            d.decompose(word)
            elapsed = time.time() - start
            assert elapsed < 5.0, f"{word} took {elapsed:.2f}s (>5s limit)"

    def test_innovation_has_root_nov(self):
        """'innovation' should detect root 'nov' (new)."""
        d = get_decomposer()
        result = d.decompose("innovation")
        assert result["status"] == "FOUND"
        roots = [c for c in result["components"] if c["type"] == "root"]
        root_texts = [r["text"] for r in roots]
        assert "nov" in root_texts, f"Expected 'nov' root, got {root_texts}"

    def test_response_structure(self):
        """Response should have all required fields."""
        d = get_decomposer()
        result = d.decompose("happy")
        required_fields = ["word", "found", "status", "confidence",
                          "components", "origin_trace", "word_family",
                          "friend_words"]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_word_family_dict(self):
        """Word family should be a dict."""
        d = get_decomposer()
        result = d.decompose("happy")
        assert isinstance(result["word_family"], dict)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
