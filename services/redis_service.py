"""
Redis Service — Primary short-term memory layer for DocRecSys.
Handles session management, prediction caching, and maps result caching.
All cache operations are centralized here for consistency.
"""
from __future__ import annotations
import json, logging, math
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_pool = None
_client = None
_available = False


def init_redis(url: str):
    """Initialize Redis connection pool. Call once at app startup."""
    global _pool, _client, _available
    try:
        import redis
        _pool = redis.ConnectionPool.from_url(url, decode_responses=True)
        _client = redis.Redis(connection_pool=_pool)
        _client.ping()
        _available = True
        logger.info("Redis connected: %s", url.split("@")[-1] if "@" in url else url)
    except Exception as e:
        logger.warning("Redis unavailable (%s). Falling back to in-memory.", e)
        _available = False


def is_available() -> bool:
    return _available


def get_client():
    return _client


# ── Session Operations ──────────────────────────────────────────────

def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


def get_session(session_id: str, ttl: int = 1800) -> dict:
    """
    Load session from Redis. Creates a new one if not found.
    Refreshes TTL on every access.
    """
    if not _available:
        return _new_session()

    key = _session_key(session_id)
    try:
        raw = _client.get(key)
        if raw:
            _client.expire(key, ttl)
            return json.loads(raw)
    except Exception as e:
        logger.error("Redis get_session error: %s", e)

    # New session
    session = _new_session()
    save_session(session_id, session, ttl)
    return session


def save_session(session_id: str, session: dict, ttl: int = 1800):
    """Save full session to Redis with TTL."""
    if not _available:
        return
    key = _session_key(session_id)
    try:
        session["last_updated"] = datetime.now(timezone.utc).isoformat()
        _client.setex(key, ttl, json.dumps(session))
    except Exception as e:
        logger.error("Redis save_session error: %s", e)


def update_session(session_id: str, data: dict, ttl: int = 1800):
    """
    Merge new data into existing session. Never overwrites existing values
    with empty ones. Appends to list fields.
    """
    session = get_session(session_id, ttl)

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
        elif value:  # Only update if value is truthy
            session[key] = value

    session["last_updated"] = datetime.now(timezone.utc).isoformat()
    save_session(session_id, session, ttl)
    return session


def reset_session(session_id: str):
    """Delete a session from Redis."""
    if not _available:
        return
    try:
        _client.delete(_session_key(session_id))
    except Exception as e:
        logger.error("Redis reset_session error: %s", e)


def _new_session() -> dict:
    """Create a fresh session object."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "symptoms": [],
        "duration": "",
        "severity": "",
        "age": "",
        "gender": "",
        "riskFactors": [],
        "followupAnswers": [],
        "followup_count": 0,
        "awaiting": None,
        "latitude": None,
        "longitude": None,
        "predicted_disease": "",
        "specialist": "",
        "feedback": [],
        "created_at": now,
        "last_updated": now,
    }


# ── Prediction Cache ────────────────────────────────────────────────

def _prediction_key(symptoms: list[str]) -> str:
    """Normalize symptoms to a deterministic cache key."""
    normalized = sorted(set(s.lower().strip() for s in symptoms if s))
    return f"prediction:{'_'.join(normalized)}"


def get_prediction_cache(symptoms: list[str]) -> dict | None:
    """Check Redis for cached prediction results."""
    if not _available or not symptoms:
        return None
    key = _prediction_key(symptoms)
    try:
        raw = _client.get(key)
        if raw:
            logger.info("Prediction cache HIT: %s", key)
            return json.loads(raw)
        logger.info("Prediction cache MISS: %s", key)
    except Exception as e:
        logger.error("Redis get_prediction_cache error: %s", e)
    return None


def set_prediction_cache(symptoms: list[str], result: dict, ttl: int = 86400):
    """Cache prediction results with 24h TTL."""
    if not _available or not symptoms:
        return
    key = _prediction_key(symptoms)
    try:
        _client.setex(key, ttl, json.dumps(result))
        logger.info("Prediction cached: %s (TTL=%ds)", key, ttl)
    except Exception as e:
        logger.error("Redis set_prediction_cache error: %s", e)


# ── Maps Cache ──────────────────────────────────────────────────────

def _maps_key(specialist: str, lat: float, lng: float, radius_km: int = 0) -> str:
    """Create maps cache key with 3 decimal place precision (~111m) and radius."""
    return f"doctor_search:{specialist.lower().replace(' ', '_')}:{lat:.3f}:{lng:.3f}:{radius_km}km"


def get_maps_cache(specialist: str, lat: float, lng: float, radius_km: int = 0) -> list | None:
    """Check Redis for cached maps search results."""
    if not _available:
        return None
    key = _maps_key(specialist, lat, lng, radius_km)
    try:
        raw = _client.get(key)
        if raw:
            logger.info("Maps cache HIT: %s", key)
            return json.loads(raw)
        logger.info("Maps cache MISS: %s", key)
    except Exception as e:
        logger.error("Redis get_maps_cache error: %s", e)
    return None


def set_maps_cache(specialist: str, lat: float, lng: float, radius_km: int = 0, results: list = None, ttl: int = 900):
    """Cache maps search results with 15min TTL."""
    if not _available:
        return
    if results is None:
        results = []
    key = _maps_key(specialist, lat, lng, radius_km)
    try:
        _client.setex(key, ttl, json.dumps(results))
        logger.info("Maps cached: %s (%d results, TTL=%ds)", key, len(results), ttl)
    except Exception as e:
        logger.error("Redis set_maps_cache error: %s", e)


# ── Utility ─────────────────────────────────────────────────────────

def get_stats() -> dict:
    """Return Redis connection stats."""
    if not _available:
        return {"available": False}
    try:
        info = _client.info("keyspace")
        return {
            "available": True,
            "keyspace": info,
        }
    except Exception:
        return {"available": False}
