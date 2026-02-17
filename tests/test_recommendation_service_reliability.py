"""
Reliability tests for Recommendation Service
Measures: Algorithm Consistency, Timeout Handling, Diversity Delivery
"""

import pytest
import requests
import time

BASE_URL = "http://localhost:8003"

class TestRecommendationServiceReliability:
    
    @pytest.mark.reliability
    def test_recommendation_consistency(self):
        """Same query should return similar quality results"""
        query = "jazz piano"
        scores = []
        
        for _ in range(10):
            response = requests.get(
                f"{BASE_URL}/recommendations/query",
                params={"query": query, "limit": 10},
                timeout=30
            )
            
            assert response.status_code == 200
            data = response.json()
            recommendations = data.get("recommendations", [])
            
            if recommendations:
                avg_score = sum(r['score'] for r in recommendations) / len(recommendations)
                scores.append(avg_score)
        
        # Average scores should be consistent (within 20 points)
        score_range = max(scores) - min(scores)
        assert score_range < 20, \
            f"Recommendation quality too variable: range={score_range}"
        
        print(f"\n📊 Consistency Stats:")
        print(f"   Score range: {score_range:.1f}")
        print(f"   Avg score: {sum(scores)/len(scores):.1f}")
    
    @pytest.mark.reliability
    def test_diversity_reliability(self):
        """Service should consistently deliver diverse results"""
        diversity_ratios = []
        
        for _ in range(10):
            response = requests.get(
                f"{BASE_URL}/recommendations/query",
                params={"query": "rock music", "limit": 10},
                timeout=30
            )
            
            assert response.status_code == 200
            data = response.json()
            recommendations = data.get("recommendations", [])
            
            if recommendations:
                unique_artists = len(set(r['artist_name'] for r in recommendations))
                total_songs = len(recommendations)
                diversity_ratio = unique_artists / total_songs
                diversity_ratios.append(diversity_ratio)
        
        avg_diversity = sum(diversity_ratios) / len(diversity_ratios)
        
        # Should maintain >60% diversity on average
        assert avg_diversity >= 0.6, \
            f"Diversity too low: {avg_diversity*100:.1f}%"
        
        print(f"\n🎨 Diversity Stats:")
        print(f"   Average diversity: {avg_diversity*100:.1f}%")
    
    @pytest.mark.reliability
    def test_timeout_handling_reliability(self):
        """Service should handle MusicBrainz API timeouts gracefully"""
        # Complex query that might timeout
        response = requests.get(
            f"{BASE_URL}/recommendations/query",
            params={"query": "obscure experimental avant-garde", "limit": 10},
            timeout=35  # Slightly longer than service timeout
        )
        
        # Should return something, not crash
        assert response.status_code in [200, 504]
        
        if response.status_code == 200:
            data = response.json()
            # Should have attempted to return results or graceful error
            assert "recommendations" in data or "error" in data
    
    @pytest.mark.reliability
    def test_empty_result_handling(self):
        """Service should handle empty results gracefully"""
        # Nonsense query
        response = requests.get(
            f"{BASE_URL}/recommendations/query",
            params={"query": "xyzabc123impossible", "limit": 10},
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty list, not error
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)