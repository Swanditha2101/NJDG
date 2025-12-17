import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from pathlib import Path
from helpers.sidebar import render_sidebar
from components.language import render_language_header
# ----------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------
st.set_page_config(
    page_title="Judicial Anomaly Detection",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_language_header()
render_sidebar()
st.title("⚖️ Judicial Anomaly Detection & Case Intelligence")

# ----------------------------------------------------
# DATA LOADING
# ----------------------------------------------------
@st.cache_data
def load_data():
    cases_path = Path(__file__).parent.parent / "data/ISDMHack_Cases_students.csv"
    hearings_path = Path(__file__).parent.parent / "data/ISDMHack_Hear_students.csv"

    cases = pd.read_csv(cases_path)
    hearings = pd.read_csv(hearings_path)

    return cases, hearings


# ----------------------------------------------------
# COLUMN NORMALIZATION (CRITICAL)
# ----------------------------------------------------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip().str.lower()

    column_map = {
        "cnr": "cnr_number",
        "cnr_no": "cnr_number",
        "case_id": "cnr_number",

        "no_of_hearings": "total_hearings",
        "hearing_count": "total_hearings",

        "disposal_days": "disposal_days",
        "case_disposal_days": "disposal_days",

        "date_filed": "date_filed",
        "decision_date": "decision_date",
    }

    df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})
    return df


# ----------------------------------------------------
# CLEAN CASES
# ----------------------------------------------------
def clean_cases(cases: pd.DataFrame) -> pd.DataFrame:
    cases = normalize_columns(cases)

    for col in ["date_filed", "decision_date"]:
        if col in cases.columns:
            cases[col] = pd.to_datetime(cases[col], errors="coerce")

    if "date_filed" in cases.columns and "decision_date" in cases.columns:
        cases["case_duration"] = (
            cases["decision_date"] - cases["date_filed"]
        ).dt.days
    else:
        cases["case_duration"] = np.nan

    numeric_cols = cases.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        cases[col] = cases[col].fillna(cases[col].median())

    return cases


# ----------------------------------------------------
# ANOMALY DETECTION
# ----------------------------------------------------
def detect_anomalies(df: pd.DataFrame, contamination: float):
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if not numeric_cols:
        st.error("No numeric columns available for anomaly detection.")
        return df

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42
    )

    model.fit(df[numeric_cols])

    df["anomaly_flag"] = model.predict(df[numeric_cols]) == -1
    df["anomaly_score"] = model.decision_function(df[numeric_cols])

    return df


# ----------------------------------------------------
# EXPLAINABLE REASONS & SEVERITY
# ----------------------------------------------------
def explain_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    reasons = []
    severity = []

    for _, row in df.iterrows():
        r = []
        s = "Low"

        if row.get("case_duration", 0) > df["case_duration"].quantile(0.90):
            r.append("Unusually long case duration")
            s = "High"

        if row.get("total_hearings", 0) > df.get("total_hearings", pd.Series()).quantile(0.95):
            r.append("Excessive number of hearings")
            s = "Critical"

        if row.get("disposal_days", 0) > df.get("disposal_days", pd.Series()).quantile(0.95):
            r.append("Abnormally high disposal days")

        reasons.append(", ".join(r) if r else "Statistical outlier pattern")
        severity.append(s)

    df["anomaly_reason"] = reasons
    df["severity"] = severity

    return df


# ----------------------------------------------------
# MAIN DASHBOARD
# ----------------------------------------------------
def run_dashboard():
    cases, hearings = load_data()
    cases = clean_cases(cases)

    st.sidebar.subheader("Detection Controls")
    contamination = st.sidebar.slider(
        "Expected Anomaly Ratio",
        0.01, 0.20, 0.05, 0.01
    )

    cases = detect_anomalies(cases, contamination)
    cases = explain_anomalies(cases)

    anomalies = cases[cases["anomaly_flag"]]

    # ---------------------- TABS ----------------------
    tab1, tab2, tab3 = st.tabs(
        ["📊 Overview", "🚨 Anomalous Cases", "🔍 Case Drill-Down"]
    )

    # ---------------------- TAB 1 ----------------------
    with tab1:
        st.subheader("System Overview")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Cases", len(cases))
        col2.metric("Anomalous Cases", len(anomalies))
        col3.metric(
            "Anomaly %",
            f"{(len(anomalies) / max(len(cases),1)) * 100:.2f}%"
        )

        st.info(
            "Anomalies indicate statistically unusual case patterns. "
            "They are NOT proof of wrongdoing."
        )

    # ---------------------- TAB 2 ----------------------
    with tab2:
        st.subheader("Detected Anomalies")

        display_cols = [
            c for c in [
                "cnr_number",
                "case_duration",
                "total_hearings",
                "disposal_days",
                "severity",
                "anomaly_reason"
            ]
            if c in anomalies.columns
        ]

        if display_cols:
            st.dataframe(
                anomalies[display_cols],
                use_container_width=True
            )
        else:
            st.warning("No displayable columns found.")

    # ---------------------- TAB 3 ----------------------
    with tab3:
        st.subheader("Case Drill-Down")

        if "cnr_number" not in cases.columns:
            st.error("CNR Number column not available.")
            return

        selected = st.selectbox(
            "Select Case (CNR Number)",
            cases["cnr_number"].astype(str).unique()
        )

        case = cases[cases["cnr_number"].astype(str) == selected]

        st.write(case.T)

        if case["anomaly_flag"].iloc[0]:
            st.error("⚠️ This case is flagged as ANOMALOUS")
            st.write("**Reason:**", case["anomaly_reason"].iloc[0])
            st.write("**Severity:**", case["severity"].iloc[0])
        else:
            st.success("✅ This case is within normal statistical range")


# ----------------------------------------------------
# ENTRY POINT
# ----------------------------------------------------
if __name__ == "__main__":
    run_dashboard()
