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

def get_ai_context(df):
    if df is None or df.empty:
        return "No channel data loaded yet."
    
    total_views = df['view_count'].sum()
    avg_eng = df['engagement_rate'].mean()
    top_video = df.loc[df['view_count'].idxmax()]['title']
    
    return f"Total Views: {total_views}, Avg Engagement: {avg_eng:.2f}%, Top Video: {top_video}"

def render_ask_pilot(df_videos, df_monthly, stats, ch_id):
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