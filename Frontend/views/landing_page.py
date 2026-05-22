import streamlit as st
from analytics import get_all_channels_list, get_channel_stats
import live_data

def render_landing_page():
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
    
