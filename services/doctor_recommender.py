"""
Doctor Recommender Service
Maps predicted diseases to specialists and provides hardcoded sample
doctor data.  Supports optional city filtering.
"""

from __future__ import annotations

# Disease → specialist mapping
DISEASE_TO_SPECIALIST: dict[str, str] = {
    "Common Cold": "General Physician",
    "Influenza (Flu)": "General Physician",
    "COVID-19": "Pulmonologist",
    "Gastroenteritis": "Gastroenterologist",
    "Migraine": "Neurologist",
    "Hypertension": "Cardiologist",
    "Dengue Fever": "General Physician",
    "Typhoid": "General Physician",
    "Urinary Tract Infection": "Urologist",
    "Pneumonia": "Pulmonologist",
    "Allergic Rhinitis": "ENT Specialist",
    "Malaria": "General Physician",
    "Jaundice": "Gastroenterologist",
    "Anxiety Disorder": "Psychiatrist",
    "Diabetes (Type 2)": "Endocrinologist",
}

# Sample doctors keyed by specialist
DOCTORS_DB: dict[str, list[dict]] = {
    "General Physician": [
        {"name": "Dr. Ananya Sharma", "hospital": "Apollo Clinic", "city": "Mumbai", "contact": "+91-98765-43210"},
        {"name": "Dr. Rajesh Kumar", "hospital": "Fortis Hospital", "city": "Delhi", "contact": "+91-98765-43211"},
        {"name": "Dr. Priya Menon", "hospital": "Manipal Hospital", "city": "Bangalore", "contact": "+91-98765-43212"},
    ],
    "Pulmonologist": [
        {"name": "Dr. Vikram Patel", "hospital": "Medanta Hospital", "city": "Delhi", "contact": "+91-98765-43213"},
        {"name": "Dr. Sneha Reddy", "hospital": "KIMS Hospital", "city": "Hyderabad", "contact": "+91-98765-43214"},
        {"name": "Dr. Arjun Nair", "hospital": "Aster CMI", "city": "Bangalore", "contact": "+91-98765-43215"},
    ],
    "Gastroenterologist": [
        {"name": "Dr. Deepak Gupta", "hospital": "Max Hospital", "city": "Delhi", "contact": "+91-98765-43216"},
        {"name": "Dr. Kavitha Iyer", "hospital": "Global Hospital", "city": "Mumbai", "contact": "+91-98765-43217"},
        {"name": "Dr. Suresh Babu", "hospital": "Narayana Health", "city": "Bangalore", "contact": "+91-98765-43218"},
    ],
    "Neurologist": [
        {"name": "Dr. Anil Mehta", "hospital": "AIIMS", "city": "Delhi", "contact": "+91-98765-43219"},
        {"name": "Dr. Swati Joshi", "hospital": "Kokilaben Hospital", "city": "Mumbai", "contact": "+91-98765-43220"},
    ],
    "Cardiologist": [
        {"name": "Dr. Ramesh Chandra", "hospital": "Narayana Hrudayalaya", "city": "Bangalore", "contact": "+91-98765-43221"},
        {"name": "Dr. Pooja Saxena", "hospital": "Medanta Hospital", "city": "Delhi", "contact": "+91-98765-43222"},
        {"name": "Dr. Kiran Desai", "hospital": "Lilavati Hospital", "city": "Mumbai", "contact": "+91-98765-43223"},
    ],
    "Urologist": [
        {"name": "Dr. Manish Agarwal", "hospital": "Fortis Hospital", "city": "Delhi", "contact": "+91-98765-43224"},
        {"name": "Dr. Nithya Rajan", "hospital": "Apollo Hospital", "city": "Chennai", "contact": "+91-98765-43225"},
    ],
    "ENT Specialist": [
        {"name": "Dr. Harish Verma", "hospital": "Columbia Asia", "city": "Bangalore", "contact": "+91-98765-43226"},
        {"name": "Dr. Sunita Das", "hospital": "Hinduja Hospital", "city": "Mumbai", "contact": "+91-98765-43227"},
    ],
    "Psychiatrist": [
        {"name": "Dr. Alok Srivastava", "hospital": "NIMHANS", "city": "Bangalore", "contact": "+91-98765-43228"},
        {"name": "Dr. Meera Kapoor", "hospital": "Fortis Mental Health", "city": "Delhi", "contact": "+91-98765-43229"},
    ],
    "Endocrinologist": [
        {"name": "Dr. Sanjay Bhat", "hospital": "Manipal Hospital", "city": "Bangalore", "contact": "+91-98765-43230"},
        {"name": "Dr. Rekha Pillai", "hospital": "Apollo Hospital", "city": "Chennai", "contact": "+91-98765-43231"},
    ],
}


def get_specialist(disease: str) -> str:
    """Return the specialist type for a disease, or a default."""
    return DISEASE_TO_SPECIALIST.get(disease, "General Physician")


def recommend_doctors(
    disease: str,
    city: str | None = None,
) -> dict:
    """
    Return {
        "specialist": str,
        "doctors": [ { name, hospital, city, contact }, ... ]
    }
    """
    specialist = get_specialist(disease)
    doctors = DOCTORS_DB.get(specialist, DOCTORS_DB["General Physician"])

    if city:
        city_lower = city.strip().lower()
        filtered = [d for d in doctors if d["city"].lower() == city_lower]
        if filtered:
            doctors = filtered
        # If no match in city, return all doctors for that specialist

    return {
        "specialist": specialist,
        "doctors": doctors,
    }
