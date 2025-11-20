#!/usr/bin/env python3
"""
Generate traffic to Orchestr8r for metrics collection
Simulates realistic usage patterns
"""

import requests
import time
import random

API_GATEWAY = "http://localhost:8000"

# Sample queries to rotate through
QUERIES = [
    "rock music",
    "jazz piano",
    "hip hop",
    "electronic dance",
    "classical symphony",
    "blues guitar",
    "country ballads",
    "reggae",
]

ARTISTS = [
    "the beatles",
    "miles davis",
    "kendrick lamar",
    "daft punk",
    "beethoven",
]

def make_request(endpoint, params):
    """Make a request and return status"""
    try:
        response = requests.get(f"{API_GATEWAY}{endpoint}", params=params, timeout=30)
        return response.status_code
    except Exception as e:
        print(f"Error: {e}")
        return 0

def generate_traffic():
    """Generate realistic traffic patterns"""
    print("🚀 Starting traffic generation...")
    print("Press Ctrl+C to stop\n")
    
    request_count = 0
    
    while True:
        try:
            # Rotate through different types of requests
            action = random.choice(['recommendation', 'artist_search', 'album_search'])
            
            if action == 'recommendation':
                query = random.choice(QUERIES)
                status = make_request('/api/recommendations/query', {'query': query, 'limit': 10})
                print(f"✓ Recommendation query: '{query}' - Status: {status}")
            
            elif action == 'artist_search':
                artist = random.choice(ARTISTS)
                status = make_request('/api/artists/search', {'query': artist, 'limit': 10})
                print(f"✓ Artist search: '{artist}' - Status: {status}")
            
            elif action == 'album_search':
                artist = random.choice(ARTISTS)
                status = make_request('/api/albums/search', {'artist_name': artist, 'limit': 10})
                print(f"✓ Album search: '{artist}' - Status: {status}")
            
            request_count += 1
            
            if request_count % 10 == 0:
                print(f"\n📊 Generated {request_count} requests so far...\n")
            
            # Wait 2-5 seconds between requests (realistic usage)
            time.sleep(random.uniform(2, 5))
            
        except KeyboardInterrupt:
            print(f"\n✓ Traffic generation stopped after {request_count} requests")
            break

if __name__ == "__main__":
    generate_traffic()