"""
Triage & Emergency Alert Service
Provides confidence-level interpretation, triage suggestions,
and emergency keyword detection.
"""

from __future__ import annotations

# ── Emergency keywords ──────────────────────────────────────────────
EMERGENCY_KEYWORDS = [
    "chest pain", "breathing difficulty", "shortness of breath",
    "unconsciousness", "severe bleeding", "seizure",
    "heart attack", "stroke", "choking",
]

EMERGENCY_MESSAGE = (
    "🚨 **EMERGENCY ALERT** 🚨\n\n"
    "Based on your description, this may require **immediate medical attention**.\n\n"
    "**Please call emergency services or visit the nearest hospital immediately.**\n\n"
    "Do NOT wait — time is critical."
)


def check_emergency(text: str) -> bool:
    """Return True if the input contains emergency keywords."""
    lower = text.lower()
    return any(kw in lower for kw in EMERGENCY_KEYWORDS)


def interpret_confidence(confidence: float) -> str:
    """
    Map confidence to a human label.
        > 0.70 → Likely condition
        0.40–0.70 → Possible condition
        < 0.40 → Uncertain
    """
    if confidence > 0.70:
        return "Likely condition"
    if confidence >= 0.40:
        return "Possible condition"
    return "Uncertain — please consult a doctor"


def triage_suggestion(confidence: float, symptoms: list[str]) -> str:
    """
    Return a triage suggestion string based on confidence level and
    the presence of risky keywords.
    """
    # If any emergency keyword is present in symptoms, escalate
    risky = any(s in EMERGENCY_KEYWORDS for s in symptoms)
    if risky or confidence > 0.70:
        return "⚠️ Seek medical attention promptly"
    if confidence >= 0.40:
        return "🩺 Consult a doctor at your convenience"
    return "📋 Monitor your symptoms and rest"


def needs_followup(symptoms: list[str], confidence: float) -> dict | None:
    """
    Return a follow-up question dict if the input is too vague or
    confidence is low and we can refine.  Returns None if no follow-up
    is needed.
    """
    if len(symptoms) < 2:
        return {
            "type": "more_symptoms",
            "question": (
                "I'd like to give you a better assessment. "
                "Could you describe any other symptoms you're experiencing?"
            ),
        }
    if confidence < 0.40:
        return {
            "type": "duration",
            "question": "How long have you been experiencing these symptoms?",
        }
    if confidence < 0.55:
        return {
            "type": "severity",
            "question": "Would you say the symptoms are mild, moderate, or severe?",
        }
    return None
