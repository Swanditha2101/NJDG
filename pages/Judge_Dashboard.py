import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from streamlit_cookies_manager import EncryptedCookieManager
from components.language import render_language_header, t
from preprocessing import load_data, clean_cases, clean_hearings
from helpers.sidebar import render_sidebar
from sessions import validate_token

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Judge Dashboard", layout="wide")
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
    st.warning(t("login_first"))
    st.switch_page("pages/Login.py")

render_sidebar()

# -------------------------------------------------
# DATA LOAD (ROBUST MERGE — FIXED)
# -------------------------------------------------
@st.cache_data(show_spinner=False)
def load_all():
    cases, hearings = load_data()

    cases = clean_cases(cases)
    hearings = clean_hearings(hearings)

    cases.columns = cases.columns.str.lower().str.strip()
    hearings.columns = hearings.columns.str.lower().str.strip()

    case_keys = ["combined_case_number", "cnr_number", "case_number"]
    hearing_keys = ["combinedcasenumber", "cnr_number", "case_number"]

    left_key = next((k for k in case_keys if k in cases.columns), None)
    right_key = next((k for k in hearing_keys if k in hearings.columns), None)

    if not left_key or not right_key:
        raise ValueError("No common merge key found between cases and hearings")

    merged = pd.merge(
        cases,
        hearings,
        left_on=left_key,
        right_on=right_key,
        how="left",
        suffixes=("_case", "_hear")
    )

    merged["judge"] = merged.get(
        "beforehonourablejudges",
        merged.get("njdg_judge_name", "UNKNOWN")
    )

    return merged

df = load_all()

# -------------------------------------------------
# SCORES
# -------------------------------------------------
today = pd.Timestamp.today()
df["date_filed"] = pd.to_datetime(df["date_filed"], errors="coerce")
df["age_days"] = (today - df["date_filed"]).dt.days.fillna(0)

df["case_health_score"] = (
    0.5 * np.clip(100 - df["age_days"] / 5, 0, 100) +
    0.3 * np.where(df["current_status"].str.lower().str.contains("disposed", na=False), 100, 60)
).round(1)

df["priority_score"] = (
    0.6 * (100 - df["case_health_score"]) +
    0.4 * np.clip(df["age_days"] / 10, 0, 100)
).round(1)

# -------------------------------------------------
# JUDGE CONTEXT
# -------------------------------------------------
judge = st.session_state.user_name
judge_cases = df[df["judge"].str.upper() == judge.upper()]

if judge_cases.empty:
    st.warning(f"No cases found for Judge: {judge}")
    st.stop()

st.success(f"{t('logged_in_as')} {judge}")

# -------------------------------------------------
# NAVIGATION
# -------------------------------------------------
page = st.pills(
    "",
    [t("case_management"), t("alerts"), t("hearing_overview"), t("dashboard")],
    label_visibility="collapsed"
)

# -------------------------------------------------
# CASE MANAGEMENT
# -------------------------------------------------
if page == t("case_management"):
    st.header(t("case_management"))
    st.dataframe(
        judge_cases.sort_values("priority_score", ascending=False),
        use_container_width=True
    )

# -------------------------------------------------
# ALERTS
# -------------------------------------------------
elif page == t("alerts"):
    st.header(t("alerts"))
    critical = judge_cases[
        (judge_cases["case_health_score"] < 40) |
        (judge_cases["age_days"] > 730)
    ]
    st.dataframe(critical, use_container_width=True)

# -------------------------------------------------
# HEARING OVERVIEW
# -------------------------------------------------
elif page == "Hearing Overview":
    st.header("Hearing Overview")

    today = pd.to_datetime("today").normalize()

    if 'nexthearingdate' in judge_cases.columns:
        judge_cases['nexthearingdate'] = pd.to_datetime(judge_cases['nexthearingdate'], errors='coerce')
        today_hearings = judge_cases[judge_cases['nexthearingdate'] == today]
        upcoming_hearings = judge_cases[judge_cases['nexthearingdate'] > today]
    else:
        today_hearings, upcoming_hearings = pd.DataFrame(), pd.DataFrame()

    rescheduled = judge_cases[judge_cases['previoushearing'].notnull()] if 'previoushearing' in judge_cases.columns else pd.DataFrame()

    st.subheader("Today's Hearings")
    if not today_hearings.empty:
        st.dataframe(today_hearings[['case_number', 'nexthearingdate', 'appearancedate', 'purposeofhearing', 'judge']])
    else:
        st.info("No hearings today")

    st.subheader("Upcoming Hearings")
    if not upcoming_hearings.empty:
        st.dataframe(upcoming_hearings[['case_number', 'nexthearingdate', 'appearancedate', 'purposeofhearing', 'judge']])
    else:
        st.info("No upcoming hearings")

    st.subheader("Rescheduled Hearings")
    if not rescheduled.empty:
        st.dataframe(rescheduled[['case_number', 'nexthearingdate', 'previoushearing', 'purposeofhearing']])
    else:
        st.info("No rescheduled hearings")

# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------
elif page == "Dashboards / Charts":
    st.header("Dashboards & Charts")

    if 'disposal_year' in judge_cases.columns:
        disposal_trend = judge_cases.groupby('disposal_year').size().reset_index(name='count')
        fig = px.line(disposal_trend, x='disposal_year', y='count', title="Case Disposal Trend")
        st.plotly_chart(fig, width='stretch')

    fig_status = px.bar(
        judge_cases.groupby('current_status').size().reset_index(name='count'),
        x='current_status',
        y='count',
        title="Case Status Distribution"
    )
    st.plotly_chart(fig_status, width='stretch')
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("total_cases"), len(judge_cases))
    col2.metric(t("disposed"), judge_cases["current_status"].str.contains("disposed", case=False).sum())
    col3.metric(t("pending"), (~judge_cases["current_status"].str.contains("disposed", case=False)).sum())
    col4.metric(t("avg_health"), round(judge_cases["case_health_score"].mean(), 1))

    fig = px.histogram(judge_cases, x="case_health_score", nbins=10)
    st.plotly_chart(fig, use_container_width=True)