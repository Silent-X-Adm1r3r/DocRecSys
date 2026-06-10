"""
Hospital Search Service — Finds and ranks nearby hospitals.
Ranking: Distance → Rating → Review Count.
"""
from __future__ import annotations
import logging
from services import maps_service

logger = logging.getLogger(__name__)


def search_hospitals(
    lat: float | None = None,
    lng: float | None = None,
    specialty: str = "",
    is_emergency: bool = False,
    limit: int = 5,
) -> list[dict]:
    """Search for nearby hospitals, ranked by distance first."""
    if not lat or not lng or not maps_service.is_available():
        return []

    if is_emergency:
        results = maps_service.get_emergency_hospitals(lat, lng)
    else:
        keyword = f"{specialty} hospital" if specialty else "hospital"
        # Use progressive radius up to 50km for hospitals
        radii = [10, 25, 50]
        results = []
        for radius in radii:
            results = maps_service.search_nearby(lat, lng, keyword, radius_km=radius)
            if len(results) >= 3:
                break

    hospitals = []
    for place in results[:limit]:
        distance_km = place.get("distance_km", 0)
        hospital_type = "Emergency" if is_emergency else _classify_hospital(place.get("types", []))

        hospitals.append({
            "name": place.get("name", ""),
            "address": place.get("address", ""),
            "rating": place.get("rating", 0),
            "review_count": place.get("review_count", 0),
            "open_now": place.get("open_now"),
            "hospital_type": hospital_type,
            "distance_km": distance_km,
            "distance": f"{distance_km} km" if distance_km else "",
            "latitude": place.get("lat", 0),
            "longitude": place.get("lng", 0),
            "place_id": place.get("place_id", ""),
        })

    # Sort by distance → rating → reviews
    hospitals.sort(key=lambda h: (
        h.get("distance_km", 999),
        -(h.get("rating", 0) or 0),
        -(h.get("review_count", 0) or 0),
    ))

    return hospitals[:limit]


def _classify_hospital(types: list[str]) -> str:
    if "hospital" in types:
        return "Hospital"
    if "doctor" in types:
        return "Clinic"
    if "health" in types:
        return "Health Center"
    return "Medical Facility"
