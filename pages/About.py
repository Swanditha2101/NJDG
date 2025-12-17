import streamlit as st

st.set_page_config(
    page_title="About Us",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="stSidebarNav"] {
    display: none !important;
}
header[data-testid="stHeader"] {
    height: 0px !important;
}
</style>
""", unsafe_allow_html=True)

if st.button("Home"):
    st.switch_page("app.py")

st.markdown("""
# About Nyayadrishti

Nyayadrishti is a **Judicial Case Management Dashboard** designed to bring transparency, efficiency, and clarity to the judicial process.

### 🌟 Our Mission
- Faster case disposal through data-driven insights  
- Effective monitoring of hearings and case timelines  
- Transparent access to judicial statistics  

### ⚖️ Why Nyayadrishti?
- Real-time analytics  
- AI-powered predictions  
- Anomaly detection for delays  
""")
