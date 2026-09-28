import streamlit as st
import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from frontend.components import apply_sre_theme
from frontend.pages_dashboard import show_dashboard
from frontend.pages_incident_center import show_incident_center
from frontend.pages_approval import show_approval_page
from frontend.pages_postmortem import show_postmortem_page
from frontend.pages_hindsight import show_hindsight_page
from frontend.pages_runbooks import show_runbooks_page
from frontend.pages_history import show_history_page
from frontend.pages_assistant import show_assistant_page
from frontend.pages_analytics import show_analytics_page
from backend.config import settings

st.set_page_config(
    page_title="SRE-Shield | AI Incident Response Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply Dark Enterprise Theme
apply_sre_theme()

# Sidebar Navigation
with st.sidebar:
    st.markdown("""
    <div style="padding: 10px 0 16px 0; border-bottom: 1px solid #1e293b;">
        <span style="font-size: 1.45rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.02em;">🛡️ SRE-Shield</span><br/>
        <span style="font-size: 0.78rem; color: #94a3b8; font-weight: 500;">Self-Learning Incident Response</span>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # System Status Card
    st.markdown(f"""
    <div style="background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 12px; margin-bottom: 16px;">
        <div style="font-size: 0.72rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 6px;">System State</div>
        <div style="font-size: 0.8rem; color: #10b981; font-weight: 600;">● Engine: Hindsight Memory</div>
        <div style="font-size: 0.8rem; color: #a855f7; font-weight: 600;">● Safety: Simulation Mode</div>
        <div style="font-size: 0.8rem; color: #60a5fa; font-weight: 600;">● Defense: Redaction Active</div>
        <div style="font-size: 0.78rem; color: #94a3b8; margin-top: 4px;">LLM: <code>{settings.GROQ_MODEL}</code></div>
    </div>
    """, unsafe_allow_html=True)

    NAV_ITEMS = [
        "Executive Dashboard",
        "Incident Center & AI Diagnosis",
        "Human Approval & Execution",
        "Post-Mortem & Learning Loop",
        "Hindsight Memory Inspector",
        "Runbook Catalog",
        "Incident History",
        "SRE AI Copilot / Assistant",
        "SRE Analytics & MTTR"
    ]

    # Handle cross-page navigation state
    if "nav_choice" not in st.session_state:
        st.session_state["nav_choice"] = NAV_ITEMS[0]

    current_idx = NAV_ITEMS.index(st.session_state["nav_choice"]) if st.session_state["nav_choice"] in NAV_ITEMS else 0

    selected_page = st.radio(
        "Navigation",
        NAV_ITEMS,
        index=current_idx,
        label_visibility="collapsed"
    )

    if selected_page != st.session_state["nav_choice"]:
        st.session_state["nav_choice"] = selected_page
        st.rerun()

    st.write("---")
    st.markdown("<span style='font-size: 0.75rem; color: #64748b;'>SRE-Shield v1.0 • Hackathon Edition</span>", unsafe_allow_html=True)

# Main Page Routing
page = st.session_state["nav_choice"]

if page == "Executive Dashboard":
    show_dashboard()
elif page == "Incident Center & AI Diagnosis":
    show_incident_center()
elif page == "Human Approval & Execution":
    show_approval_page()
elif page == "Post-Mortem & Learning Loop":
    show_postmortem_page()
elif page == "Hindsight Memory Inspector":
    show_hindsight_page()
elif page == "Runbook Catalog":
    show_runbooks_page()
elif page == "Incident History":
    show_history_page()
elif page == "SRE AI Copilot / Assistant":
    show_assistant_page()
elif page == "SRE Analytics & MTTR":
    show_analytics_page()
