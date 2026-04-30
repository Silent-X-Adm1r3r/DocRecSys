"""
DocRecSys — Centralized Configuration
All tuneable settings in one place. Override via environment variables.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Database ────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'data', 'docrecsys.db')}")
SQLITE_PATH = os.path.join(BASE_DIR, "data", "docrecsys.db")

# ── ML Model Paths ─────────────────────────────────────────────────
MODEL_DIR = os.path.join(BASE_DIR, "models")
DISEASE_MODEL_PATH = os.path.join(MODEL_DIR, "disease_predictor.pkl")
TFIDF_PATH = os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl")
LABEL_ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")
MODEL_METADATA_PATH = os.path.join(MODEL_DIR, "model_metadata.json")

# ── Data Paths ──────────────────────────────────────────────────────
DATA_DIR = os.path.join(BASE_DIR, "data")
SYMPTOM_DISEASE_CSV = os.path.join(DATA_DIR, "symptom_disease_data.csv")
SYMPTOM_SYNONYMS_JSON = os.path.join(DATA_DIR, "symptom_synonyms.json")
DOCTORS_JSON = os.path.join(DATA_DIR, "doctors_india.json")

# ── App Settings ────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "docrecsys-dev-secret-key-change-in-prod")
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "0.0.0.0")

# ── Rate Limiting ───────────────────────────────────────────────────
RATE_LIMIT = os.getenv("RATE_LIMIT", "60 per minute")
RATE_LIMIT_WEBHOOK = os.getenv("RATE_LIMIT_WEBHOOK", "30 per minute")

# ── Prediction Settings ────────────────────────────────────────────
MAX_PREDICTIONS = 3
CONFIDENCE_THRESHOLD = 0.15
MAX_MESSAGE_LENGTH = 2000

# ── Emergency ───────────────────────────────────────────────────────
INDIA_EMERGENCY_NUMBER = "112"
INDIA_AMBULANCE_NUMBER = "108"
MENTAL_HEALTH_HELPLINE = "1800-599-0019"  # NIMHANS
WOMEN_HELPLINE = "181"
