import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime
import os
from PIL import Image
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import Counter, defaultdict
import numpy as np
import pandas as pd

# Configuration - Use environment variable with fallback
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")

# Set page configuration
st.set_page_config(page_title="Orchestr8r: Continuous Delivery of your Perfect Playlist", page_icon="ui/static/images/orchestr8r_8.ico", layout="wide", initial_sidebar_state="collapsed")

# Initialize session state
if 'username' not in st.session_state:
    st.session_state.username = "guest"


if 'search_analytics' not in st.session_state:
    st.session_state.search_analytics = []
if 'recommendation_history' not in st.session_state:
    st.session_state.recommendation_history = []

def create_score_distribution_chart(recommendations):
    """Create a histogram showing the distribution of recommendation scores"""
    if not recommendations:
        return None
    
    scores = [rec['score'] for rec in recommendations]
    
    fig = go.Figure(data=[
        go.Histogram(
            x=scores,
            nbinsx=10,
            marker_color='#6366F1',
            opacity=0.75,
            text=[f"Count: {len([s for s in scores if i*10 <= s < (i+1)*10])}" for i in range(10)],
            textposition='auto'
        )
    ])
    
    fig.update_layout(
        title="🎯 Recommendation Score Distribution",
        xaxis_title="Score Range",
        yaxis_title="Number of Songs",
        height=350,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_artist_diversity_donut(recommendations):
    """Create a donut chart showing artist diversity"""
    if not recommendations:
        return None
    
    artist_counts = Counter([rec['artist_name'] for rec in recommendations])
    
    # Limit to top 8 artists, group others as "Others"
    top_artists = dict(artist_counts.most_common(8))
    others_count = sum(artist_counts.values()) - sum(top_artists.values())
    
    if others_count > 0:
        top_artists['Others'] = others_count
    
    colors = ['#6366F1', '#8B5CF6', '#EC4899', '#EF4444', '#F97316', 
              '#EAB308', '#22C55E', '#06B6D4', '#64748B']
    
    fig = go.Figure(data=[
        go.Pie(
            labels=list(top_artists.keys()),
            values=list(top_artists.values()),
            hole=0.4,
            marker_colors=colors[:len(top_artists)],
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>Songs: %{value}<br>Percentage: %{percent}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title="🎤 Artist Distribution",
        height=400,
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.01)
    )
    
    return fig

def create_recommendation_strategy_breakdown(recommendations):
    """Create a bar chart showing different recommendation strategies used"""
    if not recommendations:
        return None
    
    # Extract strategy types
    strategies = []
    for rec in recommendations:
        rec_type = rec.get('recommendation_type', 'unknown')
        if 'diverse_genre' in rec_type:
            strategies.append('Genre-Based')
        elif 'diverse_tag' in rec_type:
            strategies.append('Tag-Based')
        elif 'diverse_fallback' in rec_type:
            strategies.append('Direct Search')
        else:
            strategies.append('Other')
    
    strategy_counts = Counter(strategies)
    
    fig = go.Figure(data=[
        go.Bar(
            x=list(strategy_counts.keys()),
            y=list(strategy_counts.values()),
            marker_color=['#6366F1', '#8B5CF6', '#EC4899', '#EF4444'],
            text=list(strategy_counts.values()),
            textposition='auto'
        )
    ])
    
    fig.update_layout(
        title="🔍 Recommendation Strategies Used",
        xaxis_title="Strategy Type",
        yaxis_title="Number of Songs",
        height=350,
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_score_vs_popularity_scatter(recommendations):
    """Create scatter plot showing score vs artist popularity"""
    if not recommendations or len(recommendations) < 3:
        return None
    
    # Calculate artist popularity based on frequency in results
    all_artists = [rec['artist_name'] for rec in st.session_state.recommendation_history]
    artist_popularity = Counter(all_artists)
    
    data = []
    for rec in recommendations:
        popularity = artist_popularity.get(rec['artist_name'], 1)
        data.append({
            'track': rec['track_title'][:30] + '...' if len(rec['track_title']) > 30 else rec['track_title'],
            'artist': rec['artist_name'],
            'score': rec['score'],
            'popularity': popularity,
            'strategy': rec.get('recommendation_type', 'unknown').replace('_', ' ').title()
        })
    
    df = pd.DataFrame(data)
    
    fig = px.scatter(
        df, 
        x='popularity', 
        y='score',
        color='strategy',
        size=[20] * len(df),  # Uniform size
        hover_data=['track', 'artist'],
        title="📊 Score vs Artist Discovery Frequency",
        labels={'popularity': 'Times Artist Appeared', 'score': 'Recommendation Score'},
        color_discrete_sequence=['#6366F1', '#8B5CF6', '#EC4899', '#EF4444', '#F97316']
    )
    
    fig.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)')
    return fig

def create_search_quality_gauge(recommendations, query_analysis):
    """Create a gauge showing search quality metrics"""
    if not recommendations:
        return None
    
    # Calculate quality score
    avg_score = np.mean([rec['score'] for rec in recommendations])
    unique_artists = len(set([rec['artist_name'] for rec in recommendations]))
    diversity_score = (unique_artists / len(recommendations)) * 100
    
    # Overall quality combines average score and diversity
    overall_quality = (avg_score * 0.7) + (diversity_score * 0.3)
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = overall_quality,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "🎯 Search Quality Score"},
        delta = {'reference': 80, 'increasing': {'color': "#22C55E"}, 'decreasing': {'color': "#EF4444"}},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "#6366F1"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 80], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(height=300)
    return fig

def create_session_trend_line(search_history):
    """Create a line chart showing search session trends"""
    if len(search_history) < 2:
        return None
    
    search_numbers = list(range(1, len(search_history) + 1))
    avg_scores = []
    unique_artists = []
    
    for search in search_history:
        if search['recommendations']:
            avg_score = np.mean([rec['score'] for rec in search['recommendations']])
            unique_count = len(set([rec['artist_name'] for rec in search['recommendations']]))
        else:
            avg_score = 0
            unique_count = 0
        avg_scores.append(avg_score)
        unique_artists.append(unique_count)
    
    fig = make_subplots(
        rows=1, cols=1,
        subplot_titles=['Search Session Quality Trend']
    )
    
    fig.add_trace(
        go.Scatter(
            x=search_numbers,
            y=avg_scores,
            mode='lines+markers',
            name='Average Score',
            line=dict(color='#6366F1', width=3),
            marker=dict(size=8)
        )
    )
    
    fig.update_layout(
        title="📈 Your Search Session Progress",
        xaxis_title="Search Number",
        yaxis_title="Average Score",
        height=300,
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_genre_detection_radar(query_analysis):
    """Create radar chart showing detected musical elements"""
    if not query_analysis:
        return None
    
    # Simulate genre/mood detection confidence
    categories = ['Genre Match', 'Mood Detection', 'Artist Relevance', 'Diversity', 'Accuracy']
    values = []
    
    # Calculate values based on query analysis
    genre_conf = 90 if query_analysis.get('detected_genre') else 30
    artist_conf = min(100, (query_analysis.get('unique_artists', 0) * 10))
    diversity_conf = 85 if 'diverse' in str(query_analysis.get('strategy_used', '')) else 60
    
    values = [genre_conf, 75, artist_conf, diversity_conf, 80]  # Mock some values
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Algorithm Confidence',
        line_color='#6366F1',
        fillcolor='rgba(99, 102, 241, 0.3)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        title="🧠 Algorithm Analysis Confidence",
        height=400
    )
    
    return fig



# Function to load images safely
def load_image(image_path):
    """Load image with error handling"""
    try:
        if os.path.exists(image_path):
            return Image.open(image_path)
        else:
            st.warning(f"Image not found: {image_path}")
            return None
    except Exception as e:
        st.error(f"Error loading image: {e}")
        return None

# Define image paths relative to the ui directory
def get_image_path(filename):
    """Get the correct image path whether running locally or in Docker"""
    # Try different possible paths
    possible_paths = [
        f"ui/static/images/{filename}",  # From project root
        f"static/images/{filename}",     # From ui directory
        f"./static/images/{filename}",   # Relative from current
        filename  # Direct filename if in same directory
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # If no file found, return the most likely path for error reporting
    return f"ui/static/images/{filename}"

# Load and display header image/logo
logo_path = get_image_path("orchestr8r_logo.png")
logo_image = load_image(logo_path)
if logo_image:
        st.image(logo_image, caption=None, use_column_width=True)

st.title("Orchestr8r: Continuous Delivery of your Perfect Playlist \nMusic Recommendation System using Microservices Architecture")

       

st.markdown("Discover music with smart recommendations that understand artists, genres, and moods")

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

# Apply CSS for coloring the active tab title
st.markdown("""
<style>
.stTabs [aria-selected="true"] {
    color: white !important;
    background-color: #6366F1 !important; /* Dark Blue background */
    border-radius: 15px 15px 0px 0px; /* Applies rounding to top corners only */
    overflow: hidden !important; /* Ensures the rounded corners are visible */
    padding-top: 20px; /* Adjust top padding */
    padding-bottom: 20px; /* Adjust bottom padding */
    padding-left: 15px; /* Adjust left padding */
    padding-right: 15px; /* Adjust right padding */
        
}
.stTabs [data-baseweb="tab-list"] {
    gap: 1px; /* Adjust gap between tabs */
}
</style>
""", unsafe_allow_html=True)

# Main navigation
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🏠 Home", "🎤 Search Artists", "💿 Search Albums", "🎯 Recommendations", "💾 Saved Data", "🔧 Info for Nerds"])

with tab1:
    st.header("🏠 Enhanced Music Discovery with Visual Analytics")
    
    # Search interface (keep existing)
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
                # Your existing API call code here...
                params = {"query": query, "limit": 10}
                response = requests.get(f"{API_GATEWAY_URL}/api/recommendations/query", 
                                      params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    recommendations = data.get("recommendations", [])
                    query_analysis = data.get("query_analyzed", {})
                    
                    # Store for analytics
                    search_entry = {
                        'query': query,
                        'recommendations': recommendations,
                        'timestamp': datetime.now(),
                        'analysis': query_analysis
                    }
                    st.session_state.search_analytics.append(search_entry)
                    st.session_state.recommendation_history.extend(recommendations)
                    
                    if recommendations:
                        st.success(f"🎉 Found {len(recommendations)} smart recommendations!")
                        
                        # Create tabbed interface for results
                        result_tabs = st.tabs(["📊 Visual Overview", "🎵 Song List", "📈 Analytics", "🧠 Algorithm Insights"])
                        
                        with result_tabs[0]:  # Visual Overview
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Score distribution
                                score_chart = create_score_distribution_chart(recommendations)
                                if score_chart:
                                    st.plotly_chart(score_chart, use_container_width=True)
                                
                                # Recommendation strategies
                                strategy_chart = create_recommendation_strategy_breakdown(recommendations)
                                if strategy_chart:
                                    st.plotly_chart(strategy_chart, use_container_width=True)
                            
                            with col2:
                                # Artist diversity
                                diversity_chart = create_artist_diversity_donut(recommendations)
                                if diversity_chart:
                                    st.plotly_chart(diversity_chart, use_container_width=True)
                                
                                # Quality gauge
                                quality_gauge = create_search_quality_gauge(recommendations, query_analysis)
                                if quality_gauge:
                                    st.plotly_chart(quality_gauge, use_container_width=True)
                        
                        with result_tabs[1]:  # Song List
                            # Your existing song list display code
                            for i, rec in enumerate(recommendations, 1):
                                # ... existing song display code ...
                                pass
                        
                        with result_tabs[2]:  # Analytics
                            if len(st.session_state.search_analytics) > 1:
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    # Session trend
                                    trend_chart = create_session_trend_line(st.session_state.search_analytics)
                                    if trend_chart:
                                        st.plotly_chart(trend_chart, use_container_width=True)
                                
                                with col2:
                                    # Score vs popularity scatter
                                    scatter_chart = create_score_vs_popularity_scatter(recommendations)
                                    if scatter_chart:
                                        st.plotly_chart(scatter_chart, use_container_width=True)
                                
                                # Session statistics
                                st.subheader("📊 Session Statistics")
                                col1, col2, col3, col4 = st.columns(4)
                                
                                total_searches = len(st.session_state.search_analytics)
                                total_songs = len(st.session_state.recommendation_history)
                                unique_artists = len(set([r['artist_name'] for r in st.session_state.recommendation_history]))
                                avg_score = np.mean([r['score'] for r in st.session_state.recommendation_history])
                                
                                with col1:
                                    st.metric("Total Searches", total_searches)
                                with col2:
                                    st.metric("Songs Discovered", total_songs)
                                with col3:
                                    st.metric("Unique Artists", unique_artists)
                                with col4:
                                    st.metric("Avg Score", f"{avg_score:.1f}")
                            else:
                                st.info("Search more to see analytics trends!")
                        
                        with result_tabs[3]:  # Algorithm Insights
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Genre detection radar
                                radar_chart = create_genre_detection_radar(query_analysis)
                                if radar_chart:
                                    st.plotly_chart(radar_chart, use_container_width=True)
                            
                            with col2:
                                # Algorithm analysis details
                                st.subheader("🔍 Query Analysis")
                                if query_analysis:
                                    for key, value in query_analysis.items():
                                        if key != 'error':
                                            st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                                
                                # Performance metrics
                                st.subheader("⚡ Performance")
                                processing_time = query_analysis.get('processing_time', 'N/A')
                                st.write(f"**Processing Time:** {processing_time}")
                                st.write(f"**Algorithm Version:** {data.get('algorithm_version', 'N/A')}")
            
            except Exception as e:
                st.error(f"Error: {e}")
    
    # Add session management
    if st.session_state.recommendation_history:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 View Complete Session Analytics"):
                # Show comprehensive session view
                pass
        with col2:
            if st.button("🗑️ Clear Session Data"):
                st.session_state.search_analytics = []
                st.session_state.recommendation_history = []
                st.success("Session data cleared!")
                st.rerun()

with tab2:
    st.header("🎤 Search Artists")
    
    query = st.text_input("Enter artist name:", placeholder="e.g., Radiohead")
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
        artist_name = st.text_input("Artist name:", placeholder="e.g., Radiohead")
    with col2:
        album_title = st.text_input("Album title:", placeholder="e.g., Pablo Honey")
    
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
                                  placeholder="e.g., Kendrick Lamar, Chappell Roan, Miles Davis")
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
    st.header("🔧 Service Status & Algorithm Information & Verification")
    
    # Add explanation of algorithm improvements
    st.info("""
    🎯 **Enhanced Algorithm**: 
    - **Artist Focus**: 30% weight on matching artists
    - **Genre Intelligence**: 25% weight on musical genres  
    - **Mood Detection**: Understands "upbeat", "relaxing", "aggressive", etc.
    - **Smart Search**: Multiple search strategies per query
    - **Title Balance**: Only 25% weight (down from 90%+)
    """)
    

    # Check if enhanced algorithm is running
    st.subheader("🧠 Algorithm Status")
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/recommendations/query", 
                              params={"query": "test algorithm", "limit": 1}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "query_analyzed" in data:
                st.success("✅ **Enhanced Algorithm Active**")
                #st.json(data.get("query_analyzed", {}))
                
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
st.markdown("🔧 Built with Streamlit, FastAPI, and Claude.ai for building Enhanced AI Recommendations | Version 0.2 beta")
