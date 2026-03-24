"""
DocRecSys — AI-Powered Symptom Checker & Doctor Recommendation
Flask application entry point.
"""

from flask import Flask, render_template, request, jsonify
import uuid

from services.symptom_extractor import extract_symptoms, extract_duration, extract_severity
from services.predictor import predict_diseases
from services.doctor_recommender import recommend_doctors
from services.triage import (
    check_emergency, EMERGENCY_MESSAGE,
    interpret_confidence, triage_suggestion, needs_followup,
)
from services.response_formatter import format_response

app = Flask(__name__)

# ── In-memory session store ─────────────────────────────────────────
# { session_id: { "symptoms": [...], "severity": str|None,
#                 "duration": str|None, "awaiting": str|None,
#                 "feedback": [] } }
sessions: dict[str, dict] = {}

# ── In-memory feedback store ────────────────────────────────────────
feedback_store: list[dict] = []


# ── Routes ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/webhook", methods=["POST"])
def webhook():
    """Main chat endpoint."""
    data = request.get_json(force=True)
    session_id = data.get("session_id", str(uuid.uuid4()))
    user_message = data.get("message", "").strip()
    city = data.get("city")  # optional

    if not user_message:
        return jsonify({"type": "error", "message": "Please type a message."})

    # Initialise session if new
    if session_id not in sessions:
        sessions[session_id] = {
            "symptoms": [],
            "severity": None,
            "duration": None,
            "awaiting": None,
            "followup_asked": False,
            "feedback": [],
        }

    session = sessions[session_id]

    # ── 1. Emergency check (always first) ───────────────────────────
    if check_emergency(user_message):
        resp = format_response(
            symptoms=[], predictions=[], interpretations=[],
            triage="", doctor_info=None,
            emergency=True, emergency_msg=EMERGENCY_MESSAGE,
        )
        return jsonify({"session_id": session_id, **resp})

    # ── 2. Handle follow-up answers ─────────────────────────────────
    if session["awaiting"]:
        awaiting = session["awaiting"]
        session["awaiting"] = None

        if awaiting == "more_symptoms":
            new_symptoms = extract_symptoms(user_message)
            session["symptoms"].extend(new_symptoms)
            # deduplicate
            session["symptoms"] = list(set(session["symptoms"]))

        elif awaiting == "duration":
            dur = extract_duration(user_message)
            if dur:
                session["duration"] = dur
            # also check if user sneaked in more symptoms
            extra = extract_symptoms(user_message)
            if extra:
                session["symptoms"] = list(set(session["symptoms"] + extra))

        elif awaiting == "severity":
            sev = extract_severity(user_message)
            if sev:
                session["severity"] = sev
            extra = extract_symptoms(user_message)
            if extra:
                session["symptoms"] = list(set(session["symptoms"] + extra))

    else:
        # ── 3. Normal symptom extraction ────────────────────────────
        new_symptoms = extract_symptoms(user_message)
        session["symptoms"] = list(set(session["symptoms"] + new_symptoms))

        dur = extract_duration(user_message)
        if dur:
            session["duration"] = dur
        sev = extract_severity(user_message)
        if sev:
            session["severity"] = sev

    symptoms = session["symptoms"]

    # ── 4. Run prediction ───────────────────────────────────────────
    predictions = predict_diseases(
        symptoms,
        severity=session["severity"],
        duration=session["duration"],
    )

    # ── 5. Check if follow-up is needed (only once per session) ──────
    top_confidence = predictions[0]["confidence"] if predictions else 0
    followup = None
    if not session.get("followup_asked"):
        followup = needs_followup(symptoms, top_confidence)

    if followup:
        session["awaiting"] = followup["type"]
        session["followup_asked"] = True
        resp = format_response(
            symptoms=symptoms, predictions=predictions,
            interpretations=[], triage="", doctor_info=None,
            followup=followup,
        )
        return jsonify({"session_id": session_id, **resp})

    # ── 6. Build full response ──────────────────────────────────────
    interpretations = [interpret_confidence(p["confidence"]) for p in predictions]
    triage = triage_suggestion(top_confidence, symptoms)

    doctor_info = None
    if predictions:
        doctor_info = recommend_doctors(predictions[0]["disease"], city=city)

    resp = format_response(
        symptoms=symptoms,
        predictions=predictions,
        interpretations=interpretations,
        triage=triage,
        doctor_info=doctor_info,
    )

    return jsonify({"session_id": session_id, **resp})


@app.route("/feedback", methods=["POST"])
def feedback():
    """Capture 👍/👎 feedback."""
    data = request.get_json(force=True)
    session_id = data.get("session_id", "unknown")
    vote = data.get("vote")  # "up" or "down"

    entry = {"session_id": session_id, "vote": vote}
    feedback_store.append(entry)

    if session_id in sessions:
        sessions[session_id]["feedback"].append(vote)

    return jsonify({"status": "ok", "message": "Thank you for your feedback!"})


# ── Run ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
