import streamlit as st
from preprocessing import load_data, clean_cases

st.title("Nyayadrishti Case Verification")

# ------------------ GET CNR FROM URL ------------------
cnr = st.experimental_get_query_params().get("cnr", [""])[0]

# ------------------ LOAD CASES ------------------
cases, _ = load_data()
cases = clean_cases(cases)

# ------------------ VERIFICATION LOGIC ------------------
if not cnr:
    st.info("Scan a QR code with a CNR number to verify the case.")
else:
    case = cases[cases["cnr_number"] == cnr]
    
    if case.empty:
        st.error("❌ Case not found or invalid CNR.")
    else:
        case = case.iloc[0]
        st.success(f"✅ Case Verified: {case['cnr_number']}")
        
        st.markdown("### Case Details")
        st.write({
            "Court Name": case.get("court_name", "N/A"),
            "Case Type": case.get("case_type", "N/A"),
            "Filing Year": case.get("filing_year", "N/A"),
            "Total Hearings": case.get("total_hearings", "N/A"),
            "Status": "Disposed" if case.get("disposal_days", 0) > 0 else "Pending",
            "Advocate": case.get("PetitionerAdvocate", "N/A"),
            "Presiding Judge": case.get("Njdg_Judge_Name", "N/A"),
        })

        st.markdown("---")
        st.info(
            "This page verifies the authenticity of the case document generated via Nyayadrishti. "
            "Scan the QR code from the PDF to reach this page."
        )
