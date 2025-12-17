import streamlit as st

st.set_page_config(
    page_title="Help",
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
# Help & Support

### 📞 Contact
- Technical: +91 83690 67848  
- Data Queries: +91 63623 16342  

### ❓ Common Issues
- Login problems  
- Data not loading  
- Dashboard errors  
""")
