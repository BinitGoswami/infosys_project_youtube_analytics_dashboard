import streamlit as st
import auth
from analytics import get_my_channel

def render_header():
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
        is_logged_in = auth.is_authenticated()
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
    
