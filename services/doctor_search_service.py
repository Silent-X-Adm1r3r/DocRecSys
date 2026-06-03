"""
Doctor Search Service — Finds specialist doctors using Google Maps as primary source.
Ranking: Distance → Rating → Review Count.
Static database is last-resort fallback.
"""
from __future__ import annotations
import logging
from services.database import get_doctors as get_db_doctors
from services import maps_service
from services.specialist_mapping_service import get_search_radius, get_fallback_queries

logger = logging.getLogger(__name__)


def search_doctors(
    specialist: str,
    lat: float | None = None,
    lng: float | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    Search for doctors. Google Maps is the primary source.
    Static database is used only when Maps API fails.

    Priority: Google Maps → Places API → Static dataset fallback
    Ranking:  Distance → Rating → Review Count
    """
    maps_doctors = []

    # Priority 1: Google Maps with fallback search chain
    if lat and lng and maps_service.is_available():
        radius_km = get_search_radius(specialist)
        fallback_queries = get_fallback_queries(specialist)

        results, query_used = maps_service.search_with_fallback(
            lat, lng,
            specialist=specialist,
            fallback_queries=fallback_queries,
            radius_km=radius_km,
            min_results=3,
            max_results=limit,
        )

        logger.info("Doctor search: query=%s, results=%d", query_used, len(results))

        for place in results[:limit]:
            # Try to get phone number from Place Details
            phone = ""
            details = maps_service.get_place_details(place.get("place_id", ""))
            if details:
                phone = details.get("phone", "")

            maps_doctors.append({
                "name": place.get("name", ""),
                "specialization": specialist,
                "hospital": place.get("address", ""),
                "rating": place.get("rating", 0),
                "review_count": place.get("review_count", 0),
                "reviews": place.get("review_count", 0),
                "distance_km": place.get("distance_km", 0),
                "address": place.get("address", ""),
                "phone": phone,
                "maps_url": place.get("maps_url", ""),
                "latitude": place.get("lat", 0),
                "longitude": place.get("lng", 0),
                "open_now": place.get("open_now"),
                "place_id": place.get("place_id", ""),
                "source": "maps",
            })

    # Priority 4: Static dataset fallback (only when Maps fails)
    if not maps_doctors:
        logger.info("Maps unavailable or no results — falling back to static dataset")
        db_doctors = get_db_doctors(specialist, limit=limit)
        for doc in db_doctors:
            doc["source"] = "database"
            doc["distance_km"] = None
            doc["maps_url"] = ""
            doc["latitude"] = None
            doc["longitude"] = None
            doc["review_count"] = 0
            doc["reviews"] = 0
        return db_doctors[:limit]

    # Sort by: distance → rating → review count
    maps_doctors.sort(key=lambda d: (
        d.get("distance_km", 999),
        -(d.get("rating", 0) or 0),
        -(d.get("review_count", 0) or 0),
    ))

    return maps_doctors[:limit]
