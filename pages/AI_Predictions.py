import streamlit as st
import pandas as pd
import numpy as np
from preprocessing import load_data, clean_cases
from helpers.sidebar import render_sidebar
from sklearn.metrics import mean_absolute_error
from components.language import render_language_header, t
# --------------------------------------------------
# Page Config
# --------------------------------------------------
st.set_page_config(
    page_title="AI Predictions",
    layout="wide",
    initial_sidebar_state="expanded",
)
render_language_header()
# Sidebar style
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background-color: #F8FAFC !important;
}
[data-testid="stSidebar"] * {
    color: black !important;
}
</style>
""", unsafe_allow_html=True)

render_sidebar()
st.title("AI-Assisted Disposal Time Predictions")

# --------------------------------------------------
# Load & Clean Data (Cached)
# --------------------------------------------------
@st.cache_data(show_spinner=False)
def load_cases():
    cases, _ = load_data()
    cases = clean_cases(cases)
    return cases

cases = load_cases()

required_cols = ["cnr_number", "disposal_days", "total_hearings", "filing_year"]
missing = [c for c in required_cols if c not in cases.columns]

if missing:
    st.error(f"Missing columns: {missing}")
    st.stop()

min_year = cases["filing_year"].min()

# --------------------------------------------------
# Prediction Controls (Global)
# --------------------------------------------------
with st.expander("Prediction Parameters", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        hearing_weight = st.slider("Days added per hearing", 10, 50, 20)
    with col2:
        year_weight = st.slider("Backlog effect per year", 5, 30, 10)
    with col3:
        baseline = st.slider("Baseline court delay (days)", 50, 200, 100)

# --------------------------------------------------
# Explainable Prediction Logic
# --------------------------------------------------
cases["hearing_component"] = cases["total_hearings"] * hearing_weight
cases["year_component"] = (cases["filing_year"] - min_year) * year_weight
cases["baseline_component"] = baseline

cases["predicted_disposal"] = (
    cases["hearing_component"]
    + cases["year_component"]
    + cases["baseline_component"]
).round(0)

cases["best_case_days"] = (cases["predicted_disposal"] * 0.8).round(0)
cases["worst_case_days"] = (cases["predicted_disposal"] * 1.25).round(0)

# Delay risk
def delay_risk(days):
    if days < 180:
        return "Low"
    elif days <= 365:
        return "Medium"
    return "High"

cases["delay_risk"] = cases["predicted_disposal"].apply(delay_risk)

# Bottleneck
def detect_bottleneck(row):
    reasons = []
    if row["total_hearings"] >= 8:
        reasons.append("High hearings")
    if row["filing_year"] <= min_year + 1:
        reasons.append("Old backlog")
    if not reasons:
        reasons.append("Normal flow")
    return ", ".join(reasons)

cases["primary_bottleneck"] = cases.apply(detect_bottleneck, axis=1)

# --------------------------------------------------
# Tabs Layout (LIKE JUDGE DASHBOARD)
# --------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Overview",
        "Case Predictions",
        "Explain a Case",
        "Court Insights",
    ]
)

# --------------------------------------------------
# TAB 1 — OVERVIEW
# --------------------------------------------------
with tab1:
    st.subheader("What this system does")
    st.write("""
    This module provides **explainable, AI-assisted predictions**
    for estimating case disposal timelines.

    **Key characteristics**
    - Transparent & rule-based
    - No black-box ML
    - Policy-safe for judiciary
    """)

    mae = mean_absolute_error(cases["disposal_days"], cases["predicted_disposal"])
    st.metric("Prediction Error (MAE)", f"{mae:.1f} days")

# --------------------------------------------------
# TAB 2 — CASE PREDICTIONS
# --------------------------------------------------
with tab2:
    st.subheader("Explainable Case-Level Predictions")

    st.dataframe(
        cases[
            [
                "cnr_number",
                "total_hearings",
                "disposal_days",
                "predicted_disposal",
                "best_case_days",
                "worst_case_days",
                "delay_risk",
                "primary_bottleneck",
            ]
        ].head(25),
        use_container_width=True,
    )

# --------------------------------------------------
# TAB 3 — EXPLAIN A CASE
# --------------------------------------------------
with tab3:
    st.subheader("Explain Prediction for a Specific Case")

    cnr = st.text_input("Enter CNR Number")

    if cnr:
        row = cases[cases["cnr_number"] == cnr]
        if row.empty:
            st.warning("Case not found.")
        else:
            r = row.iloc[0]

            st.markdown("### Prediction Breakdown")
            st.write(f"""
            • Hearings contribution: **{int(r['hearing_component'])} days**  
            • Filing year backlog: **{int(r['year_component'])} days**  
            • Baseline delay: **{int(r['baseline_component'])} days**  

            **Expected disposal:** {int(r['predicted_disposal'])} days  
            **Best case:** {int(r['best_case_days'])} days  
            **Worst case:** {int(r['worst_case_days'])} days  

            **Delay risk:** {r['delay_risk']}  
            **Primary bottleneck:** {r['primary_bottleneck']}
            """)

# --------------------------------------------------
# TAB 4 — COURT INSIGHTS
# --------------------------------------------------
with tab4:
    st.subheader("Court-Level Intelligence")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Avg Predicted Disposal", f"{int(cases['predicted_disposal'].mean())} days")
    with col2:
        st.metric(
            "High Delay Risk (%)",
            f"{int((cases['delay_risk'] == 'High').mean() * 100)}%",
        )
    with col3:
        st.metric("Avg Hearings / Case", f"{cases['total_hearings'].mean():.1f}")

    st.subheader("Actual vs Predicted Trend")
    st.line_chart(cases[["disposal_days", "predicted_disposal"]])
