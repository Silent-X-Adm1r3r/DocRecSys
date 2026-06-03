"""
Maps Service — Google Maps integration for nearby doctors/hospitals.
Features: Redis caching, progressive radius search, multi-stage fallback,
specialist-rarity-aware radius, distance calculation, embedded map data.
"""
from __future__ import annotations
import logging, math
import requests

from services import redis_service
from services.logger import log_doctor_search

logger = logging.getLogger(__name__)

_API_KEY = ""


def init_maps(api_key: str):
    global _API_KEY
    _API_KEY = api_key
    if api_key:
        logger.info("Google Maps API initialized")
    else:
        logger.warning("GOOGLE_MAPS_API_KEY not set. Maps features disabled.")


def is_available() -> bool:
    return bool(_API_KEY)


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in km between two points using Haversine formula."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)


def search_nearby(
    lat: float, lng: float, keyword: str,
    radius_km: int = 20, max_results: int = 10
) -> list[dict]:
    """Search Google Places API for nearby medical facilities."""
    if not _API_KEY:
        return []

    try:
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            "location": f"{lat},{lng}",
            "radius": radius_km * 1000,
            "keyword": keyword,
            "type": "doctor|hospital|health",
            "key": _API_KEY,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("status") != "OK":
            logger.warning("Places API status: %s (keyword=%s)", data.get("status"), keyword)
            return []

        results = []
        for place in data.get("results", [])[:max_results]:
            loc = place.get("geometry", {}).get("location", {})
            place_lat = loc.get("lat", 0)
            place_lng = loc.get("lng", 0)
            distance_km = haversine_km(lat, lng, place_lat, place_lng) if place_lat and place_lng else 0

            results.append({
                "place_id": place.get("place_id", ""),
                "name": place.get("name", ""),
                "address": place.get("vicinity", ""),
                "rating": place.get("rating", 0),
                "review_count": place.get("user_ratings_total", 0),
                "lat": place_lat,
                "lng": place_lng,
                "distance_km": distance_km,
                "open_now": place.get("opening_hours", {}).get("open_now"),
                "types": place.get("types", []),
                "maps_url": f"https://www.google.com/maps/place/?q=place_id:{place.get('place_id', '')}",
            })

        # Sort by distance
        results.sort(key=lambda x: x.get("distance_km", 999))
        return results

    except requests.Timeout:
        logger.error("Places API timeout (keyword=%s, radius=%dkm)", keyword, radius_km)
        return []
    except Exception as e:
        logger.error("Places API error: %s", e)
        return []


def search_with_fallback(
    lat: float, lng: float,
    specialist: str,
    fallback_queries: list[str],
    radius_km: int = 50,
    min_results: int = 3,
    max_results: int = 10,
) -> tuple[list[dict], str]:
    """
    Multi-stage fallback search. Tries each query in sequence,
    progressively expanding radius if needed.

    Returns: (results, query_that_worked)
    """
    from config import MAPS_CACHE_TTL

    # Check Redis cache first
    cached = redis_service.get_maps_cache(specialist, lat, lng)
    if cached is not None:
        return cached, f"{specialist} (cached)"

    # Progressive radius steps within the max
    radii = _generate_radii(radius_km)

    all_results = []
    winning_query = ""

    for query in fallback_queries:
        for radius in radii:
            results = search_nearby(lat, lng, query, radius_km=radius, max_results=max_results)

            log_doctor_search(
                logger,
                maps_query=query,
                search_radius=radius,
                result_count=len(results),
                latitude=lat,
                longitude=lng,
            )

            if len(results) >= min_results:
                # Cache and return
                redis_service.set_maps_cache(specialist, lat, lng, results, ttl=MAPS_CACHE_TTL)
                return results, f"{query} (radius={radius}km)"

            if results:
                all_results.extend(results)

        if all_results:
            break

    # Deduplicate by place_id
    seen_ids = set()
    deduped = []
    for r in all_results:
        pid = r.get("place_id", "")
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            deduped.append(r)

    deduped.sort(key=lambda x: x.get("distance_km", 999))

    if deduped:
        redis_service.set_maps_cache(specialist, lat, lng, deduped, ttl=MAPS_CACHE_TTL)
        winning_query = f"fallback (combined {len(fallback_queries)} queries)"

    return deduped[:max_results], winning_query


def _generate_radii(max_radius_km: int) -> list[int]:
    """Generate progressive radius steps up to max."""
    steps = []
    r = 10
    while r <= max_radius_km:
        steps.append(r)
        if r < 25:
            r += 15
        elif r < 50:
            r += 25
        else:
            r += 50
    if not steps or steps[-1] < max_radius_km:
        steps.append(max_radius_km)
    return steps


def get_directions(
    origin_lat: float, origin_lng: float,
    dest_lat: float, dest_lng: float
) -> dict | None:
    """Get driving directions between two points."""
    if not _API_KEY:
        return None
    try:
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": f"{origin_lat},{origin_lng}",
            "destination": f"{dest_lat},{dest_lng}",
            "mode": "driving",
            "key": _API_KEY,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("status") != "OK" or not data.get("routes"):
            return None
        route = data["routes"][0]["legs"][0]
        return {
            "distance": route.get("distance", {}).get("text", ""),
            "duration": route.get("duration", {}).get("text", ""),
            "distance_m": route.get("distance", {}).get("value", 0),
            "duration_s": route.get("duration", {}).get("value", 0),
        }
    except Exception as e:
        logger.error("Directions API error: %s", e)
        return None


def get_emergency_hospitals(lat: float, lng: float) -> list[dict]:
    """Find nearest emergency hospitals."""
    return search_nearby(lat, lng, "emergency hospital", radius_km=30, max_results=5)


def get_place_details(place_id: str) -> dict | None:
    """Get detailed info for a place (phone, website, etc.)."""
    if not _API_KEY or not place_id:
        return None
    try:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "formatted_phone_number,website,url,opening_hours",
            "key": _API_KEY,
        }
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()
        if data.get("status") != "OK":
            return None
        result = data.get("result", {})
        return {
            "phone": result.get("formatted_phone_number", ""),
            "website": result.get("website", ""),
            "maps_url": result.get("url", ""),
        }
    except Exception as e:
        logger.error("Place Details API error: %s", e)
        return None
