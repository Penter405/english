"""
Tests for the API endpoints.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from fastapi.testclient import TestClient
from index import app


client = TestClient(app)


class TestAPI:

    def test_post_analyze(self):
        """POST /api/analyze should return results."""
        response = client.post("/api/analyze", json={"word": "happy"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FOUND"
        assert "components" in data
        assert "confidence" in data

    def test_get_analyze_backward_compat(self):
        """GET /api/analyze should still work."""
        response = client.get("/api/analyze?word=happy")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FOUND"

    def test_input_validation_rejects_numbers(self):
        """Should reject words with numbers."""
        response = client.post("/api/analyze", json={"word": "hello123"})
        assert response.status_code == 400

    def test_input_validation_rejects_long(self):
        """Should reject words > 50 chars."""
        response = client.post("/api/analyze", json={"word": "a" * 51})
        assert response.status_code in (400, 422)

    def test_too_hard_for_gibberish(self):
        """Gibberish should return TOO_HARD."""
        response = client.post("/api/analyze", json={"word": "asdfghjkl"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "TOO_HARD"

    def test_health_endpoint(self):
        """GET /api/health should return ok."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_rules_endpoint(self):
        """GET /api/rules should return rules."""
        response = client.get("/api/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert len(data["rules"]) > 0

    def test_system_stats(self):
        """GET /api/system_stats should return stats."""
        response = client.get("/api/system_stats")
        assert response.status_code == 200
        data = response.json()
        assert "engine_version" in data

    def test_search_endpoint(self):
        """GET /api/search should return results."""
        response = client.get("/api/search?root=dict")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_response_has_confidence(self):
        """Response should include confidence level."""
        response = client.post("/api/analyze", json={"word": "innovation"})
        assert response.status_code == 200
        data = response.json()
        valid = {"HIGH_CONFIDENCE", "MEDIUM_CONFIDENCE", "LOW_CONFIDENCE", "TOO_HARD"}
        assert data["confidence"] in valid


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
