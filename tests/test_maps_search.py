"""
Maps Search Tests — Google Maps integration, fallback search, distance ranking.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.maps_service import haversine_km, _generate_radii
from services.specialist_mapping_service import (
    get_specialist, get_specialist_rarity, get_search_radius,
    get_fallback_queries,
)


# ── Haversine Distance Tests ───────────────────────────────────────

class TestHaversine:

    def test_same_point(self):
        d = haversine_km(13.0, 80.0, 13.0, 80.0)
        assert d == 0.0

    def test_known_distance(self):
        # Chennai to Bangalore ≈ 290 km
        d = haversine_km(13.0827, 80.2707, 12.9716, 77.5946)
        assert 275 < d < 310

    def test_short_distance(self):
        # ~1km difference
        d = haversine_km(13.0, 80.0, 13.009, 80.0)
        assert 0.5 < d < 1.5


# ── Radius Generation Tests ────────────────────────────────────────

class TestRadiusGeneration:

    def test_small_radius(self):
        radii = _generate_radii(25)
        assert 10 in radii
        assert 25 in radii

    def test_large_radius(self):
        radii = _generate_radii(100)
        assert 10 in radii
        assert 100 in radii

    def test_radius_progressive(self):
        radii = _generate_radii(100)
        # Should be monotonically increasing
        for i in range(1, len(radii)):
            assert radii[i] > radii[i - 1]


# ── Specialist Mapping Tests ───────────────────────────────────────

class TestSpecialistMapping:

    def test_known_disease(self):
        assert get_specialist("Migraine") == "Neurologist"
        assert get_specialist("Diabetes") == "Endocrinologist"
        assert get_specialist("Common Cold") == "General Physician"

    def test_unknown_disease_defaults_to_gp(self):
        assert get_specialist("Unknown Disease XYZ") == "General Physician"

    def test_rarity_classification(self):
        assert get_specialist_rarity("Neurologist") == "rare"
        assert get_specialist_rarity("Dermatologist") == "common"
        assert get_specialist_rarity("General Physician") == "general"

    def test_search_radius_by_rarity(self):
        r_general = get_search_radius("General Physician")
        r_common = get_search_radius("Dermatologist")
        r_rare = get_search_radius("Neurologist")
        assert r_general < r_common < r_rare


# ── Fallback Query Chain Tests ─────────────────────────────────────

class TestFallbackQueries:

    def test_neurologist_chain(self):
        queries = get_fallback_queries("Neurologist")
        assert queries[0] == "Neurologist"
        assert any("Clinic" in q or "Hospital" in q for q in queries)
        assert "Hospital" in queries
        assert "Doctor" in queries

    def test_general_physician_chain(self):
        queries = get_fallback_queries("General Physician")
        assert queries[0] == "General Physician"
        assert "Hospital" in queries
        assert "Doctor" in queries

    def test_no_duplicates(self):
        queries = get_fallback_queries("Cardiologist")
        lowered = [q.lower() for q in queries]
        assert len(lowered) == len(set(lowered))

    def test_chain_ends_with_generic(self):
        queries = get_fallback_queries("Endocrinologist")
        assert queries[-1] == "Doctor"


# ── Doctor Search Integration (unit level) ─────────────────────────

class TestDoctorSearch:

    @pytest.fixture(autouse=True)
    def _init_db(self):
        from services.database import init_db
        from config import SQLITE_PATH
        init_db(SQLITE_PATH)

    def test_search_without_maps(self):
        """Search should fall back to database when Maps is unavailable."""
        from services.doctor_search_service import search_doctors
        doctors = search_doctors("General Physician", lat=None, lng=None, limit=5)
        # Should return static DB results or empty
        assert isinstance(doctors, list)

    def test_search_returns_list(self):
        from services.doctor_search_service import search_doctors
        result = search_doctors("Dermatologist", limit=3)
        assert isinstance(result, list)


# ── Hospital Search Tests ──────────────────────────────────────────

class TestHospitalSearch:

    def test_search_without_location(self):
        from services.hospital_search_service import search_hospitals
        hospitals = search_hospitals(lat=None, lng=None)
        assert hospitals == []

    def test_search_returns_list(self):
        from services.hospital_search_service import search_hospitals
        result = search_hospitals(lat=13.0, lng=80.0, limit=3)
        assert isinstance(result, list)
