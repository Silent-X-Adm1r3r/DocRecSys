"""
DocRecSys — Centralized Configuration
All tuneable settings in one place. Override via environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Database ────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'data', 'docrecsys.db')}")
SQLITE_PATH = os.path.join(BASE_DIR, "data", "docrecsys.db")

# ── MongoDB ─────────────────────────────────────────────────────────
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "docrecsys")

# ── Redis ───────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL = int(os.getenv("SESSION_TTL", "1800"))           # 30 minutes
PREDICTION_CACHE_TTL = int(os.getenv("PREDICTION_CACHE_TTL", "86400"))  # 24 hours
MAPS_CACHE_TTL = int(os.getenv("MAPS_CACHE_TTL", "900"))     # 15 minutes

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
DISEASE_DESCRIPTIONS_JSON = os.path.join(DATA_DIR, "disease_descriptions.json")
SYMPTOM_WEIGHTS_JSON = os.path.join(DATA_DIR, "symptom_weights.json")
FOLLOWUP_QUESTIONS_JSON = os.path.join(DATA_DIR, "followup_questions.json")

# ── Gemini AI ───────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── Google Maps ─────────────────────────────────────────────────────
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# ── Specialist Search Radius (km) ──────────────────────────────────
RADIUS_GENERAL = int(os.getenv("RADIUS_GENERAL", "25"))       # General Physician
RADIUS_COMMON = int(os.getenv("RADIUS_COMMON", "50"))         # Common specialists
RADIUS_RARE = int(os.getenv("RADIUS_RARE", "100"))            # Rare specialists

# ── App Settings ────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "docrecsys-dev-secret-key-change-in-prod")
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "0.0.0.0")

# ── Rate Limiting ───────────────────────────────────────────────────
RATE_LIMIT = os.getenv("RATE_LIMIT", "60 per minute")
RATE_LIMIT_WEBHOOK = os.getenv("RATE_LIMIT_WEBHOOK", "30 per minute")

# ── Prediction Settings ────────────────────────────────────────────
MAX_PREDICTIONS = 5
CONFIDENCE_HIGH = 0.70
CONFIDENCE_MODERATE = 0.40
CONFIDENCE_THRESHOLD = 0.10
MAX_MESSAGE_LENGTH = 2000

# ── Follow-Up Settings ─────────────────────────────────────────────
MAX_FOLLOWUP_QUESTIONS = 3

# ── Emergency ───────────────────────────────────────────────────────
INDIA_EMERGENCY_NUMBER = "112"
INDIA_AMBULANCE_NUMBER = "108"
MENTAL_HEALTH_HELPLINE = "1800-599-0019"  # NIMHANS
WOMEN_HELPLINE = "181"
