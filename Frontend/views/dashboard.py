import streamlit as st
import pandas as pd
from analytics import get_channel_stats, get_channel_videos, get_monthly_analytics
import live_data

from views.tabs.overview import render_overview
from views.tabs.strategy import render_strategy
from views.tabs.performance import render_performance
from views.tabs.comparison import render_comparison
from views.tabs.recommendation import render_recommendation
from views.tabs.ask_pilot import render_ask_pilot

def render_dashboard():
    ch_id = st.session_state['channel_id']
    stats = get_channel_stats(ch_id)

    if stats['total_videos'] == 0 and 'has_synced' not in st.session_state:
        success = live_data.sync_channel_data(ch_id)
        if success:
            st.session_state['has_synced'] = True
            st.rerun() # Reload page to show the new data
        else:
            st.error("Could not sync data. Please check your API Key quota.")
    df_videos = get_channel_videos(ch_id)
    df_monthly = get_monthly_analytics(df_videos) if not df_videos.empty else pd.DataFrame()
    
    # =========================================================
    # 1. NEW HEADER (With Custom URL & 1px Spacing)
    # =========================================================
    img_url = stats.get('channel_image') or "https://via.placeholder.com/150"
    c_name = stats['channel_name']
    
    # Custom URL Logic
    c_url = stats.get('custom_url', '') 
    if c_url and not c_url.startswith('@') and 'http' not in c_url:
        c_url = f"@{c_url}"
    elif not c_url or c_url == 'N/A':
        c_url = ""

    st.markdown(f"""
    <div class="channel-header-container">
        <img src="{img_url}" class="channel-avatar">
        <div class="channel-info">
            <h1 class="channel-title">{c_name}</h1>
            <p class="channel-url">{c_url}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # A. COMMON TABS (Depend ONLY on data availability)
    if df_videos.empty: 
        tabs = ["Overview", "Comparison"]
    else: 
        tabs = ["Overview", "Strategy", "Performance", "Comparison"]

    # B. PRIVATE TABS (Depend ONLY on login status)
    if st.session_state.get("authenticated"):
        tabs.extend(["Recommendation", "Ask Pilot"]) 

    # C. Render the Menu
    current_selection = st.radio("Navigation", tabs, horizontal=True, label_visibility="collapsed")
    st.markdown('<div style="height: 1px; width: 100%; background-color: #333; margin-top: 5px; margin-bottom: 25px;"></div>', unsafe_allow_html=True)
    
    # --- ROUTING TO INDIVIDUAL TABS ---
    if "Overview" in current_selection:
        render_overview(df_videos, df_monthly, stats, ch_id)
    elif "Strategy" in current_selection:
        render_strategy(df_videos, df_monthly, stats, ch_id)
    elif "Performance" in current_selection:
        render_performance(df_videos, df_monthly, stats, ch_id)
    elif "Comparison" in current_selection:
        render_comparison(df_videos, df_monthly, stats, ch_id)
    elif "Recommendation" in current_selection:
        render_recommendation(df_videos, df_monthly, stats, ch_id)
    elif "Ask Pilot" in current_selection:
        render_ask_pilot(df_videos, df_monthly, stats, ch_id)