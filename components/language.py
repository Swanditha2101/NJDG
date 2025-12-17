import streamlit as st

def render_language_header():
    st.markdown(
        """
        <style>
        /* ===== LANGUAGE HEADER BAR ===== */
        .language-bar {
            position: sticky;
            top: 0;
            z-index: 1000;
            background-color: #000000;
            color: #FFFFFF;
            padding: 10px 16px;
            font-size: 14px;
            border-bottom: 1px solid #222;
        }

        .language-bar span {
            color: #FFFFFF;
            font-weight: 500;
        }

        .language-bar .hint {
            font-size: 13px;
            color: #CCCCCC;
        }

        /* Remove Streamlit default top padding */
        section[data-testid="stAppViewContainer"] > div:first-child {
            padding-top: 0rem;
        }
        </style>

        <div class="language-bar">
            <span>🌐 Language</span>
            <span class="hint">
                &nbsp;&nbsp;| Right-click anywhere → Translate (Telugu / Kannada / Hindi)
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )
