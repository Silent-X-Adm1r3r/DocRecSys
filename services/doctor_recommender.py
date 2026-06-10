"""
Doctor Recommender — Orchestrates specialist mapping, doctor search, and hospital search.
Geolocation is mandatory. Returns error when location is unavailable.
"""
from __future__ import annotations
import logging
from services.specialist_mapping_service import get_specialist, get_specialist_rarity
from services.doctor_search_service import search_doctors
from services.hospital_search_service import search_hospitals

logger = logging.getLogger(__name__)


def recommend_doctors(
    disease: str,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict:
    """
    Recommend doctors for a predicted disease.
    Geolocation (latitude, longitude) is MANDATORY.
    Returns error dict when location is unavailable.
    """
    # Enforce geolocation
    if not latitude or not longitude:
        return {
            "success": False,
            "error": "Unable to determine your location. Please enable location access and try again.",
            "specialist": get_specialist(disease),
            "doctors": [],
            "hospitals": [],
        }

    specialist = get_specialist(disease)
    rarity = get_specialist_rarity(specialist)

    logger.info(
        "Recommending doctors: disease=%s, specialist=%s, rarity=%s, lat=%.4f, lng=%.4f",
        disease, specialist, rarity, latitude, longitude,
    )

    doctors = search_doctors(
        specialist,
        lat=latitude,
        lng=longitude,
        limit=5,
    )

    if not doctors:
        return {
            "success": False,
            "error": "No nearby specialists found within the selected radius. Please try increasing the search radius.",
            "specialist": specialist,
            "specialist_rarity": rarity,
            "doctors": [],
            "hospitals": [],
            "user_location": {
                "latitude": latitude,
                "longitude": longitude,
            },
        }

    hospitals = search_hospitals(
        lat=latitude,
        lng=longitude,
        specialty=specialist,
        limit=5,
    )

    return {
        "success": True,
        "specialist": specialist,
        "specialist_rarity": rarity,
        "doctors": doctors,
        "hospitals": hospitals,
        "user_location": {
            "latitude": latitude,
            "longitude": longitude,
        },
    }


def recommend_emergency(
    lat: float | None = None,
    lng: float | None = None,
) -> dict:
    """Recommend emergency hospitals."""
    if not lat or not lng:
        return {
            "success": False,
            "error": "Location required for emergency hospital search.",
            "specialist": "Emergency Medicine",
            "doctors": [],
            "hospitals": [],
        }

    hospitals = search_hospitals(lat=lat, lng=lng, is_emergency=True, limit=5)
    return {
        "success": True,
        "specialist": "Emergency Medicine",
        "doctors": [],
        "hospitals": hospitals,
        "user_location": {"latitude": lat, "longitude": lng},
    }
