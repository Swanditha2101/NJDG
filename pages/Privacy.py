import streamlit as st

st.set_page_config(
    page_title="Privacy Policy",
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
# Privacy Policy

We respect user privacy.

### 🔒 What We Collect
- Aggregated judicial data  
- No personal case details  

### 🚫 What We Don’t Do
- No tracking  
- No selling data  
""")
