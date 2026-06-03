"""
MongoDB Service — Connection management and collection access.
Uses MongoDB Atlas in production, falls back gracefully if unavailable.
"""
from __future__ import annotations
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_client = None
_db = None
_available = False


def init_mongodb(uri: str, db_name: str):
    """Initialize MongoDB connection. Call once at app startup."""
    global _client, _db, _available
    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Test connection
        _client.admin.command("ping")
        _db = _client[db_name]
        _available = True
        _create_indexes()
        logger.info("MongoDB connected: %s/%s", uri.split("@")[-1] if "@" in uri else "localhost", db_name)
    except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
        logger.warning("MongoDB unavailable (%s). Using fallback mode.", e)
        _available = False


def is_available() -> bool:
    return _available


def get_db():
    """Get the MongoDB database instance."""
    return _db


def get_collection(name: str):
    """Get a MongoDB collection by name."""
    if not _available or _db is None:
        return None
    return _db[name]


def _create_indexes():
    """Create indexes for optimal query performance."""
    if not _available:
        return
    try:
        _db["diseases"].create_index("name", unique=True)
        _db["diseases"].create_index("symptoms")
        _db["symptoms"].create_index("name", unique=True)
        _db["symptoms"].create_index("aliases")
        _db["specialists"].create_index("specialization")
        _db["disease_mappings"].create_index("disease", unique=True)
        _db["disease_mappings"].create_index("specialist")
        _db["sessions"].create_index("session_id")
        _db["hospitals_cache"].create_index("cache_key")
        _db["hospitals_cache"].create_index("expires_at", expireAfterSeconds=0)
        logger.info("MongoDB indexes created.")
    except Exception as e:
        logger.warning("Index creation warning: %s", e)


# ── CRUD helpers ────────────────────────────────────────────────────

def find_diseases_by_symptoms(symptoms: list[str], limit: int = 20) -> list[dict]:
    """Find diseases that match any of the given symptoms."""
    col = get_collection("diseases")
    if col is None:
        return []
    try:
        results = list(col.find(
            {"symptoms": {"$in": symptoms}},
            {"_id": 0}
        ).limit(limit))
        return results
    except Exception as e:
        logger.error("find_diseases_by_symptoms error: %s", e)
        return []


def get_disease_by_name(name: str) -> dict | None:
    """Get a single disease by name (case-insensitive)."""
    col = get_collection("diseases")
    if col is None:
        return None
    try:
        import re
        return col.find_one(
            {"name": re.compile(f"^{re.escape(name)}$", re.IGNORECASE)},
            {"_id": 0}
        )
    except Exception as e:
        logger.error("get_disease_by_name error: %s", e)
        return None


def get_specialist_for_disease(disease: str) -> str:
    """Get the specialist mapping for a disease."""
    col = get_collection("disease_mappings")
    if col is None:
        return "General Physician"
    try:
        import re
        mapping = col.find_one(
            {"disease": re.compile(f"^{re.escape(disease)}$", re.IGNORECASE)},
            {"_id": 0}
        )
        return mapping["specialist"] if mapping else "General Physician"
    except Exception:
        return "General Physician"


def save_mongo_session(session_id: str, data: dict):
    """Save or update a session in MongoDB."""
    col = get_collection("sessions")
    if col is None:
        return
    try:
        from datetime import datetime, timezone
        col.update_one(
            {"session_id": session_id},
            {"$set": {**data, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
    except Exception as e:
        logger.error("save_mongo_session error: %s", e)


def cache_hospital_data(cache_key: str, data: list, ttl_seconds: int = 86400):
    """Cache hospital/doctor search results with TTL."""
    col = get_collection("hospitals_cache")
    if col is None:
        return
    try:
        from datetime import datetime, timezone, timedelta
        col.update_one(
            {"cache_key": cache_key},
            {"$set": {
                "data": data,
                "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
            }},
            upsert=True,
        )
    except Exception as e:
        logger.error("cache_hospital_data error: %s", e)


def get_cached_hospital_data(cache_key: str) -> list | None:
    """Retrieve cached hospital data if not expired."""
    col = get_collection("hospitals_cache")
    if col is None:
        return None
    try:
        result = col.find_one({"cache_key": cache_key}, {"_id": 0})
        return result.get("data") if result else None
    except Exception:
        return None
