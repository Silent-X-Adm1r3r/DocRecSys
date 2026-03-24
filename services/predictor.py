"""
Disease Predictor Service
Simulates a BERT-based prediction model using rule-based symptom→disease
mapping with weighted scoring.  Returns top-2 predictions filtered by a
confidence threshold.
"""

from __future__ import annotations

# ── Disease knowledge base ──────────────────────────────────────────
# Each disease maps to a dict of { symptom: weight }.
# Weights roughly represent how indicative that symptom is (0–1).

DISEASE_SYMPTOMS: dict[str, dict[str, float]] = {
    "Common Cold": {
        "cough": 0.7, "sneezing": 0.8, "runny nose": 0.9,
        "sore throat": 0.6, "headache": 0.3, "fatigue": 0.3,
        "watery eyes": 0.5, "fever": 0.3, "chills": 0.3,
    },
    "Influenza (Flu)": {
        "fever": 0.9, "cough": 0.7, "body ache": 0.8,
        "fatigue": 0.7, "headache": 0.6, "chills": 0.7,
        "sore throat": 0.4, "runny nose": 0.3, "sweating": 0.5,
        "muscle pain": 0.7, "loss of appetite": 0.4,
    },
    "COVID-19": {
        "fever": 0.8, "cough": 0.8, "fatigue": 0.7,
        "shortness of breath": 0.8, "body ache": 0.5,
        "sore throat": 0.5, "headache": 0.5, "loss of appetite": 0.5,
        "diarrhea": 0.3, "chills": 0.4,
    },
    "Gastroenteritis": {
        "nausea": 0.8, "vomiting": 0.9, "diarrhea": 0.9,
        "abdominal pain": 0.7, "stomach pain": 0.7,
        "fever": 0.4, "fatigue": 0.4, "loss of appetite": 0.5,
        "bloating": 0.4, "headache": 0.2,
    },
    "Migraine": {
        "headache": 0.95, "nausea": 0.6, "blurred vision": 0.6,
        "dizziness": 0.5, "fatigue": 0.3, "sensitivity to light": 0.7,
    },
    "Hypertension": {
        "headache": 0.5, "dizziness": 0.6, "blurred vision": 0.5,
        "chest pain": 0.4, "shortness of breath": 0.4,
        "palpitations": 0.5, "high blood pressure": 1.0,
        "fatigue": 0.3, "nausea": 0.2,
    },
    "Dengue Fever": {
        "fever": 0.9, "headache": 0.7, "body ache": 0.8,
        "joint pain": 0.8, "skin rash": 0.6, "fatigue": 0.6,
        "nausea": 0.5, "vomiting": 0.4, "muscle pain": 0.7,
        "loss of appetite": 0.5,
    },
    "Typhoid": {
        "fever": 0.9, "headache": 0.6, "abdominal pain": 0.7,
        "fatigue": 0.7, "loss of appetite": 0.6, "diarrhea": 0.5,
        "constipation": 0.4, "sweating": 0.4, "chills": 0.4,
    },
    "Urinary Tract Infection": {
        "frequent urination": 0.9, "abdominal pain": 0.5,
        "blood in urine": 0.7, "fever": 0.4, "back pain": 0.4,
        "dark urine": 0.6, "nausea": 0.3,
    },
    "Pneumonia": {
        "cough": 0.8, "fever": 0.8, "shortness of breath": 0.8,
        "chest pain": 0.7, "fatigue": 0.6, "chills": 0.6,
        "sweating": 0.5, "loss of appetite": 0.4,
        "body ache": 0.4, "headache": 0.3,
    },
    "Allergic Rhinitis": {
        "sneezing": 0.9, "runny nose": 0.8, "watery eyes": 0.8,
        "itching": 0.6, "sore throat": 0.3, "headache": 0.3,
        "fatigue": 0.2,
    },
    "Malaria": {
        "fever": 0.9, "chills": 0.8, "sweating": 0.7,
        "headache": 0.6, "body ache": 0.6, "nausea": 0.5,
        "vomiting": 0.5, "fatigue": 0.7, "joint pain": 0.4,
    },
    "Jaundice": {
        "yellow skin": 0.95, "dark urine": 0.8, "fatigue": 0.6,
        "nausea": 0.5, "abdominal pain": 0.5, "loss of appetite": 0.6,
        "fever": 0.3, "itching": 0.4, "vomiting": 0.3,
    },
    "Anxiety Disorder": {
        "anxiety": 0.9, "palpitations": 0.6, "insomnia": 0.7,
        "dizziness": 0.4, "sweating": 0.4, "fatigue": 0.5,
        "headache": 0.3, "nausea": 0.3, "numbness": 0.3,
        "shortness of breath": 0.3,
    },
    "Diabetes (Type 2)": {
        "frequent urination": 0.8, "fatigue": 0.6,
        "blurred vision": 0.5, "weight loss": 0.6,
        "numbness": 0.5, "tingling": 0.5, "loss of appetite": 0.3,
    },
}

# Severity multiplier
SEVERITY_MULTIPLIER = {"severe": 1.15, "moderate": 1.0, "mild": 0.9}

CONFIDENCE_THRESHOLD = 0.20  # ignore predictions below 20 %


def predict_diseases(
    symptoms: list[str],
    severity: str | None = None,
    duration: str | None = None,
) -> list[dict]:
    """
    Return up to 2 predictions sorted by confidence, each dict has:
        { "disease": str, "confidence": float }
    Confidence is 0-1.
    """
    if not symptoms:
        return []

    scores: dict[str, float] = {}

    for disease, symptom_weights in DISEASE_SYMPTOMS.items():
        total_weight = sum(symptom_weights.values())
        matched_weight = sum(
            symptom_weights[s] for s in symptoms if s in symptom_weights
        )
        if matched_weight == 0:
            continue
        raw_confidence = matched_weight / total_weight

        # Apply severity modifier
        if severity:
            raw_confidence *= SEVERITY_MULTIPLIER.get(severity, 1.0)

        # Clamp to 1.0
        scores[disease] = min(raw_confidence, 1.0)

    # Filter by threshold
    filtered = {d: c for d, c in scores.items() if c >= CONFIDENCE_THRESHOLD}
    if not filtered:
        return []

    # Sort descending and take top-2
    sorted_diseases = sorted(filtered.items(), key=lambda x: x[1], reverse=True)[:2]

    return [{"disease": d, "confidence": round(c, 2)} for d, c in sorted_diseases]
