import streamlit as st
import json
from backend.database.connection import SyncSessionLocal
from backend.database.models import Runbook

def show_runbooks_page():
    st.markdown("## 📖 Standard Operating Runbooks Library")
    st.markdown("Automated and peer-reviewed procedures used by SRE-Shield to resolve production incidents.")
    st.write("")

    session = SyncSessionLocal()
    try:
        runbooks = session.query(Runbook).all()
        if not runbooks:
            st.info("No runbooks found.")
            return

        search_kw = st.text_input("🔍 Filter Runbooks by keyword or problem type:", value="")
        filtered_rbs = [
            rb for rb in runbooks
            if not search_kw or (search_kw.lower() in rb.name.lower() or search_kw.lower() in rb.problem_type.lower() or search_kw.lower() in rb.code.lower())
        ]

        st.write(f"Showing **{len(filtered_rbs)}** of {len(runbooks)} Runbooks:")

        for rb in filtered_rbs:
            total_uses = rb.success_count + rb.failure_count
            rate = round((rb.success_count / total_uses * 100), 1) if total_uses > 0 else 100.0

            with st.expander(f"📘 [{rb.code}] {rb.name} — Success Rate: {rate}% ({rb.success_count} runs)", expanded=(rb.code == "DB-CONNECTION-001")):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**Problem Classification:** `{rb.problem_type}`")
                with col2:
                    st.markdown(f"**Execution Risk:** <span class='badge badge-medium'>{rb.risk_level}</span>", unsafe_allow_html=True)

                st.write("")

                # Tabs for runbook sections
                t_inv, t_res, t_cmd, t_ver = st.tabs([
                    "🔍 Investigation Steps",
                    "🛠️ Resolution Steps",
                    "💻 CLI Commands",
                    "✅ Verification Steps"
                ])

                with t_inv:
                    steps = json.loads(rb.investigation_steps or "[]")
                    for s in steps:
                        st.markdown(f"- {s}")

                with t_res:
                    res_steps = json.loads(rb.resolution_steps or "[]")
                    for s in res_steps:
                        st.markdown(f"- {s}")

                with t_cmd:
                    cmds = json.loads(rb.cli_commands or "[]")
                    for c in cmds:
                        st.markdown(f"**{c.get('description', '')}** (Risk: `{c.get('risk', 'MEDIUM')}`):")
                        st.code(c.get("command", ""), language="bash")

                with t_ver:
                    ver_steps = json.loads(rb.verification_steps or "[]")
                    for v in ver_steps:
                        st.markdown(f"- {v}")

    finally:
        session.close()
