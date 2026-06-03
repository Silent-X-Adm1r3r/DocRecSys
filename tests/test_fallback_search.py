"""
Fallback Search Tests — Validates multi-stage fallback search logic.
Tests the progressive search chain: Specialist → Clinic → Hospital → Doctor
"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.specialist_mapping_service import (
    get_fallback_queries, get_specialist, get_search_radius,
    get_specialist_rarity, RARE_SPECIALISTS, COMMON_SPECIALISTS,
)
from services.maps_service import haversine_km, _generate_radii


# ── Fallback Query Chain Structure ─────────────────────────────────

class TestFallbackChainStructure:
    """Validates the structure of fallback query chains."""

    def test_chain_starts_with_specialist(self):
        for spec in ["Neurologist", "Cardiologist", "Dermatologist", "Pulmonologist"]:
            queries = get_fallback_queries(spec)
            assert queries[0] == spec, f"Chain for {spec} should start with {spec}"

    def test_chain_ends_with_generic(self):
        for spec in ["Neurologist", "Endocrinologist", "Rheumatologist"]:
            queries = get_fallback_queries(spec)
            assert queries[-1] == "Doctor", f"Chain for {spec} should end with 'Doctor'"

    def test_chain_includes_hospital(self):
        for spec in ["Neurologist", "Cardiologist", "Oncologist"]:
            queries = get_fallback_queries(spec)
            assert "Hospital" in queries, f"Chain for {spec} should include 'Hospital'"

    def test_chain_has_minimum_length(self):
        for spec in ["Neurologist", "General Physician", "Dermatologist"]:
            queries = get_fallback_queries(spec)
            assert len(queries) >= 3, f"Chain for {spec} should have ≥3 entries"

    def test_chain_no_duplicates(self):
        for spec in ["Neurologist", "Cardiologist", "Endocrinologist",
                      "General Physician", "Psychiatrist"]:
            queries = get_fallback_queries(spec)
            lowered = [q.lower() for q in queries]
            assert len(lowered) == len(set(lowered)), \
                f"Duplicates found in chain for {spec}: {queries}"


class TestFallbackChainContent:
    """Validates specific fallback chain content."""

    def test_neurologist_chain(self):
        queries = get_fallback_queries("Neurologist")
        assert queries[0] == "Neurologist"
        assert any("Neurology" in q or "Neurolog" in q for q in queries[1:3])

    def test_general_physician_chain(self):
        queries = get_fallback_queries("General Physician")
        assert queries[0] == "General Physician"
        assert "Family Doctor" in queries
        assert "Clinic" in queries

    def test_cardiologist_chain(self):
        queries = get_fallback_queries("Cardiologist")
        assert queries[0] == "Cardiologist"

    def test_psychiatrist_chain(self):
        queries = get_fallback_queries("Psychiatrist")
        assert queries[0] == "Psychiatrist"


# ── Specialist Rarity Coverage ─────────────────────────────────────

class TestRarityCoverage:
    """Ensures all specialists have proper rarity classification."""

    def test_rare_specialists_have_larger_radius(self):
        for spec in RARE_SPECIALISTS:
            radius = get_search_radius(spec)
            assert radius >= 75, f"{spec} (rare) should have radius ≥75km, got {radius}"

    def test_common_specialists_have_medium_radius(self):
        for spec in COMMON_SPECIALISTS:
            radius = get_search_radius(spec)
            assert 25 <= radius <= 75, f"{spec} (common) should have 25-75km radius, got {radius}"

    def test_general_has_smallest_radius(self):
        radius = get_search_radius("General Physician")
        assert radius <= 30, f"GP should have radius ≤30km, got {radius}"

    def test_unknown_specialist_defaults_to_general(self):
        rarity = get_specialist_rarity("Unknown Specialist")
        assert rarity == "general"


# ── Progressive Radius Tests ───────────────────────────────────────

class TestProgressiveRadius:
    """Tests the progressive radius expansion logic."""

    def test_radii_are_sorted(self):
        for max_r in [25, 50, 100, 150]:
            radii = _generate_radii(max_r)
            for i in range(1, len(radii)):
                assert radii[i] > radii[i-1], \
                    f"Radii not sorted for max={max_r}: {radii}"

    def test_radii_include_max(self):
        for max_r in [25, 50, 100]:
            radii = _generate_radii(max_r)
            assert max_r in radii, f"Max radius {max_r} not in {radii}"

    def test_radii_start_small(self):
        radii = _generate_radii(100)
        assert radii[0] <= 15, f"First radius should be ≤15km, got {radii[0]}"


# ── Disease → Specialist → Radius Integration ─────────────────────

class TestDiseaseToRadiusIntegration:
    """End-to-end: disease → specialist → rarity → radius → fallback chain."""

    @pytest.mark.parametrize("disease,expected_spec,expected_rarity", [
        ("Migraine", "Neurologist", "rare"),
        ("Diabetes", "Endocrinologist", "rare"),
        ("Acne", "Dermatologist", "common"),
        ("Common Cold", "General Physician", "general"),
        ("Hypertension", "Cardiologist", "common"),
        ("Arthritis", "Rheumatologist", "rare"),
        ("Gastroenteritis", "Gastroenterologist", "common"),
        ("Anxiety Disorder", "Psychiatrist", "common"),
    ])
    def test_disease_to_specialist_mapping(self, disease, expected_spec, expected_rarity):
        specialist = get_specialist(disease)
        assert specialist == expected_spec, f"{disease} → {specialist}, expected {expected_spec}"

        rarity = get_specialist_rarity(specialist)
        assert rarity == expected_rarity, f"{specialist} rarity: {rarity}, expected {expected_rarity}"

        radius = get_search_radius(specialist)
        assert radius > 0

        queries = get_fallback_queries(specialist)
        assert len(queries) >= 3
        assert queries[0] == specialist


# ── Distance Ranking Tests ─────────────────────────────────────────

class TestDistanceRanking:
    """Tests that results would be sorted by distance."""

    def test_closer_first(self):
        results = [
            {"name": "Far", "distance_km": 15.0},
            {"name": "Near", "distance_km": 2.0},
            {"name": "Mid", "distance_km": 8.0},
        ]
        sorted_results = sorted(results, key=lambda x: x["distance_km"])
        assert sorted_results[0]["name"] == "Near"
        assert sorted_results[1]["name"] == "Mid"
        assert sorted_results[2]["name"] == "Far"

    def test_distance_then_rating(self):
        results = [
            {"name": "A", "distance_km": 5.0, "rating": 3.0},
            {"name": "B", "distance_km": 5.0, "rating": 4.5},
            {"name": "C", "distance_km": 2.0, "rating": 3.5},
        ]
        sorted_results = sorted(results, key=lambda x: (x["distance_km"], -x["rating"]))
        assert sorted_results[0]["name"] == "C"  # Closest
        assert sorted_results[1]["name"] == "B"  # Same distance, higher rating
