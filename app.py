"""
DocRecSys — AI-Powered Medical Symptom Checker & Doctor Recommendation
Production-grade Flask application with ML prediction, security hardening,
rate limiting, and SQLite persistence.
"""
import os, uuid, logging, html
from flask import Flask, render_template, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import (
    SECRET_KEY, DEBUG, PORT, HOST, SQLITE_PATH,
    RATE_LIMIT, RATE_LIMIT_WEBHOOK, MAX_MESSAGE_LENGTH,
)
from services.symptom_extractor import extract_symptoms, extract_duration, extract_severity
from services.predictor import predict_diseases, get_model_info
from services.doctor_recommender import recommend_doctors
from services.triage import (
    check_emergency, interpret_confidence, triage_suggestion, needs_followup,
)
from services.response_formatter import format_response
from services.database import init_db, save_session, save_feedback, save_emergency_alert

# ── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Flask App ───────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = SECRET_KEY

# ── Rate Limiting ───────────────────────────────────────────────────
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[RATE_LIMIT],
    storage_uri="memory://",
)

# ── In-memory session store ─────────────────────────────────────────
sessions: dict[str, dict] = {}

# ── Database init ───────────────────────────────────────────────────
init_db(SQLITE_PATH)
logger.info("DocRecSys started — ML model: %s", get_model_info().get("status", "unknown"))

# ── Security headers ────────────────────────────────────────────────
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ── Error Handlers ──────────────────────────────────────────────────
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"type": "error", "message": "Invalid request."}), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify({"type": "error", "message": "Resource not found."}), 404

@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"type": "error", "message": "Too many requests. Please wait a moment."}), 429

@app.errorhandler(500)
def server_error(e):
    logger.error("Internal error: %s", e)
    return jsonify({"type": "error", "message": "An internal error occurred. Please try again."}), 500

# ── Routes ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({"status": "ok", "model": get_model_info()})

@app.route("/webhook", methods=["POST"])
@limiter.limit(RATE_LIMIT_WEBHOOK)
def webhook():
    """Main chat endpoint."""
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"type": "error", "message": "Invalid JSON."}), 400

    session_id = str(data.get("session_id", uuid.uuid4()))
    user_message = str(data.get("message", "")).strip()
    city = data.get("city")

    # Input validation
    if not user_message:
        return jsonify({"type": "error", "message": "Please type a message."})
    if len(user_message) > MAX_MESSAGE_LENGTH:
        return jsonify({"type": "error", "message": f"Message too long (max {MAX_MESSAGE_LENGTH} characters)."})

    # Sanitize
    user_message = html.unescape(user_message)

    # Init session
    if session_id not in sessions:
        sessions[session_id] = {
            "symptoms": [], "severity": None, "duration": None,
            "awaiting": None, "followup_asked": False, "feedback": [],
        }
    session = sessions[session_id]

    # ── 1. Emergency check ──────────────────────────────────────────
    emergency_data = check_emergency(user_message)
    if emergency_data:
        save_emergency_alert(session_id, user_message, emergency_data["score"], emergency_data["level"])
        resp = format_response(
            symptoms=[], predictions=[], interpretations=[],
            triage="", doctor_info=None,
            emergency=True, emergency_data=emergency_data,
        )
        return jsonify({"session_id": session_id, **resp})

    # ── 2. Handle follow-up answers ─────────────────────────────────
    if session["awaiting"]:
        awaiting = session["awaiting"]
        session["awaiting"] = None
        if awaiting == "more_symptoms":
            new_symptoms = extract_symptoms(user_message)
            session["symptoms"].extend(new_symptoms)
            session["symptoms"] = list(set(session["symptoms"]))
        elif awaiting == "duration":
            dur = extract_duration(user_message)
            if dur: session["duration"] = dur
            extra = extract_symptoms(user_message)
            if extra: session["symptoms"] = list(set(session["symptoms"] + extra))
        elif awaiting == "severity":
            sev = extract_severity(user_message)
            if sev: session["severity"] = sev
            extra = extract_symptoms(user_message)
            if extra: session["symptoms"] = list(set(session["symptoms"] + extra))
    else:
        # ── 3. Normal symptom extraction ────────────────────────────
        new_symptoms = extract_symptoms(user_message)
        session["symptoms"] = list(set(session["symptoms"] + new_symptoms))
        dur = extract_duration(user_message)
        if dur: session["duration"] = dur
        sev = extract_severity(user_message)
        if sev: session["severity"] = sev

    symptoms = session["symptoms"]

    # ── 4. Run prediction ───────────────────────────────────────────
    predictions = predict_diseases(symptoms, severity=session["severity"], duration=session["duration"])

    # ── 5. Follow-up check ──────────────────────────────────────────
    top_confidence = predictions[0]["confidence"] if predictions else 0
    followup = None
    if not session.get("followup_asked"):
        followup = needs_followup(symptoms, top_confidence)
    if followup:
        session["awaiting"] = followup["type"]
        session["followup_asked"] = True
        resp = format_response(
            symptoms=symptoms, predictions=predictions,
            interpretations=[], triage="", doctor_info=None, followup=followup,
        )
        return jsonify({"session_id": session_id, **resp})

    # ── 6. Full response ────────────────────────────────────────────
    interpretations = [interpret_confidence(p["confidence"]) for p in predictions]
    triage = triage_suggestion(top_confidence, symptoms)

    doctor_info = None
    if predictions:
        doctor_info = recommend_doctors(predictions[0]["disease"], city=city)

    resp = format_response(
        symptoms=symptoms, predictions=predictions,
        interpretations=interpretations, triage=triage, doctor_info=doctor_info,
    )

    # Persist session
    save_session(session_id, symptoms, [p["disease"] for p in predictions], city)

    return jsonify({"session_id": session_id, **resp})


@app.route("/feedback", methods=["POST"])
@limiter.limit("20 per minute")
def feedback():
    """Capture thumbs-up/down feedback."""
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"type": "error", "message": "Invalid JSON."}), 400

    session_id = str(data.get("session_id", "unknown"))
    vote = data.get("vote")
    if vote not in ("up", "down"):
        return jsonify({"type": "error", "message": "Invalid vote."}), 400

    save_feedback(session_id, vote)
    if session_id in sessions:
        sessions[session_id]["feedback"].append(vote)

    return jsonify({"status": "ok", "message": "Thank you for your feedback!"})


@app.route("/reset", methods=["POST"])
def reset():
    """Reset a chat session."""
    data = request.get_json(force=True) if request.data else {}
    session_id = data.get("session_id")
    if session_id and session_id in sessions:
        del sessions[session_id]
    return jsonify({"status": "ok", "message": "Session reset."})


# ── Run ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=DEBUG, port=PORT, host=HOST)
