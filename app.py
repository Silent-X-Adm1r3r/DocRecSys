"""
DocRecSys — AI-Powered Medical Symptom Checker & Doctor Recommendation
Production-grade Flask application with Redis session management, Gemini AI,
dataset-driven prediction, Google Maps integration, and context-aware follow-ups.
"""
import os, uuid, logging, html
from flask import Flask, render_template, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import (
    SECRET_KEY, DEBUG, PORT, HOST, SQLITE_PATH,
    RATE_LIMIT, RATE_LIMIT_WEBHOOK, MAX_MESSAGE_LENGTH,
    GEMINI_API_KEY, GEMINI_MODEL, GOOGLE_MAPS_API_KEY,
    MONGODB_URI, MONGODB_DB_NAME, MAX_PREDICTIONS,
    MAX_FOLLOWUP_QUESTIONS, CONFIDENCE_HIGH, CONFIDENCE_MODERATE,
    REDIS_URL, SESSION_TTL,
)

# ── Structured Logging ──────────────────────────────────────────────
from services.logger import setup_logging, log_symptom_check
setup_logging()
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

# ── Initialize Services ────────────────────────────────────────────
from services.database import init_db
from services.mongodb import init_mongodb
from services.gemini_service import init_gemini
from services.maps_service import init_maps
from services.redis_service import init_redis

init_redis(REDIS_URL)
init_db(SQLITE_PATH)
init_mongodb(MONGODB_URI, MONGODB_DB_NAME)
init_gemini(GEMINI_API_KEY, GEMINI_MODEL)
init_maps(GOOGLE_MAPS_API_KEY)

logger.info("DocRecSys started — all services initialized")

# ── Import Services ─────────────────────────────────────────────────
from services.symptom_extractor import extract_symptoms, extract_duration, extract_severity, get_display_name
from services.gemini_service import extract_symptoms_gemini, is_available as gemini_available
from services.conversation_service import (
    get_session, update_session, enrich_context,
    get_information_completeness, get_followup_count,
    increment_followup_count, reset_session,
)
from services.followup_service import should_ask_followup
from services.emergency_service import check_emergency, check_red_flags
from services.disease_prediction_service import predict_diseases
from services.confidence_service import get_overall_confidence, interpret_confidence
from services.explanation_service import generate_explanation, generate_summary_explanation
from services.doctor_recommender import recommend_doctors, recommend_emergency
from services.response_formatter import format_response
from services.database import save_session as db_save_session, save_feedback, save_emergency_alert

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
    return render_template("index.html", maps_api_key=GOOGLE_MAPS_API_KEY)

@app.route("/health")
def health():
    from services.gemini_service import get_status as gemini_status
    from services.maps_service import is_available as maps_available
    from services.mongodb import is_available as mongo_available
    from services.redis_service import is_available as redis_available
    return jsonify({
        "status": "ok",
        "gemini": gemini_status(),
        "maps": maps_available(),
        "mongodb": mongo_available(),
        "redis": redis_available(),
    })

@app.route("/webhook", methods=["POST"])
@limiter.limit(RATE_LIMIT_WEBHOOK)
def webhook():
    """Main chat endpoint — context-aware AI pipeline with Redis session."""
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"type": "error", "message": "Invalid JSON."}), 400

    session_id = str(data.get("session_id", uuid.uuid4()))
    user_message = str(data.get("message", "")).strip()
    lat = data.get("lat")
    lng = data.get("lng")

    # Convert lat/lng to float if provided
    try:
        lat = float(lat) if lat else None
        lng = float(lng) if lng else None
    except (ValueError, TypeError):
        lat, lng = None, None

    # Input validation
    if not user_message:
        return jsonify({"type": "error", "message": "Please type a message."})
    if len(user_message) > MAX_MESSAGE_LENGTH:
        return jsonify({"type": "error", "message": f"Message too long (max {MAX_MESSAGE_LENGTH} characters)."})

    # Sanitize
    user_message = html.unescape(user_message)

    # ══════════════════════════════════════════════════════════════
    # STEP 1: Load Redis session & store coordinates
    # ══════════════════════════════════════════════════════════════
    session = get_session(session_id)

    # Store/update location in session
    if lat and lng:
        update_session(session_id, {"latitude": lat, "longitude": lng})
    else:
        # Use previously stored coordinates if available
        lat = lat or session.get("latitude")
        lng = lng or session.get("longitude")

    # ══════════════════════════════════════════════════════════════
    # STEP 2: Emergency check (overrides everything)
    # ══════════════════════════════════════════════════════════════
    emergency_data = check_emergency(user_message)
    if emergency_data:
        save_emergency_alert(session_id, user_message, emergency_data["score"], emergency_data["level"])
        # Get emergency hospitals if location available
        emergency_recs = recommend_emergency(lat=lat, lng=lng) if lat and lng else None
        resp = format_response(
            symptoms=[], predictions=[], interpretations=[],
            triage="", doctor_info=emergency_recs,
            emergency=True, emergency_data=emergency_data,
        )
        return jsonify({"session_id": session_id, **resp})

    # ══════════════════════════════════════════════════════════════
    # STEP 3: Handle follow-up answers
    # ══════════════════════════════════════════════════════════════
    awaiting = session.get("awaiting")
    if awaiting:
        update_session(session_id, {"awaiting": None})
        _process_followup_answer(session_id, user_message, awaiting)
    else:
        # ══════════════════════════════════════════════════════════
        # STEP 4: Symptom extraction (Gemini + Local) & merge into session
        # ══════════════════════════════════════════════════════════
        _extract_and_enrich(session_id, user_message)

    # Reload session after enrichment
    session = get_session(session_id)
    symptoms = session.get("symptoms", [])

    # ══════════════════════════════════════════════════════════════
    # STEP 5: Red flag check (warning, continue flow)
    # ══════════════════════════════════════════════════════════════
    red_flags = check_red_flags(user_message, symptoms)

    # ══════════════════════════════════════════════════════════════
    # STEP 6: Context-aware follow-up (only ask for missing info)
    # ══════════════════════════════════════════════════════════════
    completeness = get_information_completeness(session_id)
    followup_count = get_followup_count(session_id)

    followup = should_ask_followup(
        symptoms=symptoms,
        completeness=completeness,
        followup_count=followup_count,
        max_followups=MAX_FOLLOWUP_QUESTIONS,
        session=session,  # Pass session for context-awareness
    )

    if followup:
        update_session(session_id, {"awaiting": followup["type"]})
        increment_followup_count(session_id)
        resp = format_response(
            symptoms=symptoms, predictions=[], interpretations=[],
            triage="", doctor_info=None, followup=followup,
        )
        return jsonify({"session_id": session_id, **resp})

    # ══════════════════════════════════════════════════════════════
    # STEP 7: Disease prediction (dataset-driven, with Redis cache)
    # ══════════════════════════════════════════════════════════════
    predictions = predict_diseases(
        symptoms,
        severity=session.get("severity"),
        duration=session.get("duration"),
        top_n=MAX_PREDICTIONS,
    )

    # ══════════════════════════════════════════════════════════════
    # STEP 8: Confidence scoring
    # ══════════════════════════════════════════════════════════════
    interpretations = [interpret_confidence(p["confidence"]) for p in predictions]
    confidence_info = get_overall_confidence(predictions)

    # ══════════════════════════════════════════════════════════════
    # STEP 9: Triage suggestion
    # ══════════════════════════════════════════════════════════════
    top_confidence = predictions[0]["confidence"] if predictions else 0
    triage = _triage_suggestion(top_confidence, symptoms)

    # ══════════════════════════════════════════════════════════════
    # STEP 10: Explanation generation
    # ══════════════════════════════════════════════════════════════
    explanation = generate_summary_explanation(predictions, symptoms)
    # Add per-disease explanations
    for pred in predictions:
        pred["explanation"] = generate_explanation(
            pred["disease"], pred.get("matching_symptoms", []),
            pred["confidence"], symptoms,
        )
        pred["explanation_symptoms"] = [get_display_name(s) for s in pred.get("matching_symptoms", symptoms)]

    # ══════════════════════════════════════════════════════════════
    # STEP 11: Specialist mapping + Doctor/Hospital search
    #          (requires geolocation)
    # ══════════════════════════════════════════════════════════════
    doctor_info = None
    location_error = None
    if predictions:
        doctor_info = recommend_doctors(
            predictions[0]["disease"],
            latitude=lat, longitude=lng,
        )
        # Store predicted disease and specialist in session
        update_session(session_id, {
            "predicted_disease": predictions[0]["disease"],
            "specialist": doctor_info.get("specialist", ""),
        })

        if doctor_info.get("success") is False:
            location_error = doctor_info.get("error", "")

    # ══════════════════════════════════════════════════════════════
    # STEP 12: Precautions
    # ══════════════════════════════════════════════════════════════
    precautions = predictions[0].get("precautions", []) if predictions else []

    # ══════════════════════════════════════════════════════════════
    # STEP 13: Format and return
    # ══════════════════════════════════════════════════════════════
    resp = format_response(
        symptoms=symptoms,
        predictions=predictions,
        interpretations=interpretations,
        triage=triage,
        doctor_info=doctor_info,
        explanation=explanation,
        red_flags=red_flags,
        confidence_info=confidence_info,
        precautions=precautions,
        location_error=location_error,
    )

    # Log structured event
    log_symptom_check(
        logger,
        session_id=session_id,
        symptoms=symptoms,
        disease=predictions[0]["disease"] if predictions else "",
        confidence=predictions[0]["confidence"] if predictions else 0,
        specialist=doctor_info.get("specialist", "") if doctor_info else "",
        latitude=lat,
        longitude=lng,
    )

    # Persist session to SQLite for analytics
    db_save_session(session_id, symptoms, [p["disease"] for p in predictions])

    return jsonify({"session_id": session_id, **resp})


# ── Helper functions ────────────────────────────────────────────────

def _extract_and_enrich(session_id: str, text: str):
    """Extract symptoms using Gemini + local extractor and enrich session."""
    new_data = {}

    # Try Gemini first
    if gemini_available():
        session = get_session(session_id)
        gemini_result = extract_symptoms_gemini(text, context=session)
        if gemini_result:
            # Normalize Gemini symptoms to canonical form
            gemini_symptoms = gemini_result.get("symptoms", [])
            normalized = []
            for s in gemini_symptoms:
                canonical = s.lower().replace(" ", "_").replace("-", "_")
                normalized.append(canonical)

            new_data["symptoms"] = normalized
            if gemini_result.get("duration"):
                new_data["duration"] = gemini_result["duration"]
            if gemini_result.get("severity"):
                new_data["severity"] = gemini_result["severity"]
            if gemini_result.get("age"):
                new_data["age"] = gemini_result["age"]
            if gemini_result.get("gender"):
                new_data["gender"] = gemini_result["gender"]
            if gemini_result.get("riskFactors"):
                new_data["riskFactors"] = gemini_result["riskFactors"]

    # Always run local extractor (catches what Gemini might miss)
    local_symptoms = extract_symptoms(text)
    existing_symptoms = new_data.get("symptoms", [])
    combined = list(set(existing_symptoms + local_symptoms))
    new_data["symptoms"] = combined

    # Local duration/severity
    dur = extract_duration(text)
    if dur and not new_data.get("duration"):
        new_data["duration"] = dur
    sev = extract_severity(text)
    if sev and not new_data.get("severity"):
        new_data["severity"] = sev

    enrich_context(session_id, new_data)


def _process_followup_answer(session_id: str, text: str, awaiting: str):
    """Process a follow-up answer and enrich session."""
    new_data = {"followupAnswers": [{"type": awaiting, "answer": text}]}

    if awaiting == "more_symptoms":
        symptoms = extract_symptoms(text)
        new_data["symptoms"] = symptoms
    elif awaiting == "duration":
        dur = extract_duration(text)
        if dur:
            new_data["duration"] = dur
        symptoms = extract_symptoms(text)
        if symptoms:
            new_data["symptoms"] = symptoms
    elif awaiting == "severity":
        sev = extract_severity(text)
        if sev:
            new_data["severity"] = sev
        symptoms = extract_symptoms(text)
        if symptoms:
            new_data["symptoms"] = symptoms

    enrich_context(session_id, new_data)


def _triage_suggestion(confidence: float, symptoms: list[str]) -> str:
    risky = {"chest_pain", "breathlessness", "high_fever", "seizure", "loss_of_consciousness", "slurred_speech", "vomiting"}
    has_risky = bool(set(symptoms) & risky)
    if has_risky or confidence > 0.70:
        return "\u26a0\ufe0f Seek medical attention promptly"
    if confidence >= 0.40:
        return "\U0001fa7a Consult a doctor at your convenience"
    return "\U0001f4cb Monitor your symptoms and rest"


# ── Additional Endpoints ────────────────────────────────────────────

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
    session = get_session(session_id)
    session.setdefault("feedback", []).append(vote)

    return jsonify({"status": "ok", "message": "Thank you for your feedback!"})


@app.route("/reset", methods=["POST"])
def reset():
    """Reset a chat session."""
    data = request.get_json(force=True) if request.data else {}
    session_id = data.get("session_id")
    if session_id:
        reset_session(session_id)
    return jsonify({"status": "ok", "message": "Session reset."})


# ── Run ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=DEBUG, port=PORT, host=HOST)
