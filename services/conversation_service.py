"""
Conversation Service — Redis-backed session memory for multi-turn medical consultations.
Each answer enriches (never overwrites) existing context.
Redis provides TTL-based expiry (30 min) with auto-refresh on interaction.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from services import redis_service

logger = logging.getLogger(__name__)

# In-memory fallback when Redis is unavailable
_fallback_sessions: dict[str, dict] = {}


def get_session(session_id: str) -> dict:
    """Get or create a conversation session from Redis."""
    if redis_service.is_available():
        from config import SESSION_TTL
        return redis_service.get_session(session_id, ttl=SESSION_TTL)
    # Fallback to in-memory
    if session_id not in _fallback_sessions:
        _fallback_sessions[session_id] = redis_service._new_session()
    return _fallback_sessions[session_id]


def update_session(session_id: str, data: dict) -> None:
    """Update session with new data (merge, never overwrite)."""
    if redis_service.is_available():
        from config import SESSION_TTL
        redis_service.update_session(session_id, data, ttl=SESSION_TTL)
    else:
        session = get_session(session_id)
        for key, value in data.items():
            if key == "symptoms" and isinstance(value, list):
                existing = set(session.get("symptoms", []))
                existing.update(value)
                session["symptoms"] = list(existing)
            elif key == "followupAnswers" and isinstance(value, list):
                session.setdefault("followupAnswers", []).extend(value)
            elif key == "riskFactors" and isinstance(value, list):
                existing = set(session.get("riskFactors", []))
                existing.update(value)
                session["riskFactors"] = list(existing)
            elif value:
                session[key] = value
        session["last_updated"] = datetime.now(timezone.utc).isoformat()


def enrich_context(session_id: str, new_data: dict) -> dict:
    """Enrich session with new data and return full context. Never overwrites."""
    update_session(session_id, new_data)
    return get_session(session_id)


def get_information_completeness(session_id: str) -> float:
    """
    Calculate information completeness score (0.0 - 1.0).
    Required: symptoms (40%), duration (20%), severity (20%)
    Preferred: age (10%), gender (10%)
    """
    session = get_session(session_id)
    score = 0.0

    # Symptoms (40%) — proportional to count
    symptoms = session.get("symptoms", [])
    if len(symptoms) >= 3:
        score += 0.40
    elif len(symptoms) == 2:
        score += 0.30
    elif len(symptoms) == 1:
        score += 0.20

    # Duration (20%)
    if session.get("duration"):
        score += 0.20

    # Severity (20%)
    if session.get("severity"):
        score += 0.20

    # Age (10%)
    if session.get("age"):
        score += 0.10

    # Gender (10%)
    if session.get("gender"):
        score += 0.10

    return round(score, 2)


def get_followup_count(session_id: str) -> int:
    """Get the number of follow-up questions asked so far."""
    return get_session(session_id).get("followup_count", 0)


def increment_followup_count(session_id: str) -> int:
    """Increment and return the follow-up count."""
    session = get_session(session_id)
    count = session.get("followup_count", 0) + 1
    update_session(session_id, {"followup_count": count})
    return count


def reset_session(session_id: str) -> None:
    """Reset a session."""
    if redis_service.is_available():
        redis_service.reset_session(session_id)
    elif session_id in _fallback_sessions:
        del _fallback_sessions[session_id]
