"""
Disease Predictor — Uses ML engine for real AI-powered predictions.
Falls back to enhanced rule-based scoring if model isn't available.
"""
from __future__ import annotations
import os, logging
from services.ml_engine import MLEngine
from services.symptom_extractor import get_display_name

logger = logging.getLogger(__name__)

_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
_engine: MLEngine | None = None

SEVERITY_MULTIPLIER = {"severe": 1.15, "moderate": 1.0, "mild": 0.9}

def _get_engine() -> MLEngine:
    global _engine
    if _engine is None:
        _engine = MLEngine(_MODEL_DIR)
    return _engine

def predict_diseases(
    symptoms: list[str],
    severity: str | None = None,
    duration: str | None = None,
    top_n: int = 3,
) -> list[dict]:
    """
    Return up to top_n predictions, each:
    { disease, confidence, confidence_pct, matching_symptoms, explanation }
    """
    if not symptoms:
        return []

    engine = _get_engine()

    if engine.is_loaded:
        results = engine.predict(symptoms, top_n=top_n)
    else:
        results = _fallback_predict(symptoms, top_n)

    # Apply severity modifier
    if severity and severity in SEVERITY_MULTIPLIER:
        mult = SEVERITY_MULTIPLIER[severity]
        for r in results:
            r["confidence"] = min(round(r["confidence"] * mult, 3), 1.0)

    # Add display info
    for r in results:
        r["confidence_pct"] = f"{round(r['confidence'] * 100)}%"
        r["explanation_symptoms"] = [get_display_name(s) for s in r.get("matching_symptoms", symptoms)]

    # Filter very low confidence
    results = [r for r in results if r["confidence"] >= 0.05]

    return results[:top_n]

def _fallback_predict(symptoms: list[str], top_n: int) -> list[dict]:
    """Simple rule-based fallback if ML model is unavailable."""
    # Minimal hardcoded mappings
    RULES = {
        "Common Cold": ["continuous_sneezing","cough","throat_irritation","headache","fatigue","runny_nose","congestion","chills","mild_fever"],
        "Influenza": ["high_fever","cough","body_ache","fatigue","headache","chills","sweating","muscle_pain","joint_pain"],
        "Gastroenteritis": ["nausea","vomiting","diarrhoea","abdominal_pain","stomach_pain","fatigue","loss_of_appetite"],
        "Migraine": ["headache","nausea","blurred_and_distorted_vision","visual_disturbances"],
        "Hypertension": ["headache","chest_pain","breathlessness","high_bp","fatigue"],
        "COVID-19": ["cough","high_fever","fatigue","breathlessness","headache","loss_of_smell","body_ache"],
        "Dengue": ["high_fever","headache","body_ache","joint_pain","skin_rash","fatigue","muscle_pain","red_spots_over_body"],
        "Malaria": ["high_fever","chills","sweating","headache","body_ache","nausea","vomiting","fatigue"],
        "Diabetes": ["fatigue","weight_loss","excessive_hunger","blurred_and_distorted_vision","polyuria"],
        "Anxiety Disorder": ["anxiety","restlessness","insomnia","palpitations","breathlessness","fatigue"],
    }
    scores = []
    for disease, disease_symptoms in RULES.items():
        matched = [s for s in symptoms if s in disease_symptoms]
        if matched:
            conf = len(matched) / len(disease_symptoms)
            scores.append({"disease": disease, "confidence": round(conf, 3), "matching_symptoms": matched})
    scores.sort(key=lambda x: x["confidence"], reverse=True)
    return scores[:top_n]

def get_model_info() -> dict:
    return _get_engine().get_model_info()
