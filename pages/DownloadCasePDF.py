import streamlit as st
import tempfile
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

from preprocessing import load_data, clean_cases
from helpers.sidebar import render_sidebar
from components.language import render_language_header

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Download Case PDF",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_language_header()
render_sidebar()

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
    }
    [data-testid="stSidebar"] * {
        color: black !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Case Information Download")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
@st.cache_data(show_spinner=False)
def load_cases():
    cases, _ = load_data()
    cases = clean_cases(cases)
    return cases

cases = load_cases()

if "cnr_number" not in cases.columns:
    st.error("CNR Number column not found")
    st.stop()

# --------------------------------------------------
# SELECT CASE
# --------------------------------------------------
st.subheader("Select Case")

case_number = st.text_input("Enter Case Number")
case = None

if st.button("Search Case"):
    filtered = cases[cases["cnr_number"] == case_number]
    if filtered.empty:
        st.error("No case found with that CNR number.")
    else:
        case = filtered.iloc[0]

# --------------------------------------------------
# PREVIEW
# --------------------------------------------------
if case is not None:
    st.subheader("Case Preview")

    c1, c2, c3 = st.columns(3)
    c1.metric("Filing Year", case.get("filing_year", "N/A"))
    c2.metric("Total Hearings", case.get("total_hearings", "N/A"))
    c3.metric(
        "Status",
        "Disposed" if case.get("disposal_days", 0) > 0 else "Pending",
    )

    st.markdown("---")

    # --------------------------------------------------
    # PDF GENERATOR
    # --------------------------------------------------
    def generate_case_pdf(row):
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("<b>Judicial Case Summary</b>", styles["Title"]))
        story.append(Spacer(1, 16))

        data = [
            ["Field", "Value"],
            ["CNR Number", row.get("cnr_number", "N/A")],
            ["Court Name", row.get("court_name", "N/A")],
            ["Case Type", row.get("case_type", "N/A")],
            ["Filing Year", row.get("filing_year", "N/A")],
            ["Total Hearings", row.get("total_hearings", "N/A")],
            [
                "Disposal Days",
                row["disposal_days"] if row.get("disposal_days", 0) > 0 else "Pending",
            ],
        ]

        table = Table(data, colWidths=[180, 320])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        story.append(table)
        story.append(Spacer(1, 20))

        risk = "High" if row.get("disposal_days", 0) > 365 else "Normal"

        story.append(Paragraph("<b>Analytical Summary</b>", styles["Heading2"]))
        story.append(
            Paragraph(
                f"• Delay Risk: <b>{risk}</b><br/>"
                f"• Generated using explainable judicial analytics",
                styles["Normal"],
            )
        )

        story.append(Spacer(1, 16))
        story.append(
            Paragraph(
                "<i>This is a system-generated document for decision support only.</i>",
                styles["Italic"],
            )
        )

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        SimpleDocTemplate(tmp.name, pagesize=A4).build(story)
        return tmp.name

    # --------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------
    st.subheader("Download")

    if st.button("📥 Generate PDF"):
        pdf_path = generate_case_pdf(case)
        with open(pdf_path, "rb") as f:
            st.download_button(
                "⬇️ Download Case PDF",
                data=f,
                file_name=f"{case.get('cnr_number', 'case')}_case_summary.pdf",
                mime="application/pdf",
            )