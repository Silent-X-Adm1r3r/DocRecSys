"""
Follow-Up Question Service — Context-aware follow-up questions.
Only asks for genuinely MISSING information.
Rules:
  1. Maximum 3 follow-up questions per session.
  2. One question at a time.
  3. Never ask for information already in the session.
  4. Stop once required info (symptoms + duration + severity) is present.
  5. After 3 questions, proceed with available data.
"""
from __future__ import annotations
import json, os, logging

logger = logging.getLogger(__name__)

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_QUESTIONS: dict = {}

# Load follow-up question mappings
_questions_path = os.path.join(_BASE, "data", "followup_questions.json")
if os.path.exists(_questions_path):
    with open(_questions_path, "r", encoding="utf-8") as f:
        _QUESTIONS = json.load(f)

# Symptom-to-category mapping
_SYMPTOM_CATEGORIES = {
    "headache": "headache", "head_pain": "headache", "migraine": "headache",
    "chest_pain": "chest_pain", "chest_tightness": "chest_pain",
    "abdominal_pain": "abdominal_pain", "stomach_pain": "abdominal_pain", "belly_pain": "abdominal_pain",
    "high_fever": "fever", "mild_fever": "fever",
    "breathlessness": "breathing", "cough": "breathing", "phlegm": "breathing",
    "skin_rash": "skin", "itching": "skin", "acne": "skin", "skin_peeling": "skin",
    "joint_pain": "joint_pain", "knee_pain": "joint_pain", "hip_joint_pain": "joint_pain",
    "back_pain": "joint_pain", "neck_pain": "joint_pain",
    "vomiting": "digestive", "nausea": "digestive", "diarrhoea": "digestive",
    "indigestion": "digestive", "acidity": "digestive", "constipation": "digestive",
    "anxiety": "mental_health", "depression": "mental_health", "insomnia": "mental_health",
    "burning_micturition": "urinary", "bladder_discomfort": "urinary",
    "blurred_and_distorted_vision": "eye", "visual_disturbances": "eye",
}


def should_ask_followup(
    symptoms: list[str],
    completeness: float,
    followup_count: int,
    max_followups: int = 3,
    session: dict | None = None,
) -> dict | None:
    """
    Determine if a follow-up question should be asked.
    Returns question dict or None if no follow-up needed.

    Context-aware: checks session for existing data and only asks
    for genuinely missing fields.
    """
    # Rule: after max questions, proceed with available data
    if followup_count >= max_followups:
        return None

    # Rule: if completeness is sufficient, no follow-up
    if completeness >= 0.70:
        return None

    # Rule: no symptoms at all → ask for symptoms
    if not symptoms:
        return {
            "type": "more_symptoms",
            "question": (
                "I wasn't able to identify specific symptoms from that. "
                "Could you describe what you're feeling in more detail? "
                'For example: "I have a headache, fever, and body ache."'
            ),
        }

    # Context-aware: check what's missing from session
    if session:
        has_duration = bool(session.get("duration"))
        has_severity = bool(session.get("severity"))

        # Only ask for what's genuinely missing
        if not has_duration and not has_severity:
            # Ask for duration first (more important for diagnosis)
            return {
                "type": "duration",
                "question": "How long have you been experiencing these symptoms?",
            }
        elif not has_duration:
            return {
                "type": "duration",
                "question": "How long have you been experiencing these symptoms?",
            }
        elif not has_severity:
            return {
                "type": "severity",
                "question": "How severe are the symptoms — mild, moderate, or severe?",
            }

        # Both duration and severity present — try symptom-specific question
        category = _get_primary_category(symptoms)
        question = _get_next_question(category, followup_count, symptoms)
        if question:
            return question

        # All required info present
        return None

    # No session context — use generic fallback based on count
    return _get_generic_followup(symptoms, followup_count)


def _get_primary_category(symptoms: list[str]) -> str:
    """Determine the primary symptom category."""
    category_counts: dict[str, int] = {}
    for symptom in symptoms:
        cat = _SYMPTOM_CATEGORIES.get(symptom, "general")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    if not category_counts:
        return "general"
    return max(category_counts, key=category_counts.get)


def _get_next_question(category: str, followup_count: int, symptoms: list[str]) -> dict | None:
    """Get the next appropriate follow-up question for a category."""
    cat_questions = _QUESTIONS.get(category, _QUESTIONS.get("general", {}))
    questions_list = cat_questions.get("questions", [])

    if followup_count >= len(questions_list):
        return None

    q = questions_list[followup_count]
    return {
        "type": q.get("type", "more_symptoms"),
        "question": q["question"],
    }


def _get_generic_followup(symptoms: list[str], count: int) -> dict | None:
    """Generate generic follow-up based on what info is missing."""
    if count == 0:
        return {
            "type": "duration",
            "question": "How long have you been experiencing these symptoms?",
        }
    elif count == 1:
        return {
            "type": "severity",
            "question": "How severe are your symptoms — mild, moderate, or severe?",
        }
    elif count == 2:
        return {
            "type": "more_symptoms",
            "question": "Are there any other symptoms you're experiencing that you haven't mentioned?",
        }
    return None
