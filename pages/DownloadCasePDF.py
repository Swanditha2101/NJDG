import streamlit as st
import tempfile
import os

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

from preprocessing import load_data, clean_cases
from helpers.sidebar import render_sidebar

# ------------------ PAGE CONFIG ------------------
st.set_page_config(
    page_title="Download Case PDF",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar()
st.title("Case Information Download")

# ------------------ LOAD DATA ------------------
@st.cache_data(show_spinner=False)
def load_cases():
    cases, _ = load_data()
    return clean_cases(cases)

cases = load_cases()
if "cnr_number" not in cases.columns:
    st.error("CNR Number column not found")
    st.stop()

# ------------------ SELECT CASE ------------------
st.subheader("Select Case")
case_number = st.text_input("Enter Case Number")

if st.button("Search Case"):
    filtered = cases[cases["cnr_number"] == case_number]
    if filtered.empty:
        st.error("No case found")
        st.stop()
    st.session_state.case = filtered.iloc[0]

# ------------------ PDF GENERATOR ------------------
def generate_case_pdf(row):
    styles = getSampleStyleSheet()
    story = []

    # ---------- HEADER ----------
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        header = [
            [Image(logo_path, 50, 100),
             Paragraph("<b>Nyayadrishti</b><br/>Judicial Case Summary", styles["Title"])]
        ]
    else:
        header = [
            ["",
             Paragraph("<b>Nyayadrishti</b><br/>Judicial Case Summary", styles["Title"])]
        ]
    header_table = Table(header, colWidths=[80, 420])
    story.append(header_table)
    story.append(Spacer(1, 20))

    # ---------- CASE DETAILS ----------
    data = [
        ["Field", "Value"],
        ["CNR Number", row["cnr_number"]],
        ["Court Name", row.get("court_name", "N/A")],
        ["Case Type", row.get("case_type", "N/A")],
        ["Filing Year", row.get("filing_year", "N/A")],
        ["Total Hearings", row.get("total_hearings", "N/A")],
        ["Status", "Disposed" if row.get("disposal_days", 0) > 0 else "Pending"],
        ["Advocate", row.get("PetitionerAdvocate", "N/A")],
        ["Presiding Judge", row.get("Njdg_Judge_Name", "N/A")],
    ]
    table = Table(data, colWidths=[180, 320])
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
    )
    story.append(table)
    story.append(Spacer(1, 20))

    # ---------- QR CODE ----------
    # Dynamic URL: use secrets if available, else fallback
    try:
        base_url = st.secrets["APP_URL"]
    except:
        base_url = "http://localhost:8501"

    verify_url = f"{base_url}/VerifyCase?cnr={row['cnr_number']}"
    qr_code = qr.QrCodeWidget(verify_url)
    bounds = qr_code.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    drawing = Drawing(120, 120, transform=[120/width, 0, 0, 120/height, 0, 0])
    drawing.add(qr_code)
    story.append(Paragraph("<b>Scan QR to verify case authenticity</b>", styles["Heading3"]))
    story.append(drawing)
    story.append(Spacer(1, 10))

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    SimpleDocTemplate(tmp.name, pagesize=A4).build(story)
    return tmp.name

# ------------------ ACTIONS ------------------
if "case" in st.session_state:
    case = st.session_state.case
    if st.button("📥 Generate PDF"):
        pdf_path = generate_case_pdf(case)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        st.download_button(
            "⬇️ Download Case PDF",
            data=pdf_bytes,
            file_name=f"{case['cnr_number']}_Nyayadrishti.pdf",
            mime="application/pdf",
        )
