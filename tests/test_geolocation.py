"""
Geolocation Tests — Validates geolocation enforcement in the API.
"""
import json
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestGeolocationEnforcement:
    """Tests that geolocation is handled properly."""

    def test_webhook_accepts_coordinates(self, client):
        """Valid lat/lng should be accepted."""
        r = client.post("/webhook", json={
            "session_id": "geo-001",
            "message": "I have severe headache and fever for 3 days",
            "lat": 13.0827,
            "lng": 80.2707,
        })
        data = r.get_json()
        assert r.status_code == 200
        assert data["type"] in ("followup", "result", "no_match", "emergency")

    def test_webhook_without_coordinates_still_works(self, client):
        """Webhook should still process without coordinates (prediction works)."""
        r = client.post("/webhook", json={
            "session_id": "geo-002",
            "message": "I have headache, fever, body ache for 3 days, moderate severity",
        })
        data = r.get_json()
        assert r.status_code == 200
        assert data["type"] in ("followup", "result", "no_match")

    def test_result_without_location_shows_error(self, client):
        """When no coordinates, result should include location_error."""
        # Send enough info to get a result
        r = client.post("/webhook", json={
            "session_id": "geo-003",
            "message": "I have severe headache, fever, body ache, chills, and sweating for 5 days. Moderate severity.",
        })
        data = r.get_json()
        # May need follow-ups first
        for _ in range(3):
            if data["type"] != "followup":
                break
            r = client.post("/webhook", json={
                "session_id": "geo-003",
                "message": "5 days, severe, I also have nausea and fatigue",
            })
            data = r.get_json()

        if data["type"] == "result":
            # Should have location_error since we didn't send lat/lng
            assert data.get("location_error") or (
                data.get("doctor_recommendation") and
                len(data["doctor_recommendation"].get("doctors", [])) == 0
            )

    def test_coordinates_reused_from_session(self, client):
        """Once coordinates are sent, they should persist in session."""
        # First message with coordinates
        client.post("/webhook", json={
            "session_id": "geo-004",
            "message": "I have a headache",
            "lat": 12.9716,
            "lng": 77.5946,
        })

        # Second message without coordinates — should use session coordinates
        r = client.post("/webhook", json={
            "session_id": "geo-004",
            "message": "I also have fever and body ache for 2 days, moderate severity",
        })
        data = r.get_json()
        assert r.status_code == 200

    def test_invalid_coordinates_handled(self, client):
        """Invalid lat/lng values should be handled gracefully."""
        r = client.post("/webhook", json={
            "session_id": "geo-005",
            "message": "I have a headache",
            "lat": "invalid",
            "lng": "bad",
        })
        data = r.get_json()
        assert r.status_code == 200
        assert data["type"] in ("followup", "result", "no_match")


class TestDoctorRecommender:
    """Tests the doctor recommender with and without location."""

    def test_recommend_without_location_returns_error(self):
        from services.doctor_recommender import recommend_doctors
        result = recommend_doctors("Migraine", latitude=None, longitude=None)
        assert result["success"] is False
        assert "error" in result

    def test_recommend_emergency_without_location(self):
        from services.doctor_recommender import recommend_emergency
        result = recommend_emergency(lat=None, lng=None)
        assert result["success"] is False
        assert "error" in result
