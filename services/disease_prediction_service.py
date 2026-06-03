"""
Disease Prediction Service — Dataset-driven disease ranking with Redis caching.
Uses weighted scoring from medical datasets, NOT Gemini.
Always returns Top 5 ranked diseases.
Checks Redis prediction cache before computing.
"""
from __future__ import annotations
import json, os, logging, math

from services import redis_service
from services.logger import log_prediction

logger = logging.getLogger(__name__)

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load symptom weights
_SYMPTOM_WEIGHTS: dict = {}
_weights_path = os.path.join(_BASE, "data", "symptom_weights.json")
if os.path.exists(_weights_path):
    with open(_weights_path, "r", encoding="utf-8") as f:
        _SYMPTOM_WEIGHTS = json.load(f)
        _SYMPTOM_WEIGHTS.pop("_comment", None)

# Load disease descriptions
_DISEASE_INFO: dict = {}
_desc_path = os.path.join(_BASE, "data", "disease_descriptions.json")
if os.path.exists(_desc_path):
    with open(_desc_path, "r", encoding="utf-8") as f:
        _DISEASE_INFO = json.load(f)

SEVERITY_MULTIPLIER = {"severe": 1.15, "moderate": 1.0, "mild": 0.90}
DURATION_BOOST = {
    "chronic": 1.10, "persistent": 1.10,
    "weeks": 1.08, "month": 1.05, "months": 1.10,
    "days": 1.0, "hours": 0.95, "just started": 0.90,
}


def predict_diseases(
    symptoms: list[str],
    severity: str | None = None,
    duration: str | None = None,
    top_n: int = 5,
) -> list[dict]:
    """
    Predict diseases using weighted dataset scoring.
    Returns Top N ranked diseases with confidence scores.

    Process:
    1. Check Redis prediction cache
    2. Match symptoms against disease database
    3. Calculate weighted score per disease
    4. Apply severity/duration modifiers
    5. Combine with ML model if available
    6. Cache results in Redis
    7. Return Top N with explanations
    """
    if not symptoms:
        return []

    # Step 0: Check Redis prediction cache
    from config import PREDICTION_CACHE_TTL
    cached = redis_service.get_prediction_cache(symptoms)
    if cached:
        log_prediction(
            logger,
            symptoms=symptoms,
            prediction_cache_hit=True,
            disease=cached[0]["disease"] if cached else "",
            confidence=cached[0]["confidence"] if cached else 0,
        )
        return cached

    # Step 1: Dataset-driven scoring
    dataset_scores = _score_from_datasets(symptoms)

    # Step 2: ML model scoring (ensemble boost)
    ml_scores = _score_from_ml_model(symptoms)

    # Step 3: Combine scores (70% dataset, 30% ML)
    combined = _combine_scores(dataset_scores, ml_scores)

    # Step 4: Apply severity modifier
    if severity and severity in SEVERITY_MULTIPLIER:
        mult = SEVERITY_MULTIPLIER[severity]
        for disease in combined:
            combined[disease] = min(combined[disease] * mult, 1.0)

    # Step 5: Apply duration modifier
    if duration:
        dur_mult = _get_duration_multiplier(duration)
        for disease in combined:
            combined[disease] = min(combined[disease] * dur_mult, 1.0)

    # Step 6: Sort and return Top N
    ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)
    results = []
    for disease, confidence in ranked[:top_n]:
        if confidence < 0.05:
            continue

        info = _DISEASE_INFO.get(disease, {})
        weights = _SYMPTOM_WEIGHTS.get(disease, {})
        matching = [s for s in symptoms if s in weights]

        results.append({
            "disease": disease,
            "confidence": round(confidence, 3),
            "confidence_pct": f"{round(confidence * 100)}%",
            "matching_symptoms": matching if matching else symptoms,
            "description": info.get("description", ""),
            "precautions": info.get("precautions", []),
            "severity_level": info.get("severity", "moderate"),
        })

    # Always return at least some results
    if not results and symptoms:
        results = _fallback_predict(symptoms, top_n)

    # Step 7: Cache results in Redis
    if results:
        redis_service.set_prediction_cache(symptoms, results, ttl=PREDICTION_CACHE_TTL)
        log_prediction(
            logger,
            symptoms=symptoms,
            prediction_cache_hit=False,
            disease=results[0]["disease"],
            confidence=results[0]["confidence"],
        )

    return results


def _score_from_datasets(symptoms: list[str]) -> dict[str, float]:
    """Score diseases using symptom weight datasets."""
    scores: dict[str, float] = {}

    for disease, disease_weights in _SYMPTOM_WEIGHTS.items():
        if disease.startswith("_"):
            continue

        total_weight = sum(disease_weights.values())
        if total_weight == 0:
            continue

        # Calculate weighted overlap
        matched_weight = 0.0
        match_count = 0
        for symptom in symptoms:
            if symptom in disease_weights:
                matched_weight += disease_weights[symptom]
                match_count += 1

        if match_count == 0:
            continue

        # Scoring factors:
        # 1. Weighted symptom overlap (what % of disease weight is matched)
        overlap_score = matched_weight / total_weight

        # 2. Coverage penalty (if user has symptoms not in this disease)
        coverage = match_count / max(len(symptoms), 1)

        # 3. Minimum symptoms threshold (at least 1 key symptom needed)
        # Higher weight for more matching symptoms
        match_bonus = min(match_count / 3, 1.0)  # saturates at 3

        # Combined score
        score = (overlap_score * 0.50) + (coverage * 0.25) + (match_bonus * 0.25)

        # Boost if matching a high-weight symptom (pathognomonic)
        max_matched_weight = max((disease_weights.get(s, 0) for s in symptoms), default=0)
        if max_matched_weight >= 0.90:
            score *= 1.15

        scores[disease] = min(score, 1.0)

    return scores


def _score_from_ml_model(symptoms: list[str]) -> dict[str, float]:
    """Get scores from the trained ML model."""
    try:
        from services.ml_engine import MLEngine
        model_dir = os.path.join(_BASE, "models")
        engine = MLEngine(model_dir)
        if engine.is_loaded:
            results = engine.predict(symptoms, top_n=10)
            return {r["disease"]: r["confidence"] for r in results}
    except Exception as e:
        logger.debug("ML model unavailable: %s", e)
    return {}


def _combine_scores(dataset_scores: dict, ml_scores: dict) -> dict[str, float]:
    """Combine dataset and ML scores. 70% dataset, 30% ML."""
    all_diseases = set(dataset_scores.keys()) | set(ml_scores.keys())
    combined = {}

    for disease in all_diseases:
        ds = dataset_scores.get(disease, 0)
        ml = ml_scores.get(disease, 0)

        if ds > 0 and ml > 0:
            # Both agree — stronger signal
            combined[disease] = (ds * 0.65) + (ml * 0.35)
        elif ds > 0:
            combined[disease] = ds * 0.85
        elif ml > 0:
            combined[disease] = ml * 0.70
        else:
            combined[disease] = 0

    return combined


def _get_duration_multiplier(duration: str) -> float:
    """Get duration-based score modifier."""
    lower = duration.lower()
    for keyword, mult in DURATION_BOOST.items():
        if keyword in lower:
            return mult
    return 1.0


def _fallback_predict(symptoms: list[str], top_n: int) -> list[dict]:
    """Simple rule-based fallback if both dataset and ML are empty."""
    RULES = {
        "Common Cold": ["continuous_sneezing", "cough", "throat_irritation", "headache", "fatigue", "runny_nose", "congestion", "chills", "mild_fever"],
        "Influenza": ["high_fever", "cough", "body_ache", "fatigue", "headache", "chills", "sweating", "muscle_pain", "joint_pain"],
        "Gastroenteritis": ["nausea", "vomiting", "diarrhoea", "abdominal_pain", "stomach_pain", "fatigue", "loss_of_appetite"],
        "Migraine": ["headache", "nausea", "blurred_and_distorted_vision", "visual_disturbances"],
        "Hypertension": ["headache", "chest_pain", "breathlessness", "high_bp", "fatigue"],
        "COVID-19": ["cough", "high_fever", "fatigue", "breathlessness", "headache", "loss_of_smell", "body_ache"],
        "Dengue": ["high_fever", "headache", "body_ache", "joint_pain", "skin_rash", "fatigue", "muscle_pain", "red_spots_over_body"],
        "Malaria": ["high_fever", "chills", "sweating", "headache", "body_ache", "nausea", "vomiting", "fatigue"],
        "Diabetes": ["fatigue", "weight_loss", "excessive_hunger", "blurred_and_distorted_vision", "polyuria"],
        "Anxiety Disorder": ["anxiety", "restlessness", "insomnia", "palpitations", "breathlessness", "fatigue"],
    }

    scores = []
    for disease, disease_symptoms in RULES.items():
        matched = [s for s in symptoms if s in disease_symptoms]
        if matched:
            conf = len(matched) / len(disease_symptoms)
            info = _DISEASE_INFO.get(disease, {})
            scores.append({
                "disease": disease,
                "confidence": round(conf, 3),
                "confidence_pct": f"{round(conf * 100)}%",
                "matching_symptoms": matched,
                "description": info.get("description", ""),
                "precautions": info.get("precautions", []),
                "severity_level": info.get("severity", "moderate"),
            })

    scores.sort(key=lambda x: x["confidence"], reverse=True)
    return scores[:top_n]


def get_disease_info(disease_name: str) -> dict:
    """Get full disease info including description, precautions, severity."""
    return _DISEASE_INFO.get(disease_name, {})
