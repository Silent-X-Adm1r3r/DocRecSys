"""
Advanced Symptom Extractor — NLP-powered extraction of symptoms,
duration, severity, and negation from natural language input.
Uses expanded vocabulary, synonym mapping, and fuzzy matching.
"""
from __future__ import annotations
import re, os, json
from difflib import get_close_matches

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Load synonym mapping ────────────────────────────────────────────
_SYNONYMS: dict[str, str] = {}
_syn_path = os.path.join(_BASE, "data", "symptom_synonyms.json")
if os.path.exists(_syn_path):
    with open(_syn_path, "r", encoding="utf-8") as f:
        _SYNONYMS = json.load(f)

# ── Canonical symptom vocabulary (these match the ML model's feature names) ──
SYMPTOM_VOCAB = [
    "itching","skin_rash","nodal_skin_eruptions","continuous_sneezing","shivering",
    "chills","joint_pain","stomach_pain","acidity","ulcers_on_tongue",
    "muscle_wasting","vomiting","burning_micturition","spotting_urination","fatigue",
    "weight_gain","anxiety","cold_hands_and_feets","mood_swings","weight_loss",
    "restlessness","lethargy","patches_in_throat","irregular_sugar_level","cough",
    "high_fever","sunken_eyes","breathlessness","sweating","dehydration",
    "indigestion","headache","yellowish_skin","dark_urine","nausea",
    "loss_of_appetite","pain_behind_the_eyes","back_pain","constipation","abdominal_pain",
    "diarrhoea","mild_fever","yellow_urine","yellowing_of_eyes","acute_liver_failure",
    "fluid_overload","swelling_of_stomach","swelled_lymph_nodes","malaise","blurred_and_distorted_vision",
    "phlegm","throat_irritation","redness_of_eyes","sinus_pressure","runny_nose",
    "congestion","chest_pain","weakness_in_limbs","fast_heart_rate","excessive_hunger",
    "extra_marital_contacts","drying_and_tingling_lips","slurred_speech","knee_pain","hip_joint_pain",
    "muscle_weakness","stiff_neck","swelling_joints","movement_stiffness","spinning_movements",
    "loss_of_balance","unsteadiness","weakness_of_one_body_side","loss_of_smell","bladder_discomfort",
    "foul_smell_of_urine","continuous_feel_of_urine","passage_of_gases","internal_itching","toxic_look_typhos",
    "depression","irritability","muscle_pain","altered_sensorium","red_spots_over_body",
    "belly_pain","abnormal_menstruation","dischromic_patches","watering_from_eyes","increased_appetite",
    "polyuria","family_history","mucoid_sputum","rusty_sputum","lack_of_concentration",
    "visual_disturbances","receiving_blood_transfusion","receiving_unsterile_injections","coma","stomach_bleeding",
    "distention_of_abdomen","history_of_alcohol_consumption","blood_in_sputum","prominent_veins_on_calf",
    "palpitations","painful_walking","pus_filled_pimples","blackheads","scurring",
    "skin_peeling","silver_like_dusting","small_dents_in_nails","inflammatory_nails","blister",
    "red_sore_around_nose","yellow_crust_ooze","prognosis","swollen_legs","swollen_blood_vessels",
    "puffy_face_and_eyes","enlarged_thyroid","brittle_nails","swollen_extremeties",
    "obesity","ear_pain","neck_pain","bruising","hair_loss",
    "loss_of_consciousness","seizure","high_bp","low_bp","body_ache",
    "skin_darkening","numbness","tingling","insomnia","acne","bloody_stool",
]

# Human-readable display names
DISPLAY_NAMES = {s: s.replace("_", " ").title() for s in SYMPTOM_VOCAB}

# Negation words
NEGATION_WORDS = {"no", "not", "don't", "dont", "doesn't", "doesnt", "without", "never", "haven't", "havent", "isn't", "isnt", "none", "nor"}

def extract_symptoms(text: str) -> list[str]:
    """Return deduplicated list of canonical symptom names found in text."""
    lower = text.lower()
    found: set[str] = set()
    negated: set[str] = set()

    # Check negation patterns
    neg_pattern = re.compile(r'\b(' + '|'.join(NEGATION_WORDS) + r')\b\s+(\w[\w\s]{2,30})')
    neg_matches = neg_pattern.findall(lower)
    neg_context = " ".join(m[1] for m in neg_matches)

    # 1. Check synonyms (longest first)
    for alias, canonical in sorted(_SYNONYMS.items(), key=lambda x: -len(x[0])):
        if alias in lower:
            if canonical.startswith("_emergency"):
                continue  # handled by triage
            # Check negation
            if _is_negated(alias, lower):
                negated.add(canonical)
            else:
                found.add(canonical)

    # 2. Check canonical vocab (as space-separated form)
    for symptom in sorted(SYMPTOM_VOCAB, key=len, reverse=True):
        readable = symptom.replace("_", " ")
        if readable in lower or symptom in lower:
            if _is_negated(readable, lower):
                negated.add(symptom)
            else:
                found.add(symptom)

    # 3. Fuzzy matching for typos (only if few matches found)
    if len(found) < 2:
        words = re.findall(r'\b\w{4,}\b', lower)
        readable_symptoms = [s.replace("_", " ") for s in SYMPTOM_VOCAB]
        for word in words:
            matches = get_close_matches(word, readable_symptoms, n=1, cutoff=0.8)
            if matches:
                canonical = matches[0].replace(" ", "_")
                if canonical not in negated:
                    found.add(canonical)

    # Remove negated
    found -= negated
    return list(found)

def _is_negated(phrase: str, text: str) -> bool:
    """Check if a phrase is preceded by a negation word."""
    idx = text.find(phrase)
    if idx < 0:
        return False
    prefix = text[max(0, idx-20):idx].strip()
    return any(prefix.endswith(neg) or f" {neg}" in prefix for neg in NEGATION_WORDS)

def extract_duration(text: str) -> str | None:
    """Extract duration mention from text."""
    match = re.search(r'(\d+)\s*(day|days|week|weeks|month|months|hour|hours|year|years)', text, re.IGNORECASE)
    if match:
        return f"{match.group(1)} {match.group(2).lower()}"
    qualitative = [
        "long time", "few days", "a week", "recently", "just started",
        "since morning", "since yesterday", "since last week", "since last month",
        "couple of days", "a few hours", "for weeks", "past few days",
        "on and off", "intermittent", "chronic", "persistent",
    ]
    for kw in sorted(qualitative, key=len, reverse=True):
        if kw in text.lower():
            return kw
    return None

def extract_severity(text: str) -> str | None:
    """Extract severity level from text."""
    lower = text.lower()
    severe = ["severe", "very bad", "intense", "extreme", "unbearable", "terrible", "worst", "excruciating", "agonizing", "critical", "sharp", "stabbing", "crushing"]
    moderate = ["moderate", "medium", "somewhat", "noticeable", "considerable", "significant", "bothersome"]
    mild = ["mild", "slight", "little", "minor", "faint", "dull", "subtle", "barely"]

    if any(w in lower for w in severe):
        return "severe"
    if any(w in lower for w in moderate):
        return "moderate"
    if any(w in lower for w in mild):
        return "mild"
    return None

def get_display_name(symptom: str) -> str:
    """Get human-readable name for a canonical symptom."""
    return DISPLAY_NAMES.get(symptom, symptom.replace("_", " ").title())
