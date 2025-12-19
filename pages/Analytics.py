import streamlit as st
import plotly.express as px
import pandas as pd

from preprocessing import load_data, clean_cases, clean_hearings, merge_data
from helpers.sidebar import render_sidebar
from components.language import render_language_header

# --------------------------------------------------
# Page Config
# --------------------------------------------------
st.set_page_config(
    page_title="Analytics",
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

st.title("Judicial Analytics Dashboard")

# --------------------------------------------------
# Load & Preprocess Data (CACHED)
# --------------------------------------------------
@st.cache_data(show_spinner=False)
def load_all_data():
    cases, hearings = load_data()
    cases = clean_cases(cases)
    hearings = clean_hearings(hearings)
    merged = merge_data(cases, hearings)
    return cases, hearings, merged

cases, hearings, merged = load_all_data()

# --------------------------------------------------
# Sidebar Filters
# --------------------------------------------------
st.sidebar.header("Filters")

years = sorted(cases["filing_year"].dropna().unique())

selected_years = st.sidebar.multiselect(
    "Select Filing Years",
    options=years,
    default=years,
)

def filter_by_year(df, col="filing_year"):
    if selected_years and col in df.columns:
        return df[df[col].isin(selected_years)]
    return df

filtered_cases = filter_by_year(cases)
filtered_merged = filter_by_year(merged)

# Attach filing year to hearings
if {"case_id", "filing_year"}.issubset(cases.columns) and "case_id" in hearings.columns:
    hearings_with_year = hearings.merge(
        cases[["case_id", "filing_year"]],
        on="case_id",
        how="left",
    )
    filtered_hearings = filter_by_year(hearings_with_year)
else:
    filtered_hearings = hearings

# --------------------------------------------------
# High-Level Metrics
# --------------------------------------------------
total_cases = len(filtered_cases)
disposed_cases = filtered_cases["disposal_days"].gt(0).sum()
pending_cases = total_cases - disposed_cases
older_than_1yr = filtered_cases["disposal_days"].gt(365).sum()

case_clearance_rate = (
    disposed_cases / total_cases * 100 if total_cases > 0 else 0
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Cases", total_cases)
c2.metric("Disposed Cases", disposed_cases)
c3.metric("Pending Cases", pending_cases)
c4.metric("Pending > 1 Year", older_than_1yr)
c5.metric(
    "Case Clearance Rate",
    f"{case_clearance_rate:.2f}%",
    help="Disposed cases ÷ total cases (selected years)",
)

st.markdown("---")

# --------------------------------------------------
# Tabs
# --------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Case Funnel",
    "Disposal Trend",
    "Judge Workload",
    "Disposal Distribution",
    "CCR Trend",
])

# --------------------------------------------------
# TAB 1 — Case Funnel (FIXED)
# --------------------------------------------------
with tab1:
    st.subheader("Case Progress Funnel")

    if "remappedstages" in filtered_merged.columns:
        funnel_df = (
            filtered_merged["remappedstages"]
            .value_counts()
            .reset_index()
        )
        # 🔥 CRITICAL FIX
        funnel_df.columns = ["Stage", "Count"]

        fig = px.funnel(
            funnel_df,
            x="Count",
            y="Stage",
            title="Cases Across Judicial Stages",
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Stage data not available.")

# --------------------------------------------------
# TAB 2 — Disposal Trend
# --------------------------------------------------
with tab2:
    st.subheader("Average Disposal Time by Filing Year")

    if {"filing_year", "disposal_days"}.issubset(filtered_cases.columns):
        trend_df = filtered_cases.copy()
        trend_df["filing_year"] = trend_df["filing_year"].astype(int)

        trend = (
            trend_df
            .groupby("filing_year", as_index=False)["disposal_days"]
            .mean()
        )

        trend["filing_year"] = trend["filing_year"].astype(str)

        fig = px.line(
            trend,
            x="filing_year",
            y="disposal_days",
            markers=True,
            title="Average Disposal Days per Filing Year",
        )
        fig.update_xaxes(type="category")

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Required columns missing.")

# --------------------------------------------------
# TAB 3 — Judge Workload
# --------------------------------------------------
with tab3:
    st.subheader("Judge Hearing Workload")

    judge_columns = [
        "before_honourable_judges",
        "before_hon_judge",
        "njdg_judge_name",
    ]

    judge_col = next(
        (col for col in judge_columns if col in filtered_hearings.columns),
        None,
    )

    if judge_col:
        judge_df = (
            filtered_hearings[judge_col]
            .value_counts()
            .head(15)
            .reset_index()
        )
        judge_df.columns = ["Judge", "Hearings"]

        fig = px.bar(
            judge_df,
            x="Judge",
            y="Hearings",
            title="Top Judges by Hearing Count",
            color="Hearings",
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption("Top 15 judges by number of hearings")
    else:
        st.warning("Judge information not found.")

# --------------------------------------------------
# TAB 4 — Disposal Distribution
# --------------------------------------------------
with tab4:
    st.subheader("Distribution of Disposal Days")

    if "disposal_days" in filtered_cases.columns:
        fig = px.histogram(
            filtered_cases,
            x="disposal_days",
            nbins=40,
            title="Disposal Time Distribution",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Disposal days column not found.")

# --------------------------------------------------
# TAB 5 — Case Clearance Rate Trend
# --------------------------------------------------
with tab5:
    st.subheader("Case Clearance Rate by Filing Year")

    unique_case_id = "cnr_number"

    if {"filing_year", unique_case_id}.issubset(filtered_cases.columns):
        ccr_df = (
            filtered_cases
            .assign(disposed=lambda x: x["disposal_days"].gt(0))
            .groupby("filing_year", as_index=False)
            .agg(
                total_cases=(unique_case_id, "count"),
                disposed_cases=("disposed", "sum"),
            )
        )

        ccr_df["CCR (%)"] = (
            ccr_df["disposed_cases"] / ccr_df["total_cases"] * 100
        )
        ccr_df["filing_year"] = ccr_df["filing_year"].astype(str)

        fig = px.line(
            ccr_df,
            x="filing_year",
            y="CCR (%)",
            markers=True,
            title="Case Clearance Rate Trend",
        )
        fig.update_yaxes(range=[0, 100])
        fig.update_xaxes(type="category")

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Required columns missing for CCR.")
