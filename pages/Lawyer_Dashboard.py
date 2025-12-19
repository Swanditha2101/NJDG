import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
from streamlit_cookies_manager import EncryptedCookieManager
from components.language import render_language_header

from preprocessing import load_data, clean_cases, clean_hearings, merge_data
from helpers.sidebar import render_sidebar
from sessions import validate_token
from utils import load_notes, save_notes, load_reminders, save_reminders

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Advocate Dashboard", layout="wide")
render_language_header()

# -------------------------------------------------
# COOKIE LOGIN
# -------------------------------------------------
cookies = EncryptedCookieManager(
    prefix="nyayadrishti_",
    password="super_secret_password_here"
)

if not cookies.ready():
    st.stop()

def auto_login(c):
    token = c.get("session_token")
    name = c.get("user_name")
    return token and name and validate_token(name, token)

if not st.session_state.get("authenticated") and auto_login(cookies):
    st.session_state.authenticated = True
    st.session_state.user_name = cookies.get("user_name")

if not st.session_state.get("authenticated"):
    st.warning(("login_first"))
    st.switch_page("pages/Login.py")

render_sidebar()

# -------------------------------------------------
# DATA
# -------------------------------------------------
@st.cache_data(show_spinner=False)
def load_all():
    cases, hearings = load_data()
    cases = clean_cases(cases)
    hearings = clean_hearings(hearings)
    merged = merge_data(cases, hearings)
    merged.columns = merged.columns.str.lower().str.strip()
    return merged

df = load_all()

# -------------------------------------------------
# HEALTH
# -------------------------------------------------
today = pd.Timestamp.today()
df["date_filed"] = pd.to_datetime(df["date_filed"], errors="coerce")
df["age_days"] = (today - df["date_filed"]).dt.days.fillna(0)

df["case_health_score"] = (
    0.5 * np.clip(100 - df["age_days"] / 5, 0, 100) +
    0.3 * np.where(df["current_status"].str.lower().str.contains("disposed", na=False), 100, 60)
).round(1)

# -------------------------------------------------
# LAWYER CONTEXT
# -------------------------------------------------
lawyer = st.session_state.user_name

portfolio = df[
    df["petitioneradvocate"].str.contains(lawyer, case=False, na=False) |
    df["respondentadvocate"].str.contains(lawyer, case=False, na=False)
]

if portfolio.empty:
    st.info(("no_cases"))
    st.stop()

st.success(f"{('logged_in_as')} {lawyer}")

# -------------------------------------------------
# LAWYER HEALTH
# -------------------------------------------------
active = portfolio[portfolio["current_status"].str.lower() != "disposed"]
hearings_7 = portfolio[
    (pd.to_datetime(portfolio["nexthearingdate"], errors="coerce") <= today + timedelta(days=7))
]

pressure = 0.4 * len(active) + 0.3 * len(hearings_7)
lawyer_health = int(np.clip(100 - pressure * 2, 0, 100))

st.subheader(("lawyer_health"))
st.metric(("lawyer_health"), f"{lawyer_health} / 100")

# -------------------------------------------------
# PORTFOLIO
# -------------------------------------------------
st.subheader(("your_cases"))
st.dataframe(
    portfolio[
        ["cnr_number", "case_number", "current_status", "case_health_score", "nexthearingdate"]
    ],
    use_container_width=True
)

# -------------------------------------------------
# WORKSPACE
# -------------------------------------------------
st.subheader(("case_workspace"))
cnr = st.text_input("CNR Number")

notes = load_notes()
reminders = load_reminders()

if cnr:
    case = portfolio[portfolio["cnr_number"] == cnr]
    if not case.empty:
        row = case.iloc[0]

        st.markdown(f"### {('notes')}")
        note_text = st.text_area("", notes.get(cnr, ""))
        if st.button(("save_notes")):
            notes[cnr] = note_text
            save_notes(notes)
            st.success("Saved")

        nh = pd.to_datetime(row["nexthearingdate"], errors="coerce")
        if pd.notna(nh):
            reminders[cnr] = str((nh - timedelta(days=2)).date())
            save_reminders(reminders)

# -------------------------------------------------
# REMINDERS
# -------------------------------------------------
st.subheader(("reminders"))
if reminders:
    st.dataframe(pd.DataFrame(reminders.items(), columns=["CNR", "Date"]), use_container_width=True)
else:
    st.info("No reminders yet.")
