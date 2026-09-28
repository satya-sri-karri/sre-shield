import streamlit as st
import asyncio
import json
from backend.database.connection import SyncSessionLocal
from backend.database.models import Incident, PostMortem
from backend.agents.postmortem_agent import postmortem_agent

def show_postmortem_page():
    st.markdown("## 📜 Post-Mortem & Closed-Loop Memory Retention")
    st.markdown("Turn every resolved outage into persistent organizational intelligence using Hindsight Agent Memory.")
    st.write("")

    # Visual Learning Loop Banner
    st.markdown("""
    <div style="background: linear-gradient(90deg, #0f172a 0%, #1e1b4b 50%, #064e3b 100%); border: 1px solid #334155; border-radius: 8px; padding: 14px 20px; margin-bottom: 20px;">
        <span style="font-size: 0.8rem; font-weight: 700; color: #93c5fd; text-transform: uppercase; letter-spacing: 0.08em;">Continuous SRE Learning Loop</span>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 0.85rem; color: #e2e8f0; font-weight: 500; overflow-x: auto;">
            <span>1. Alert</span> ➔
            <span>2. Recall Memory</span> ➔
            <span>3. AI Diagnosis</span> ➔
            <span>4. Human Approval</span> ➔
            <span>5. Verification</span> ➔
            <span style="color: #34d399; font-weight: 700;">6. Post-Mortem</span> ➔
            <span style="color: #60a5fa; font-weight: 700;">7. Hindsight Retain</span> ➔
            <span style="color: #f59e0b; font-weight: 700;">8. Future Immunity</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    session = SyncSessionLocal()
    try:
        resolved_incidents = session.query(Incident).filter(
            Incident.status == "RESOLVED"
        ).order_by(Incident.resolved_at.desc()).all()

        if not resolved_incidents:
            st.info("No resolved incidents available yet to generate post-mortems for.")
            return

        inc_map = {f"{inc.id} - {inc.service} ({inc.title[:50]}...)": inc.id for inc in resolved_incidents}
        default_idx = 0
        if "postmortem_target_id" in st.session_state:
            for idx, (label, i_id) in enumerate(inc_map.items()):
                if i_id == st.session_state["postmortem_target_id"]:
                    default_idx = idx
                    break

        selected_label = st.selectbox("Select Resolved Incident for Post-Mortem", list(inc_map.keys()), index=default_idx)
        target_id = inc_map[selected_label]
        target_inc = session.query(Incident).filter(Incident.id == target_id).first()

        # Check existing post-mortem
        existing_pm = session.query(PostMortem).filter(PostMortem.incident_id == target_id).first()

        col_act1, col_act2 = st.columns([3, 1])
        with col_act1:
            if existing_pm:
                st.success(f"Existing Post-Mortem `{existing_pm.id}` found. Approved: {'Yes' if existing_pm.is_approved else 'Draft'}.")
            else:
                st.warning("No post-mortem created yet for this incident.")

        with col_act2:
            if st.button("🤖 Generate Draft via AI", use_container_width=True):
                with st.spinner("Synthesizing post-mortem timeline, root causes, and prevention strategies..."):
                    draft = asyncio.run(postmortem_agent.generate_postmortem(target_id))
                    st.session_state[f"pm_draft_{target_id}"] = draft
                    st.rerun()

        # Populate form data
        cached_draft = st.session_state.get(f"pm_draft_{target_id}")

        if cached_draft:
            init_title = cached_draft.get("title", f"Post-Mortem: {target_inc.title}")
            init_summary = cached_draft.get("summary", "")
            init_impact = cached_draft.get("impact", "")
            init_root = cached_draft.get("root_cause", target_inc.root_cause)
            init_res = cached_draft.get("resolution", target_inc.suggested_action)
            init_cmds = cached_draft.get("commands_used", [target_inc.suggested_command])
            init_timeline = cached_draft.get("timeline", [])
            init_worked = cached_draft.get("what_worked", "")
            init_failed = cached_draft.get("what_failed", "")
            init_prev = cached_draft.get("prevention", "")
            init_mon = cached_draft.get("recommended_monitoring", "")
            init_lessons = cached_draft.get("lessons_learned", "")
        elif existing_pm:
            init_title = existing_pm.title
            init_summary = existing_pm.summary
            init_impact = existing_pm.impact
            init_root = existing_pm.root_cause
            init_res = existing_pm.resolution
            init_cmds = json.loads(existing_pm.commands_used or "[]")
            init_timeline = json.loads(existing_pm.timeline or "[]")
            init_worked = existing_pm.what_worked
            init_failed = existing_pm.what_failed
            init_prev = existing_pm.prevention
            init_mon = existing_pm.recommended_monitoring
            init_lessons = existing_pm.lessons_learned
        else:
            # Fallback default draft
            init_title = f"Post-Mortem: {target_inc.service} Outage"
            init_summary = f"{target_inc.service} suffered service degradation resulting in error: {target_inc.error_message[:60]}"
            init_impact = "Customer transactions failed; recovery achieved in under 15 minutes."
            init_root = target_inc.root_cause
            init_res = target_inc.suggested_action
            init_cmds = [target_inc.suggested_command]
            init_timeline = [{"time": "12:00", "event": "Alert fired"}, {"time": "12:05", "event": "Resolved via SRE-Shield"}]
            init_worked = "Rapid memory recall matched verified runbook."
            init_failed = "Threshold alert was reactive rather than predictive."
            init_prev = "Tune resource quotas and autoscaling."
            init_mon = "Alert on capacity utilization > 80%."
            init_lessons = "Always verify downstream connection pools before traffic surges."

        with st.form("pm_form"):
            pm_title = st.text_input("Post-Mortem Title", value=init_title)
            
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                pm_summary = st.text_area("Incident Summary", value=init_summary, height=90)
                pm_impact = st.text_area("Customer / Business Impact", value=init_impact, height=90)
                pm_root = st.text_area("Confirmed Root Cause", value=init_root, height=90)
                pm_res = st.text_area("Resolution Steps Taken", value=init_res, height=90)
            with c_f2:
                pm_worked = st.text_area("What Worked Well", value=init_worked, height=90)
                pm_failed = st.text_area("What Went Wrong / Failed", value=init_failed, height=90)
                pm_prev = st.text_area("Prevention Strategy & Safeguards", value=init_prev, height=90)
                pm_lessons = st.text_area("Key Lessons Learned (Stored into Memory)", value=init_lessons, height=90)

            pm_mon = st.text_input("Recommended Monitoring / New Alerts", value=init_mon)
            approver = st.text_input("Approving Engineer / SRE Lead", value="Principal SRE Lead")

            save_btn = st.form_submit_button("💾 Approve & Retain into Hindsight Persistent Memory", type="primary", use_container_width=True)

        if save_btn:
            pm_payload = {
                "title": pm_title,
                "summary": pm_summary,
                "impact": pm_impact,
                "timeline": init_timeline,
                "root_cause": pm_root,
                "resolution": pm_res,
                "commands_used": init_cmds,
                "what_worked": pm_worked,
                "what_failed": pm_failed,
                "prevention": pm_prev,
                "recommended_monitoring": pm_mon,
                "lessons_learned": pm_lessons,
                "approved_by": approver
            }

            with st.spinner("Retaining into Hindsight Experience Network & triggering Reflection..."):
                ret_result = asyncio.run(postmortem_agent.approve_and_save_postmortem(
                    incident_id=target_id,
                    pm_content=pm_payload,
                    approved_by=approver
                ))

            st.balloons()
            st.success(f"🎉 **Learning Loop Closed!** Incident `{target_id}` post-mortem has been approved and retained into Hindsight Agent Memory.")

            # Display Hindsight Memory Impact
            h_ret = ret_result.get("hindsight_retention", {})
            st.markdown(f"""
            <div style="background-color: #064e3b; border: 1px solid #059669; border-radius: 8px; padding: 16px; margin-top: 14px;">
                <span style="font-weight: 700; color: #a7f3d0; font-size: 1.05rem;">🧠 Hindsight Memory Retention Summary:</span>
                <ul style="color: #ecfdf5; margin-top: 8px; font-size: 0.92rem;">
                    <li><strong>Experience ID Created:</strong> <code>{h_ret.get('experience_id', 'EXP-NEW')}</code></li>
                    <li><strong>Memory Defense Sanitization:</strong> Safely cleansed {h_ret.get('sanitization_report', {}).get('redaction_count', 0)} secrets.</li>
                    <li><strong>Entity Summary Reflection:</strong> {h_ret.get('reflection', {}).get('updated_entity_summary', 'Service profile updated')}</li>
                    <li><strong>Evolving Belief:</strong> Strengthened operational confidence for future outages.</li>
                </ul>
                <p style="color: #34d399; font-size: 0.88rem; margin-bottom: 0;">
                    ✅ Any future incident matching this pattern will now immediately receive this verified resolution!
                </p>
            </div>
            """, unsafe_allow_html=True)

    finally:
        session.close()
