"""
Emergency Service — Enhanced emergency and red-flag detection.
Emergency overrides ALL other workflows.
Red flags show warnings but continue recommendation flow.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

# ── Emergency patterns (single symptoms) ────────────────────────────
EMERGENCY_KEYWORDS = [
    "chest pain", "heart attack", "cardiac arrest",
    "breathing difficulty", "shortness of breath", "can't breathe", "cannot breathe", "choking",
    "unconscious", "unconsciousness", "not breathing", "stopped breathing",
    "severe bleeding", "heavy bleeding", "blood loss", "hemorrhage",
    "seizure", "seizures", "convulsion", "convulsions", "fits",
    "stroke", "paralysis", "paralyzed", "one side numb",
    "slurred speech", "can't speak", "difficulty speaking",
    "suicidal", "want to die", "kill myself", "end my life", "self harm",
    "hurting myself", "suicide",
    "severe allergic reaction", "anaphylaxis", "throat swelling",
    "poisoning", "overdose", "swallowed poison",
    "drowning", "electrocution", "severe burn", "severe burns",
    "head injury", "head trauma", "skull fracture",
    "stabbing", "gunshot", "gunshot wound",
    "snake bite", "dog bite",
    "high fever with confusion", "altered consciousness",
    "coughing blood", "vomiting blood",
    "facial drooping", "face drooping", "arm weakness", "sudden paralysis",
    "severe allergic", "swollen tongue", "difficulty swallowing",
]

# ── Dangerous combinations ──────────────────────────────────────────
DANGEROUS_COMBOS = [
    ({"chest pain", "breathlessness"}, 95, "CRITICAL", "Possible cardiac emergency"),
    ({"chest pain", "can't breathe"}, 95, "CRITICAL", "Possible cardiac emergency"),
    ({"chest pain", "cant breathe"}, 95, "CRITICAL", "Possible cardiac emergency"),
    ({"chest pain", "cannot breathe"}, 95, "CRITICAL", "Possible cardiac emergency"),
    ({"chest pain", "shortness of breath"}, 95, "CRITICAL", "Possible cardiac emergency"),
    ({"chest pain", "breathing difficulty"}, 95, "CRITICAL", "Possible cardiac emergency"),
    ({"chest pain", "sweating", "nausea"}, 95, "CRITICAL", "Heart attack warning signs"),
    ({"high fever", "confusion"}, 90, "CRITICAL", "Severe infection or meningitis risk"),
    ({"high fever", "stiff neck", "headache"}, 90, "CRITICAL", "Possible meningitis"),
    ({"severe headache", "slurred speech"}, 90, "CRITICAL", "Possible stroke"),
    ({"headache", "weakness of one body side"}, 90, "CRITICAL", "Possible stroke"),
    ({"facial drooping", "arm weakness"}, 95, "CRITICAL", "Stroke — FAST protocol"),
    ({"breathing difficulty", "chest pain"}, 85, "URGENT", "Cardiopulmonary emergency"),
    ({"high fever", "rash", "body ache"}, 75, "HIGH", "Possible dengue/meningococcal"),
    ({"severe abdominal pain", "vomiting"}, 70, "HIGH", "Possible surgical emergency"),
    ({"seizure", "high fever"}, 85, "URGENT", "Febrile seizure"),
    ({"vomiting blood", "abdominal pain"}, 85, "URGENT", "GI hemorrhage"),
    ({"severe headache", "vision loss"}, 80, "URGENT", "Possible stroke or intracranial bleed"),
    ({"breathlessness", "swollen tongue"}, 90, "CRITICAL", "Anaphylaxis"),
]

# ── Red flag symptoms (warning but continue) ────────────────────────
RED_FLAG_KEYWORDS = [
    "blood in stool", "bloody stool", "rectal bleeding",
    "blood in urine", "hematuria",
    "unexplained weight loss", "losing weight rapidly",
    "persistent cough", "chronic cough", "coughing for weeks",
    "severe recurring headaches", "worst headache ever",
    "lump", "unusual lump", "growing lump",
    "night sweats", "persistent night sweats",
    "difficulty swallowing", "dysphagia",
    "persistent fatigue", "extreme tiredness",
    "persistent fever", "fever for weeks",
]

# ── India emergency numbers ─────────────────────────────────────────
EMERGENCY_NUMBERS = {
    "general": "112",
    "ambulance": "108",
    "mental_health": "1800-599-0019 (NIMHANS iCall)",
    "women": "181",
    "poison": "1800-11-6117",
}

MENTAL_HEALTH_KEYWORDS = [
    "suicidal", "want to die", "kill myself", "end my life",
    "self harm", "hurting myself", "suicide", "no reason to live",
    "better off dead", "cutting myself",
]


def check_emergency(text: str) -> dict | None:
    """
    Check for emergency indicators.
    Returns None if safe, or dict with level, score, message, numbers.
    This OVERRIDES all other workflows.
    """
    lower = text.lower()

    # Mental health emergency (highest priority)
    if any(kw in lower for kw in MENTAL_HEALTH_KEYWORDS):
        return {
            "level": "CRITICAL",
            "score": 100,
            "type": "mental_health",
            "message": _mental_health_message(),
            "numbers": EMERGENCY_NUMBERS,
        }

    # Check dangerous combinations
    for combo_set, score, level, reason in DANGEROUS_COMBOS:
        if all(kw in lower for kw in combo_set):
            return {
                "level": level,
                "score": score,
                "type": "combination",
                "reason": reason,
                "message": _emergency_message(level, reason),
                "numbers": EMERGENCY_NUMBERS,
            }

    # Check single emergency keywords
    for kw in EMERGENCY_KEYWORDS:
        if kw in lower:
            score = _keyword_severity(kw)
            level = _score_to_level(score)
            return {
                "level": level,
                "score": score,
                "type": "keyword",
                "trigger": kw,
                "message": _emergency_message(level, kw),
                "numbers": EMERGENCY_NUMBERS,
            }

    return None


def check_red_flags(text: str, symptoms: list[str] = None) -> list[dict]:
    """
    Check for red-flag symptoms that warrant a warning but don't override flow.
    Returns list of red flag warnings.
    """
    lower = text.lower()
    flags = []

    for kw in RED_FLAG_KEYWORDS:
        if kw in lower:
            flags.append({
                "flag": kw,
                "message": _red_flag_message(kw),
                "severity": "warning",
            })

    # Also check extracted symptoms for red flags
    if symptoms:
        symptom_red_flags = {"bloody_stool", "blood_in_sputum", "loss_of_consciousness", "seizure"}
        for s in symptoms:
            if s in symptom_red_flags and not any(f["flag"] == s for f in flags):
                flags.append({
                    "flag": s.replace("_", " "),
                    "message": _red_flag_message(s.replace("_", " ")),
                    "severity": "warning",
                })

    return flags


def _keyword_severity(kw: str) -> int:
    """Assign severity score to individual keywords."""
    critical = {"heart attack", "cardiac arrest", "not breathing", "stopped breathing",
                "unconscious", "unconsciousness", "anaphylaxis", "poisoning", "overdose",
                "stroke", "drowning", "electrocution", "gunshot", "stabbing",
                "facial drooping", "sudden paralysis"}
    urgent = {"seizure", "seizures", "severe bleeding", "heavy bleeding", "hemorrhage",
              "coughing blood", "vomiting blood", "head injury", "head trauma",
              "severe burn", "snake bite", "paralysis", "choking", "arm weakness"}
    high = {"chest pain", "breathing difficulty", "shortness of breath",
            "severe allergic reaction", "high fever with confusion", "slurred speech",
            "difficulty swallowing", "swollen tongue"}
    if kw in critical:
        return 95
    if kw in urgent:
        return 80
    if kw in high:
        return 70
    return 60


def _score_to_level(score: int) -> str:
    if score >= 90:
        return "CRITICAL"
    if score >= 75:
        return "URGENT"
    if score >= 60:
        return "HIGH"
    return "MODERATE"


def _emergency_message(level: str, reason: str) -> str:
    if level == "CRITICAL":
        return (
            f"🚨 **CRITICAL EMERGENCY ALERT** 🚨\n\n"
            f"**Detected: {reason}**\n\n"
            f"This requires **IMMEDIATE emergency medical attention**.\n\n"
            f"📞 **Call 112 (Emergency)** or **108 (Ambulance)** NOW\n\n"
            f"⚠️ Do NOT wait — every second counts.\n\n"
            f"While waiting for help:\n"
            f"• Keep the person calm and still\n"
            f"• Do not give food or water\n"
            f"• If unconscious, place in recovery position"
        )
    if level == "URGENT":
        return (
            f"🔴 **URGENT MEDICAL ALERT** 🔴\n\n"
            f"**Detected: {reason}**\n\n"
            f"Please seek **emergency medical care within the next hour**.\n\n"
            f"📞 Call **108** for an ambulance or go to the nearest Emergency Room.\n\n"
            f"This situation may rapidly worsen without medical intervention."
        )
    return (
        f"⚠️ **HIGH PRIORITY MEDICAL ALERT** ⚠️\n\n"
        f"**Detected: {reason}**\n\n"
        f"Please **consult a doctor as soon as possible today**.\n\n"
        f"📞 If symptoms worsen, call **112** or visit the nearest hospital."
    )


def _mental_health_message() -> str:
    return (
        "💙 **You are not alone. Help is available right now.** 💙\n\n"
        "If you or someone you know is in crisis, please reach out:\n\n"
        "📞 **NIMHANS Helpline:** 1800-599-0019 (Free, 24/7)\n"
        "📞 **iCall:** 9152987821\n"
        "📞 **Vandrevala Foundation:** 1860-2662-345 (24/7)\n"
        "📞 **Emergency:** 112\n\n"
        "You matter. Please talk to someone. 🙏"
    )


def _red_flag_message(flag: str) -> str:
    return (
        f"⚠️ **Medical Attention Advised** — '{flag}' may require "
        f"further investigation by a healthcare professional. "
        f"Please consult a doctor for proper evaluation."
    )
