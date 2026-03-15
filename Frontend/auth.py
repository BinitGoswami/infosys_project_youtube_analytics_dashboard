import streamlit as st
import analytics
from google_auth_oauthlib.flow import Flow
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS_FILE")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = ['https://www.googleapis.com/auth/userinfo.email', 
          'https://www.googleapis.com/auth/userinfo.profile', 
          'openid',
          'https://www.googleapis.com/auth/youtube.readonly']

def init():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user_email" not in st.session_state:
        st.session_state["user_email"] = None
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = None
        
    analytics.init_user_db()

def is_authenticated():
    if "code" in st.query_params and not st.session_state["authenticated"]:
        handle_google_redirect()
    return st.session_state["authenticated"]

def login_dialog():
    # 1. Initialize State for toggling views
    if "auth_mode" not in st.session_state:
        st.session_state["auth_mode"] = "login"

    # 2. LOGO & HEADER
    st.markdown("""
        <div style="
            display: flex; 
            align-items: center; 
            justify-content: center; 
            gap: 12px; 
            margin-bottom: 10px; /* Reduced from 25px */
        ">
            <div style="
                display: flex; align-items: center; justify-content: center; 
                width: 40px; height: 40px; 
                background: linear-gradient(135deg, rgba(217, 3, 104, 0.1), rgba(130, 47, 175, 0.1)); 
                border-radius: 10px; border: 1px solid rgba(255,255,255,0.05);
            ">
                <span style="font-size: 18px;">🔐</span>
            </div>
            <h2 style="
                margin: 0; font-size: 22px; font-weight: 700;
                background: linear-gradient(90deg, #fff, #ccc);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            ">
                Member Login
            </h2>
        </div>
    """, unsafe_allow_html=True)

    # 3. TABS (Email vs Google)
    tab_email, tab_google = st.tabs(["Email", "Google"])

    with tab_email:
        
        
        # --- VIEW: LOGIN ---
        if st.session_state["auth_mode"] == "login":
            email = st.text_input("Email", placeholder="name@example.com", key="login_email", label_visibility="collapsed")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="login_pass", label_visibility="collapsed")
            
            
            if st.button("Sign In", type="primary", width='stretch'):
                if not email or not password:
                    st.toast("Please enter both Email and Password!", icon="⚠️")
                else:
                    if analytics.verify_user(email, password):
                        # 1. Identity Verified
                        st.session_state["authenticated"] = True
                        st.session_state["user_email"] = email
                        st.session_state["user_name"] = analytics.get_user_name(email)
                        
                        # 2. Check for YouTube Authorization
                        my_id = analytics.get_my_channel(email)
                        
                        if my_id:
                            # Already linked -> Go to Dashboard
                            login_success(email)
                        else:
                            # Not linked -> DIRECT REDIRECT to Google Auth
                            flow = Flow.from_client_secrets_file(
                                GOOGLE_CLIENT_SECRETS_FILE,
                                scopes=SCOPES,
                                redirect_uri=REDIRECT_URI
                            )
                            auth_url, _ = flow.authorization_url(prompt='consent')
                            
                            # JavaScript-style redirect to Google
                            st.markdown(f'<meta http-equiv="refresh" content="0;URL=\'{auth_url}\'">', unsafe_allow_html=True)
                            st.write("Verifying YouTube permissions...")
                    else:
                        st.toast("Invalid Email or Password", icon="❌")

            # THE BOTTOM TOGGLE BUTTON YOU WANTED
            st.markdown('<div style="text-align: center; margin: 15px 0; color: #666; font-size: 13px;">Don\'t have an account?</div>', unsafe_allow_html=True)
            if st.button("Create Account", type="primary", width='stretch'):
                st.session_state["auth_mode"] = "signup"
                st.rerun()

        elif st.session_state["auth_mode"] == "authorize_youtube":
            st.info("To link your data, please authorize this app to access your YouTube Channel statistics.")
            
            # 1. Setup the Google Flow for authorization
            if os.path.exists(GOOGLE_CLIENT_SECRETS_FILE):
                flow = Flow.from_client_secrets_file(
                    GOOGLE_CLIENT_SECRETS_FILE,
                    scopes=SCOPES,
                    redirect_uri=REDIRECT_URI
                )
                # prompt='consent' forces the "Permission" screen to appear
                auth_url, _ = flow.authorization_url(prompt='consent')

                # 2. Redirect to Google for verification
                st.markdown(f'''
                    <a href="{auth_url}" target="_self" style="text-decoration: none;">
                        <div class="google-btn">
                            Authorize with Google
                        </div>
                    </a>
                ''', unsafe_allow_html=True)
            else:
                st.error("Missing client_secret.json configuration.")

        # --- VIEW: SIGN UP ---
        else:
            name = st.text_input("Full Name", placeholder="e.g. John Doe", key="signup_name", label_visibility="collapsed")
            email = st.text_input("Email", placeholder="name@example.com", key="signup_email", label_visibility="collapsed")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="signup_pass")
            
            
            if st.button("Create Account", type="primary", width='stretch'):
                if name and email and password:
                    if analytics.create_user(email, password, name):
                        st.success("Account created! Logging in...")
                        login_success(email)
                    else:
                        st.error("User already exists")
                else:
                    st.toast("⚠️ Please fill all fields!")

            # THE BOTTOM TOGGLE BUTTON (BACK)
            st.markdown('<div style="text-align: center; margin: 15px 0; color: #666; font-size: 13px;">Already have an account?</div>', unsafe_allow_html=True)
            if st.button("Back to Sign In", type="primary", width='stretch'):
                st.session_state["auth_mode"] = "login"
                st.rerun()

    # --- GOOGLE MODE ---
    with tab_google:
        
        if os.path.exists(GOOGLE_CLIENT_SECRETS_FILE):
            flow = Flow.from_client_secrets_file(
                GOOGLE_CLIENT_SECRETS_FILE,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI
            )
            auth_url, _ = flow.authorization_url(prompt='select_account')
            
            # CLEANER CODE: Uses the .google-btn class from style.css
            st.markdown(f'''
                <a href="{auth_url}" target="_self" style="text-decoration: none;">
                    <div class="google-btn">
                        Continue with Google
                    </div>
                </a>
            ''', unsafe_allow_html=True)
        else:
            st.error("Missing client_secret.json")

def handle_google_redirect():
    try:
        code = st.query_params["code"]
        flow = Flow.from_client_secrets_file(
            GOOGLE_CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        flow.fetch_token(code=code)
        session = flow.authorized_session()
        
        user_info = session.get('https://www.googleapis.com/userinfo/v2/me').json()
        email = user_info.get('email')
        name = user_info.get('name', 'User')

        # 1. IDENTIFY: Check MySQL immediately
        existing_channel_id = analytics.get_my_channel(email)

        if existing_channel_id:
            # 2. LOCK STATE: Set everything main.py needs
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = email
            st.session_state["user_name"] = name
            st.session_state['channel_id'] = existing_channel_id
            st.session_state['just_browsing'] = False
            
            # 3. CLEANUP & FLIP: Remove 'code' from URL and re-render
            st.query_params.clear()
            st.session_state["show_auth_dialog"] = False
            st.rerun() # Skip login_success to avoid redundant checks
            return 

        # 4. AUTHORIZE: Only for brand new users
        ch_res = session.get('https://www.googleapis.com/youtube/v3/channels?part=id&mine=true').json()
        if ch_res.get('items'):
            channel_id = ch_res['items'][0]['id']
            analytics.link_user_channel(email, channel_id, name)
            st.session_state['channel_id'] = channel_id
            st.session_state['just_browsing'] = False

        st.query_params.clear()
        login_success(email)

    except Exception as e:
        st.error(f"Redirect Error: {e}")
        
# auth.py
def login_success(email):
    # 1. AUTHENTICATE: Set the core session states
    st.session_state["authenticated"] = True
    st.session_state["user_email"] = email
    
    # 2. IDENTIFY: Get the user's name from the DB (Fixes the split error)
    st.session_state["user_name"] = analytics.get_user_name(email) 
    
    # 3. YOUTUBE CHECK: Fetch the channel ID linked to this Email
    my_id = analytics.get_my_channel(email) 
    
    if my_id:
        # 4. RENDER: Set the ID so main.py skips the landing page
        st.session_state['channel_id'] = my_id 
        st.session_state['just_browsing'] = False
        st.toast(f"Authorized! Loading {my_id} dashboard...")
    else:
        # If no channel is linked, they stay on landing but are logged in
        st.session_state['channel_id'] = None
        st.toast("Authenticated! Please search and select your channel.")
    
    # 5. EXECUTE: Close the login box and re-run the app logic
    st.session_state["show_auth_dialog"] = False
    st.rerun()

def logout():
    # Clear Auth Details
    st.session_state["authenticated"] = False
    st.session_state["user_email"] = None
    st.session_state["user_name"] = None
    
    # Force Back to Landing Page (Clear the Dashboard ID)
    if 'channel_id' in st.session_state:
        st.session_state['channel_id'] = None 
        
    # Reload
    st.rerun()