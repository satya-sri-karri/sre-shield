import streamlit as st
import json
import pandas as pd
from backend.database.connection import SyncSessionLocal
from backend.database.models import Incident, PostMortem

def show_history_page():
    st.markdown("## 🗄️ Incident History & Audit Records")
    st.markdown("Searchable repository of all active and resolved production incidents with post-mortem logs.")
    st.write("")

    session = SyncSessionLocal()
    try:
        # Filter controls
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)

        all_services = [s[0] for s in session.query(Incident.service).distinct().all()]
        all_statuses = [st[0] for st in session.query(Incident.status).distinct().all()]

        with f_col1:
            sel_service = st.selectbox("Filter Service", ["All Services"] + all_services)
        with f_col2:
            sel_severity = st.selectbox("Filter Severity", ["All Severities", "CRITICAL", "HIGH", "MEDIUM", "LOW"])
        with f_col3:
            sel_status = st.selectbox("Filter Status", ["All Statuses"] + all_statuses)
        with f_col4:
            search_text = st.text_input("Search Logs / Root Cause", value="")

        # Query construction
        query = session.query(Incident).order_by(Incident.created_at.desc())
        if sel_service != "All Services":
            query = query.filter(Incident.service == sel_service)
        if sel_severity != "All Severities":
            query = query.filter(Incident.severity == sel_severity)
        if sel_status != "All Statuses":
            query = query.filter(Incident.status == sel_status)
        if search_text:
            query = query.filter(
                (Incident.root_cause.ilike(f"%{search_text}%")) |
                (Incident.error_message.ilike(f"%{search_text}%")) |
                (Incident.title.ilike(f"%{search_text}%"))
            )

        incidents = query.all()

        st.write(f"Displaying **{len(incidents)}** incident(s):")

        for inc in incidents:
            sev_color = "red" if inc.severity == "CRITICAL" else ("orange" if inc.severity == "HIGH" else "blue")
            mttr_disp = f"{round((inc.mttr_seconds or 0)/60, 1)}m" if inc.status == "RESOLVED" else "Ongoing"

            with st.expander(f"[{inc.id}] {inc.service} — {inc.title[:65]}... ({inc.status} | MTTR: {mttr_disp})"):
                col_d1, col_d2, col_d3 = st.columns(3)
                with col_d1:
                    st.markdown(f"**Severity:** `{inc.severity}`")
                    st.markdown(f"**Status:** `{inc.status}`")
                with col_d2:
                    st.markdown(f"**Created At:** {inc.created_at.strftime('%Y-%m-%d %H:%M:%S') if inc.created_at else ''}")
                    st.markdown(f"**Resolved At:** {inc.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if inc.resolved_at else 'In Progress'}")
                with col_d3:
                    st.markdown(f"**Runbook Applied:** `{inc.recommended_runbook_id or 'General'}`")
                    st.markdown(f"**Verification:** `{inc.verification_status}`")

                st.write("")
                st.markdown(f"**Error Signature:** `{inc.error_message}`")
                st.markdown(f"**Root Cause:** {inc.root_cause or 'Under investigation'}")
                st.markdown(f"**Approved Action:** {inc.suggested_action}")

                if inc.suggested_command:
                    st.markdown("**Executed Command:**")
                    st.code(inc.suggested_command, language="bash")

                if inc.execution_output:
                    st.markdown("**Execution & Verification Output:**")
                    st.code(f"{inc.execution_output}\n\n{inc.verification_output}", language="yaml")

                # Linked Post-Mortem
                pm = session.query(PostMortem).filter(PostMortem.incident_id == inc.id).first()
                if pm:
                    st.markdown("---")
                    st.markdown(f"#### 📜 Post-Mortem: {pm.title}")
                    st.markdown(f"**Executive Summary:** {pm.summary}")
                    st.markdown(f"**Impact:** {pm.impact}")
                    st.markdown(f"**Key Lessons Learned:** {pm.lessons_learned}")

    finally:
        session.close()
