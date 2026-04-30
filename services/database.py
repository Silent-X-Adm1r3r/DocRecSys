"""
Database Service — SQLite storage for doctors, sessions, feedback.
Auto-initialises on first use. Import and call init_db() at app startup.
"""
from __future__ import annotations
import sqlite3, json, os, logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_DB_PATH: str | None = None

def init_db(db_path: str):
    """Create tables if they don't exist and load doctor data."""
    global _DB_PATH
    _DB_PATH = db_path
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        # Load doctors if table is empty
        count = conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
        if count == 0:
            _load_doctors(conn)
    logger.info("Database initialised at %s", db_path)

@contextmanager
def _connect():
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    specialization TEXT NOT NULL,
    hospital TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    experience_years INTEGER DEFAULT 0,
    rating REAL DEFAULT 4.0,
    consultation_fee TEXT,
    available_days TEXT,
    phone TEXT
);
CREATE INDEX IF NOT EXISTS idx_doctors_spec ON doctors(specialization);
CREATE INDEX IF NOT EXISTS idx_doctors_city ON doctors(city);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    symptoms TEXT,
    predictions TEXT,
    city TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    vote TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS emergency_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    trigger_text TEXT,
    severity_score REAL,
    emergency_level TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def _load_doctors(conn: sqlite3.Connection):
    """Load doctors from JSON into SQLite."""
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "doctors_india.json")
    if not os.path.exists(json_path):
        logger.warning("doctors_india.json not found at %s", json_path)
        return
    with open(json_path, "r", encoding="utf-8") as f:
        doctors = json.load(f)
    conn.executemany(
        "INSERT INTO doctors (name,specialization,hospital,city,state,experience_years,rating,consultation_fee,available_days,phone) VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(d["name"],d["specialization"],d["hospital"],d["city"],d["state"],d.get("experience_years",0),d.get("rating",4.0),d.get("consultation_fee",""),d.get("available_days",""),d.get("phone","")) for d in doctors]
    )
    logger.info("Loaded %d doctors into database", len(doctors))

# ── Public query functions ──────────────────────────────────────────

def get_doctors(specialization: str, city: str | None = None, limit: int = 5) -> list[dict]:
    """Fetch doctors by specialization, optionally filtered by city."""
    with _connect() as conn:
        if city:
            # Fuzzy city match
            city_variants = _city_aliases(city)
            placeholders = ",".join("?" for _ in city_variants)
            rows = conn.execute(
                f"SELECT * FROM doctors WHERE specialization=? AND LOWER(city) IN ({placeholders}) ORDER BY rating DESC, experience_years DESC LIMIT ?",
                [specialization] + city_variants + [limit]
            ).fetchall()
            if not rows:
                # Fallback: all doctors for that specialty
                rows = conn.execute(
                    "SELECT * FROM doctors WHERE specialization=? ORDER BY rating DESC, experience_years DESC LIMIT ?",
                    [specialization, limit]
                ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM doctors WHERE specialization=? ORDER BY rating DESC, experience_years DESC LIMIT ?",
                [specialization, limit]
            ).fetchall()
        return [dict(r) for r in rows]

def save_session(session_id: str, symptoms: list, predictions: list, city: str | None = None):
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions (id, symptoms, predictions, city) VALUES (?,?,?,?)",
            [session_id, json.dumps(symptoms), json.dumps(predictions), city]
        )

def save_feedback(session_id: str, vote: str):
    with _connect() as conn:
        conn.execute("INSERT INTO feedback (session_id, vote) VALUES (?,?)", [session_id, vote])

def save_emergency_alert(session_id: str, trigger_text: str, severity_score: float, level: str):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO emergency_alerts (session_id, trigger_text, severity_score, emergency_level) VALUES (?,?,?,?)",
            [session_id, trigger_text, severity_score, level]
        )

def _city_aliases(city: str) -> list[str]:
    """Return lowercase variants for fuzzy city matching."""
    c = city.strip().lower()
    aliases = {
        "bangalore": ["bengaluru", "bangalore"],
        "bengaluru": ["bengaluru", "bangalore"],
        "bombay": ["mumbai", "bombay"],
        "mumbai": ["mumbai", "bombay"],
        "calcutta": ["kolkata", "calcutta"],
        "kolkata": ["kolkata", "calcutta"],
        "madras": ["chennai", "madras"],
        "chennai": ["chennai", "madras"],
        "delhi": ["new delhi", "delhi"],
        "new delhi": ["new delhi", "delhi"],
        "trivandrum": ["thiruvananthapuram", "trivandrum"],
        "thiruvananthapuram": ["thiruvananthapuram", "trivandrum"],
        "pondicherry": ["puducherry", "pondicherry"],
        "puducherry": ["puducherry", "pondicherry"],
        "guwahati": ["dispur", "guwahati"],
        "chandigarh": ["chandigarh"],
    }
    return aliases.get(c, [c])
