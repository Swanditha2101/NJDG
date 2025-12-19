import streamlit as st
from pathlib import Path
import base64
from streamlit_cookies_manager import EncryptedCookieManager

# --------------------------------------------------
# LOAD LOGO (UNCHANGED)
# --------------------------------------------------
base_dir = Path(__file__).parent.parent
logo_path = base_dir / "logo.png"

logo_b64 = ""
if logo_path.exists():
    with open(logo_path, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()

# --------------------------------------------------
# SIDEBAR RENDER
# --------------------------------------------------
def render_sidebar():
    st.sidebar.markdown(f"""
    <style>
    [data-testid="stSidebar"] {{
        background-color: #F8FAFC !important;
    }}

    [data-testid="stSidebar"] * {{
        color: black !important;
    }}

    /* Hide Streamlit default navigation */
    [data-testid="stSidebar"] nav,
    [data-testid="stSidebarNav"],
    [data-testid="stVerticalNav"],
    nav[aria-label="Page navigation"] {{
        display: none !important;
    }}

    /* Sidebar buttons */
    [data-testid="stSidebar"] .stButton > button {{
        width: 100% !important;
        padding: 10px 14px !important;
        text-align: left !important;
        border-radius: 8px !important;
        background-color: transparent !important;
        color: black !important;
        font-weight: 500;
    }}

    [data-testid="stSidebar"] .stButton {{
        margin-bottom: 8px !important;
    }}

    [data-testid="stSidebar"] img {{
        position: fixed;
        top: 20px;
        left: 22px;
        width: 72px;
        z-index: 9999;
    }}
    </style>

    <img src="data:image/png;base64,{logo_b64}">
    """, unsafe_allow_html=True)

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------
    st.sidebar.header("Navigation")

    if st.sidebar.button("Home"):
        st.switch_page("app.py")

    # Dynamic main button (UNCHANGED BEHAVIOUR)
    if st.session_state.get("authenticated") and st.session_state.get("user_role") in ["Judge", "Advocate (Lawyer)"]:
        main_label = "Your Cases"
    else:
        main_label = "Login"

    if st.sidebar.button(main_label):
        if st.session_state.get("authenticated"):
            role = st.session_state.get("user_role")
            if role == "Judge":
                st.switch_page("pages/Judge_Dashboard.py")
            elif role == "Advocate (Lawyer)":
                st.switch_page("pages/Lawyer_Dashboard.py")
            else:
                st.switch_page("pages/Login.py")
        else:
            st.switch_page("pages/Login.py")

    if st.sidebar.button("AI Predictions"):
        st.switch_page("pages/AI_Predictions.py")

    if st.sidebar.button("Anomaly Detection"):
        st.switch_page("pages/Anomaly_Detection.py")

    if st.sidebar.button("Analytics"):
        st.switch_page("pages/Analytics.py")

    # --------------------------------------------------
    # ✅ DOWNLOAD PAGE (ADDED — UI SAME)
    # --------------------------------------------------
    if st.sidebar.button("Download Case PDF"):
        st.switch_page("pages/DownloadCasePDF.py")

    st.sidebar.markdown("---")

    # --------------------------------------------------
    # LOGOUT (UNCHANGED)
    # --------------------------------------------------
    if st.session_state.get("authenticated"):
        if st.sidebar.button("Logout"):
            try:
                from sessions import delete_token
                user = st.session_state.get("user_name")
                if user:
                    delete_token(user)
            except Exception:
                pass

            st.session_state.authenticated = False
            st.session_state.user_role = None
            st.session_state.user_name = None

            try:
                cookies = EncryptedCookieManager(
                    prefix="nyayadrishti_",
                    password="super_secret_password_here"
                )
                if cookies.ready():
                    cookies["authenticated"] = "false"
                    cookies["user_role"] = ""
                    cookies["user_name"] = ""
                    cookies.save()
            except Exception:
                pass

            st.switch_page("pages/Login.py")
