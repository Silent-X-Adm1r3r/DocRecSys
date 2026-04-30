"""
Doctor Recommender — SQLite-backed with comprehensive disease-to-specialist
mapping and multi-factor ranking.
"""
from __future__ import annotations
from services.database import get_doctors

# Comprehensive disease → specialist mapping
DISEASE_TO_SPECIALIST: dict[str, str] = {
    "Common Cold": "General Physician",
    "Influenza": "General Physician",
    "COVID-19": "Pulmonologist",
    "Gastroenteritis": "Gastroenterologist",
    "Migraine": "Neurologist",
    "Hypertension": "Cardiologist",
    "Dengue": "General Physician",
    "Typhoid": "General Physician",
    "Urinary Tract Infection": "Urologist",
    "Pneumonia": "Pulmonologist",
    "Allergy": "General Physician",
    "Allergic Rhinitis": "ENT Specialist",
    "Malaria": "General Physician",
    "Jaundice": "Gastroenterologist",
    "Anxiety Disorder": "Psychiatrist",
    "Depression": "Psychiatrist",
    "Diabetes": "Endocrinologist",
    "Fungal infection": "Dermatologist",
    "GERD": "Gastroenterologist",
    "Chronic Cholestasis": "Gastroenterologist",
    "Drug Reaction": "General Physician",
    "Peptic Ulcer Disease": "Gastroenterologist",
    "AIDS": "Infectious Disease Specialist",
    "Bronchial Asthma": "Pulmonologist",
    "Cervical Spondylosis": "Orthopedic Surgeon",
    "Paralysis (Brain Hemorrhage)": "Neurologist",
    "Chicken Pox": "General Physician",
    "Hepatitis A": "Gastroenterologist",
    "Hepatitis B": "Gastroenterologist",
    "Hepatitis C": "Gastroenterologist",
    "Hepatitis D": "Gastroenterologist",
    "Hepatitis E": "Gastroenterologist",
    "Alcoholic Hepatitis": "Gastroenterologist",
    "Tuberculosis": "Pulmonologist",
    "Heart Attack": "Cardiologist",
    "Varicose Veins": "Cardiologist",
    "Hypothyroidism": "Endocrinologist",
    "Hyperthyroidism": "Endocrinologist",
    "Hypoglycemia": "Endocrinologist",
    "Osteoarthritis": "Orthopedic Surgeon",
    "Arthritis": "Rheumatologist",
    "Vertigo": "ENT Specialist",
    "Acne": "Dermatologist",
    "Psoriasis": "Dermatologist",
    "Impetigo": "Dermatologist",
    "Dimorphic Hemorrhoids (Piles)": "General Physician",
    "Epilepsy": "Neurologist",
    "Kidney Stones": "Nephrologist",
    "Chronic Kidney Disease": "Nephrologist",
    "Irritable Bowel Syndrome": "Gastroenterologist",
    "Anemia": "General Physician",
}


def get_specialist(disease: str) -> str:
    """Return the specialist type for a disease."""
    return DISEASE_TO_SPECIALIST.get(disease, "General Physician")


def recommend_doctors(disease: str, city: str | None = None) -> dict:
    """
    Return {
        specialist: str,
        doctors: [ { name, hospital, city, state, experience_years, rating, consultation_fee, available_days, phone } ]
    }
    """
    specialist = get_specialist(disease)
    doctors = get_doctors(specialist, city=city, limit=5)

    return {
        "specialist": specialist,
        "doctors": doctors,
    }
