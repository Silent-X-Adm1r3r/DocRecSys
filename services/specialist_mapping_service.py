"""
Specialist Mapping Service — Centralized disease-to-specialist mapping
with rarity classification and search helper utilities.
"""
from __future__ import annotations
import logging
from services.mongodb import get_specialist_for_disease as _mongo_get

logger = logging.getLogger(__name__)

# ── Comprehensive Disease → Specialist Mapping ──────────────────────
DISEASE_TO_SPECIALIST = {
    # General Physician
    "Common Cold": "General Physician",
    "Influenza": "General Physician",
    "Dengue": "General Physician",
    "Typhoid": "General Physician",
    "Malaria": "General Physician",
    "Chicken Pox": "General Physician",
    "Drug Reaction": "General Physician",
    "Allergy": "General Physician",
    "Dimorphic Hemorrhoids (Piles)": "General Physician",
    "Anemia": "General Physician",
    "Viral Fever": "General Physician",

    # Cardiology
    "Hypertension": "Cardiologist",
    "Heart Attack": "Cardiologist",
    "Heart Disease": "Cardiologist",
    "Varicose Veins": "Cardiologist",

    # Neurology
    "Migraine": "Neurologist",
    "Paralysis (Brain Hemorrhage)": "Neurologist",
    "Epilepsy": "Neurologist",

    # Pulmonology
    "COVID-19": "Pulmonologist",
    "Pneumonia": "Pulmonologist",
    "Bronchial Asthma": "Pulmonologist",
    "Tuberculosis": "Pulmonologist",

    # Gastroenterology
    "Gastroenteritis": "Gastroenterologist",
    "Jaundice": "Gastroenterologist",
    "GERD": "Gastroenterologist",
    "Chronic Cholestasis": "Gastroenterologist",
    "Peptic Ulcer Disease": "Gastroenterologist",
    "Hepatitis A": "Gastroenterologist",
    "Hepatitis B": "Gastroenterologist",
    "Hepatitis C": "Gastroenterologist",
    "Hepatitis D": "Gastroenterologist",
    "Hepatitis E": "Gastroenterologist",
    "Alcoholic Hepatitis": "Gastroenterologist",
    "Irritable Bowel Syndrome": "Gastroenterologist",

    # Endocrinology
    "Diabetes": "Endocrinologist",
    "Hypothyroidism": "Endocrinologist",
    "Hyperthyroidism": "Endocrinologist",
    "Hypoglycemia": "Endocrinologist",

    # Dermatology
    "Fungal infection": "Dermatologist",
    "Acne": "Dermatologist",
    "Psoriasis": "Dermatologist",
    "Impetigo": "Dermatologist",

    # Rheumatology
    "Arthritis": "Rheumatologist",
    "Rheumatoid Arthritis": "Rheumatologist",

    # Orthopedics
    "Cervical Spondylosis": "Orthopedic Surgeon",
    "Osteoarthritis": "Orthopedic Surgeon",

    # Urology
    "Urinary Tract Infection": "Urologist",
    "Kidney Stones": "Urologist",

    # Nephrology
    "Chronic Kidney Disease": "Nephrologist",

    # ENT
    "Allergic Rhinitis": "ENT Specialist",
    "Vertigo": "ENT Specialist",

    # Psychiatry
    "Anxiety Disorder": "Psychiatrist",
    "Depression": "Psychiatrist",

    # Infectious Disease
    "AIDS": "Infectious Disease Specialist",

    # Oncology
    "Cancer": "Oncologist",
}


# ── Specialist Rarity Classification ────────────────────────────────
RARE_SPECIALISTS = {
    "Neurologist", "Endocrinologist", "Rheumatologist", "Oncologist",
    "Nephrologist", "Infectious Disease Specialist",
}

COMMON_SPECIALISTS = {
    "Dermatologist", "Gastroenterologist", "Pulmonologist", "Cardiologist",
    "Orthopedic Surgeon", "Urologist", "ENT Specialist", "Psychiatrist",
}

GENERAL_SPECIALISTS = {
    "General Physician",
}


def get_specialist(disease: str) -> str:
    """Get the recommended specialist for a disease."""
    # Try MongoDB first (may have custom mappings)
    spec = _mongo_get(disease)
    if spec and spec != "General Physician":
        return spec
    return DISEASE_TO_SPECIALIST.get(disease, "General Physician")


def get_specialist_rarity(specialist: str) -> str:
    """Classify specialist rarity: 'rare', 'common', or 'general'."""
    if specialist in RARE_SPECIALISTS:
        return "rare"
    if specialist in COMMON_SPECIALISTS:
        return "common"
    return "general"


def get_search_radius(specialist: str) -> int:
    """Get search radius in km based on specialist rarity."""
    from config import RADIUS_GENERAL, RADIUS_COMMON, RADIUS_RARE
    rarity = get_specialist_rarity(specialist)
    if rarity == "rare":
        return RADIUS_RARE
    if rarity == "common":
        return RADIUS_COMMON
    return RADIUS_GENERAL


def get_fallback_queries(specialist: str) -> list[str]:
    """
    Generate a fallback search query chain for a specialist.
    Example: "Neurologist" → ["Neurologist", "Neurology Clinic",
             "Neurology Hospital", "Hospital", "Doctor"]
    """
    # Extract the specialty root (e.g., "Neurologist" → "Neurology")
    root = specialist
    if specialist.endswith("ist"):
        root = specialist[:-3]  # Neurologist → Neurolog
        # Fix common suffixes
        if root.endswith("log"):
            root = root + "y"  # Neurolog → Neurology
        elif root.endswith("iat"):
            root = root[:-3] + "iatry"  # Psychiatr → Psychiatry
        elif root.endswith("trist"):
            root = root[:-5] + "try"
    elif specialist.endswith("geon"):
        root = specialist.replace("Surgeon", "Surgery")
    elif specialist == "General Physician":
        return ["General Physician", "Family Doctor", "Clinic", "Hospital", "Doctor"]

    queries = [
        specialist,                      # "Neurologist"
        f"{root} Clinic",               # "Neurology Clinic"
        f"{root} Hospital",             # "Neurology Hospital"
        f"{specialist} near me",         # "Neurologist near me"
        "Hospital",                      # Generic hospital
        "Doctor",                        # Last resort
    ]

    # Deduplicate while preserving order
    seen = set()
    result = []
    for q in queries:
        q_lower = q.lower()
        if q_lower not in seen:
            seen.add(q_lower)
            result.append(q)
    return result
