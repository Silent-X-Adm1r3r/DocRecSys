"""
Redis Service Tests — Session management, prediction caching, maps caching.
Tests require a running Redis instance. Skipped when Redis is unavailable.
"""
import json
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import redis_service

# Initialize Redis (will set _available=False if not running)
from config import REDIS_URL
redis_service.init_redis(REDIS_URL)

# Skip all tests if Redis is not available
pytestmark = pytest.mark.skipif(
    not redis_service.is_available(),
    reason="Redis server not available"
)


# ── Session Tests ───────────────────────────────────────────────────

class TestSessionManagement:

    def test_new_session_has_required_fields(self):
        session = redis_service._new_session()
        assert "symptoms" in session
        assert "duration" in session
        assert "severity" in session
        assert "latitude" in session
        assert "longitude" in session
        assert "created_at" in session
        assert isinstance(session["symptoms"], list)

    def test_get_session_creates_new(self):
        session = redis_service.get_session("test-new-001", ttl=60)
        assert session["symptoms"] == []
        assert session["duration"] == ""
        assert session["latitude"] is None

    def test_save_and_retrieve_session(self):
        sid = "test-save-001"
        session = redis_service._new_session()
        session["symptoms"] = ["headache", "fever"]
        session["duration"] = "2 days"
        redis_service.save_session(sid, session, ttl=60)

        retrieved = redis_service.get_session(sid, ttl=60)
        assert "headache" in retrieved["symptoms"]
        assert "fever" in retrieved["symptoms"]
        assert retrieved["duration"] == "2 days"

    def test_update_session_merges_symptoms(self):
        sid = "test-merge-001"
        redis_service.save_session(sid, {
            **redis_service._new_session(),
            "symptoms": ["headache"],
        }, ttl=60)

        redis_service.update_session(sid, {"symptoms": ["fever", "cough"]}, ttl=60)
        session = redis_service.get_session(sid, ttl=60)
        assert set(session["symptoms"]) == {"headache", "fever", "cough"}

    def test_update_session_does_not_overwrite_with_empty(self):
        sid = "test-nooverwrite-001"
        redis_service.save_session(sid, {
            **redis_service._new_session(),
            "duration": "3 days",
            "severity": "moderate",
        }, ttl=60)

        redis_service.update_session(sid, {"duration": "", "severity": ""}, ttl=60)
        session = redis_service.get_session(sid, ttl=60)
        assert session["duration"] == "3 days"
        assert session["severity"] == "moderate"

    def test_update_session_stores_location(self):
        sid = "test-location-001"
        redis_service.update_session(sid, {
            "latitude": 13.0827,
            "longitude": 80.2707,
        }, ttl=60)
        session = redis_service.get_session(sid, ttl=60)
        assert session["latitude"] == 13.0827
        assert session["longitude"] == 80.2707

    def test_reset_session(self):
        sid = "test-reset-001"
        redis_service.save_session(sid, {
            **redis_service._new_session(),
            "symptoms": ["headache"],
        }, ttl=60)
        redis_service.reset_session(sid)
        session = redis_service.get_session(sid, ttl=60)
        assert session["symptoms"] == []


# ── Prediction Cache Tests ──────────────────────────────────────────

class TestPredictionCache:

    def test_cache_miss(self):
        result = redis_service.get_prediction_cache(["unknown_symptom_xyz"])
        assert result is None

    def test_cache_hit(self):
        symptoms = ["test_headache", "test_fever"]
        prediction = [{"disease": "TestFlu", "confidence": 0.85}]
        redis_service.set_prediction_cache(symptoms, prediction, ttl=60)

        cached = redis_service.get_prediction_cache(symptoms)
        assert cached is not None
        assert cached[0]["disease"] == "TestFlu"

    def test_cache_normalization(self):
        """Same symptoms in different order should hit the same cache."""
        symptoms_a = ["fever", "headache"]
        symptoms_b = ["headache", "fever"]
        prediction = [{"disease": "CommonCold", "confidence": 0.6}]

        redis_service.set_prediction_cache(symptoms_a, prediction, ttl=60)
        cached = redis_service.get_prediction_cache(symptoms_b)
        assert cached is not None
        assert cached[0]["disease"] == "CommonCold"

    def test_empty_symptoms_no_cache(self):
        result = redis_service.get_prediction_cache([])
        assert result is None


# ── Maps Cache Tests ────────────────────────────────────────────────

class TestMapsCache:

    def test_maps_cache_miss(self):
        result = redis_service.get_maps_cache("TestSpec", 99.999, 99.999)
        assert result is None

    def test_maps_cache_hit(self):
        redis_service.set_maps_cache("TestCardiologist", 13.083, 80.271,
                                      [{"name": "Test Clinic"}], ttl=60)
        cached = redis_service.get_maps_cache("TestCardiologist", 13.083, 80.271)
        assert cached is not None
        assert cached[0]["name"] == "Test Clinic"


# ── Health Check (always runs) ──────────────────────────────────────

@pytest.mark.skipif(False, reason="Always runs")
class TestRedisHealth:

    def test_is_available(self):
        assert isinstance(redis_service.is_available(), bool)

    def test_get_stats(self):
        stats = redis_service.get_stats()
        assert "available" in stats
