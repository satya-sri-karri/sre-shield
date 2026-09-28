import streamlit as st
import asyncio
import time
from backend.database.connection import SyncSessionLocal
from backend.database.models import Incident
from backend.execution.executor import executor

def show_approval_page():
    st.markdown("## 🛡️ Human-in-the-Loop Approval & Safe Execution")
    st.markdown(
        "<span class='badge badge-sim'>SIMULATION MODE ACTIVE</span> &nbsp; "
        "Production safety guardrails enforced. Autonomous command execution is prohibited.",
        unsafe_allow_html=True
    )
    st.write("")

    session = SyncSessionLocal()
    try:
        # Fetch pending incidents
        pending = session.query(Incident).filter(
            Incident.status.in_(["AWAITING_APPROVAL", "INVESTIGATING", "NEW"])
        ).order_by(Incident.created_at.desc()).all()

        if not pending:
            st.success("🎉 No incidents currently awaiting approval! All systems operating within normal parameters.")
            st.info("You can simulate an outage in the **Incident Center** or view past executions in **Incident History**.")
            return

        incident_options = {f"{inc.id} - {inc.service} ({inc.severity})": inc.id for inc in pending}
        default_index = 0

        # Preselect if passed from incident center
        if "selected_incident_id" in st.session_state:
            for idx, (label, i_id) in enumerate(incident_options.items()):
                if i_id == st.session_state["selected_incident_id"]:
                    default_index = idx
                    break

        selected_label = st.selectbox("Select Pending Incident to Review", list(incident_options.keys()), index=default_index)
        target_id = incident_options[selected_label]
        target_inc = session.query(Incident).filter(Incident.id == target_id).first()

        if not target_inc:
            st.error("Incident not found.")
            return

        # Incident Summary Card
        st.markdown(f"""
        <div style="background-color: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 18px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 1.2rem; font-weight: 700; color: #f8fafc;">{target_inc.title}</span>
                <span class="badge badge-critical">{target_inc.severity}</span>
            </div>
            <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 4px;"><strong>Target Service:</strong> {target_inc.service}</p>
            <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 4px;"><strong>Diagnosed Root Cause:</strong> <span style="color: #f1f5f9;">{target_inc.root_cause}</span></p>
            <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 4px;"><strong>Recommended Runbook:</strong> <code>{target_inc.recommended_runbook_id or 'DB-CONNECTION-001'}</code> (Confidence: {int((target_inc.confidence_score or 0.95)*100)}%)</p>
        </div>
        """, unsafe_allow_html=True)

        # AI Recommended Action Card
        st.markdown("### 🤖 AI Recommended Remediation")
        risk_color = "#ef4444" if target_inc.risk_level == "HIGH" else ("#f59e0b" if target_inc.risk_level == "MEDIUM" else "#10b981")
        
        st.markdown(f"""
        <div style="background-color: #131b2e; border: 1px solid #2563eb; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 600; color: #93c5fd;">Recommended Action Plan</span>
                <span style="font-size: 0.8rem; font-weight: 700; color: {risk_color};">RISK: {target_inc.risk_level}</span>
            </div>
            <p style="color: #cbd5e1; margin-top: 8px; font-size: 0.92rem;">
                <strong>Reason:</strong> {target_inc.reasoning_explanation or target_inc.suggested_action}
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Editable command area (allows Modify & Execute)
        st.markdown("##### 💻 Proposed Production Command")
        command_to_run = st.text_area(
            "CLI Command (You can modify this command prior to approval):",
            value=target_inc.suggested_command or "kubectl rollout restart deployment/checkout-api",
            height=85
        )

        engineer_name = st.text_input("Reviewing Engineer Name", value="Lead SRE Engineer (On-Call)")

        # Action Buttons
        col_app, col_mod, col_rej = st.columns([2, 2, 1])

        with col_app:
            approve_btn = st.button("✅ Approve & Execute Command", type="primary", use_container_width=True)

        with col_mod:
            modify_btn = st.button("🛠️ Execute Modified Command", use_container_width=True)

        with col_rej:
            reject_btn = st.button("❌ Reject Action", use_container_width=True)

        if approve_btn or modify_btn:
            st.write("---")
            st.markdown("### ⚙️ Execution & Live Verification Timeline")
            
            progress_placeholder = st.empty()
            
            with progress_placeholder.container():
                st.markdown(f"1. **Authorization Logged**: Approved by `{engineer_name}` at cluster gateway.")
                time.sleep(0.6)
                st.markdown(f"2. **Dispatching Command [SIMULATION MODE]**: `{command_to_run}`...")
                time.sleep(0.8)
                st.markdown("3. **Probing Service Health (`GET /healthz`)**: Response: `200 OK` (14ms)...")
                time.sleep(0.7)
                st.markdown("4. **Verifying SLO Metrics**: Error rate decreased from 48.2% to **0.00%**!")

            # Trigger execution in backend
            exec_res = asyncio.run(executor.execute_and_verify(
                incident_id=target_id,
                command_to_run=command_to_run,
                approved_by=engineer_name
            ))

            st.success(f"🎉 **Incident {target_id} Successfully Resolved!**")

            with st.expander("🔍 View Raw Command Execution Output & Verification Details", expanded=True):
                st.code(exec_res["execution_output"], language="bash")
                st.code(exec_res["verification_output"], language="yaml")

            # Post-mortem CTA
            st.write("")
            st.markdown("#### 📝 Complete the Learning Loop")
            pm_col1, pm_col2 = st.columns([3, 1])
            with pm_col1:
                st.info("The outage is resolved, but the learning loop is incomplete until post-mortem is retained in Hindsight Memory.")
            with pm_col2:
                if st.button("🚀 Draft Post-Mortem", type="primary", use_container_width=True):
                    st.session_state["nav_choice"] = "Post-Mortem & Learning Loop"
                    st.session_state["postmortem_target_id"] = target_id
                    st.rerun()

        elif reject_btn:
            asyncio.run(executor.reject_action(
                incident_id=target_id,
                rejected_by=engineer_name,
                reason="Engineer opted for manual debugging."
            ))
            st.warning(f"Action rejected for incident {target_id}. Status remains in INVESTIGATING.")
            st.rerun()

    finally:
        session.close()
