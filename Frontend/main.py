import streamlit as st
import pandas as pd
import auth
import live_data
import plotly.express as px
import plotly.graph_objects as go
import pycountry as pc
from analytics import format_big_number, get_channel_stats, get_channel_videos, get_monthly_analytics, compare_channels, get_all_channels_list, get_seasonal_analytics, get_top_keywords, get_duration_clustering, get_my_channel
import warnings

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

warnings.filterwarnings('ignore')

def get_ai_context(df):
    if df is None or df.empty:
        return "No channel data loaded yet."
    
    total_views = df['view_count'].sum()
    avg_eng = df['engagement_rate'].mean()
    top_video = df.loc[df['view_count'].idxmax()]['title']
    
    return f"Total Views: {total_views}, Avg Engagement: {avg_eng:.2f}%, Top Video: {top_video}"

# --- CONFIGURATION ---
st.set_page_config(page_title="YouTube Analytics Studio", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# --- LOAD CSS ---
def local_css(file_name):
    # This dynamically finds the folder where main.py is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, file_name)
    
    with open(file_path, encoding='utf-8') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

# --- AUTH INIT ---

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# Initialize the loop-prevention flag
if "just_browsing" not in st.session_state:
    st.session_state["just_browsing"] = False

auth.init() 
is_logged_in = auth.is_authenticated()

# SMART REDIRECT LOGIC

if is_logged_in and st.session_state.get('channel_id') is None:
    stored_id = get_my_channel(st.session_state["user_email"])
    if stored_id:
        st.session_state['channel_id'] = stored_id
        st.rerun()

# 1. TOP HEADER (Back Button & Login)
col_nav, col_space, col_auth = st.columns([1, 6, 1])

# --- LEFT COLUMN: BACK BUTTON ---
with col_nav:
    if st.session_state.get('channel_id') is not None:
        # If logged in, "Back" means "I want to search another channel"
        if st.button("←", type="secondary", key="main_back_btn"):
            st.session_state['channel_id'] = None
            # Set this to True to stop the Auto-Redirect loop
            st.session_state['just_browsing'] = True 
            st.rerun()

# --- RIGHT COLUMN: PROFILE MENU ---
with col_auth:
    if is_logged_in:
        user_name = st.session_state.get("user_name", "User")
        user_email = st.session_state.get("user_email", "")
        # If user_name is None, use "User" as a default
        user_name = st.session_state.get("user_name") or "User"
        first_name = user_name.split(' ')[0]
        user_pic = st.session_state.get("user_picture")

        if not user_pic:
             safe_name = user_name.replace(" ", "+")
             user_pic = f"https://ui-avatars.com/api/?name={safe_name}&background=random&color=fff&rounded=true"

        # CSS: CIRCLE PROFILE PICTURE TRIGGER
        st.markdown(f"""
        <style>
        /* 1. TARGET THE POPOVER BUTTON (The Trigger) */
        div[data-testid="stPopover"] > button {{
            background-image: url('{user_pic}') !important;
            background-size: cover !important;
            background-position: center !important;
            /* Make it a Circle */
            border-radius: 50% !important;
            border: 2px solid #333 !important;
            /* Fixed Size */
            width: 50px !important;
            height: 50px !important;
            /* Hide Default Text */
            color: transparent !important;
            padding: 0 !important;
            /* Float Right to edge of column */
            float: right !important;
        }}
        /* 2. REMOVE THE ARROW ICON */
        div[data-testid="stPopover"] > button svg {{
            display: none !important;
        }}

        /* 3. HOVER GLOW */
        div[data-testid="stPopover"] > button:hover {{
            border-color: #00E5FF !important;
            box-shadow: 0 0 15px rgba(0, 229, 255, 0.6);
            transform: scale(1.1);
        }}

        /* 4. CENTER DROPDOWN TEXT */
        div[data-testid="stPopoverBody"] {{
            text-align: center !important;
        }}
        </style>

        """, unsafe_allow_html=True)

        # RENDER MENU
        with st.popover(" "):
            st.markdown(f"""
            <div style="display: flex; flex-direction: column; align-items: center;">
                <img src="{user_pic}" style="width: 75px; height: 75px; border-radius: 50%; border: 3px solid #1A1A1A; margin-bottom: 10px;">
                <h3 style="margin:0; font-size:18px; font-weight:700;">Hi, {first_name}!</h3>
                <p style="color:#888; font-size:13px; margin:0; margin-bottom: 10px;">{user_email}</p>
            </div>
            """, unsafe_allow_html=True)
            # CHANGE: Use 'primary' to trigger your Pink Gradient CSS

            if st.button("Logout", type="primary", key="nav_logout_btn", use_container_width=True):
                auth.logout()

# ==========================================
# 2. LOGIN DIALOG
# ==========================================
if st.session_state.get("show_auth_dialog"):
    st.write("#")
    with st.container():
        c1, c2, c3 = st.columns([3, 2, 3])
        with c2:
            auth.login_dialog()
            if st.button("Cancel", type="primary", width='stretch', key="dialog_back_btn"):
                st.session_state["show_auth_dialog"] = False
                st.rerun()
    st.stop() 


# ==========================================
# 3. MAIN APP
# ==========================================
if 'channel_id' not in st.session_state: st.session_state['channel_id'] = None

# --- SCENARIO A: LANDING PAGE ---
if st.session_state['channel_id'] is None:

    # 1. CHECK FOR LOGIN CLICK (The "Link" Trick)
    # If user clicked the "Login" link, the URL has ?auth=login
    if "auth" in st.query_params and st.query_params["auth"] == "login":
        st.session_state["show_auth_dialog"] = True
        st.query_params.clear() # Clear the URL so it doesn't reopen on refresh
        st.rerun()
    # 1. FIXED NAVBAR (Pinned to Top)
    st.markdown("""
        <div class="fixed-header-landing">
            <div class="fixed-nav-links">
                <a class="nav-slide-link" href="#home">Home</a>
                <a class="nav-slide-link" href="#features">Features</a>
                <a class="nav-slide-link" href="#how-it-works">How It Works</a>
                <a class="nav-slide-link" href="#about">About</a>
                <a class="nav-slide-link" href="?auth=login" target="_self">Login</a>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 2. ANCHOR TARGETS (Used for the jump-links)
    st.markdown('<div id="home"></div>', unsafe_allow_html=True)

    # 3. HERO SECTION (Title & Search)
    st.markdown('<div id="home" style="padding-top: 100px;"></div>', unsafe_allow_html=True) 
    
    # --- ADD THIS BLOCK TO FORCE THE SIZE ---
    st.markdown("""
    <style>
        .landing-title {
            font-size: 7rem !important; /* <--- Adjust this number (e.g. 7rem, 8rem, 120px) */
            line-height: 1.1 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    # ----------------------------------------

    st.markdown("""
        <h1 class="landing-title">
            YouTube Analytics<br>Studio
        </h1>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div class="hero-subtitle">
            Unlock deep insights, track growth patterns, and outsmart your competition with our 
            <span class="highlight-text">AI-driven</span> engine.
        </div>
    """, unsafe_allow_html=True)

    c_left, c_center, c_right = st.columns([1, 2, 1])
    
    with c_center:
        # --- YOUR EXISTING SEARCH LOGIC STARTS HERE ---
        df_channels = get_all_channels_list()
        
        if not df_channels.empty:
            channel_map = dict(zip(df_channels['channel_name'], df_channels['channel_id']))
            
            # Define columns: Search Bar (4 parts) + Button (1 part)
            col_search, col_btn = st.columns([4, 1], vertical_alignment="bottom")

            # 1. THE DROPDOWN (in the wide column)
            with col_search:
                selected_name = st.selectbox(
                    "Search Channel", 
                    options=df_channels['channel_name'], 
                    label_visibility="collapsed", 
                    index=None,                  
                    placeholder="Select Channel Name..."  
                )

            with col_btn:
                if st.button("Search", type="primary", width='stretch', key="landing_search_btn"):
                    
                    if not selected_name:
                        st.toast("⚠️ Please select a Channel Name first!")
                    
                    else:
                        cid = channel_map[selected_name]
                        
                        # 1. Check if we already have stats in DB
                        current_stats = get_channel_stats(cid)
                        
                        if current_stats is not None:
                            # 🟢 SMART CHECK: Is the image missing?
                            if not current_stats.get('channel_image'):
                                live_data.update_channel_image_only(cid)
                            
                            # 2. Load the Dashboard
                            st.session_state['channel_id'] = cid
                            st.session_state['selected_channel'] = selected_name
                            st.rerun()
                            
                        else:
                            live_data.sync_channel_data(cid)
                            st.session_state['channel_id'] = cid
                            st.rerun()
        else:
            st.warning("Database empty.")

    st.markdown('<div style="height: 60px;"></div>', unsafe_allow_html=True) # Spacer

# 3. FEATURES SECTION (Zig-Zag with CSS Graphics)
    st.markdown("---")
    st.markdown("""
<div id="features" style="padding: 50px 0;">

<div class="header-animate">
<h2 style="text-align:center; font-size: 3rem; font-weight: 800; margin-bottom: 20px;">
Why Use This 
<span style="color:#FF3B30;">Studio?</span>
</h2>
<p style="text-align:center; color:#888; font-size: 1.2rem; max-width: 600px; margin: 0 auto; margin-bottom: 60px;">
Stop guessing. Start growing. Our advanced analytics engine reveals the data YouTube Studio hides.
</p>
</div>

<div class="timeline-container">

<div class="timeline-item">
<div class="timeline-content animate-left">
<div class="content-box">
<span class="step-number" style="color:#D90368;">Feature 01</span>
<h3 style="color:white; margin:0 0 15px 0; font-size: 1.8rem;">Data-Driven Growth</h3>
<p style="color:#aaa; font-size:16px; margin:0; line-height:1.6;">
We analyze hidden patterns to predict future trends. See the data behind the views.
</p>
</div>
</div>
<div class="timeline-dot"></div>
<div class="timeline-visual animate-right">
<div class="mock-interface">
<div class="mock-header"><div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div></div>

<div class="mock-body">
 <div class="ui-chart-box">
<div class="ui-bar h-1"></div>
<div class="ui-bar h-2"></div>
<div class="ui-bar h-3"></div>
</div>
</div>

</div>
</div>
</div>

<div class="timeline-item">
<div class="timeline-visual animate-left">
<div class="mock-interface">
<div class="mock-header"><div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div></div>

<div class="mock-body">
 <div class="ui-search-box">
<div class="ui-search-line"></div>
<div class="ui-search-btn"></div>
</div>
</div>

</div>
</div>
<div class="timeline-dot"></div>
<div class="timeline-content animate-right">
<div class="content-box">
<span class="step-number" style="color:#822FAF;">Feature 02</span>
<h3 style="color:white; margin:0 0 15px 0; font-size: 1.8rem;">Real-Time Intelligence</h3>
<p style="color:#aaa; font-size:16px; margin:0; line-height:1.6;">
Direct integration with the YouTube Data API v3 for instant, up-to-the-second stats.
</p>
</div>
</div>
</div>

<div class="timeline-item">
<div class="timeline-content animate-left">
<div class="content-box">
<span class="step-number" style="color:#D90368;">Feature 03</span>
<h3 style="color:white; margin:0 0 15px 0; font-size: 1.8rem;">Competitor Spy</h3>
<p style="color:#aaa; font-size:16px; margin:0; line-height:1.6;">
Compare stats side-by-side and adapt winning strategies from top players in your niche.
</p>
</div>
</div>
<div class="timeline-dot"></div>
<div class="timeline-visual animate-right">
<div class="mock-interface">
<div class="mock-header"><div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div></div>

<div class="mock-body">
<div class="ui-growth-box">
<div class="ui-trend-line"></div>
<div class="ui-trend-arrow"></div>
</div>
</div>

</div>
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

    # 4. HOW IT WORKS SECTION 
    st.markdown("---")
    st.markdown("""
    <div id="how-it-works" style="padding: 50px 0;">
        <div class="header-animate">
            <h2 style="text-align:center; font-size: 3rem; font-weight: 800; margin-bottom: 20px;">
                How It 
                <span style="color:#FF3B30;">Works</span>
            </h2>
            <p style="text-align:center; color:#888; font-size: 1.2rem; max-width: 600px; margin: 0 auto; margin-bottom: 60px;">
                Simple, fast, and powerful. See how our engine transforms raw data into your competitive advantage in three easy steps.
            </p>
        </div>
        <div class="timeline-container">  
            <div class="timeline-item">
                <div class="timeline-content animate-left">
                    <div class="content-box">
                        <span class="step-number">Step 01</span>
                        <h3 style="color:white; margin:0 0 10px 0;">Global Search</h3>
                        <p style="color:#aaa; font-size:15px; margin:0;">
                            Enter any channel name. Our system instantly queries the YouTube Data API.
                        </p>
                    </div>
                </div>
                <div class="timeline-dot"></div>
<div class="timeline-visual animate-right">
<div class="mock-interface">
<div class="mock-header"><div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div></div> 
<div class="mock-body">
<div class="ui-search-box">
<div class="ui-search-line"></div>
<div class="ui-search-btn"></div>
</div>
</div>
</div>
</div>
</div>
<div class="timeline-item">
<div class="timeline-visual animate-left">
<div class="mock-interface">
<div class="mock-header"><div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div></div>
<div class="mock-body">
<div class="ui-chart-box">
<div class="ui-bar h-1"></div>
<div class="ui-bar h-2"></div>
<div class="ui-bar h-3"></div>
</div>
</div>
</div>
</div>
<div class="timeline-dot"></div>
<div class="timeline-content animate-right">
<div class="content-box">
<span class="step-number">Step 02</span>
<h3 style="color:white; margin:0 0 10px 0;">Deep Analysis</h3>
<p style="color:#aaa; font-size:15px; margin:0;">
We crunch the numbers. Hidden engagement metrics and historical data are processed.
</p>
</div>
</div>
</div>
<div class="timeline-item">
<div class="timeline-content animate-left">
<div class="content-box">
<span class="step-number">Step 03</span>
<h3 style="color:white; margin:0 0 10px 0;">Growth Strategy</h3>
<p style="color:#aaa; font-size:15px; margin:0;">
Get actionable insights. Compare performance and apply winning strategies.
</p>
</div>
</div>
<div class="timeline-dot"></div>
<div class="timeline-visual animate-right">
<div class="mock-interface">
<div class="mock-header"><div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div></div>
<div class="mock-body">
<div class="ui-growth-box">
<div class="ui-trend-line"></div>
<div class="ui-trend-arrow"></div>
</div>
</div>
</div>
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
    # --- 5. THE MISSION & BRANDED FOOTER (Combined) ---
    st.markdown("""
        <div id="about" style="padding: 50px 0;">
            <div class="header-animate">
                <h2 style="text-align:center; font-size: 3rem; font-weight: 800; margin-bottom: 20px;">
                    <span style="color:#FF3B30;">
                        About
                    </span>
                </h2>
                <p style="text-align:center; color:#888; font-size: 1.2rem; max-width: 600px; margin: 0 auto; margin-bottom: 60px;">
                    I built this <b>YouTube Analytics Studio</b> as a personal commitment to the creator community. 
                    Driven by a passion for data engineering, I designed every algorithm and interface to serve 
                    as the ultimate bridge between raw metrics and actionable success. My goal is to empower 
                    solo creators with the same deep insights used by major studios, ensuring that every 
                    content strategy is backed by precision and AI-driven intelligence.
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    # --- 6. Footer ---
    st.markdown("""
        <div class="absolute-bottom-footer">
            <div class="footer-line-separator"></div>
                <div class="footer-text-row">
                    <span>© 2026 Crafted by <b>Binit Krishna Goswami</b></span>
                    <span class="footer-pipe-divider">|</span>
                    <a href="https://linkedin.com/in/binit-krishna-goswami" target="_blank" class="linkedin-blue-link">Connect on LinkedIn</a>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- SCENARIO B: DASHBOARD ---
else:
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
    
    # --- TAB 1: OVERVIEW (THE SIX BOXES) ---
    if "Overview" in current_selection:
        
        # A. Prepare Data
        if not df_videos.empty:
            avg_len = df_videos['duration_min'].mean()
            total_earn = df_videos['est_earnings'].sum()
        else:
            avg_len = 0.0
            total_earn = 0.0

        country_code = stats.get('country', 'N/A')
        country_name = country_code # (Assuming you handled the pycountry logic or kept it simple)
        if country_code and len(country_code) == 2:
            try:
                c_obj = pc.countries.get(alpha_2=country_code)
                country_name = c_obj.name if c_obj else country_code
            except: pass

        created_raw = stats.get('channel_created_at')
        if created_raw:
            try: joined_date = pd.to_datetime(created_raw).strftime('%d %b %Y')
            except: joined_date = str(created_raw)
        else: joined_date = "N/A"

        # B. THE 6 BOXES (2 Rows x 3 Cols)
        
        # Row 1
        r1_c1, r1_c2, r1_c3 = st.columns(3)
        metrics_row1 = [
            ("Subscribers", format_big_number(stats['subscribers'])),
            ("Total Views", format_big_number(stats['total_views'])),
            ("Est. Revenue", f"$ {format_big_number(total_earn)}") 
        ]
        for col, (lbl, val) in zip([r1_c1, r1_c2, r1_c3], metrics_row1):
            col.markdown(f'<div class="kpi-card"><div class="kpi-lbl">{lbl}</div><div class="kpi-val">{val}</div></div>', unsafe_allow_html=True)
            
        st.write("######") # Spacer
        
        # Row 2
        r2_c1, r2_c2, r2_c3 = st.columns(3)
        metrics_row2 = [
            ("Avg Duration", f"{avg_len:.1f} min"),
            ("Country", country_name),
            ("Created On", joined_date)
        ]
        for col, (lbl, val) in zip([r2_c1, r2_c2, r2_c3], metrics_row2):
            col.markdown(f'<div class="kpi-card"><div class="kpi-lbl">{lbl}</div><div class="kpi-val">{val}</div></div>', unsafe_allow_html=True)
        
        st.write("###")
        
        # Only show graphs if we have data
        if not df_videos.empty:
            # ...TAB 1: OVERVIEW...

            # GROWTH TRAJECTORY
            if not df_monthly.empty:
                # 1. Calculate Ranges with Buffer
                max_views = df_monthly['view_count'].max()
                
                # Top Headroom (10%)
                y_max = max_views * 1.1 
                
                y_buffer = max_views * 0.05 
                
                x_min = df_monthly['published_at'].min()
                x_max = df_monthly['published_at'].max()

                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=df_monthly['published_at'], 
                    y=df_monthly['view_count'],
                    mode='lines+markers',
                    name='Views',
                    line=dict(color='#00E5FF', width=3, shape='spline'),
                    
                    # High Visibility Markers
                    marker=dict(
                        size=6, 
                        color='white', 
                        line=dict(width=1, color='#00E5FF')
                    ),
                    
                    fill='tozeroy',
                    fillcolor='rgba(0, 229, 255, 0.1)'
                ))

                fig.update_layout(
                    title=dict(
                        text="Growth Trajectory",
                        font=dict(size=20, color='#00E5FF', family="Inter, sans-serif"),
                        x=0.5, 
                        xanchor='center', 
                        y=0.95
                    ),
                    paper_bgcolor='#1A1A1A', 
                    plot_bgcolor='#1A1A1A',
                    height=350,
                    margin=dict(l=20, r=20, t=50, b=20),
                    
                    xaxis=dict(
                        title=dict(text="Date", font=dict(color='#00E5FF')),
                        showgrid=False, 
                        linecolor='#333',
                        tickfont=dict(color='white'),
                        range=[x_min, x_max], 
                        showspikes=False
                    ),
                    
                    yaxis=dict(
                        title=dict(text="Total Views", font=dict(color='#00E5FF')),
                        showgrid=True, 
                        gridcolor='#333', 
                        gridwidth=1,
                        
                        # CHANGE: Show the Zero Line explicitly
                        zeroline=True,
                        zerolinecolor='#555', # Visible line at 0
                        zerolinewidth=1,
                        
                        tickfont=dict(color='white'),
                        
                        # CHANGE: Start range BELOW zero to lift the dots
                        range=[-y_buffer, y_max] 
                    ),
                    hovermode="closest"
                )

                st.plotly_chart(fig, width='stretch')
                
            else:
                st.info("No growth data available yet.")
            st.write("###")
            
            # 1. PREPARE DATA (Top 10 by Views)
            top_df = df_videos.sort_values(by='view_count', ascending=False).head(10)[['title', 'view_count', 'published_at']].copy()
            
            if not top_df.empty:
                top_df.insert(0, 'Rank', range(1, len(top_df) + 1))
                
                # 2. BUILD HTML
                table_html = '<div class="custom-table-container">'
                table_html += '<div class="custom-header"><h5>Top Performing Videos</h5></div>'
                
                table_html += '<table class="styled-table">'
                table_html += '<thead>'
                table_html += '<tr>'
                table_html += '<th width="10%" class="col-center">Rank</th>'
                table_html += '<th width="60%" class="col-left">Video</th>'
                table_html += '<th width="15%" class="col-center">Views</th>'
                table_html += '<th width="15%" class="col-center">Date</th>'
                table_html += '</tr>'
                table_html += '</thead>'
                table_html += '<tbody>'
                
                for index, row in top_df.iterrows():
                    rank = row['Rank']
                    title = row['title']
                    views = f"{row['view_count']:,}"
                    date = row['published_at'].strftime("%d %b %Y") 
                    
                    table_html += '<tr>'
                    table_html += f'<td class="col-center">{rank}</td>'
                    table_html += f'<td class="col-left">{title}</td>'
                    table_html += f'<td class="col-center">{views}</td>'
                    table_html += f'<td class="col-center">{date}</td>'
                    table_html += '</tr>'
                
                table_html += '</tbody></table></div>'
                
                # 3. RENDER
                st.markdown(table_html, unsafe_allow_html=True)

            else:
                st.info("No video data found.")

    # --- TAB 2: STRATEGY ---
    elif "Strategy" in current_selection:
        if df_videos.empty: st.stop()

        # --- ROW 1: UPLOAD FREQUENCY (Full Width) ---
        if not df_monthly.empty:
            # 1. Create the Bar Chart
            fig_freq = px.bar(df_monthly, x='published_at', y='upload_count', 
                            color='view_count', 
                            color_continuous_scale='Turbo', # Rainbow Gradient
                            )
            
            fig_freq.update_traces(
                marker_line_width=1.5, 
                marker_line_color='#1A1A1A', # Dark border to separate bars
                opacity=1
            )

            # Calculate dynamic range for "Lifted" look
            y_max = df_monthly['upload_count'].max()
            y_buffer = y_max * 0.05 # 5% buffer below zero

            # 2. Apply Designer Styling
            fig_freq.update_layout(
                title=dict(
                    text="Upload Frequency",
                    font=dict(size=18, color='#00E5FF', family="Inter, sans-serif"), # Cyan Title
                    x=0.5, xanchor='center', y=0.95
                ),
                paper_bgcolor='rgba(0,0,0,0)', # Transparent (Shows CSS Grey)
                plot_bgcolor='rgba(0,0,0,0)',
                height=400, # Slightly taller since it's full width
                margin=dict(l=20, r=20, t=50, b=20),
                xaxis=dict(
                    title=dict(text="Date", font=dict(color='#00E5FF')),
                    showgrid=False, 
                    tickfont=dict(color='white')
                ),
                yaxis=dict(
                    title=dict(text="Uploads", font=dict(color='#00E5FF')),
                    showgrid=True, gridcolor='#333',
                    tickfont=dict(color='white'),
                    range=[-y_buffer, y_max * 1.1],
                    zeroline=False
                ),
                coloraxis_colorbar=dict(
                    title=dict(text="Views", font=dict(color='#AAA')),
                    tickfont=dict(color='#AAA')
                )
            )

            fig_freq.add_hline(
                y=0, 
                line_color="#333", 
                line_width=1, 
                layer="above" # This forces it to be visible on top
            )

            st.plotly_chart(fig_freq, use_container_width=True)
        else:
            st.info("No frequency data.")
        
        st.write("###") # Spacer between graphs

        # --- ROW 2: ENGAGEMENT SCATTER (Full Width) ---
        fig_corr = px.scatter(df_videos, x='like_count', y='comment_count', 
                            hover_data=['title'], 
                            color_discrete_sequence=['#FF007F']) # Purple Dots
        
        # Add borders to dots for neon effect
        fig_corr.update_traces(marker=dict(size=6, line=dict(width=1, color='white'), opacity=0.8))
        
        # Apply Designer Styling
        fig_corr.update_layout(
            title=dict(
                text="Engagement Correlation",
                font=dict(size=18, color='#00E5FF', family="Inter, sans-serif"), # Cyan Title
                x=0.5, xanchor='center', y=0.95
            ),
            paper_bgcolor='rgba(0,0,0,0)', # Transparent (Shows CSS Grey)
            plot_bgcolor='rgba(0,0,0,0)',
            height=400,
            margin=dict(l=20, r=20, t=50, b=20),
            xaxis=dict(
                title=dict(text="Likes", font=dict(color='#00E5FF')),
                showgrid=False,
                tickfont=dict(color='white')
            ),
            yaxis=dict(
                title=dict(text="Comments", font=dict(color='#00E5FF')),
                showgrid=True, gridcolor='#333',
                tickfont=dict(color='white')
            )
        )
        st.plotly_chart(fig_corr, use_container_width=True)

        st.write("###") # Spacer

        # --- ROW 3: BEST UPLOAD STRATEGY (Combo Chart: Day vs Hour) ---
        if not df_videos.empty:
            # 1. Prepare Data
            df_videos['day_name'] = df_videos['published_at'].dt.day_name()
            df_videos['hour'] = df_videos['published_at'].dt.hour
            
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            # Metric 1 (Bars)
            daily_views = df_videos.groupby('day_name')['view_count'].mean().reindex(days_order).fillna(0)
            
            # Metric 2 (Line)
            hourly_perf = df_videos.groupby(['day_name', 'hour'])['view_count'].mean().reset_index()
            # Handle empty data case for reindexing
            if not hourly_perf.empty:
                best_hour_idx = hourly_perf.groupby('day_name')['view_count'].idxmax()
                best_hours = hourly_perf.loc[best_hour_idx].set_index('day_name').reindex(days_order).fillna(0)
            else:
                best_hours = pd.DataFrame({'hour': [0]*7}, index=days_order)

            fig_combo = go.Figure()

            # BAR TRACE (Avg Views)
            fig_combo.add_trace(go.Bar(
                x=daily_views.index,
                y=daily_views.values,
                name='Avg Views',
                marker_color='rgba(130, 47, 175, 0.6)', 
                marker_line_color="#ABAF2F",            
                marker_line_width=1.5,
                yaxis='y1' 
            ))

            # LINE TRACE (Best Hour)
            fig_combo.add_trace(go.Scatter(
                x=best_hours.index,
                y=best_hours['hour'],
                name='Best Hour',
                mode='lines+markers',
                line=dict(color='#34FF01', width=4), 
                marker=dict(size=10, color='white', line=dict(width=2, color='#34FF01')),
                yaxis='y2' 
            ))

            # 3. Designer Layout
            fig_combo.update_layout(
                title=dict(
                    text="Best Upload Strategy (Day vs Hour)",
                    font=dict(size=20, color='#00E5FF', family="Inter, sans-serif"),
                    x=0.5, xanchor='center', y=0.95
                ),
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                height=600,
                
                margin=dict(l=30, r=60, t=40, b=80), # Added bottom margin
                
                xaxis=dict(
                    showgrid=False,
                    tickfont=dict(color='white', size=14),
                    title=dict(text="Day of Week", font=dict(color='#00E5FF'), standoff=20)
                ),
                
                # Left Axis (Views)
                yaxis=dict(
                    title=dict(text="Avg Views", font=dict(color="#F2FF03")),
                    showgrid=True, gridcolor='#333',
                    tickfont=dict(color='white'),
                    side='left'
                ),
                
                # Right Axis (Hours)
                yaxis2=dict(
                    title=dict(text="Best Time (24h)", font=dict(color="#34FF01")),
                    overlaying='y',
                    side='right',
                    showgrid=False,
                    tickfont=dict(color='white'),
                    range=[0, 24] 
                ),
                
                # 🟢 LEGEND: Top-Right & "Container" Look
                legend=dict(
                    orientation="v",       
                    yanchor="top", y=0.95, 
                    xanchor="right", x=0.99, # Shifted to Right
                    bgcolor="rgba(0,0,0,0.9)", # Dark Black Container
                    bordercolor="#555",
                    borderwidth=1,
                    font=dict(color='white')
                )
            )
            
            st.plotly_chart(fig_combo, use_container_width=True)
        
        st.write("###") # Spacer

        # --- ROW 4: AUDIENCE BEHAVIOR (Side-by-Side Pies) ---
        c_season, c_mix = st.columns(2)
        
        # 1. LEFT SIDE: SEASONAL TRENDS
        with c_season:
            df_seasonal = get_seasonal_analytics(df_videos)
            if not df_seasonal.empty:
                fig_season = px.pie(df_seasonal, 
                                    values='view_count', 
                                    names='month_name', 
                                    hole=0.6,
                                    color_discrete_sequence=px.colors.sequential.Turbo
                                )
                
                fig_season.update_traces(
                    textposition='outside', 
                    textinfo='label+percent',
                    texttemplate='%{label}<br>%{percent}',
                    marker=dict(line=dict(color='#1A1A1A', width=2))
                )
                
                fig_season.update_layout(
                    title=dict(
                        text="Seasonal Trends",
                        font=dict(size=18, color='#00E5FF', family="Inter, sans-serif"),
                        x=0.5, xanchor='center', y=0.95
                    ),
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    
                    # 🔥 INCREASED HEIGHT TO 500px
                    height=500,
                    
                    # 🔥 INCREASED MARGINS (Prevents label clipping)
                    margin=dict(l=60, r=60, t=80, b=80),
                    showlegend=False
                )
                st.plotly_chart(fig_season, use_container_width=True)
            else:
                st.info("Not enough data for seasonal trends.")

        # 2. RIGHT SIDE: ENGAGEMENT MIX (Likes vs Comments)
        with c_mix:
            total_likes = df_videos['like_count'].sum()
            total_comments = df_videos['comment_count'].sum()
            
            if total_likes + total_comments > 0:
                # Create simple dataframe for the pie chart
                mix_data = pd.DataFrame({
                    'Type': ['Likes', 'Comments'],
                    'Count': [total_likes, total_comments]
                })
                
                fig_mix = px.pie(mix_data, 
                                values='Count', 
                                names='Type', 
                                hole=0.6,
                                color_discrete_sequence=['#00E5FF', '#D90368'] 
                            )
                
                fig_mix.update_traces(
                    textposition='outside', 
                    textinfo='label+percent',
                    texttemplate='%{label}<br>%{value:.2s}', 
                    marker=dict(line=dict(color='#1A1A1A', width=2))
                )
                
                fig_mix.update_layout(
                    title=dict(
                        text="Engagement Mix",
                        font=dict(size=18, color='#D90368', family="Inter, sans-serif"), 
                        x=0.5, xanchor='center', y=0.95
                    ),
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    
                    # 🔥 INCREASED HEIGHT TO 500px
                    height=500,
                    
                    # 🔥 INCREASED MARGINS
                    margin=dict(l=60, r=60, t=80, b=80),
                    showlegend=False
                )
                st.plotly_chart(fig_mix, use_container_width=True)
            else:
                st.info("No engagement data found.")

        st.write("###") # Spacer
        
        # --- ROW 5: TRENDING TOPICS (Vertical Fixed Color) ---
        df_keywords = get_top_keywords(df_videos)
        if not df_keywords.empty:
            # 1. Create Vertical Bar Chart
            fig_words = px.bar(df_keywords, 
                                x='Word', 
                                y='Count'
                                )
            
            # 2. Styling: Fixed Color + White Border
            fig_words.update_traces(
                marker_color='#822FAF', # 🟣 FIXED NEON PURPLE COLOR
                marker_line_color="#6A00FF", 
                marker_line_width=1.5, 
                opacity=1
            )
            
            # 3. Designer Layout
            fig_words.update_layout(
                title=dict(
                    text="Trending Topics",
                    font=dict(size=18, color='#00E5FF', family="Inter, sans-serif"),
                    x=0.5, xanchor='center', y=0.95
                ),
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                height=450,
                margin=dict(l=20, r=20, t=60, b=60),
                
                xaxis=dict(
                    title=dict(text="Keywords", font=dict(color='#00E5FF', size=14)), 
                    tickfont=dict(color='white', size=12), 
                    showgrid=False
                ),
                
                yaxis=dict(
                    title=dict(text="Frequency", font=dict(color='#00E5FF', size=14)), 
                    tickfont=dict(color='white'), 
                    showgrid=True, 
                    gridcolor='#333'
                )
            )
            st.plotly_chart(fig_words, use_container_width=True)

        st.write("###") # Spacer

        # --- ROW 6: VIDEO DURATION CLUSTERING (Full Width) ---
        df_clustered = get_duration_clustering(df_videos)
        if not df_clustered.empty:
            df_clustered['duration_cluster'] = df_clustered['duration_cluster'].replace({
                "Short & Snappy ⚡": "Short & Snappy",
                "Deep Dives 🧠": "Deep Dives",
                "Long & Boring 😴": "Long & Boring",
                "Standard Video 📹": "Standard Video"
            })
            fig_cluster = px.scatter(df_clustered, x='duration_min', y='engagement_rate', 
                                   color='duration_cluster', 
                                   hover_data=['title'], 
                                   color_discrete_map={"Short & Snappy": "#00CC96", "Deep Dives": "#AB63FA", "Long & Boring": "#EF553B", "Standard Video": "#636EFA"})
            
            # Add vertical line at 15 mins (YouTube standard)
            fig_cluster.add_vline(x=15, line_dash="dash", line_color="white", opacity=0.3)
            
            fig_cluster.update_layout(
                title=dict(
                    text="Video Duration Clustering",
                    font=dict(size=18, color='#00E5FF', family="Inter, sans-serif"),
                    x=0.5, xanchor='center', y=0.95
                ),
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                height=450,
                margin=dict(l=20, r=20, t=50, b=20),
                xaxis=dict(title=dict(text="Duration (Mins)", font=dict(color='#00E5FF')), tickfont=dict(color='white'), showgrid=False),
                yaxis=dict(title=dict(text="Engagement Rate", font=dict(color='#00E5FF')), tickfont=dict(color='white'), showgrid=True, gridcolor='#333'),
                
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="right",
                    x=0.99,
                    bgcolor="rgba(0,0,0,0.8)", # Semi-transparent black box
                    bordercolor="#333",
                    borderwidth=1,
                    font=dict(color='white')
                )
            )
            st.plotly_chart(fig_cluster, use_container_width=True)

            st.write("###") # Spacer

    # --- TAB 3: PERFORMANCE ---
    elif "Performance" in current_selection:
        if df_videos.empty: st.stop() 

        # 1: Clean the category column (Remove Emojis)
        df_videos['category'] = df_videos['category'].replace({
            'Viral Content 🚀': 'Viral Content',
            'Underperforming ⚠️': 'Underperforming',
            'Loyal Fanbase (Low Views / High Eng.) ❤️': 'Loyal Fanbase', # Handle potential long names
            'Loyal Fanbase ❤️': 'Loyal Fanbase',
            'High Views / Low Eng. 📉': 'High Views',
            'High Views 📉': 'High Views'
        })

        # 2: Create Chart with Clean Keys
        fig_cat = px.scatter(df_videos, x='view_count', y='engagement_rate', 
                           color='category', 
                           hover_data=['title'], 
                           color_discrete_map={
                               'Viral Content': '#00CC96', 
                               'Underperforming': '#EF553B', 
                               'Loyal Fanbase': '#AB63FA', 
                               'High Views': '#FFA15A'
                           })
        
        # 3: Apply the "Black Box Legend" Layout
        fig_cat.update_layout(
            title=dict(
                text="Performance Matrix",
                font=dict(size=18, color='#00E5FF', family="Inter, sans-serif"),
                x=0.5, xanchor='center', y=0.95
            ),
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            height=450,
            margin=dict(l=20, r=20, t=50, b=20),
            
            xaxis=dict(
                title=dict(text="View Count", font=dict(color='#00E5FF')), 
                tickfont=dict(color='white'), 
                showgrid=False
            ),
            yaxis=dict(
                title=dict(text="Engagement Rate", font=dict(color='#00E5FF')), 
                tickfont=dict(color='white'), 
                showgrid=True, 
                gridcolor='#333'
            ),
            
            # THE LEGEND BOX (Top Right)
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99,
                bgcolor="rgba(0,0,0,0.8)",
                bordercolor="#333",
                borderwidth=1,
                font=dict(color='white')
            )
        )
        st.plotly_chart(fig_cat, use_container_width=True)
        
        st.write("###")
        
        st.markdown('<h3 style="color:#00E5FF; font-size:20px; margin-bottom:15px;">Recent Trend Analysis</h3>', unsafe_allow_html=True)
        
        if len(df_videos) > 0:
            # 1. CALCULATE METRICS
            recent_videos = df_videos.head(10)
            
            # Trend Logic
            is_improving = recent_videos['view_count'].mean() > df_videos['view_count'].mean()
            trend_status = "Improving" if is_improving else "Declining"
            trend_color = "#00CC96" if is_improving else "#EF553B"
            
            # Best Video (Title + Truncate if too long)
            best_vid_title = df_videos.loc[df_videos['view_count'].idxmax()]['title']
            if len(best_vid_title) > 45: best_vid_title = best_vid_title[:45] + "..."
            
            # Highest Engagement (Title + Truncate)
            best_eng_title = df_videos.loc[df_videos['engagement_rate'].idxmax()]['title']
            if len(best_eng_title) > 45: best_eng_title = best_eng_title[:45] + "..."

            # 2. CSS FOR CARDS
            st.markdown("""
            <style>
            .trend-card {
                background-color: #1A1A1A;
                border: 1px solid #333;
                border-radius: 15px;
                padding: 25px 20px;
                height: 180px; /* Fixed height for alignment */
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
                box-shadow: 0 4px 10px rgba(0,0,0,0.3);
                transition: transform 0.3s ease, border-color 0.3s ease;
            }
            .trend-card:hover {
                border-color: #D90368; /* Pink Glow on Hover */
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(217, 3, 104, 0.2);
            }
            .trend-label {
                color: #888;
                font-size: 13px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 1.2px;
                margin-bottom: 15px;
            }
            .trend-value {
                color: #fff;
                font-size: 18px;
                font-weight: 600;
                line-height: 1.4;
                
                /* Limit lines to 3 */
                display: -webkit-box;
                -webkit-line-clamp: 3;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            </style>
            """, unsafe_allow_html=True)

            # 3. RENDER CARDS IN COLUMNS
            c1, c2, c3 = st.columns(3)

            with c1:
                st.markdown(f"""
                <div class="trend-card">
                    <div class="trend-label">Overall Trend</div>
                    <div class="trend-value" style="color: {trend_color}; font-size: 24px;">{trend_status}</div>
                </div>
                """, unsafe_allow_html=True)

            with c2:
                st.markdown(f"""
                <div class="trend-card">
                    <div class="trend-label">Most Viewed Video</div>
                    <div class="trend-value" title="{df_videos.loc[df_videos['view_count'].idxmax()]['title']}">
                        "{best_vid_title}"
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with c3:
                st.markdown(f"""
                <div class="trend-card">
                    <div class="trend-label">Highest Engagement</div>
                    <div class="trend-value" title="{df_videos.loc[df_videos['engagement_rate'].idxmax()]['title']}">
                        "{best_eng_title}"
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        else:
            st.info("Not enough data for trend analysis.")

        st.write("###")

    # --- TAB 4: COMPARISON (Optimized Layout) ---
    elif "Comparison" in current_selection:
        st.markdown('<h3 style="color:#00E5FF; margin-bottom:20px;">Competitive Visual Analysis</h3>', unsafe_allow_html=True)
        
        df_channels = get_all_channels_list()
        current_name = stats['channel_name']
        competitor_options = df_channels[df_channels['channel_name'] != current_name]['channel_name']
        
        c_sel, _ = st.columns([2, 2])
        with c_sel:
            comp_name = st.selectbox(
                "Select Competitor", 
                options=competitor_options, 
                index=None, 
                placeholder="Select Competitor Channel",
                label_visibility="collapsed"
            )
        
        if comp_name:
            channel_map = dict(zip(df_channels['channel_name'], df_channels['channel_id']))
            id2 = channel_map[comp_name]
            comp_df = compare_channels([ch_id, id2])
            
            if not comp_df.empty:
                # Shared Black Box Legend Style
                def get_legend_style(position="right"):
                    return dict(
                        yanchor="top", y=0.99,
                        xanchor="left" if position == "left" else "right",
                        x=0.01 if position == "left" else 0.99,
                        bgcolor="rgba(0,0,0,0.8)",
                        bordercolor="#333",
                        borderwidth=1,
                        font=dict(color='white', size=11)
                    )
                st.write("###")

                # --- ROW 1: DONUT PIE CHARTS ---
                col_p1, col_p2 = st.columns(2)
                
                with col_p1:
                    fig_subs = px.pie(comp_df, values='subscribers', names='channel_name', 
                                    hole=0.5, color_discrete_sequence=['#D90368', '#00E5FF'])
                    fig_subs.update_layout(
                        title=dict(text="SUBSCRIBERS", font=dict(color='#00E5FF', size=18), x=0.5, xanchor='center'),
                        paper_bgcolor="rgba(0,0,0,0)",
                        legend=get_legend_style("left")  # Legend at Top-Left for long names
                    )
                    st.plotly_chart(fig_subs, use_container_width=True)

                with col_p2:
                    fig_views = px.pie(comp_df, values='total_views', names='channel_name', 
                                    hole=0.5, color_discrete_sequence=['#822FAF', '#009688'])
                    fig_views.update_layout(
                        title=dict(text="VIEWS", font=dict(color='#00E5FF', size=18), x=0.5, xanchor='center'),
                        paper_bgcolor="rgba(0,0,0,0)",
                        legend=get_legend_style("left")
                    )
                    st.plotly_chart(fig_views, use_container_width=True)

                # --- ROW 2: EFFICIENCY BAR CHART ---
                st.write("###")
                comp_df['avg_views'] = comp_df['total_views'] / comp_df['total_videos']
                
                fig_eff = px.bar(comp_df, x='channel_name', y='avg_views', color='channel_name',
                                color_discrete_map={current_name: '#D90368', comp_name: '#00E5FF'})
                
                fig_eff.update_layout(
                    title=dict(text="CONTENT EFFICIENCY", font=dict(color='#00E5FF', size=18), x=0.5, xanchor='center'),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    legend=get_legend_style("right"),
                    xaxis=dict(title=dict(text="Channel Name", font=dict(color='#00E5FF')), tickfont=dict(color='white')),
                    yaxis=dict(title=dict(text="Avg Views per Video", font=dict(color='#00E5FF')), tickfont=dict(color='white'), gridcolor='#333')
                )
                st.plotly_chart(fig_eff, use_container_width=True)

                # --- ROW 3: GROWTH SCALABILITY (RADAR/LINE) ---
                st.write("###")
                metrics = ['Subscribers', 'Total Views', 'Total Videos']
                ch1_data = comp_df[comp_df['channel_name'] == current_name].iloc[0]
                ch2_data = comp_df[comp_df['channel_name'] == comp_name].iloc[0]

                fig_radar = go.Figure()
                # Normalized metrics for side-by-side comparison
                fig_radar.add_trace(go.Scatter(x=metrics, y=[1, 1, 1], name=current_name, line=dict(color='#D90368', width=4)))
                fig_radar.add_trace(go.Scatter(x=metrics, y=[
                    ch2_data['subscribers']/ch1_data['subscribers'] if ch1_data['subscribers']>0 else 1,
                    ch2_data['total_views']/ch1_data['total_views'] if ch1_data['total_views']>0 else 1,
                    ch2_data['total_videos']/ch1_data['total_videos'] if ch1_data['total_videos']>0 else 1
                ], name=comp_name, line=dict(color='#00E5FF', width=4)))

                fig_radar.update_layout(
                    title=dict(text="PERFORMANCE SCALABILITY", font=dict(color='#00E5FF', size=18), x=0.5, xanchor='center'),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    legend=get_legend_style("right"),
                    xaxis=dict(title=dict(text="Metric Category", font=dict(color='#00E5FF')), tickfont=dict(color='white')),
                    yaxis=dict(title=dict(text="Performance Scale", font=dict(color='#00E5FF')), tickfont=dict(color='white'), gridcolor='#333')
                )
                st.plotly_chart(fig_radar, use_container_width=True)

        st.write("###")

    # --- TAB 5: RECOMMENDATION (THE GROWTH ENGINE) ---
    elif "Recommendation" in current_selection:
        
        # =========================================================
        # 1. CSS STYLES (HEIGHT SYNCHRONIZATION FIX)
        # =========================================================
        st.markdown("""
        <style>
        /* 1. FORCE COLUMNS TO CENTER CONTENT VERTICALLY */
        [data-testid="column"] {
            display: flex;
            flex-direction: column;
            justify-content: center; /* This forces alignment */
            height: 100%;
        }

        /* 2. TEXT BOX (Glass Card) */
        .glass-card {
            background: rgba(20, 20, 20, 0.6);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            
            /* FIXED HEIGHT: 350px */
            height: 350px !important; 
            padding: 40px;
            margin: 0 !important; /* Remove external margins */
            
            display: flex;
            flex-direction: column;
            justify-content: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            overflow: hidden; 
            transition: all 0.3s ease; 
        }
        
        .glass-card h3 {
            font-size: 28px !important;
            font-weight: 800 !important;
            margin: 0 0 15px 0 !important;
            color: #FFFFFF !important;
            line-height: 1.2 !important;
        }
        
        .glass-card p {
            font-size: 16px !important;
            color: #E0E0E0 !important;
            line-height: 1.6 !important;
            margin: 0 !important;
        }

        /* 3. GRAPH CONTAINER */
        div[data-testid="stPlotlyChart"] {
            background: rgba(20, 20, 20, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 10px;
            
            /* FIXED HEIGHT: 350px (Matches Text Box EXACTLY) */
            height: 350px !important; 
            margin: 0 !important; /* Remove external margins */
            
            overflow: hidden !important; 
            transition: all 0.3s ease; 
        }

        /* SHARED HOVER EFFECT */
        .glass-card:hover, div[data-testid="stPlotlyChart"]:hover {
            border-color: rgba(0, 229, 255, 0.8) !important;
            transform: translateY(-7px) !important;
            box-shadow: 0 15px 40px rgba(0, 229, 255, 0.2) !important;
        }

        /* 4. CENTER COLUMN (THE NEON DOT) */
        .timeline-col {
            display: flex;
            align-items: center; 
            justify-content: center;
            width: 100%;
            height: 100%;
        }

        .timeline-dot {
            width: 30px; 
            height: 30px;
            background: #0E0E0E; 
            border-radius: 50%;
            border-width: 6px;
            border-style: solid;
            box-shadow: 0 0 30px currentColor; 
        }
        
        /* 5. ANIMATIONS */
        .anim-left { animation: slideInLeft 0.8s ease-out forwards; }
        .anim-right { animation: slideInRight 0.8s ease-out forwards; }
        @keyframes slideInLeft { from { opacity: 0; transform: translateX(-50px); } to { opacity: 1; transform: translateX(0); } }
        @keyframes slideInRight { from { opacity: 0; transform: translateX(50px); } to { opacity: 1; transform: translateX(0); } }
        </style>
        """, unsafe_allow_html=True)

        # TITLE
        st.markdown(f"""
        <div style="text-align:center; margin-bottom: 50px;">
            <h2 style="font-size: 3.5rem; font-weight: 800; background: linear-gradient(90deg, #FF0080, #7928CA, #00E5FF); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Growth Roadmap
            </h2>
            <p style="color:#aaa; font-size:1.2rem;">Data-Driven Strategy for {stats['channel_name']}</p>
        </div>
        """, unsafe_allow_html=True)

        # --- REFINED EMPTY STATE (CSS INTEGRATED) ---
        if df_videos.empty:
            st.markdown("""
                <div style="text-align: center; padding-top: 0px;">
                    <h2 style="color: #00E5FF; font-size: 2.2rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1px;">
                        Video Data Required
                    </h2>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("""
                <div style="display: flex; justify-content: center; margin: 15px auto;">
                    <div style="width: 40px; height: 2px; background: #D90368;"></div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("""
                <div style="text-align: center; padding-bottom: 100px;">
                    <p class="hero-subtitle" style="font-size: 1.1rem !important; margin: 0 auto; max-width: 600px;">
                        Please upload your videos first to unlock these analytics. <br>
                        Our engine requires historical content patterns to generate your custom 
                        <span style="color: #D90368; font-weight: 700;">Data Strategy</span>.
                    </p>
                </div>
            """, unsafe_allow_html=True)

            st.stop()

        # =========================================================
        # 2. CALCULATE VARIABLES
        # =========================================================
        avg_eng = df_videos['engagement_rate'].mean()
        eng_color = "#00FFC8" if avg_eng > 5 else "#FF0055" 

        avg_views = df_videos['view_count'].mean()
        future_dates = pd.date_range(start=df_videos['published_at'].max(), periods=30)
        future_views = [avg_views * (1 + (0.05 * i)) for i in range(30)] 

        # =========================================================
        # 3. EXTRACT REAL TAGS
        # =========================================================
        real_tags = {}
        if 'tags' in df_videos.columns:
            for tags_str in df_videos['tags']:
                if tags_str:
                    cleaned = str(tags_str).replace("'", "").replace("[", "").replace("]", "")
                    for tag in cleaned.split(','):
                        t = tag.strip()
                        if t:
                            real_tags[t] = real_tags.get(t, 0) + 1
        
        sorted_tags = sorted(real_tags.items(), key=lambda x: x[1], reverse=True)[:5]
        
        if not sorted_tags:
            tag_x = [0]
            tag_y = ["No Tags Found"]
            tag_color = "#333"
        else:
            tag_x = [x[1] for x in sorted_tags][::-1] 
            tag_y = [x[0] for x in sorted_tags][::-1]
            tag_color = "#D90368"

        # =========================================================
        # 4. BUILD GRAPHS (Set Height to 350px exactly!)
        # =========================================================
        config = {'displayModeBar': False, 'staticPlot': False}
        
        # --- GRAPH 1: ENGAGEMENT ---
        fig_eng = px.scatter(df_videos, x='view_count', y='engagement_rate', size='comment_count', color='engagement_rate',
            color_continuous_scale=['#FF0055', '#00FFC8'], template="plotly_dark")
        
        fig_eng.update_layout(
            # 🔥 CRITICAL FIX: Match CSS height (350)
            height=350, 
            margin=dict(l=20, r=20, t=40, b=20), 
            paper_bgcolor="rgba(0,0,0,0)", 
            plot_bgcolor="rgba(0,0,0,0)", 
            showlegend=False, 
            coloraxis_colorbar=dict(title=None, tickfont=dict(color='white')),
            
            title=dict(text="Engagement vs Views", font=dict(color='#00E5FF', size=18, family="Inter"), x=0.5, xanchor='center'),
            xaxis=dict(title=dict(text="Total Views", font=dict(color='#00E5FF')), tickfont=dict(color='white'), showgrid=False, rangemode='tozero'),
            yaxis=dict(title=dict(text="Engagement Rate (%)", font=dict(color='#00E5FF')), tickfont=dict(color='white'), showgrid=True, gridcolor='#333', zeroline=True, zerolinecolor='#555', rangemode='tozero')
        )

        # --- GRAPH 2: FORECAST ---
        fig_proj = go.Figure()
        fig_proj.add_trace(go.Scatter(x=future_dates, y=future_views, mode='lines', line=dict(color='#822FAF', width=4), fill='tozeroy', fillcolor='rgba(130, 47, 175, 0.2)'))
        
        fig_proj.update_layout(
            # 🔥 CRITICAL FIX: Match CSS height (350)
            height=350, 
            margin=dict(l=20, r=20, t=40, b=20), 
            paper_bgcolor="rgba(0,0,0,0)", 
            plot_bgcolor="rgba(0,0,0,0)", 
            showlegend=False, 
            
            title=dict(text="30-Day Growth Forecast", font=dict(color='#00E5FF', size=18, family="Inter"), x=0.5, xanchor='center'),
            xaxis=dict(title=dict(text="Future Date", font=dict(color='#00E5FF')), tickfont=dict(color='white'), showgrid=False), 
            yaxis=dict(title=dict(text="Projected Views", font=dict(color='#00E5FF')), tickfont=dict(color='white'), showgrid=False, rangemode='tozero')
        )

        # --- GRAPH 3: REAL KEYWORDS ---
        fig_tags = go.Figure(go.Bar(x=tag_x, y=tag_y, orientation='h', marker_color=tag_color))
        
        fig_tags.update_layout(
            # 🔥 CRITICAL FIX: Match CSS height (350)
            height=350, 
            margin=dict(l=20, r=20, t=40, b=20), 
            paper_bgcolor="rgba(0,0,0,0)", 
            plot_bgcolor="rgba(0,0,0,0)", 
            
            title=dict(text="Top Keyword Volume", font=dict(color='#00E5FF', size=18, family="Inter"), x=0.5, xanchor='center'),
            xaxis=dict(title=dict(text="Frequency", font=dict(color='#00E5FF')), tickfont=dict(color='white'), showgrid=False, rangemode='tozero'), 
            yaxis=dict(title=dict(text="Keywords", font=dict(color='#00E5FF')), tickfont=dict(color='white', size=14), showgrid=False)
        )

        

        # =========================================================
        # 5. RENDER LAYOUT
        # =========================================================

        # --- ROW 1 ---
        c1, c2, c3 = st.columns([1, 0.2, 1], vertical_alignment="center")

        with c1:
            st.markdown(f"""
            <div class="anim-left">
                <div class="glass-card" style="border-left: 5px solid {eng_color};">
                    <div style="color: {eng_color}; font-weight:800; font-size:14px; letter-spacing:2px; margin-bottom:10px;">STEP 01</div>
                    <h3>Engagement Audit</h3>
                    <p>
                        Your engagement is <b style="color:{eng_color}">{avg_eng:.1f}%</b>.
                        {'Excellent! Push for viral growth.' if avg_eng > 5 else 'Try adding call-to-actions (CTAs) earlier in the video.'}
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div class="timeline-col">
                <div class="timeline-dot" style="border-color: {eng_color}; color: {eng_color};"></div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown('<div class="anim-right">', unsafe_allow_html=True)
            st.plotly_chart(fig_eng, use_container_width=True, config=config)
            st.markdown('</div>', unsafe_allow_html=True)

        # --- SPACER ---
        st.write("##")

        # --- ROW 2 ---
        c1, c2, c3 = st.columns([1, 0.2, 1], vertical_alignment="center")

        with c1:
            st.markdown('<div class="anim-left">', unsafe_allow_html=True)
            st.plotly_chart(fig_proj, use_container_width=True, config=config)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown("""
            <div class="timeline-col">
                <div class="timeline-dot" style="border-color: #822FAF; color: #822FAF;"></div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown("""
            <div class="anim-right">
                <div class="glass-card" style="border-right: 5px solid #822FAF; text-align: right; align-items: flex-end;">
                    <div style="color: #822FAF; font-weight:800; font-size:14px; letter-spacing:2px; margin-bottom:10px;">STEP 02</div>
                    <h3>Consistency Effect</h3>
                    <p>
                        Our model predicts a <b style="color:#822FAF">250%</b> view increase if you maintain a weekly schedule.
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # --- SPACER ---
        st.write("##")

        # --- ROW 3 ---
        c1, c2, c3 = st.columns([1, 0.2, 1], vertical_alignment="center")

        with c1:
            st.markdown("""
            <div class="anim-left">
                <div class="glass-card" style="border-left: 5px solid #D90368;">
                    <div style="color: #D90368; font-weight:800; font-size:14px; letter-spacing:2px; margin-bottom:10px;">STEP 03</div>
                    <h3>Keyword Mastery</h3>
                    <p>
                        Your top videos share specific tags. 
                        We've isolated your highest performing keywords to focus on.
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown("""
            <div class="timeline-col">
                <div class="timeline-dot" style="border-color: #D90368; color: #D90368;"></div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown('<div class="anim-right">', unsafe_allow_html=True)
            st.plotly_chart(fig_tags, use_container_width=True, config=config)
            st.markdown('</div>', unsafe_allow_html=True)

        st.write("###")

    # --- Tab 6: ASK PILOT ---
    elif "Ask Pilot" in current_selection:
        st.markdown('<h3 style="color:#00E5FF; margin-bottom: 20px;">🤖 AI Pilot</h3>', unsafe_allow_html=True)

        if "history" not in st.session_state:
            st.session_state.history = []

        GENERAL_INSTRUCTION = f"""
            You are a YouTube assistant for {stats['channel_name']}. 
            Channel Context: {get_ai_context(df_videos)}
            
            RULES:
            1. Give ONLY the specific answer. 
            2. Maximum 2 sentences. 
            3. No 'Growth Strategy' or long advice. 
            4. Be very direct.
            """
        
        # 1. THE SEARCH CONTAINER 
        with st.form("pilot_search_form", clear_on_submit=True):
            cols = st.columns([6, 1, 1])

            user_input = cols[0].text_input("Ask about your performance...", placeholder="Type here...", label_visibility="collapsed")
            submit_btn = cols[1].form_submit_button("Enter", type="primary", use_container_width=True)
            clear_btn = cols[2].form_submit_button("Clear", type="secondary", use_container_width=True)
            
            if submit_btn and user_input:
                # Process the message
                st.session_state.history.append({"role": "user", "content": user_input})
                try:
                    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                    response = client.models.generate_content(
                        model="gemini-flash-latest",
                        config=types.GenerateContentConfig(system_instruction=GENERAL_INSTRUCTION),
                        contents=[user_input]
                    )
                    st.session_state.history.append({"role": "ai", "content": response.text})
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

            # Handle the clear action inside the form logic
            if clear_btn:
                st.session_state.history = []
                st.rerun()

        # 2. REVERSED CHAT HISTORY
        for message in reversed(st.session_state.history):
            if message["role"] == "user":
                st.markdown(f'<div class="chat-row row-reverse"><div class="chat-bubble user-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-row"><div class="chat-bubble ai-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)

        st.write("###")