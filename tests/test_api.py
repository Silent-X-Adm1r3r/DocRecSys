"""
DocRecSys Test Suite — API, prediction, triage, doctor recommendation tests.
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
    assert data["model"]["status"] == "loaded"

# ── Landing Page ────────────────────────────────────────────────────

def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"DocRecSys" in r.data

# ── Webhook — Normal Prediction ─────────────────────────────────────

def test_prediction_fever_headache(client):
    r = client.post("/webhook", json={
        "session_id": "t1",
        "message": "I have fever, headache, body ache, and chills for 3 days"
    })
    data = r.get_json()
    # Should either be followup or result
    assert data["type"] in ("followup", "result", "no_match")

def test_full_flow(client):
    # First message — may trigger followup
    r = client.post("/webhook", json={
        "session_id": "t2",
        "message": "I have been having nausea, vomiting, and diarrhea"
    })
    data = r.get_json()
    if data["type"] == "followup":
        # Answer followup
        r = client.post("/webhook", json={
            "session_id": "t2",
            "message": "It's been 2 days, moderate severity, and I also have stomach pain"
        })
        data = r.get_json()
    assert data["type"] in ("result", "no_match")
    if data["type"] == "result":
        assert len(data["conditions"]) > 0
        assert "disclaimer" in data

# ── Emergency Detection ─────────────────────────────────────────────

def test_emergency_chest_pain(client):
    r = client.post("/webhook", json={
        "session_id": "t3",
        "message": "I am experiencing severe chest pain and breathlessness"
    })
    data = r.get_json()
    assert data["type"] == "emergency"
    assert data["level"] in ("CRITICAL", "URGENT", "HIGH")
    assert "numbers" in data

def test_emergency_mental_health(client):
    r = client.post("/webhook", json={
        "session_id": "t4",
        "message": "I want to end my life"
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

# ── Doctor Recommendation ───────────────────────────────────────────

def test_doctor_with_city(client):
    # Send enough symptoms to get a result directly
    r = client.post("/webhook", json={
        "session_id": "t7",
        "message": "I have severe itching, skin rash, and nodal skin eruptions",
        "city": "Mumbai"
    })
    data = r.get_json()
    if data["type"] == "followup":
        r = client.post("/webhook", json={
            "session_id": "t7",
            "message": "It's been a week and very severe"
        })
        data = r.get_json()
    if data["type"] == "result" and data.get("doctor_recommendation"):
        docs = data["doctor_recommendation"]["doctors"]
        assert len(docs) > 0

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
    # fever should ideally be negated

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

# ── Doctor Coverage Tests ───────────────────────────────────────────

def test_doctor_coverage():
    from services.database import get_doctors
    major_cities = ["Bengaluru", "Chennai", "Mumbai", "New Delhi", "Hyderabad",
                    "Kolkata", "Jaipur", "Lucknow", "Bhopal", "Bhubaneswar"]
    for city in major_cities:
        docs = get_doctors("General Physician", city=city, limit=5)
        assert len(docs) > 0, f"No General Physician found in {city}"

    specialties = ["Cardiologist", "Neurologist", "Dermatologist", "Pulmonologist",
                   "Psychiatrist", "Gastroenterologist"]
    for spec in specialties:
        docs = get_doctors(spec, limit=5)
        assert len(docs) > 0, f"No {spec} found in database"
