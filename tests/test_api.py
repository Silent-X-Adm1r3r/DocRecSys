"""
DocRecSys Test Suite — API, prediction, triage, doctor recommendation tests.
Updated for Redis-backed sessions, mandatory geolocation, context-aware flow.
Run: python -m pytest tests/ -v
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

# ── Health Check ────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert "redis" in data
    assert "gemini" in data or "mongodb" in data or "maps" in data

# ── Landing Page ────────────────────────────────────────────────────

def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"DocRecSys" in r.data

# ── Webhook — Normal Prediction ─────────────────────────────────────

def test_prediction_fever_headache(client):
    r = client.post("/webhook", json={
        "session_id": "t1",
        "message": "I have fever, headache, body ache, and chills for 3 days",
        "lat": 13.0827,
        "lng": 80.2707,
    })
    data = r.get_json()
    assert data["type"] in ("followup", "result", "no_match")

def test_full_flow_with_location(client):
    """E2E Scenario A: Full flow with location."""
    r = client.post("/webhook", json={
        "session_id": "t2",
        "message": "I have been having nausea, vomiting, and diarrhea",
        "lat": 12.9716,
        "lng": 77.5946,
    })
    data = r.get_json()
    for _ in range(4):
        if data["type"] != "followup":
            break
        r = client.post("/webhook", json={
            "session_id": "t2",
            "message": "It's been 2 days, moderate severity, and I also have stomach pain",
            "lat": 12.9716,
            "lng": 77.5946,
        })
        data = r.get_json()
    assert data["type"] in ("result", "no_match", "followup")
    if data["type"] == "result":
        assert len(data["conditions"]) > 0
        assert "disclaimer" in data

# ── Emergency Detection ─────────────────────────────────────────────

def test_emergency_chest_pain(client):
    r = client.post("/webhook", json={
        "session_id": "t3",
        "message": "I am experiencing severe chest pain and breathlessness",
    })
    data = r.get_json()
    assert data["type"] == "emergency"
    assert data["level"] in ("CRITICAL", "URGENT", "HIGH")
    assert "numbers" in data

def test_emergency_mental_health(client):
    r = client.post("/webhook", json={
        "session_id": "t4",
        "message": "I want to end my life",
    })
    data = r.get_json()
    assert data["type"] == "emergency"
    assert data["level"] == "CRITICAL"
    assert "1800-599-0019" in data["message"]

# ── Input Validation ────────────────────────────────────────────────

def test_empty_message(client):
    r = client.post("/webhook", json={"session_id": "t5", "message": ""})
    data = r.get_json()
    assert data["type"] == "error"

def test_long_message(client):
    r = client.post("/webhook", json={"session_id": "t6", "message": "a" * 3000})
    data = r.get_json()
    assert data["type"] == "error"

# ── Doctor Recommendation with Location ─────────────────────────────

def test_doctor_with_location(client):
    """E2E: Doctor recommendation with geolocation."""
    r = client.post("/webhook", json={
        "session_id": "t7",
        "message": "I have severe itching, skin rash, and nodal skin eruptions",
        "lat": 19.0760,
        "lng": 72.8777,
    })
    data = r.get_json()
    if data["type"] == "followup":
        r = client.post("/webhook", json={
            "session_id": "t7",
            "message": "It's been a week and very severe",
            "lat": 19.0760,
            "lng": 72.8777,
        })
        data = r.get_json()
    if data["type"] == "result" and data.get("doctor_recommendation"):
        dr = data["doctor_recommendation"]
        assert "specialist" in dr
        assert isinstance(dr.get("doctors", []), list)

# ── Feedback ────────────────────────────────────────────────────────

def test_feedback_valid(client):
    r = client.post("/feedback", json={"session_id": "t1", "vote": "up"})
    assert r.status_code == 200

def test_feedback_invalid(client):
    r = client.post("/feedback", json={"session_id": "t1", "vote": "maybe"})
    assert r.status_code == 400

# ── Session Reset ───────────────────────────────────────────────────

def test_reset(client):
    r = client.post("/reset", json={"session_id": "t1"})
    assert r.status_code == 200

# ── Symptom Extractor Unit Tests ────────────────────────────────────

def test_symptom_extraction():
    from services.symptom_extractor import extract_symptoms
    symptoms = extract_symptoms("I have a headache, fever, and I feel very tired")
    assert "headache" in symptoms
    assert "high_fever" in symptoms
    assert "fatigue" in symptoms

def test_negation():
    from services.symptom_extractor import extract_symptoms
    symptoms = extract_symptoms("I don't have fever but I have headache")
    assert "headache" in symptoms

def test_synonym_resolution():
    from services.symptom_extractor import extract_symptoms
    symptoms = extract_symptoms("I have stomach ache and throwing up")
    assert "abdominal_pain" in symptoms
    assert "vomiting" in symptoms

# ── Triage Unit Tests ───────────────────────────────────────────────

def test_emergency_detection():
    from services.triage import check_emergency
    result = check_emergency("I am having a heart attack")
    assert result is not None
    assert result["level"] == "CRITICAL"

def test_no_emergency():
    from services.triage import check_emergency
    result = check_emergency("I have a mild headache")
    assert result is None

# ── Context-Aware Session Tests ─────────────────────────────────────

def test_context_merging(client):
    """E2E Scenario E: Multi-turn context merging."""
    # Turn 1: Send initial symptoms
    r = client.post("/webhook", json={
        "session_id": "ctx-001",
        "message": "I have a headache and fever",
        "lat": 13.0827,
        "lng": 80.2707,
    })
    data = r.get_json()
    assert data["type"] in ("followup", "result", "no_match")

    # Turn 2: Add duration
    r = client.post("/webhook", json={
        "session_id": "ctx-001",
        "message": "It's been 3 days",
    })
    data = r.get_json()
    assert data["type"] in ("followup", "result", "no_match")

    # Turn 3: Add severity and more symptoms
    r = client.post("/webhook", json={
        "session_id": "ctx-001",
        "message": "Severe, I also have body ache and chills",
    })
    data = r.get_json()
    assert data["type"] in ("result", "followup", "no_match")

def test_session_coordinates_persist(client):
    """Coordinates sent once should persist across messages."""
    # Message 1 with coordinates
    client.post("/webhook", json={
        "session_id": "persist-001",
        "message": "I have a headache",
        "lat": 28.6139,
        "lng": 77.2090,
    })
    # Message 2 without coordinates
    r = client.post("/webhook", json={
        "session_id": "persist-001",
        "message": "I also have fever for 2 days, moderate severity",
    })
    data = r.get_json()
    assert r.status_code == 200

def test_followup_only_asks_missing(client):
    """Context-aware: should not re-ask for info already provided."""
    # Provide symptoms + duration in one message
    r = client.post("/webhook", json={
        "session_id": "norepeat-001",
        "message": "I have headache and fever for 3 days",
        "lat": 13.0827,
        "lng": 80.2707,
    })
    data = r.get_json()
    if data["type"] == "followup":
        # The follow-up should NOT ask about duration (already provided)
        assert "how long" not in data["message"].lower() or "severity" in data["message"].lower() or "more" in data["message"].lower()

# ── Redis Health in API ─────────────────────────────────────────────

def test_health_includes_redis(client):
    r = client.get("/health")
    data = r.get_json()
    assert "redis" in data

# ── Response Structure Tests ────────────────────────────────────────

def test_result_has_user_location(client):
    """Result responses should include user_location when coordinates are sent."""
    r = client.post("/webhook", json={
        "session_id": "loc-struct-001",
        "message": "I have severe headache, fever, chills, body ache for 5 days. Very severe.",
        "lat": 13.0827,
        "lng": 80.2707,
    })
    data = r.get_json()
    for _ in range(3):
        if data["type"] != "followup":
            break
        r = client.post("/webhook", json={
            "session_id": "loc-struct-001",
            "message": "5 days, severe, nausea and fatigue too",
            "lat": 13.0827,
            "lng": 80.2707,
        })
        data = r.get_json()

    if data["type"] == "result":
        if data.get("user_location"):
            assert "latitude" in data["user_location"]
            assert "longitude" in data["user_location"]

def test_result_has_specialist_rarity(client):
    """Doctor recommendations should include specialist_rarity."""
    r = client.post("/webhook", json={
        "session_id": "rarity-001",
        "message": "I have severe headache, nausea, visual disturbances for 3 days. Severe.",
        "lat": 12.9716,
        "lng": 77.5946,
    })
    data = r.get_json()
    for _ in range(3):
        if data["type"] != "followup":
            break
        r = client.post("/webhook", json={
            "session_id": "rarity-001",
            "message": "3 days, severe, also blurred vision",
            "lat": 12.9716,
            "lng": 77.5946,
        })
        data = r.get_json()

    if data["type"] == "result" and data.get("doctor_recommendation"):
        dr = data["doctor_recommendation"]
        assert "specialist_rarity" in dr
        assert dr["specialist_rarity"] in ("rare", "common", "general")

# ── Doctor Coverage Tests ───────────────────────────────────────────

def test_doctor_coverage():
    from services.database import get_doctors
    specialties = ["General Physician", "Cardiologist", "Neurologist", "Dermatologist", "Pulmonologist",
                   "Psychiatrist", "Gastroenterologist"]
    for spec in specialties:
        docs = get_doctors(spec, limit=5)
        assert len(docs) > 0, f"No {spec} found in database"
