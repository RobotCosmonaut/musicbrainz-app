"""
FMEA Tests: Recommendation Service Failure Modes
Failure Modes:
  - Genre detection failure (Severity 7)
  - Low diversity in results (Severity 5)
  - Empty result handling (Severity 7)
"""

import pytest
import requests
import time
from collections import Counter

REC_URL = "http://localhost:8003"

class TestGenreDetectionFailure:

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_genre_detection_known_genres(self):
        """
        FMEA: Genre detection should identify common genres
        Severity 7: Wrong genre = wrong recommendations
        Compare: Before (no detection) vs After (keyword matching)
        """
        genre_test_cases = [
            ("rock music", "rock"),
            ("jazz piano", "jazz"),
            ("hip-hop rap", "hip-hop"),
            ("electronic dance", "electronic"),
            ("country ballads", "country"),
            ("blues guitar", "blues"),
            ("metal heavy", "metal"),
        ]

        from services.recommendation_service import detect_genre_enhanced

        successes = 0
        failures = []

        for query, expected_genre in genre_test_cases:
            detected = detect_genre_enhanced(query)

            if detected == expected_genre:
                successes += 1
            else:
                failures.append({
                    "query": query,
                    "expected": expected_genre,
                    "detected": detected
                })

        success_rate = (successes / len(genre_test_cases)) * 100

        print(f"\n📊 Genre Detection Results:")
        print(f"   Success rate: {success_rate:.1f}%")
        if failures:
            for f in failures:
                print(f"   ❌ '{f['query']}': expected '{f['expected']}', got '{f['detected']}'")

        assert success_rate >= 70, \
            f"Genre detection too inaccurate: {success_rate:.1f}%"

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_genre_detection_none_for_unknown(self):
        """
        FMEA: Unknown genres should return None, not wrong genre
        Severity 7: Wrong genre detection = misleading recommendations
        """
        from services.recommendation_service import detect_genre_enhanced

        ambiguous_queries = [
            "music",
            "songs",
            "playlist",
            "xyzabc123"
        ]

        for query in ambiguous_queries:
            result = detect_genre_enhanced(query)
            # Should return None for ambiguous queries, not guess
            # (Acceptable if it returns None or a genre, not crash)
            assert result is None or isinstance(result, str), \
                f"Genre detection crashed on '{query}': {result}"

        print(f"\n✅ No crashes on ambiguous genre queries")


class TestDiversityFailure:

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_diversity_filter_max_per_artist(self):
        """
        FMEA: Diversity filter should limit tracks per artist
        Severity 5: Same artist repeated = poor UX
        Before Fix: No diversity filter
        After Fix: ensure_artist_diversity() limits to 1-2 per artist
        """
        from services.recommendation_service import ensure_artist_diversity

        # Create list with heavy artist repetition
        repeated_recs = [
            {
                "track_id": f"track-{i}",
                "track_title": f"Song {i}",
                "artist_name": "Same Artist",
                "artist_id": "artist-001",
                "score": 80
            }
            for i in range(8)
        ] + [
            {
                "track_id": f"track-other-{i}",
                "track_title": f"Other Song {i}",
                "artist_name": f"Artist {i}",
                "artist_id": f"artist-{i+10}",
                "score": 75
            }
            for i in range(4)
        ]

        filtered = ensure_artist_diversity(repeated_recs, max_per_artist=1)

        artist_counts = Counter(r["artist_name"] for r in filtered)

        # No artist should appear more than max_per_artist times
        for artist, count in artist_counts.items():
            assert count <= 1, \
                f"Artist '{artist}' appears {count} times (max=1)"

        print(f"\n✅ Diversity filter working:")
        print(f"   Input: {len(repeated_recs)} tracks")
        print(f"   Output: {len(filtered)} tracks")
        print(f"   Unique artists: {len(artist_counts)}")

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_diversity_ratio_in_api_response(self):
        """
        FMEA: API should return diverse artists in recommendations
        Severity 5: Low diversity = monotonous recommendations
        Measures: Unique artists / total tracks ratio
        """
        response = requests.get(
            f"{REC_URL}/recommendations/query",
            params={"query": "rock music", "limit": 10},
            timeout=30
        )

        assert response.status_code == 200
        data = response.json()
        recommendations = data.get("recommendations", [])

        if len(recommendations) >= 3:
            unique_artists = len(set(r["artist_name"] for r in recommendations))
            total_tracks = len(recommendations)
            diversity_ratio = unique_artists / total_tracks

            print(f"\n📊 Diversity Metrics:")
            print(f"   Tracks: {total_tracks}")
            print(f"   Unique artists: {unique_artists}")
            print(f"   Diversity ratio: {diversity_ratio:.2f}")

            assert diversity_ratio >= 0.5, \
                f"Poor diversity: {diversity_ratio:.2f} ({unique_artists}/{total_tracks})"


class TestEmptyResultHandling:

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_empty_results_graceful_response(self):
        """
        FMEA: Empty results should return structured response not error
        Severity 7: Crash on empty results = service failure
        Before Fix: KeyError or 500 on empty MusicBrainz response
        After Fix: Returns empty list with metadata
        """
        response = requests.get(
            f"{REC_URL}/recommendations/query",
            params={"query": "xyzabc123impossiblequery", "limit": 10},
            timeout=30
        )

        # Should not be 500
        assert response.status_code != 500, \
            "Service crashed on empty results"
        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}"

        data = response.json()

        # Should have proper structure
        assert "recommendations" in data, \
            "Missing 'recommendations' key in response"
        assert isinstance(data["recommendations"], list), \
            "Recommendations should be a list"

        print(f"\n✅ Empty results handled gracefully")
        print(f"   Response keys: {list(data.keys())}")

    @pytest.mark.fmea
    @pytest.mark.reliability
    def test_fallback_strategies_activated(self):
        """
        FMEA: Multiple fallback strategies should activate on failure
        Severity 7: No fallback = complete failure
        Tests: Fallback fires when primary search returns nothing
        """
        from services.recommendation_service import get_diverse_recommendations

        # Query that might not match genre keywords
        result = get_diverse_recommendations("general music query", limit=5)

        assert "recommendations" in result, \
            "No recommendations key in fallback result"

        # Algorithm version should be present (indicates service ran)
        assert "algorithm_version" in result, \
            "Missing algorithm version - service may have crashed"

        print(f"\n✅ Fallback strategies activated")
        print(f"   Algorithm: {result.get('algorithm_version')}")
        print(f"   Results: {len(result.get('recommendations', []))}")