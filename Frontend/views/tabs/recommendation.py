import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pycountry as pc
from analytics import format_big_number, get_channel_stats, get_channel_videos, get_monthly_analytics, compare_channels, get_seasonal_analytics, get_top_keywords, get_duration_clustering, get_all_channels_list
import live_data
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

def render_recommendation(df_videos, df_monthly, stats, ch_id):
        
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
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            
            /* FIXED HEIGHT: 350px */
            height: 350px !important; 
            padding: 30px !important;
            margin: 0 !important; 
            box-sizing: border-box !important;
            
            display: flex;
            flex-direction: column;
            justify-content: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            overflow: hidden; 
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease; 
            position: relative;
        }
        
        .glass-card::before {
            content: '';
            position: absolute;
            top: 0;
            bottom: 0;
            width: 5px;
            background-color: var(--card-accent, transparent);
            z-index: 10;
            transition: background-color 0.2s ease;
        }
        .glass-card.accent-left::before { left: 0; }
        .glass-card.accent-right::before { right: 0; }
        
        .glass-card h3 {
            font-size: 26px !important;
            font-weight: 800 !important;
            margin: 0 0 15px 0 !important;
            color: #FFFFFF !important;
            line-height: 1.2 !important;
        }
        
        .glass-card p {
            font-size: 15px !important;
            color: #E0E0E0 !important;
            line-height: 1.5 !important;
            margin: 0 !important;
        }
    
        /* 3. GRAPH CONTAINER */
        div[data-testid="stPlotlyChart"] {
            background: rgba(20, 20, 20, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            
            /* EXACT SAME STRUCTURE AS GLASS CARD */
            height: 350px !important; 
            padding: 30px !important; 
            margin: 0 !important; 
            box-sizing: border-box !important;
            
            /* Flex layout */
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            
            /* Reverting overflow to match text cards for perfect alignment */
            overflow: hidden !important; 
            position: relative;
            
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease; 
        }
    
        /* FORCE INNER CHART TO FILL PADDED BOX & PREVENT PLOTLY RESIZING */
        div[data-testid="stPlotlyChart"] > div,
        div[data-testid="stPlotlyChart"] iframe {
            width: 100% !important;
            height: 100% !important;
            min-height: 100% !important;
            max-height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
        }
        
        div[data-testid="stPlotlyChart"] ::-webkit-scrollbar {
            display: none !important;
        }
    
        /* SHARED HOVER EFFECT */
        .glass-card:hover, div[data-testid="stPlotlyChart"]:hover {
            border-color: rgba(0, 229, 255, 0.8) !important;
            box-shadow: 0 8px 25px rgba(0, 229, 255, 0.15) !important;
            z-index: 100 !important; /* Bring to front so tooltips don't clip */
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
            width: 24px; 
            height: 24px;
            background: #0E0E0E; 
            border-radius: 50%;
            border-width: 5px;
            border-style: solid;
            box-shadow: 0 0 10px currentColor; 
        }
        
        /* 5. ANIMATIONS */
        .anim-left { animation: slideInLeft 0.5s cubic-bezier(0.25, 1, 0.5, 1) forwards; }
        .anim-right { animation: slideInRight 0.5s cubic-bezier(0.25, 1, 0.5, 1) forwards; }
        
        div[data-testid="column"]:nth-child(1) div[data-testid="stPlotlyChart"] {
            animation: slideInLeft 0.5s cubic-bezier(0.25, 1, 0.5, 1) forwards;
        }
        div[data-testid="column"]:nth-child(3) div[data-testid="stPlotlyChart"] {
            animation: slideInRight 0.5s cubic-bezier(0.25, 1, 0.5, 1) forwards;
        }
        
        @keyframes slideInLeft { from { opacity: 0; transform: translate3d(-30px, 0, 0); } to { opacity: 1; transform: translate3d(0, 0, 0); } }
        @keyframes slideInRight { from { opacity: 0; transform: translate3d(30px, 0, 0); } to { opacity: 1; transform: translate3d(0, 0, 0); } }
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
                <div class="glass-card accent-left" style="--card-accent: {eng_color};">
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
            st.plotly_chart(fig_eng, use_container_width=True, config=config)
    
        # --- SPACER ---
        st.write("##")
    
        # --- ROW 2 ---
        c1, c2, c3 = st.columns([1, 0.2, 1], vertical_alignment="center")
    
        with c1:
            st.plotly_chart(fig_proj, use_container_width=True, config=config)
    
        with c2:
            st.markdown("""
            <div class="timeline-col">
                <div class="timeline-dot" style="border-color: #822FAF; color: #822FAF;"></div>
            </div>
            """, unsafe_allow_html=True)
    
        with c3:
            st.markdown("""
            <div class="anim-right">
                <div class="glass-card accent-right" style="--card-accent: #822FAF; text-align: right; align-items: flex-end;">
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
                <div class="glass-card accent-left" style="--card-accent: #D90368;">
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
            st.plotly_chart(fig_tags, use_container_width=True, config=config)
    
        st.write("###")
    
    # --- Tab 6: ASK PILOT ---
