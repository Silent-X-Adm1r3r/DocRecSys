"""
Symptom Extractor Service
Extracts symptom keywords from natural-language user input using
vocabulary matching with fuzzy substring support.
"""

# Canonical symptom vocabulary (lowercase)
SYMPTOM_VOCAB = [
    "fever", "cough", "cold", "headache", "sore throat", "runny nose",
    "body ache", "fatigue", "nausea", "vomiting", "diarrhea",
    "chest pain", "shortness of breath", "breathing difficulty",
    "dizziness", "chills", "sweating", "loss of appetite",
    "weight loss", "weight gain", "joint pain", "muscle pain",
    "back pain", "abdominal pain", "stomach pain", "bloating",
    "constipation", "heartburn", "skin rash", "itching",
    "swelling", "numbness", "tingling", "blurred vision",
    "frequent urination", "blood in urine", "dark urine",
    "yellow skin", "sneezing", "watery eyes", "ear pain",
    "insomnia", "anxiety", "depression", "palpitations",
    "high blood pressure", "low blood pressure",
    "unconsciousness", "severe bleeding", "seizure",
]

# Aliases → canonical symptom
ALIASES = {
    "throwing up": "vomiting",
    "puking": "vomiting",
    "tummy ache": "abdominal pain",
    "stomach ache": "stomach pain",
    "belly pain": "abdominal pain",
    "can't sleep": "insomnia",
    "sleeplessness": "insomnia",
    "breathlessness": "shortness of breath",
    "hard to breathe": "breathing difficulty",
    "trouble breathing": "breathing difficulty",
    "heart racing": "palpitations",
    "feel dizzy": "dizziness",
    "feeling tired": "fatigue",
    "tiredness": "fatigue",
    "high temperature": "fever",
    "temperature": "fever",
    "running nose": "runny nose",
    "loose motions": "diarrhea",
    "loose stools": "diarrhea",
    "body pain": "body ache",
    "pain in joints": "joint pain",
    "pain in back": "back pain",
    "rash": "skin rash",
    "itchy": "itching",
    "scratch": "itching",
    "throat pain": "sore throat",
}


def extract_symptoms(text: str) -> list[str]:
    """Return a deduplicated list of canonical symptoms found in *text*."""
    lower = text.lower()
    found: set[str] = set()

    # Check aliases first (longer phrases before short ones)
    for alias, canonical in sorted(ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in lower:
            found.add(canonical)

    # Check canonical vocab (longer phrases first to avoid partial hits)
    for symptom in sorted(SYMPTOM_VOCAB, key=len, reverse=True):
        if symptom in lower:
            found.add(symptom)

    return list(found)


def extract_duration(text: str) -> str | None:
    """Try to pull a rough duration mention from the text."""
    import re
    match = re.search(
        r'(\d+)\s*(day|days|week|weeks|month|months|hour|hours)', text, re.IGNORECASE
    )
    if match:
        return f"{match.group(1)} {match.group(2).lower()}"
    # qualitative
    for kw in ["long time", "few days", "a week", "recently", "just started", "since morning", "since yesterday"]:
        if kw in text.lower():
            return kw
    return None


def extract_severity(text: str) -> str | None:
    """Try to pull severity from the text."""
    lower = text.lower()
    if any(w in lower for w in ["severe", "very bad", "intense", "extreme", "unbearable", "terrible", "worst"]):
        return "severe"
    if any(w in lower for w in ["moderate", "medium", "somewhat"]):
        return "moderate"
    if any(w in lower for w in ["mild", "slight", "little", "minor"]):
        return "mild"
    return None
