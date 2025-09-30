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
from sqlalchemy import create_engine, text

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
    
    # Create bins manually for better control
    bins = list(range(0, 101, 10))  # [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    bin_labels = ['0-9', '10-19', '20-29', '30-39', '40-49', '50-59', '60-69', '70-79', '80-89', '90-100']
    
    # Count scores in each bin
    bin_counts = []
    for i in range(len(bins) - 1):
        count = sum(1 for score in scores if bins[i] <= score < bins[i + 1])
        bin_counts.append(count)
    
    # Handle the last bin (90-100) to include 100
    bin_counts[-1] = sum(1 for score in scores if 90 <= score <= 100)
    
    # Create bar chart instead of histogram for better control
    fig = go.Figure(data=[
        go.Bar(
            x=bin_labels,
            y=bin_counts,
            marker_color='#6366F1',
            opacity=0.75,
            text=[f"Count: {count}" for count in bin_counts],
            textposition='auto',
            hovertemplate='<b>Score Range: %{x}</b><br>Number of Songs: %{y}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title="🎯 Recommendation Score Distribution",
        xaxis_title="Score Range",
        yaxis_title="Number of Songs",
        height=350,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(tickangle=45)
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

def fetch_artist_countries(recommendations, api_gateway_url):
    """
    Fetch country information for artists in recommendations
    
    Args:
        recommendations: List of recommendation dicts with artist_id
        api_gateway_url: Base URL for API gateway
    
    Returns:
        Dict mapping artist_id to country code
    """
    artist_countries = {}
    
    for rec in recommendations:
        artist_id = rec.get('artist_id')
        if artist_id and artist_id not in artist_countries:
            try:
                # Fetch artist details from your API
                response = requests.get(
                    f"{api_gateway_url}/api/artists/{artist_id}",
                    timeout=5
                )
                if response.status_code == 200:
                    artist_data = response.json()
                    country = artist_data.get('country')
                    if country:
                        artist_countries[artist_id] = country
            except Exception as e:
                print(f"Error fetching artist {artist_id}: {e}")
                continue
    
    return artist_countries

def create_artist_origin_map(recommendations, api_gateway_url):
    """
    Create an interactive world map showing artist countries of origin
    
    Args:
        recommendations: List of recommendation dicts
        api_gateway_url: Base URL for API gateway
        
    Returns:
        Plotly figure object or None
    """
    if not recommendations:
        return None
    
    # Fetch country data for all artists
    import streamlit as st
    with st.spinner("Fetching artist country data..."):
        artist_countries = fetch_artist_countries(recommendations, api_gateway_url)
    
    if not artist_countries:
        return None
    
    # Map artist IDs to countries in recommendations
    countries_list = []
    for rec in recommendations:
        artist_id = rec.get('artist_id')
        if artist_id in artist_countries:
            country = artist_countries[artist_id]
            if country:  # Only add if country is not None or empty
                countries_list.append({
                    'country': country,
                    'artist_name': rec['artist_name'],
                    'track_title': rec['track_title']
                })
    
    if not countries_list:
        return None
    
    # Debug output
    st.write(f"📍 Found {len(countries_list)} tracks with country information from {len(set(c['country'] for c in countries_list))} countries")
    
    # Count artists per country
    country_counts = Counter([item['country'] for item in countries_list])
    
    # Convert ISO country codes to full names for better display
    country_name_mapping = {
        'US': 'United States',
        'GB': 'United Kingdom',
        'CA': 'Canada',
        'AU': 'Australia',
        'DE': 'Germany',
        'FR': 'France',
        'IT': 'Italy',
        'ES': 'Spain',
        'JP': 'Japan',
        'KR': 'South Korea',
        'BR': 'Brazil',
        'MX': 'Mexico',
        'AR': 'Argentina',
        'SE': 'Sweden',
        'NO': 'Norway',
        'FI': 'Finland',
        'NL': 'Netherlands',
        'BE': 'Belgium',
        'CH': 'Switzerland',
        'AT': 'Austria',
        'IE': 'Ireland',
        'NZ': 'New Zealand',
        'ZA': 'South Africa',
        'IN': 'India',
        'CN': 'China',
        'RU': 'Russia',
        'PL': 'Poland',
        'CZ': 'Czech Republic',
        'DK': 'Denmark',
        'PT': 'Portugal',
        'GR': 'Greece',
        'TR': 'Turkey',
        'IS': 'Iceland',
        'JM': 'Jamaica',
        'CU': 'Cuba',
        'CL': 'Chile',
        'CO': 'Colombia',
        'PE': 'Peru',
        'VE': 'Venezuela',
        'EG': 'Egypt',
        'NG': 'Nigeria',
        'KE': 'Kenya',
        'IL': 'Israel',
        'AE': 'United Arab Emirates',
        'SG': 'Singapore',
        'TH': 'Thailand',
        'MY': 'Malaysia',
        'PH': 'Philippines',
        'ID': 'Indonesia',
        'VN': 'Vietnam',
        'HK': 'Hong Kong',
        'TW': 'Taiwan'
    }
    
    # Prepare data for choropleth
    map_data = []
    for country_code, count in country_counts.items():
        country_name = country_name_mapping.get(country_code, country_code)
        
        # Get artist names from this country
        artists_from_country = [
            item['artist_name'] 
            for item in countries_list 
            if item['country'] == country_code
        ]
        unique_artists = list(set(artists_from_country))
        
        map_data.append({
            'country_code': country_code,
            'country_name': country_name,
            'artist_count': count,
            'artists': ', '.join(unique_artists[:5])  # Show up to 5 artists
        })
    
    df = pd.DataFrame(map_data)
    
    # Debug: Show what countries we have
    print(f"Countries found: {df['country_code'].tolist()}")
    print(f"Artist counts: {df['artist_count'].tolist()}")
    
    # Convert 2-letter ISO codes to 3-letter ISO codes for Plotly
    iso2_to_iso3 = {
        'US': 'USA', 'GB': 'GBR', 'CA': 'CAN', 'AU': 'AUS', 'DE': 'DEU',
        'FR': 'FRA', 'IT': 'ITA', 'ES': 'ESP', 'JP': 'JPN', 'KR': 'KOR',
        'BR': 'BRA', 'MX': 'MEX', 'AR': 'ARG', 'SE': 'SWE', 'NO': 'NOR',
        'FI': 'FIN', 'NL': 'NLD', 'BE': 'BEL', 'CH': 'CHE', 'AT': 'AUT',
        'IE': 'IRL', 'NZ': 'NZL', 'ZA': 'ZAF', 'IN': 'IND', 'CN': 'CHN',
        'RU': 'RUS', 'PL': 'POL', 'CZ': 'CZE', 'DK': 'DNK', 'PT': 'PRT',
        'GR': 'GRC', 'TR': 'TUR', 'IS': 'ISL', 'JM': 'JAM', 'CU': 'CUB',
        'CL': 'CHL', 'CO': 'COL', 'PE': 'PER', 'VE': 'VEN', 'EG': 'EGY',
        'NG': 'NGA', 'KE': 'KEN', 'IL': 'ISR', 'AE': 'ARE', 'SG': 'SGP',
        'TH': 'THA', 'MY': 'MYS', 'PH': 'PHL', 'ID': 'IDN', 'VN': 'VNM',
        'HK': 'HKG', 'TW': 'TWN', 'UA': 'UKR', 'RO': 'ROU', 'HU': 'HUN',
        'HR': 'HRV', 'SK': 'SVK', 'SI': 'SVN', 'BG': 'BGR', 'LT': 'LTU',
        'LV': 'LVA', 'EE': 'EST', 'RS': 'SRB', 'BA': 'BIH', 'MK': 'MKD',
        'AL': 'ALB', 'MA': 'MAR', 'TN': 'TUN', 'DZ': 'DZA', 'LY': 'LBY',
        'SA': 'SAU', 'IQ': 'IRQ', 'IR': 'IRN', 'AF': 'AFG', 'PK': 'PAK',
        'BD': 'BGD', 'LK': 'LKA', 'NP': 'NPL', 'MM': 'MMR', 'KH': 'KHM',
        'LA': 'LAO', 'MN': 'MNG', 'KZ': 'KAZ', 'UZ': 'UZB', 'TM': 'TKM',
        'KG': 'KGZ', 'TJ': 'TJK', 'GE': 'GEO', 'AM': 'ARM', 'AZ': 'AZE'
    }
    
    # Convert country codes to ISO-3
    df['country_code_iso3'] = df['country_code'].map(lambda x: iso2_to_iso3.get(x, x))
    
    # Create choropleth map with ISO-3 codes
    fig = go.Figure(data=go.Choropleth(
        locations=df['country_code_iso3'],  # Use ISO-3 codes
        z=df['artist_count'],
        locationmode='ISO-3',
        text=df['country_name'],
        colorscale=[
            [0, '#E0E7FF'],      # Very light indigo
            [0.2, '#C7D2FE'],    # Light indigo
            [0.4, '#A5B4FC'],    # Medium light indigo
            [0.6, '#818CF8'],    # Medium indigo
            [0.8, '#6366F1'],    # Indigo (your primary color)
            [1.0, '#4F46E5']     # Dark indigo
        ],
        colorbar=dict(
            title="Number of<br>Artists",
            tickmode='linear',
            tick0=0,
            dtick=1 if max(df['artist_count']) < 10 else None,
            len=0.7,
            thickness=15
        ),
        hovertemplate='<b>%{text}</b><br>' +
                      'Artists: %{z}<br>' +
                      '<extra></extra>',
        marker_line_color='white',
        marker_line_width=0.5,
        showscale=True
    ))
    
    fig.update_layout(
        title={
            'text': '🌍 Artist Countries of Origin',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#262730'}
        },
        geo=dict(
            showframe=False,
            showcoastlines=True,
            coastlinecolor='#64748B',
            projection_type='natural earth',
            bgcolor='rgba(0,0,0,0)',
            landcolor='#F1F5F9',
            oceancolor='#E0F2FE',
            showland=True,
            showcountries=True,
            countrycolor='white'
        ),
        height=500,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    return fig

def create_simple_country_visualization(recommendations, api_gateway_url):
    """
    Simpler country visualization as a fallback or alternative
    Shows countries as a sunburst or treemap
    """
    if not recommendations:
        return None
    
    artist_countries = fetch_artist_countries(recommendations, api_gateway_url)
    
    if not artist_countries:
        return None
    
    # Build data structure
    country_artists = {}
    for rec in recommendations:
        artist_id = rec.get('artist_id')
        if artist_id in artist_countries:
            country = artist_countries[artist_id]
            if country:
                if country not in country_artists:
                    country_artists[country] = []
                country_artists[country].append(rec['artist_name'])
    
    if not country_artists:
        return None
    
    # Country name mapping
    country_names = {
        'US': 'United States', 'GB': 'United Kingdom', 'CA': 'Canada',
        'AU': 'Australia', 'DE': 'Germany', 'FR': 'France', 'IT': 'Italy',
        'ES': 'Spain', 'JP': 'Japan', 'KR': 'South Korea', 'BR': 'Brazil',
        'MX': 'Mexico', 'SE': 'Sweden', 'NO': 'Norway', 'FI': 'Finland',
        'NL': 'Netherlands', 'BE': 'Belgium', 'CH': 'Switzerland', 'AT': 'Austria'
    }
    
    # Prepare sunburst data
    labels = ['All Countries']
    parents = ['']
    values = [0]
    colors = ['#6366F1']
    
    for country_code, artists in country_artists.items():
        country_name = country_names.get(country_code, country_code)
        unique_artists = list(set(artists))
        
        labels.append(country_name)
        parents.append('All Countries')
        values.append(len(artists))
        colors.append('#8B5CF6')
        
        # Add individual artists
        for artist in unique_artists[:3]:  # Limit to top 3 artists per country
            labels.append(artist)
            parents.append(country_name)
            values.append(artists.count(artist))
            colors.append('#A5B4FC')
    
    fig = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(colors=colors),
        branchvalues="total",
        hovertemplate='<b>%{label}</b><br>Tracks: %{value}<extra></extra>'
    ))
    
    fig.update_layout(
        title='🌍 Artist Distribution by Country',
        height=500,
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_country_bar_chart(recommendations, api_gateway_url):
    """
    Create a horizontal bar chart showing top countries by artist count
    Companion chart to the world map
    """
    if not recommendations:
        return None
    
    # Fetch country data
    artist_countries = fetch_artist_countries(recommendations, api_gateway_url)
    
    if not artist_countries:
        return None
    
    # Count countries
    countries_list = []
    for rec in recommendations:
        artist_id = rec.get('artist_id')
        if artist_id in artist_countries:
            countries_list.append(artist_countries[artist_id])
    
    if not countries_list:
        return None
    
    country_counts = Counter(countries_list)
    
    # Get top 10 countries
    top_countries = dict(country_counts.most_common(10))
    
    # Country name mapping
    country_name_mapping = {
        'US': '🇺🇸 United States',
        'GB': '🇬🇧 United Kingdom',
        'CA': '🇨🇦 Canada',
        'AU': '🇦🇺 Australia',
        'DE': '🇩🇪 Germany',
        'FR': '🇫🇷 France',
        'IT': '🇮🇹 Italy',
        'ES': '🇪🇸 Spain',
        'JP': '🇯🇵 Japan',
        'KR': '🇰🇷 South Korea',
        'BR': '🇧🇷 Brazil',
        'MX': '🇲🇽 Mexico',
        'SE': '🇸🇪 Sweden',
        'NO': '🇳🇴 Norway',
    }
    
    countries_display = [country_name_mapping.get(code, code) for code in top_countries.keys()]
    
    fig = go.Figure(data=[
        go.Bar(
            y=countries_display,
            x=list(top_countries.values()),
            orientation='h',
            marker_color='#6366F1',
            text=list(top_countries.values()),
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>Artists: %{x}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title="🎤 Top Countries by Artist Count",
        xaxis_title="Number of Artists",
        yaxis_title="",
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis={'categoryorder': 'total ascending'},
        margin=dict(l=150, r=20, t=50, b=50)
    )
    
    return fig


def add_database_viewer_tab():
    """Add this to your Streamlit app for web-based database viewing"""
    
    st.header("🗄️ Database Explorer")
    
    # Database connection - determine if running in Docker or locally
    # If API_GATEWAY_URL contains 'api-gateway', we're in Docker
    API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
    
    if 'api-gateway' in API_GATEWAY_URL:
        # Running inside Docker - use Docker service name
        DATABASE_URL = "postgresql://user:password@postgres:5432/musicbrainz"
    else:
        # Running locally - use localhost
        DATABASE_URL = "postgresql://user:password@localhost:5432/musicbrainz"
    
    # Or simply use the environment variable directly
    DATABASE_URL = os.getenv("DATABASE_URL", DATABASE_URL)
    
    try:
        # Table selection
        table = st.selectbox("Select table to view:", 
                           ["artists", "albums", "tracks", "user_profiles", "recommendations"])
        
        # Limit selection
        limit = st.slider("Number of records to show:", 1, 100, 20)
        
        if st.button("Query Database"):
            with st.spinner("Querying database..."):
                # Use pandas to read from database
                query = f"SELECT * FROM {table} LIMIT {limit}"
                df = pd.read_sql(query, DATABASE_URL)
                
                if not df.empty:
                    st.success(f"Found {len(df)} records")
                    st.dataframe(df, use_container_width=True)
                    
                    # Show basic stats
                    st.subheader("📊 Table Statistics")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        total_query = f"SELECT COUNT(*) as count FROM {table}"
                        total_df = pd.read_sql(total_query, DATABASE_URL)
                        st.metric("Total Records", total_df['count'][0])
                    
                    with col2:
                        st.metric("Columns", len(df.columns))
                    
                    with col3:
                        st.metric("Showing", len(df))
                    
                    # Show column info
                    st.subheader("🏗️ Table Structure")
                    structure_query = f"""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_name = '{table}'
                        ORDER BY ordinal_position
                    """
                    structure_df = pd.read_sql(structure_query, DATABASE_URL)
                    st.dataframe(structure_df, use_container_width=True)
                else:
                    st.warning("No data found in table")
        
        # Custom SQL query section
        st.subheader("📝 Custom SQL Query")
        custom_query = st.text_area("Enter your SQL query: *Note: SQL commands such as SELECT * FROM artists WHERE country = 'US' LIMIT 10 are supported. Commands like DROP, DELETE, UPDATE are not allowed for safety.*", 
                                   placeholder="SELECT * FROM artists WHERE country = 'US' LIMIT 10")
        
        if st.button("Execute Query") and custom_query:
            try:
                custom_df = pd.read_sql(custom_query, DATABASE_URL)
                st.success(f"Query executed successfully! {len(custom_df)} rows returned.")
                st.dataframe(custom_df, use_container_width=True)
            except Exception as e:
                st.error(f"Query error: {e}")
    
    except Exception as e:
        st.error(f"Database connection error: {e}")


def fetch_artist_timeline_data(recommendations, api_gateway_url):
    """
    Fetch begin_date and end_date for artists from the database
    
    Args:
        recommendations: List of recommendation dicts with artist_id
        api_gateway_url: Base URL for API gateway
    
    Returns:
        Dict mapping artist_id to timeline data
    """
    artist_timeline = {}
    
    for rec in recommendations:
        artist_id = rec.get('artist_id')
        if artist_id and artist_id not in artist_timeline:
            try:
                response = requests.get(
                    f"{api_gateway_url}/api/artists/{artist_id}",
                    timeout=5
                )
                if response.status_code == 200:
                    artist_data = response.json()
                    begin_date = artist_data.get('begin_date', '')
                    end_date = artist_data.get('end_date', '')
                    
                    # Extract year from date strings (format: YYYY-MM-DD or YYYY)
                    begin_year = None
                    end_year = None
                    
                    if begin_date:
                        try:
                            begin_year = int(begin_date.split('-')[0]) if begin_date else None
                        except (ValueError, IndexError):
                            pass
                    
                    if end_date:
                        try:
                            end_year = int(end_date.split('-')[0]) if end_date else None
                        except (ValueError, IndexError):
                            pass
                    
                    artist_timeline[artist_id] = {
                        'begin_year': begin_year,
                        'end_year': end_year,
                        'begin_date': begin_date,
                        'end_date': end_date
                    }
            except Exception as e:
                print(f"Error fetching artist {artist_id}: {e}")
                continue
    
    return artist_timeline

def classify_musical_era(begin_year, end_year=None):
    """
    Classify an artist into a musical era based on their active period
    
    Args:
        begin_year: Year artist started (int)
        end_year: Year artist ended (int or None for still active)
    
    Returns:
        String representing the musical era
    """
    if not begin_year:
        return 'Unknown Era'
    
    # Determine the primary active period (use begin_year or midpoint)
    if end_year and end_year > begin_year:
        primary_year = begin_year + (end_year - begin_year) // 2
    else:
        primary_year = begin_year
    
    # Musical era classifications
    if primary_year < 1920:
        return '🎻 Classical Era (pre-1920)'
    elif 1920 <= primary_year < 1950:
        return '🎺 Jazz Age & Swing (1920-1949)'
    elif 1950 <= primary_year < 1960:
        return '🎸 Birth of Rock & Roll (1950s)'
    elif 1960 <= primary_year < 1970:
        return '🎵 Golden Age of Rock (1960s)'
    elif 1970 <= primary_year < 1980:
        return '🎤 Disco & Punk Era (1970s)'
    elif 1980 <= primary_year < 1990:
        return '🎹 New Wave & MTV Era (1980s)'
    elif 1990 <= primary_year < 2000:
        return '💿 Grunge & Hip-Hop Rise (1990s)'
    elif 2000 <= primary_year < 2010:
        return '💻 Digital Revolution (2000s)'
    elif 2010 <= primary_year < 2020:
        return '📱 Streaming Era (2010s)'
    else:
        return '🌐 Contemporary Era (2020s+)'

def create_decade_distribution_chart(recommendations, api_gateway_url):
    """
    Create a bar chart showing distribution of artists by decade they started
    
    Args:
        recommendations: List of recommendation dicts
        api_gateway_url: Base URL for API gateway
        
    Returns:
        Plotly figure object or None
    """
    if not recommendations:
        return None
    
    # Fetch timeline data
    import streamlit as st
    with st.spinner("Fetching artist timeline data..."):
        artist_timeline = fetch_artist_timeline_data(recommendations, api_gateway_url)
    
    if not artist_timeline:
        return None
    
    # Extract decades from begin years
    decades = []
    artist_decade_map = {}
    
    for rec in recommendations:
        artist_id = rec.get('artist_id')
        if artist_id in artist_timeline:
            begin_year = artist_timeline[artist_id]['begin_year']
            if begin_year:
                decade = (begin_year // 10) * 10
                decade_label = f"{decade}s"
                decades.append(decade_label)
                artist_decade_map[rec['artist_name']] = decade_label
    
    if not decades:
        return None
    
    # Count by decade
    decade_counts = Counter(decades)
    
    # Sort decades chronologically
    sorted_decades = sorted(decade_counts.items(), key=lambda x: int(x[0][:-1]))
    
    decades_labels = [d[0] for d in sorted_decades]
    decades_values = [d[1] for d in sorted_decades]
    
    # Create bar chart
    fig = go.Figure(data=[
        go.Bar(
            x=decades_labels,
            y=decades_values,
            marker_color='#6366F1',
            text=decades_values,
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>Artists: %{y}<extra></extra>',
            marker=dict(
                line=dict(color='white', width=1)
            )
        )
    ])
    
    fig.update_layout(
        title={
            'text': '📅 Artists by Starting Decade',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#262730'}
        },
        xaxis_title="Decade",
        yaxis_title="Number of Artists",
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            tickangle=45,
            gridcolor='rgba(200,200,200,0.2)'
        ),
        yaxis=dict(
            gridcolor='rgba(200,200,200,0.2)'
        ),
        margin=dict(l=50, r=20, t=70, b=50)
    )
    
    return fig


def create_artist_timeline_gantt(recommendations, api_gateway_url, max_artists=15):
    """
    Create a Gantt chart showing artist active periods
    
    Args:
        recommendations: List of recommendation dicts
        api_gateway_url: Base URL for API gateway
        max_artists: Maximum number of artists to display
        
    Returns:
        Plotly figure object or None
    """
    if not recommendations:
        return None
    
    # Fetch timeline data
    import streamlit as st
    with st.spinner("Building artist timeline..."):
        artist_timeline = fetch_artist_timeline_data(recommendations, api_gateway_url)
    
    if not artist_timeline:
        return None
    
    # Prepare data for Gantt chart
    gantt_data = []
    
    for rec in recommendations[:max_artists]:  # Limit to avoid clutter
        artist_id = rec.get('artist_id')
        if artist_id in artist_timeline:
            timeline = artist_timeline[artist_id]
            begin_year = timeline['begin_year']
            end_year = timeline['end_year']
            
            if begin_year:
                # If no end year, assume still active (use current year)
                if not end_year:
                    end_year = datetime.now().year
                
                gantt_data.append({
                    'Artist': rec['artist_name'],
                    'Start': begin_year,
                    'Finish': end_year,
                    'Era': classify_musical_era(begin_year, end_year)
                })
    
    if not gantt_data:
        return None
    
    # Sort by start year
    gantt_data.sort(key=lambda x: x['Start'])
    
    df = pd.DataFrame(gantt_data)
    
    # Create timeline chart
    fig = px.timeline(
        df,
        x_start='Start',
        x_end='Finish',
        y='Artist',
        color='Era',
        title='⏰ Artist Active Periods Timeline',
        labels={'Start': 'Begin Year', 'Finish': 'End Year'},
        color_discrete_sequence=['#6366F1', '#8B5CF6', '#EC4899', '#F97316', 
                                '#EAB308', '#22C55E', '#06B6D4', '#3B82F6']
    )
    
    fig.update_layout(
        height=max(400, len(gantt_data) * 30),
        xaxis_title="Year",
        yaxis_title="",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.01
        )
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

    st.markdown("""
    ### Smart Song Recommendations
    Try these examples to see the enhanced algorithm:
    - **"old school rap"** - Should find classic hip-hop artists
    - **"relaxing jazz piano"** - Should prioritize jazz pianists  
    - **"energetic rock songs"** - Should find upbeat rock bands
    - **"hazy vaporwave"** - Should find hazy, ethereal slowed-down music with distorted samples
    - **"acoustic folk ballads"** - Should find folk artists with acoustic style
    """)

    
    # Search interface
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔍 What kind of music are you looking for?", 
                            placeholder="e.g., old school rap, relaxing jazz piano, energetic rock songs, hazy vaporwave")
    with col2:
        st.write("")
        st.write("")
        search_button = st.button("🎵 Get Smart Recommendations", type="primary")
    
    if search_button and query:
        with st.spinner("Analyzing your query and finding perfect matches..."):
            try:
                # API call
                params = {"query": query, "limit": 10}
                if username != "guest":
                    params["username"] = username
                
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
                        result_tabs = st.tabs(["🎵 Song List", "📊 Visual Overview", "📈 Session Analytics", "🧠 Algorithm Insights"])
                        

                        
                        with result_tabs[0]:  # Song List - FIXED VERSION
                            st.subheader("🎵 Your Song Recommendations")
                            
                            # Show query analysis if available
                            if query_analysis:
                                with st.expander("🧠 How the algorithm analyzed your query"):
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        if query_analysis.get('detected_genre'):
                                            st.write("**🎭 Detected Genre:**")
                                            st.write(f"{query_analysis['detected_genre']}")
                                    with col2:
                                        if query_analysis.get('unique_artists'):
                                            st.write("**🎤 Artist Diversity:**")
                                            st.write(f"{query_analysis.get('diversity_ratio', 'N/A')}")
                                    with col3:
                                        if query_analysis.get('processing_time'):
                                            st.write("**⚡ Processing Time:**")
                                            st.write(f"{query_analysis['processing_time']}")
                            
                            # Display recommendations with enhanced info
                            for i, rec in enumerate(recommendations, 1):
                                with st.container():
                                    # Create a colored border based on score
                                    score = rec['score']
                                    if score >= 80:
                                        border_color = "#22C55E"  # Green for high scores
                                        score_emoji = "🔥"
                                    elif score >= 60:
                                        border_color = "#6366F1"  # Blue for medium scores
                                        score_emoji = "⭐"
                                    elif score >= 40:
                                        border_color = "#F59E0B"  # Yellow for fair scores
                                        score_emoji = "👍"
                                    else:
                                        border_color = "#EF4444"  # Red for low scores
                                        score_emoji = "💡"
                                    
                                    st.markdown(f"""
                                    <div style="
                                        border-left: 5px solid {border_color}; 
                                        padding: 1rem; 
                                        margin: 1rem 0; 
                                        background-color: rgba(99, 102, 241, 0.05);
                                        border-radius: 0 8px 8px 0;
                                    ">
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    col1, col2, col3, col4, col5 = st.columns([0.5, 2.5, 1.5, 1, 1])
                                    
                                    with col1:
                                        st.markdown(f"**#{i}**")
                                        st.markdown(f"{score_emoji}")
                                    
                                    with col2:
                                        st.markdown(f"**🎵 {rec['track_title']}**")
                                        st.markdown(f"*by {rec['artist_name']}*")
                                        
                                        # Show recommendation type
                                        rec_type = rec.get('recommendation_type', 'unknown').replace('_', ' ').title()
                                        st.caption(f"Strategy: {rec_type}")
                                    
                                    with col3:
                                        st.markdown(f"**Score: {rec['score']}/100**")
                                        # Progress bar for score
                                        st.progress(rec['score']/100)
                                    
                                    with col4:
                                        # MusicBrainz ID info
                                        st.caption(f"Track ID:")
                                        st.caption(f"`{rec['track_id'][:8]}...`")
                                        
                                        if 'search_method' in rec:
                                            st.caption(f"Method: {rec['search_method'][:15]}...")
                                    
                                    with col5:
                                        # Action buttons
                                        like_button = st.button("👍 Like", key=f"like_{rec['track_id']}", 
                                                               help="Like this song", use_container_width=True)
                                        
                                        if like_button:
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
                                        
                                        save_button = st.button("💾 Save", key=f"save_{rec['track_id']}", 
                                                               help="Save for later", use_container_width=True)
                                        
                                        if save_button:
                                            try:
                                                requests.post(
                                                    f"{API_GATEWAY_URL}/api/users/{username}/listening-history",
                                                    params={
                                                        "track_id": rec['track_id'],
                                                        "artist_id": rec['artist_id'],
                                                        "interaction_type": "saved"
                                                    },
                                                    timeout=10
                                                )
                                                st.success("Saved! 💾")
                                            except Exception as e:
                                                st.error(f"Could not save: {e}")
                                    
                                    st.divider()
                            
                            # Summary at the bottom
                            st.markdown("---")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                avg_score = np.mean([rec['score'] for rec in recommendations])
                                st.metric("Average Score", f"{avg_score:.1f}/100")
                            with col2:
                                unique_artists = len(set([rec['artist_name'] for rec in recommendations]))
                                st.metric("Unique Artists", unique_artists)
                            with col3:
                                high_quality = len([rec for rec in recommendations if rec['score'] >= 80])
                                st.metric("High Quality (80+)", high_quality)
                        

                        with result_tabs[1]:  # Visual Overview
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                
                                # Artist diversity
                                diversity_chart = create_artist_diversity_donut(recommendations)
                                if diversity_chart:
                                    st.plotly_chart(diversity_chart, use_container_width=True)

                                # Decade distribution
                                decade_chart = create_decade_distribution_chart(recommendations, API_GATEWAY_URL)
                                if decade_chart:
                                    st.plotly_chart(decade_chart, use_container_width=True)
                                else:
                                    st.info("⏳ Timeline data not available for these artists")
                                
                                # Score distribution
                                score_chart = create_score_distribution_chart(recommendations)
                                if score_chart:
                                    st.plotly_chart(score_chart, use_container_width=True)
                                
                                # Recommendation strategies
                                strategy_chart = create_recommendation_strategy_breakdown(recommendations)
                                if strategy_chart:
                                    st.plotly_chart(strategy_chart, use_container_width=True)
                            
                            with col2:
                                
                                # Artist origin map
                                country_map = create_artist_origin_map(recommendations, API_GATEWAY_URL)
                                if country_map:
                                    st.plotly_chart(country_map, use_container_width=True)
        
                                    # Show detailed country breakdown
                                    with st.expander("📊 View Country Details"):
                                        artist_countries = fetch_artist_countries(recommendations, API_GATEWAY_URL)
                                        country_data = []
                                        for rec in recommendations:
                                            artist_id = rec.get('artist_id')
                                            if artist_id in artist_countries:
                                                country_data.append({
                                                    'Artist': rec['artist_name'],
                                                    'Track': rec['track_title'],
                                                    'Country': artist_countries[artist_id]
                                                })
            
                                        if country_data:
                                            country_df = pd.DataFrame(country_data)
                                            st.dataframe(country_df, use_container_width=True)
                                else:
                                    st.info("🌍 Country information not available for these artists")
                                
                                # Show summary statistics
                                artist_timeline = fetch_artist_timeline_data(recommendations, API_GATEWAY_URL)
    
                                if artist_timeline:
                                    # Build artist-year mapping
                                    artist_years = {}
                                    for rec in recommendations:
                                        artist_id = rec.get('artist_id')
                                        if artist_id in artist_timeline and artist_timeline[artist_id]['begin_year']:
                                            artist_name = rec['artist_name']
                                            begin_year = artist_timeline[artist_id]['begin_year']
                                            artist_years[artist_name] = begin_year
        
                                    if artist_years:
                                        # Find oldest and newest artists
                                        oldest_artist = min(artist_years.items(), key=lambda x: x[1])
                                        newest_artist = max(artist_years.items(), key=lambda x: x[1])
            
                                        st.metric("Oldest Artist", 
                                            f"{oldest_artist[1]}", 
                                            delta=oldest_artist[0])
                                        st.metric("Newest Artist", 
                                            f"{newest_artist[1]}", 
                                            delta=newest_artist[0])
                                        st.metric("Year Range", 
                                            f"{newest_artist[1] - oldest_artist[1]} years")
            
                                        # Count active vs ended
                                        active = sum(1 for t in artist_timeline.values() if not t['end_year'])
                                        ended = sum(1 for t in artist_timeline.values() if t['end_year'])
                                        st.metric("Still Active", f"{active}/{active+ended}")

                                # Quality gauge
                                quality_gauge = create_search_quality_gauge(recommendations, query_analysis)
                                if quality_gauge:
                                    st.plotly_chart(quality_gauge, use_container_width=True)


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
                                st.info("Search more to see this session's analytics trends!")
                        
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
                                
                                # Strategy breakdown
                                strategies_used = list(set([rec.get('recommendation_type', 'unknown') for rec in recommendations]))
                                st.write(f"**Strategies Used:** {len(strategies_used)}")
                                for strategy in strategies_used:
                                    st.write(f"• {strategy.replace('_', ' ').title()}")
                    
                    else:
                        st.warning("No recommendations found. The enhanced algorithm might need more specific search terms.")
                        st.info("Try queries like: 'jazz saxophone', 'rock guitar', 'electronic dance', 'country ballads'")
                
                else:
                    st.error(f"Recommendation service error: {response.status_code}")
                    if response.status_code == 504:
                        st.info("The service timed out. Try a simpler query or check your connection.")
                    elif response.status_code == 503:
                        st.info("The recommendation service is temporarily unavailable. Please try again later.")
                    else:
                        st.text(f"Response: {response.text}")
                        
            except requests.exceptions.Timeout:
                st.error("⏰ Request timed out. The MusicBrainz API might be slow. Try again!")
            except requests.exceptions.ConnectionError:
                st.error(f"🔌 Connection error. Cannot reach API Gateway at {API_GATEWAY_URL}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
    
    # Add session management
    if st.session_state.recommendation_history:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 View Session Overview"):
                # Show comprehensive session view
                st.subheader("📈 Session Overview")
                
                total_searches = len(st.session_state.search_analytics)
                total_songs = len(st.session_state.recommendation_history)
                
                if total_searches > 0:
                    st.write(f"**Total Searches:** {total_searches}")
                    st.write(f"**Total Songs Found:** {total_songs}")
                    
                    # Show search history
                    st.subheader("🔍 Your Search History")
                    for i, search in enumerate(st.session_state.search_analytics[-5:], 1):  # Show last 5
                        with st.expander(f"Search {i}: '{search['query']}' ({len(search['recommendations'])} results)"):
                            for rec in search['recommendations'][:3]:  # Show top 3 from each search
                                st.write(f"• **{rec['track_title']}** by *{rec['artist_name']}* (Score: {rec['score']})")
        
        with col2:
            if st.button("🗑️ Clear Session Data"):
                st.session_state.search_analytics = []
                st.session_state.recommendation_history = []
                st.success("Session data cleared!")
                st.rerun()
    

with tab2:
    st.header("🎤 Search Artists")
    
    # Initialize session state for artist details
    if 'selected_artist_id' not in st.session_state:
        st.session_state.selected_artist_id = None
    
    # Debug info (remove this after fixing)
    with st.expander("🐛 Debug Info (click to expand)"):
        st.write("Session State:")
        st.write(f"selected_artist_id: {st.session_state.selected_artist_id}")
        st.write(f"Type: {type(st.session_state.selected_artist_id)}")
    
    # Callback function to set artist ID
    def set_artist_id(artist_id):
        st.session_state.selected_artist_id = artist_id
        st.write(f"DEBUG: Setting artist_id to {artist_id}")  # Debug output
    
    # Callback to clear artist ID
    def clear_artist_id():
        st.session_state.selected_artist_id = None
    
    # Check if we should display artist details
    if st.session_state.selected_artist_id is not None and st.session_state.selected_artist_id != "":
        artist_id = st.session_state.selected_artist_id
        st.info(f"Displaying details for artist ID: {artist_id}")
        
        # Back button to return to search
        if st.button("⬅️ Back to Search", on_click=clear_artist_id):
            pass  # The callback handles the state change
        
        # Fetch and display artist details
        with st.spinner("Loading artist details..."):
            try:
                response = requests.get(f"{API_GATEWAY_URL}/api/artists/{artist_id}", timeout=10)
                
                if response.status_code == 200:
                    artist_data = response.json()
                    
                    # Display artist details
                    st.subheader(f"🎤 {artist_data['name']}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Country", artist_data.get('country', 'Unknown'))
                    with col2:
                        st.metric("Type", artist_data.get('type', 'Unknown'))
                    with col3:
                        if artist_data.get('begin_date'):
                            st.metric("Active Since", artist_data['begin_date'][:4] if len(artist_data['begin_date']) >= 4 else artist_data['begin_date'])
                    
                    # Detailed information
                    st.markdown("### 📋 Details")
                    detail_col1, detail_col2 = st.columns(2)
                    
                    with detail_col1:
                        st.write(f"**Full Name:** {artist_data['name']}")
                        st.write(f"**Sort Name:** {artist_data.get('sort_name', 'N/A')}")
                        st.write(f"**MusicBrainz ID:** `{artist_data['id']}`")
                    
                    with detail_col2:
                        st.write(f"**Country:** {artist_data.get('country', 'N/A')}")
                        st.write(f"**Begin Date:** {artist_data.get('begin_date', 'N/A')}")
                        st.write(f"**End Date:** {artist_data.get('end_date', 'Present')}")
                    
                    st.markdown("---")
                    
                    # Get albums for this artist
                    st.markdown("### 💿 Albums")
                    with st.spinner("Loading albums..."):
                        try:
                            albums_response = requests.get(
                                f"{API_GATEWAY_URL}/api/albums/search",
                                params={"artist_name": artist_data['name'], "limit": 20},
                                timeout=15
                            )
                            
                            if albums_response.status_code == 200:
                                albums_data = albums_response.json()
                                albums = albums_data.get("albums", [])
                                
                                if albums:
                                    st.success(f"Found {len(albums)} albums")
                                    
                                    # Display albums in a nice grid
                                    for album in albums:
                                        with st.expander(f"💿 {album['title']} ({album.get('date', 'Unknown')[:4] if album.get('date') else 'Unknown'})"):
                                            album_col1, album_col2 = st.columns(2)
                                            with album_col1:
                                                st.write(f"**Title:** {album['title']}")
                                                st.write(f"**Release Date:** {album.get('date', 'N/A')}")
                                            with album_col2:
                                                st.write(f"**Status:** {album.get('status', 'N/A')}")
                                                st.write(f"**Country:** {album.get('country', 'N/A')}")
                                            
                                            # Button to view album details
                                            if st.button(f"View Album Details", key=f"album_details_{album['id']}"):
                                                try:
                                                    album_detail_response = requests.get(
                                                        f"{API_GATEWAY_URL}/api/albums/{album['id']}",
                                                        timeout=10
                                                    )
                                                    if album_detail_response.status_code == 200:
                                                        album_detail = album_detail_response.json()
                                                        tracks = album_detail.get('tracks', [])
                                                        
                                                        if tracks:
                                                            st.write(f"**Tracks ({len(tracks)}):**")
                                                            for track in tracks:
                                                                duration = track.get('length', 0)
                                                                if duration > 0:
                                                                    minutes = duration // 60000
                                                                    seconds = (duration % 60000) // 1000
                                                                    duration_str = f"{minutes}:{seconds:02d}"
                                                                else:
                                                                    duration_str = "Unknown"
                                                                
                                                                st.write(f"{track['track_number']}. {track['title']} ({duration_str})")
                                                        else:
                                                            st.info("Track listing not available")
                                                    else:
                                                        st.error("Could not load album tracks")
                                                except Exception as e:
                                                    st.error(f"Error loading album: {e}")
                                else:
                                    st.info("No albums found for this artist")
                            else:
                                st.warning("Could not load albums")
                        except Exception as e:
                            st.error(f"Error loading albums: {e}")
                    
                    # Get similar songs/recommendations
                    st.markdown("---")
                    st.markdown("### 🎵 Similar Music")
                    if st.button("Get Song Recommendations", key="get_similar_from_details"):
                        with st.spinner("Finding similar songs..."):
                            try:
                                rec_response = requests.get(
                                    f"{API_GATEWAY_URL}/api/recommendations/similar/{artist_data['name']}",
                                    params={"limit": 10},
                                    timeout=15
                                )
                                if rec_response.status_code == 200:
                                    rec_data = rec_response.json()
                                    similar_songs = rec_data.get("recommendations", [])
                                    
                                    if similar_songs:
                                        st.success(f"Found {len(similar_songs)} similar songs!")
                                        for i, song in enumerate(similar_songs, 1):
                                            col1, col2, col3 = st.columns([0.5, 3, 1])
                                            with col1:
                                                st.write(f"**{i}.**")
                                            with col2:
                                                st.write(f"🎵 **{song['track_title']}** by *{song['artist_name']}*")
                                            with col3:
                                                st.write(f"Score: {song['score']}")
                                    else:
                                        st.warning("No similar songs found")
                                else:
                                    st.error("Recommendation service unavailable")
                            except Exception as e:
                                st.error(f"Error getting recommendations: {e}")
                
                else:
                    st.error(f"Could not load artist details (Status: {response.status_code})")
                    if st.button("⬅️ Back to Search (error)", on_click=clear_artist_id):
                        pass
            
            except Exception as e:
                st.error(f"Error loading artist: {e}")
                if st.button("⬅️ Back to Search (exception)", on_click=clear_artist_id):
                    pass
    
    else:
        # Regular search interface
        st.write("🔍 **Search for artists**")
        
        query = st.text_input("Enter artist name:", placeholder="e.g., Radiohead", key="artist_search_input")
        limit = st.slider("Number of results:", 1, 50, 10, key="artist_search_limit")
        
        if st.button("Search Artists", key="search_artists_btn") and query:
            with st.spinner("Searching artists..."):
                try:
                    response = requests.get(f"{API_GATEWAY_URL}/api/artists/search", 
                                          params={"query": query, "limit": limit})
                    
                    if response.status_code == 200:
                        data = response.json()
                        artists = data.get("artists", [])
                        
                        if artists:
                            st.success(f"Found {len(artists)} artists")
                            
                            for idx, artist in enumerate(artists):
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
                                        # Use unique key with index
                                        if st.button(f"View Details", 
                                                   key=f"details_{artist['id']}_{idx}",
                                                   on_click=set_artist_id,
                                                   args=(artist['id'],)):
                                            pass  # Callback handles it
                                    
                                    with col2:
                                        if st.button(f"🎵 Get Similar Songs", key=f"similar_{artist['id']}_{idx}"):
                                            # Get recommendations based on this artist
                                            with st.spinner("Finding similar songs..."):
                                                try:
                                                    rec_response = requests.get(
                                                        f"{API_GATEWAY_URL}/api/recommendations/similar/{artist['name']}",
                                                        timeout=15
                                                    )
                                                    if rec_response.status_code == 200:
                                                        rec_data = rec_response.json()
                                                        similar_songs = rec_data.get("recommendations", [])
                                                        
                                                        if similar_songs:
                                                            st.success(f"Found {len(similar_songs)} similar songs!")
                                                            for song in similar_songs[:5]:  # Show top 5
                                                                st.write(f"🎵 **{song['track_title']}** by *{song['artist_name']}* (Score: {song['score']})")
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
    
    st.subheader("Most Recent 100 Saved Artists")
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/artists", params={"limit": 100})
        if response.status_code == 200:
            data = response.json()
            artists = data.get("artists", [])
                
            if artists:
                df = pd.DataFrame(artists)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No artists saved yet")
        else:
            st.error("Could not load saved artists")
    except Exception as e:
        st.error(f"Error: {e}")
    add_database_viewer_tab()

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
