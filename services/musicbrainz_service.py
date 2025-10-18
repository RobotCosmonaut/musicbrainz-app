#
#   Orchestr8r – A Prototype Music Recommendation System using Microservices 
#   
#   MusicBrainz Service: Interacts with the MusicBrainz API to fetch artist, album, and track data.
#
#   This script was created in Microsoft VSCode and Claude.ai was referenced/utilized in the script development
#

import requests
import time
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MusicBrainzService:
    BASE_URL = "https://musicbrainz.org/ws/2"
    
    def __init__(self, app_name: str = "MusicBrainzApp", version: str = "1.0", contact: str = ""):
        self.headers = {
            'User-Agent': f'{app_name}/{version} ({contact})'
        }
        self.rate_limit_delay = 1.0  # MusicBrainz rate limit: 1 request per second
    
    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Make a rate-limited request to MusicBrainz API"""
        url = f"{self.BASE_URL}/{endpoint}"
        params['fmt'] = 'json'
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)  # Respect rate limit
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def search_artists(self, query: str, limit: int = 25) -> List[Dict]:
        """Search for artists by name"""
        params = {
            'query': query,
            'limit': limit
        }
        result = self._make_request('artist', params)
        return result.get('artists', []) if result else []
    
    def get_artist(self, artist_id: str, include: str = "releases") -> Optional[Dict]:
        """Get artist details by ID"""
        params = {'inc': include}
        return self._make_request(f'artist/{artist_id}', params)
    
    def get_release(self, release_id: str, include: str = "recordings") -> Optional[Dict]:
        """Get release (album) details by ID"""
        params = {'inc': include}
        return self._make_request(f'release/{release_id}', params)
    
    def search_releases(self, artist_name: str = "", album_title: str = "", limit: int = 25) -> List[Dict]:
        """Search for releases"""
        query_parts = []
        if artist_name:
            query_parts.append(f'artist:"{artist_name}"')
        if album_title:
            query_parts.append(f'release:"{album_title}"')
        
        if not query_parts:
            return []
        
        params = {
            'query': ' AND '.join(query_parts),
            'limit': limit
        }
        result = self._make_request('release', params)
        return result.get('releases', []) if result else []
    
    def search_recordings(self, query: str = "", artist_name: str = "", limit: int = 25) -> List[Dict]:
        """Search for recordings (songs/tracks)"""
        query_parts = []
        if query:
            query_parts.append(query)
        if artist_name:
            query_parts.append(f'artist:"{artist_name}"')
        
        if not query_parts:
            return []
        
        params = {
            'query': ' AND '.join(query_parts),
            'limit': limit
        }
        result = self._make_request('recording', params)
        return result.get('recordings', []) if result else []
    
    def get_recording(self, recording_id: str, include: str = "artists+releases") -> Optional[Dict]:
        """Get recording details by ID"""
        params = {'inc': include}
        return self._make_request(f'recording/{recording_id}', params)
    
    def get_artist_recordings(self, artist_id: str, limit: int = 50) -> List[Dict]:
        """Get recordings by artist"""
        params = {
            'query': f'arid:{artist_id}',
            'limit': limit
        }
        result = self._make_request('recording', params)
        return result.get('recordings', []) if result else []
