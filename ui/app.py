import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime
import os
from PIL import Image

# Configuration - Use environment variable with fallback
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")

st.set_page_config(page_title="Orchestr8r: Continuous Delivery of your Perfect Playlist", page_icon="🎵", layout="wide")

# Initialize session state
if 'username' not in st.session_state:
    st.session_state.username = "guest"

st.title("🎵 Orchestr8r: Continuous Delivery of your Perfect Playlist <br>Music Recommendation System using Microservices Architecture")
st.markdown("Discover music with smart recommendations that understand artists, genres, and moods")

# Debug info in sidebar
with st.sidebar:
    st.header("🔧 Debug Info")
    st.write(f"🔗 API Gateway: {API_GATEWAY_URL}")
    
    # Test API connection and version
    try:
        response = requests.get(f"{API_GATEWAY_URL}/health", timeout=5)
        if response.status_code == 200:
            st.success("✅ API Connected")
        else:
            st.error("❌ API Connection Failed")
    except Exception as e:
        st.error(f"❌ API Error: {e}")
    
    # Test recommendation service specifically
    try:
        # Test if we're hitting the enhanced recommendation service
        response = requests.get(f"{API_GATEWAY_URL}/api/recommendations/query", 
                              params={"query": "test", "limit": 1}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "query_analyzed" in data:
                st.success("✅ Enhanced Algorithm Active")
                st.json(data.get("query_analyzed", {}))
            else:
                st.warning("⚠️ Old Algorithm Running")
        else:
            st.error("❌ Recommendation Service Down")
    except Exception as e:
        st.error(f"❌ Rec Service Error: {str(e)[:100]}")

# User Profile Setup in Sidebar
with st.sidebar:
    st.header("👤 User Profile")
    username = st.text_input("Username:", value=st.session_state.username)
    if username != st.session_state.username:
        st.session_state.username = username
    
    # Load existing profile
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/users/{username}/profile", timeout=10)
        if response.status_code == 200:
            profile_data = response.json()
            st.success(f"Profile loaded for {username}")
            existing_genres = profile_data.get('favorite_genres', [])
            existing_artists = profile_data.get('favorite_artists', [])
        else:
            existing_genres = []
            existing_artists = []
    except Exception as e:
        st.sidebar.warning(f"Could not load profile: {str(e)}")
        existing_genres = []
        existing_artists = []
    
    # Profile settings
    st.subheader("Preferences")
    
    # Genre preferences
    available_genres = ["rock", "pop", "jazz", "classical", "electronic", "hip-hop", "country", "blues", "folk", "metal", "punk", "reggae", "r&b", "soul", "funk"]
    favorite_genres = st.multiselect(
        "Favorite Genres:",
        available_genres,
        default=[g for g in existing_genres if g in available_genres]
    )
    
    # Artist preferences (text input for MusicBrainz IDs)
    favorite_artists_text = st.text_area(
        "Favorite Artist IDs (one per line):",
        value='\n'.join(existing_artists) if existing_artists else "",
        help="Enter MusicBrainz Artist IDs (you can find these when searching artists)"
    )
    favorite_artists = [id.strip() for id in favorite_artists_text.split('\n') if id.strip()]
    
    if st.button("💾 Save Profile"):
        try:
            payload = {
                "favorite_genres": favorite_genres,
                "favorite_artists": favorite_artists
            }
            response = requests.post(
                f"{API_GATEWAY_URL}/api/users/{username}/profile",
                json=payload,
                timeout=10
            )
            if response.status_code == 200:
                st.success("Profile saved!")
            else:
                st.error(f"Failed to save profile: {response.status_code}")
        except Exception as e:
            st.error(f"Error: {e}")

# Main navigation
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🏠 Home", "🎤 Search Artists", "💿 Search Albums", "🎯 Recommendations", "💾 Saved Data", "🔧 Status for Nerds"])

with tab1:
    st.header("🏠 Enhanced Music Discovery")
    
    # Add explanation of improvements
    st.info("""
    🎯 **New Enhanced Algorithm**: 
    - **Artist Focus**: 30% weight on matching artists
    - **Genre Intelligence**: 25% weight on musical genres  
    - **Mood Detection**: Understands "upbeat", "relaxing", "aggressive", etc.
    - **Smart Search**: Multiple search strategies per query
    - **Title Balance**: Only 25% weight (down from 90%+)
    """)
    
    st.markdown("""
    ### Smart Song Recommendations
    Try these examples to see the enhanced algorithm:
    - **"old school rap"** - Should find classic hip-hop artists
    - **"relaxing jazz piano"** - Should prioritize jazz pianists  
    - **"energetic rock songs"** - Should find upbeat rock bands
    - **"acoustic folk ballads"** - Should find folk artists with acoustic style
    """)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔍 What kind of music are you looking for?", 
                            placeholder="e.g., old school rap, relaxing jazz piano, energetic rock songs")
    with col2:
        st.write("")
        st.write("")
        search_button = st.button("🎵 Get Smart Recommendations", type="primary")
    
    if search_button and query:
        with st.spinner("Analyzing your query and finding perfect matches..."):
            try:
                # Include username for personalization
                params = {"query": query, "limit": 10}
                if username != "guest":
                    params["username"] = username
                
                response = requests.get(f"{API_GATEWAY_URL}/api/recommendations/query", 
                                      params=params,
                                      timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    recommendations = data.get("recommendations", [])
                    query_analysis = data.get("query_analyzed", {})
                    
                    # Show query analysis
                    if query_analysis:
                        with st.expander("🧠 How the algorithm analyzed your query"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if query_analysis.get('genres'):
                                    st.write("**Genres detected:**")
                                    for genre in query_analysis['genres']:
                                        st.write(f"🎭 {genre}")
                            with col2:
                                if query_analysis.get('moods'):
                                    st.write("**Moods detected:**")
                                    for mood in query_analysis['moods']:
                                        st.write(f"😊 {mood}")
                            with col3:
                                if query_analysis.get('artists'):
                                    st.write("**Artists detected:**")
                                    for artist in query_analysis['artists']:
                                        st.write(f"🎤 {artist}")
                    
                    if recommendations:
                        st.success(f"🎉 Found {len(recommendations)} smart recommendations!")
                        
                        # Display recommendations with enhanced info
                        for i, rec in enumerate(recommendations, 1):
                            with st.container():
                                col1, col2, col3, col4, col5 = st.columns([0.5, 2.5, 2, 1, 1])
                                
                                with col1:
                                    st.markdown(f"**#{i}**")
                                
                                with col2:
                                    st.markdown(f"**🎵 {rec['track_title']}**")
                                    st.markdown(f"*by {rec['artist_name']}*")
                                
                                with col3:
                                    score_color = "🔥" if rec['score'] >= 80 else "⭐" if rec['score'] >= 60 else "👍" if rec['score'] >= 40 else "💡"
                                    st.markdown(f"{score_color} **Score: {rec['score']}/100**")
                                    
                                    # Show recommendation type
                                    rec_type = rec.get('recommendation_type', 'unknown').replace('_', ' ').title()
                                    st.caption(f"Type: {rec_type}")
                                
                                with col4:
                                    # Show search strategy if available
                                    if 'search_strategy' in rec:
                                        st.caption(f"Found via: {rec['search_strategy'][:20]}...")
                                
                                with col5:
                                    if st.button("👍", key=f"like_{rec['track_id']}", help="Like this song"):
                                        # Add to listening history
                                        try:
                                            requests.post(
                                                f"{API_GATEWAY_URL}/api/users/{username}/listening-history",
                                                params={
                                                    "track_id": rec['track_id'],
                                                    "artist_id": rec['artist_id'],
                                                    "interaction_type": "liked"
                                                },
                                                timeout=10
                                            )
                                            st.success("Liked! ❤️")
                                        except Exception as e:
                                            st.error(f"Could not save like: {e}")
                                
                                st.divider()
                    else:
                        st.warning("No recommendations found. The enhanced algorithm might need more specific search terms.")
                        st.info("Try queries like: 'jazz saxophone', 'rock guitar', 'electronic dance', 'country ballads'")
                else:
                    st.error(f"Recommendation service error: {response.status_code}")
                    st.text(f"Response: {response.text}")
            except requests.exceptions.Timeout:
                st.error("⏰ Request timed out. The MusicBrainz API might be slow. Try again!")
            except requests.exceptions.ConnectionError:
                st.error(f"🔌 Connection error. Cannot reach API Gateway at {API_GATEWAY_URL}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
    
    # Test queries section
    st.markdown("---")
    st.subheader("🧪 Test the Enhanced Algorithm")
    
    test_queries = [
        "old school rap",
        "relaxing jazz piano", 
        "energetic rock songs",
        "acoustic folk ballads",
        "electronic dance music",
        "heavy metal guitar"
    ]
    
    cols = st.columns(3)
    for i, test_query in enumerate(test_queries):
        col = cols[i % 3]
        with col:
            if st.button(f"Test: '{test_query}'", key=f"test_{i}"):
                st.session_state['test_query'] = test_query
                st.rerun()
    
    # Execute test query if selected
    if 'test_query' in st.session_state:
        query = st.session_state['test_query']
        del st.session_state['test_query']  # Clear it
        st.write(f"**Testing query: '{query}'**")
        
        try:
            params = {"query": query, "limit": 5}
            if username != "guest":
                params["username"] = username
            
            response = requests.get(f"{API_GATEWAY_URL}/api/recommendations/query", 
                                  params=params, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                recommendations = data.get("recommendations", [])
                
                if recommendations:
                    for i, rec in enumerate(recommendations[:3], 1):  # Show top 3
                        st.write(f"{i}. **{rec['track_title']}** by *{rec['artist_name']}* (Score: {rec['score']})")
                else:
                    st.write("No results found")
            else:
                st.write(f"Error: {response.status_code}")
        except Exception as e:
            st.write(f"Error: {e}")


with tab2:
    st.header("🎤 Search Artists")
    
    query = st.text_input("Enter artist name:", placeholder="e.g., The Beatles")
    limit = st.slider("Number of results:", 1, 50, 10)
    
    if st.button("Search Artists") and query:
        with st.spinner("Searching artists..."):
            try:
                response = requests.get(f"{API_GATEWAY_URL}/api/artists/search", 
                                      params={"query": query, "limit": limit})
                
                if response.status_code == 200:
                    data = response.json()
                    artists = data.get("artists", [])
                    
                    if artists:
                        st.success(f"Found {len(artists)} artists")
                        
                        for artist in artists:
                            with st.expander(f"🎤 {artist['name']} ({artist.get('country', 'Unknown')})"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**Name:** {artist['name']}")
                                    st.write(f"**Sort Name:** {artist.get('sort-name', 'N/A')}")
                                    st.write(f"**Type:** {artist.get('type', 'N/A')}")
                                with col2:
                                    st.write(f"**Country:** {artist.get('country', 'N/A')}")
                                    life_span = artist.get('life-span', {})
                                    begin = life_span.get('begin', 'N/A')
                                    end = life_span.get('end', 'Present')
                                    st.write(f"**Active:** {begin} - {end}")
                                    st.write(f"**MusicBrainz ID:** `{artist['id']}`")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button(f"View Details", key=f"details_{artist['id']}"):
                                        st.session_state.selected_artist_id = artist['id']
                                with col2:
                                    if st.button(f"🎵 Get Similar Songs", key=f"similar_{artist['id']}"):
                                        # Get recommendations based on this artist
                                        try:
                                            rec_response = requests.get(f"{API_GATEWAY_URL}/api/recommendations/similar/{artist['name']}")
                                            if rec_response.status_code == 200:
                                                rec_data = rec_response.json()
                                                similar_songs = rec_data.get("recommendations", [])
                                                
                                                if similar_songs:
                                                    st.success(f"Found {len(similar_songs)} similar songs!")
                                                    for song in similar_songs[:3]:  # Show top 3
                                                        st.write(f"🎵 **{song['track_title']}** by *{song['artist_name']}*")
                                                else:
                                                    st.warning("No similar songs found")
                                            else:
                                                st.error("Recommendation service unavailable")
                                        except Exception as e:
                                            st.error(f"Error getting recommendations: {e}")
                    else:
                        st.warning("No artists found")
                else:
                    st.error(f"Error: {response.status_code}")
            except Exception as e:
                st.error(f"Connection error: {e}")

with tab3:
    st.header("💿 Search Albums")
    
    col1, col2 = st.columns(2)
    with col1:
        artist_name = st.text_input("Artist name:", placeholder="e.g., The Beatles")
    with col2:
        album_title = st.text_input("Album title:", placeholder="e.g., Abbey Road")
    
    limit = st.slider("Number of results:", 1, 50, 10, key="album_limit")
    
    if st.button("Search Albums") and (artist_name or album_title):
        with st.spinner("Searching albums..."):
            try:
                response = requests.get(f"{API_GATEWAY_URL}/api/albums/search", 
                                      params={"artist_name": artist_name, "album_title": album_title, "limit": limit})
                
                if response.status_code == 200:
                    data = response.json()
                    albums = data.get("albums", [])
                    
                    if albums:
                        st.success(f"Found {len(albums)} albums")
                        
                        for album in albums:
                            artist_credit = album.get('artist-credit', [{}])[0]
                            artist_name_display = artist_credit.get('artist', {}).get('name', 'Unknown Artist')
                            
                            with st.expander(f"💿 {album['title']} by {artist_name_display}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**Title:** {album['title']}")
                                    st.write(f"**Artist:** {artist_name_display}")
                                    st.write(f"**Date:** {album.get('date', 'N/A')}")
                                with col2:
                                    st.write(f"**Status:** {album.get('status', 'N/A')}")
                                    st.write(f"**Country:** {album.get('country', 'N/A')}")
                                    st.write(f"**MusicBrainz ID:** `{album['id']}`")
                    else:
                        st.warning("No albums found")
                else:
                    st.error(f"Error: {response.status_code}")
            except Exception as e:
                st.error(f"Connection error: {e}")

with tab4:
    st.header("🎯 Advanced Recommendations")
    st.markdown("Get targeted music recommendations using different methods")
    
    # Recommendation method selection
    rec_method = st.selectbox(
        "Choose recommendation method:",
        ["Profile-Based", "Query-Based", "Similar Artists", "Genre Explorer"]
    )
    
    if rec_method == "Profile-Based":
        st.subheader("👤 Your Personal Recommendations")
        if username == "guest":
            st.warning("Please set a username and configure your profile to get personalized recommendations!")
        else:
            col1, col2 = st.columns([2, 1])
            with col1:
                rec_limit = st.slider("Number of recommendations:", 5, 20, 10)
            with col2:
                st.write("")
                st.write("")
                if st.button("🎵 Generate My Recommendations", type="primary"):
                    with st.spinner("Analyzing your profile and generating recommendations..."):
                        try:
                            response = requests.get(f"{API_GATEWAY_URL}/api/recommendations/profile/{username}", 
                                                  params={"limit": rec_limit})
                            if response.status_code == 200:
                                data = response.json()
                                recommendations = data.get("recommendations", [])
                                
                                if recommendations:
                                    st.success(f"🎉 Generated {len(recommendations)} personalized recommendations!")
                                    
                                    # Display with better formatting
                                    for i, rec in enumerate(recommendations, 1):
                                        with st.container():
                                            col1, col2, col3, col4 = st.columns([0.5, 3, 2, 1.5])
                                            
                                            with col1:
                                                # Score-based emoji
                                                if rec['score'] >= 90:
                                                    st.markdown("🔥")
                                                elif rec['score'] >= 80:
                                                    st.markdown("⭐")
                                                elif rec['score'] >= 70:
                                                    st.markdown("👍")
                                                else:
                                                    st.markdown("💡")
                                            
                                            with col2:
                                                st.markdown(f"**{rec['track_title']}**")
                                                st.markdown(f"*{rec['artist_name']}*")
                                            
                                            with col3:
                                                st.markdown(f"**Score:** {rec['score']}/100")
                                                rec_type = rec['recommendation_type'].replace('_', ' ').title()
                                                st.markdown(f"**Type:** {rec_type}")
                                            
                                            with col4:
                                                if st.button("❤️ Like", key=f"like_profile_{rec['track_id']}"):
                                                    # Add to listening history
                                                    try:
                                                        requests.post(
                                                            f"{API_GATEWAY_URL}/api/users/{username}/listening-history",
                                                            params={
                                                                "track_id": rec['track_id'],
                                                                "artist_id": rec['artist_id'],
                                                                "interaction_type": "liked"
                                                            }
                                                        )
                                                        st.success("Liked! ❤️")
                                                    except:
                                                        st.error("Error saving like")
                                            
                                            st.divider()
                                else:
                                    st.info("No recommendations available. Try updating your profile with favorite genres and artists!")
                            else:
                                st.error("Could not generate recommendations. Make sure your profile is configured.")
                        except Exception as e:
                            st.error(f"Error: {e}")
    
    elif rec_method == "Query-Based":
        st.subheader("🔍 Search-Based Recommendations")
        
        query = st.text_input("Describe what you're looking for:", 
                            placeholder="e.g., 'upbeat rock songs', 'relaxing piano music', 'energetic dance tracks'")
        rec_limit = st.slider("Number of recommendations:", 5, 20, 10, key="query_rec_limit")
        
        if st.button("🎵 Find Songs", type="primary") and query:
            with st.spinner("Searching for perfect matches..."):
                try:
                    response = requests.get(f"{API_GATEWAY_URL}/api/recommendations/query", 
                                          params={"query": query, "limit": rec_limit})
                    
                    if response.status_code == 200:
                        data = response.json()
                        recommendations = data.get("recommendations", [])
                        
                        if recommendations:
                            st.success(f"🎉 Found {len(recommendations)} matching songs!")
                            
                            # Create a nice grid layout
                            for i in range(0, len(recommendations), 2):
                                cols = st.columns(2)
                                for j, col in enumerate(cols):
                                    if i + j < len(recommendations):
                                        rec = recommendations[i + j]
                                        with col:
                                            with st.container():
                                                st.markdown(f"### 🎵 {rec['track_title']}")
                                                st.markdown(f"**Artist:** {rec['artist_name']}")
                                                st.markdown(f"**Match Score:** {rec['score']}/100")
                                                
                                                col1, col2 = st.columns(2)
                                                with col1:
                                                    if st.button("❤️ Like", key=f"like_query_{rec['track_id']}"):
                                                        try:
                                                            requests.post(
                                                                f"{API_GATEWAY_URL}/api/users/{username}/listening-history",
                                                                params={
                                                                    "track_id": rec['track_id'],
                                                                    "artist_id": rec['artist_id'],
                                                                    "interaction_type": "liked"
                                                                }
                                                            )
                                                            st.success("❤️")
                                                        except:
                                                            pass
                                                with col2:
                                                    if st.button("💾 Save", key=f"save_query_{rec['track_id']}"):
                                                        try:
                                                            requests.post(
                                                                f"{API_GATEWAY_URL}/api/users/{username}/listening-history",
                                                                params={
                                                                    "track_id": rec['track_id'],
                                                                    "artist_id": rec['artist_id'],
                                                                    "interaction_type": "saved"
                                                                }
                                                            )
                                                            st.success("💾")
                                                        except:
                                                            pass
                        else:
                            st.warning("No matching songs found. Try different keywords!")
                    else:
                        st.error("Search service unavailable")
                except Exception as e:
                    st.error(f"Error: {e}")
    
    elif rec_method == "Similar Artists":
        st.subheader("🎤 Discover Similar Artists")
        
        artist_name = st.text_input("Enter an artist name:", 
                                  placeholder="e.g., Radiohead, Taylor Swift, Miles Davis")
        rec_limit = st.slider("Number of recommendations:", 5, 20, 10, key="similar_rec_limit")
        
        if st.button("🎵 Find Similar Music", type="primary") and artist_name:
            with st.spinner("Finding artists and songs similar to your taste..."):
                try:
                    response = requests.get(f"{API_GATEWAY_URL}/api/recommendations/similar/{artist_name}", 
                                          params={"limit": rec_limit})
                    
                    if response.status_code == 200:
                        data = response.json()
                        recommendations = data.get("recommendations", [])
                        
                        if recommendations:
                            st.success(f"🎉 Found {len(recommendations)} songs from similar artists!")
                            
                            # Group by artist for better display
                            from collections import defaultdict
                            by_artist = defaultdict(list)
                            for rec in recommendations:
                                by_artist[rec['artist_name']].append(rec)
                            
                            for artist, songs in by_artist.items():
                                with st.expander(f"🎤 {artist} ({len(songs)} songs)"):
                                    for song in songs:
                                        col1, col2, col3 = st.columns([3, 1, 1])
                                        with col1:
                                            st.write(f"🎵 **{song['track_title']}**")
                                        with col2:
                                            st.write(f"Score: {song['score']}")
                                        with col3:
                                            if st.button("❤️", key=f"like_similar_{song['track_id']}"):
                                                try:
                                                    requests.post(
                                                        f"{API_GATEWAY_URL}/api/users/{username}/listening-history",
                                                        params={
                                                            "track_id": song['track_id'],
                                                            "artist_id": song['artist_id'],
                                                            "interaction_type": "liked"
                                                        }
                                                    )
                                                    st.success("❤️")
                                                except:
                                                    pass
                        else:
                            st.warning("No similar artists found. Try a different artist name!")
                    else:
                        st.error("Service unavailable")
                except Exception as e:
                    st.error(f"Error: {e}")
    
    elif rec_method == "Genre Explorer":
        st.subheader("🎭 Explore by Genre")
        
        col1, col2 = st.columns(2)
        with col1:
            primary_genre = st.selectbox(
                "Primary Genre:",
                ["rock", "pop", "jazz", "classical", "electronic", "hip-hop", "country", "blues", "folk", "metal"]
            )
        with col2:
            secondary_genre = st.selectbox(
                "Secondary Genre (optional):",
                ["", "alternative", "indie", "experimental", "fusion", "acoustic", "ambient", "progressive"]
            )
        
        rec_limit = st.slider("Number of recommendations:", 5, 20, 10, key="genre_rec_limit")
        
        if st.button("🎵 Explore Genre", type="primary"):
            genre_query = primary_genre
            if secondary_genre:
                genre_query += f" {secondary_genre}"
            
            with st.spinner(f"Exploring {genre_query} music..."):
                try:
                    response = requests.get(f"{API_GATEWAY_URL}/api/recommendations/query", 
                                          params={"query": f"genre:{genre_query}", "limit": rec_limit})
                    
                    if response.status_code == 200:
                        data = response.json()
                        recommendations = data.get("recommendations", [])
                        
                        if recommendations:
                            st.success(f"🎉 Discovered {len(recommendations)} {genre_query} tracks!")
                            
                            # Display in a card-like format
                            cols = st.columns(3)
                            for i, rec in enumerate(recommendations):
                                col = cols[i % 3]
                                with col:
                                    with st.container():
                                        st.markdown(f"**{rec['track_title']}**")
                                        st.markdown(f"*{rec['artist_name']}*")
                                        st.markdown(f"⭐ {rec['score']}/100")
                                        
                                        if st.button("❤️ Like", key=f"like_genre_{rec['track_id']}"):
                                            try:
                                                requests.post(
                                                    f"{API_GATEWAY_URL}/api/users/{username}/listening-history",
                                                    params={
                                                        "track_id": rec['track_id'],
                                                        "artist_id": rec['artist_id'],
                                                        "interaction_type": "liked"
                                                    }
                                                )
                                                st.success("❤️")
                                            except:
                                                pass
                                        st.markdown("---")
                        else:
                            st.warning(f"No {genre_query} music found. Try a different genre combination!")
                    else:
                        st.error("Service unavailable")
                except Exception as e:
                    st.error(f"Error: {e}")

with tab5:
    st.header("💾 Saved Data")
    
    data_tab1, data_tab2, data_tab3 = st.tabs(["Artists", "Albums", "My Activity"])
    
    with data_tab1:
        st.subheader("Saved Artists")
        try:
            response = requests.get(f"{API_GATEWAY_URL}/api/artists", params={"limit": 100})
            if response.status_code == 200:
                data = response.json()
                artists = data.get("artists", [])
                
                if artists:
                    df = pd.DataFrame(artists)
                    st.dataframe(df, use_container_width=True)
                    st.info(f"Total saved artists: {len(artists)}")
                else:
                    st.info("No artists saved yet")
            else:
                st.error("Could not load saved artists")
        except Exception as e:
            st.error(f"Error: {e}")
    
    with data_tab2:
        st.subheader("Saved Albums")
        st.info("Album listing feature coming soon...")
    
    with data_tab3:
        st.subheader("My Listening Activity")
        if username == "guest":
            st.warning("Set a username to track your activity!")
        else:
            st.info("Activity tracking feature - shows your liked songs, saved tracks, and listening patterns")
            # Here you could add code to fetch and display user's listening history

with tab6:
    st.header("🔧 Service Status & Algorithm Verification")
    
    # Check if enhanced algorithm is running
    st.subheader("🧠 Algorithm Status")
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/recommendations/query", 
                              params={"query": "test algorithm", "limit": 1}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "query_analyzed" in data:
                st.success("✅ **Enhanced Algorithm Active**")
                st.json(data.get("query_analyzed", {}))
                
                # Show version info
                health_response = requests.get(f"{API_GATEWAY_URL}/health", timeout=5)
                if health_response.status_code == 200:
                    st.write("Gateway healthy")
            else:
                st.error("❌ **Old Algorithm Running** - Rebuild needed!")
                st.code("""
# To fix, run:
docker-compose down
docker-compose build --no-cache recommendation-service
docker-compose up
                """)
        else:
            st.error(f"❌ Recommendation service error: {response.status_code}")
    except Exception as e:
        st.error(f"❌ Cannot verify algorithm: {e}")
    
    st.subheader("🏥 Service Health")
    
    services = [
        ("API Gateway", f"{API_GATEWAY_URL}/health"),
        ("Recommendation Service", f"http://localhost:8003/health" if API_GATEWAY_URL == "http://localhost:8000" else "Internal")
    ]
    
    for service_name, health_url in services:
        try:
            if health_url == "Internal":
                st.info(f"ℹ️ {service_name} (Internal Docker service)")
                continue
                
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                service_data = response.json()
                st.success(f"✅ {service_name}")
                
                # Show version if available
                if "version" in service_data:
                    st.caption(f"Version: {service_data['version']}")
                    
            else:
                st.error(f"❌ {service_name} (Status: {response.status_code})")
        except Exception as e:
            st.error(f"❌ {service_name} - {str(e)[:50]}...")

# Footer
st.markdown("---")
st.markdown("🔧 Built with Streamlit, FastAPI, Claude.ai for building Enhanced AI Recommendations | Version 2.0")
