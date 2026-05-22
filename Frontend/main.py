import streamlit as st
import pandas as pd
import auth
import live_data
import warnings
import os
from analytics import get_my_channel

from views.header import render_header
from views.landing_page import render_landing_page
from views.dashboard import render_dashboard

warnings.filterwarnings('ignore')

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
render_header()

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
# 3. MAIN APP ROUTING
# ==========================================
if 'channel_id' not in st.session_state: 
    st.session_state['channel_id'] = None

# --- ROUTER ---
if st.session_state['channel_id'] is None:
    render_landing_page()
else:
    render_dashboard()