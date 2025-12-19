import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error

from preprocessing import load_data, clean_cases
from helpers.sidebar import render_sidebar
from components.language import render_language_header

# --------------------------------------------------
# Page Config
# --------------------------------------------------
st.set_page_config(
    page_title="AI Predictions",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_language_header()
render_sidebar()

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

REQUIRED_COLS = [
    "cnr_number",
    "disposal_days",
    "total_hearings",
    "filing_year",
]

missing = [c for c in REQUIRED_COLS if c not in cases.columns]
if missing:
    st.error(f"Missing required columns: {missing}")
    st.stop()

min_year = cases["filing_year"].min()

# --------------------------------------------------
# Prediction Controls
# --------------------------------------------------
with st.expander("Prediction Parameters", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        hearing_weight = st.slider("Days added per hearing", 10, 50, 20)
    with c2:
        year_weight = st.slider("Backlog impact per year", 5, 30, 10)
    with c3:
        baseline_delay = st.slider("Baseline court delay (days)", 50, 200, 100)

# --------------------------------------------------
# Prediction Engine (Cached)
# --------------------------------------------------
@st.cache_data(show_spinner=False)
def generate_predictions(df, hearing_weight, year_weight, baseline_delay, min_year):
    data = df.copy()

    data["hearing_component"] = data["total_hearings"] * hearing_weight
    data["year_component"] = (data["filing_year"] - min_year) * year_weight
    data["baseline_component"] = baseline_delay

    data["predicted_disposal"] = (
        data["hearing_component"]
        + data["year_component"]
        + data["baseline_component"]
    ).round(0)

    data["best_case_days"] = (data["predicted_disposal"] * 0.8).round(0)
    data["worst_case_days"] = (data["predicted_disposal"] * 1.25).round(0)

    return data

cases = generate_predictions(
    cases,
    hearing_weight,
    year_weight,
    baseline_delay,
    min_year,
)

# --------------------------------------------------
# Risk Classification (Data-Driven)
# --------------------------------------------------
low_th = cases["predicted_disposal"].quantile(0.33)
high_th = cases["predicted_disposal"].quantile(0.66)

def delay_risk(days):
    if days <= low_th:
        return "Low"
    elif days <= high_th:
        return "Medium"
    return "High"

cases["delay_risk"] = cases["predicted_disposal"].apply(delay_risk)

# --------------------------------------------------
# Bottleneck Detection
# --------------------------------------------------
def detect_bottleneck(row):
    reasons = []

    if row["total_hearings"] >= 8:
        reasons.append("High hearings")

    if row["filing_year"] <= min_year + 1:
        reasons.append("Old backlog")

    return " & ".join(reasons) if reasons else "Normal flow"

cases["primary_bottleneck"] = cases.apply(detect_bottleneck, axis=1)

# --------------------------------------------------
# Tabs Layout
# --------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Case Predictions",
    "Explain a Case",
    "Court Insights",
])

# --------------------------------------------------
# TAB 1 — OVERVIEW
# --------------------------------------------------
with tab1:
    st.subheader("What this system does")
    st.write("""
    This module provides **transparent, explainable predictions**
    for estimating judicial case disposal timelines.

    • Rule-based  
    • No black-box ML  
    • Safe for judicial decision support  
    """)

    mae = mean_absolute_error(
        cases["disposal_days"],
        cases["predicted_disposal"],
    )

    mape = (
        np.mean(
            np.abs(
                (cases["disposal_days"] - cases["predicted_disposal"])
                / cases["disposal_days"]
            )
        ) * 100
    )

    c1, c2 = st.columns(2)
    c1.metric("Mean Absolute Error", f"{mae:.1f} days")
    c2.metric("Mean Absolute % Error", f"{mape:.1f}%")

# --------------------------------------------------
# TAB 2 — CASE PREDICTIONS
# --------------------------------------------------
with tab2:
    st.subheader("Explainable Case-Level Predictions")

    risk_filter = st.multiselect(
        "Filter by Delay Risk",
        options=cases["delay_risk"].unique(),
        default=cases["delay_risk"].unique(),
    )

    filtered = cases[cases["delay_risk"].isin(risk_filter)]

    display_cols = [
        "cnr_number",
        "total_hearings",
        "disposal_days",
        "predicted_disposal",
        "best_case_days",
        "worst_case_days",
        "delay_risk",
        "primary_bottleneck",
    ]

    def risk_color(val):
        if val == "High":
            return "background-color:#fee2e2"
        if val == "Medium":
            return "background-color:#fef9c3"
        return "background-color:#dcfce7"

    st.dataframe(
        filtered[display_cols]
        .style.applymap(risk_color, subset=["delay_risk"]),
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
            **Hearings impact:** {int(r.hearing_component)} days  
            **Backlog impact:** {int(r.year_component)} days  
            **Baseline delay:** {int(r.baseline_component)} days  

            **Expected disposal:** {int(r.predicted_disposal)} days  
            **Best case:** {int(r.best_case_days)} days  
            **Worst case:** {int(r.worst_case_days)} days  

            **Delay risk:** {r.delay_risk}  
            **Primary bottleneck:** {r.primary_bottleneck}
            """)

# --------------------------------------------------
# TAB 4 — COURT INSIGHTS
# --------------------------------------------------
with tab4:
    st.subheader("Court-Level Intelligence")

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Avg Predicted Disposal",
        f"{int(cases['predicted_disposal'].mean())} days",
    )
    c2.metric(
        "High Risk Cases",
        f"{int((cases['delay_risk'] == 'High').mean() * 100)}%",
    )
    c3.metric(
        "Avg Hearings / Case",
        f"{cases['total_hearings'].mean():.1f}",
    )

    st.subheader("Actual vs Predicted Trend")
    st.line_chart(cases[["disposal_days", "predicted_disposal"]])
