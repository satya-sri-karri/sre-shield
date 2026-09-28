import streamlit as st
import asyncio
import json
import pandas as pd
from backend.database.connection import SyncSessionLocal
from backend.database.models import MemoryExperience, EntitySummary, EvolvingBelief, WorldFact
from backend.memory.hindsight_engine import hindsight

def show_hindsight_page():
    st.markdown("## 🧠 Hindsight Agent Memory Inspector")
    st.markdown("Hindsight organizes incident memory into 4 structured reasoning networks rather than flat text chunks, enabling true continuous learning.")
    st.write("")

    session = SyncSessionLocal()
    try:
        # Top summary stats
        exp_count = session.query(MemoryExperience).count()
        ent_count = session.query(EntitySummary).count()
        bel_count = session.query(EvolvingBelief).count()
        wld_count = session.query(WorldFact).count()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("1. Experience Network", f"{exp_count} Memories", "First-person actions")
        with col2:
            st.metric("2. Entity Summaries", f"{ent_count} Services", "Rolling profiles")
        with col3:
            st.metric("3. Evolving Beliefs", f"{bel_count} Heuristics", "Calibrated over time")
        with col4:
            st.metric("4. World Network", f"{wld_count} Facts", "Topology & SLAs")

        st.write("")

        # Live Memory Query Sandbox
        with st.expander("🔎 Interactive Memory Recall Sandbox (Test Hindsight Query)", expanded=False):
            test_col1, test_col2 = st.columns([3, 1])
            with test_col1:
                test_q = st.text_input("Enter error pattern or symptom to query memory:", value="connection pool exhausted HTTP 500")
            with test_col2:
                st.write("")
                run_test = st.button("Query Memory Bank", use_container_width=True)

            if run_test and test_q:
                recall_res = asyncio.run(hindsight.recall(query_service="", error_message=test_q, logs="", top_k=3))
                if recall_res["has_matches"]:
                    st.success(f"Matched {recall_res['match_count']} memories! Top match: `{recall_res['top_match']['incident_id']}` ({recall_res['top_match']['similarity_pct']}% similarity)")
                    st.json(recall_res["top_match"])
                else:
                    st.warning("No high-confidence match found for this query.")

        st.write("---")

        # Tabs for the 4 Networks
        t1, t2, t3, t4 = st.tabs([
            "🧠 Experience Network",
            "🏢 Entity Summaries",
            "⚡ Evolving Beliefs",
            "🌐 World Network"
        ])

        with t1:
            st.markdown("#### 1. Experience Network (First-Person SRE Incident Trajectories)")
            st.markdown("Stores historical outages, verified remediation commands, failure patterns, and recall counters.")
            exps = session.query(MemoryExperience).order_by(MemoryExperience.created_at.desc()).all()
            if exps:
                exp_rows = []
                for e in exps:
                    exp_rows.append({
                        "Memory ID": e.id,
                        "Incident ID": e.incident_id,
                        "Service": e.service,
                        "Error Signature": e.error_signature[:45] + "...",
                        "Root Cause": e.root_cause[:45] + "...",
                        "Runbook": e.runbook_code or "N/A",
                        "Outcome": e.outcome,
                        "Times Recalled": e.recall_count,
                        "Retained On": e.created_at.strftime("%Y-%m-%d %H:%M") if e.created_at else ""
                    })
                st.dataframe(pd.DataFrame(exp_rows), use_container_width=True, hide_index=True)

                # Drill down selector
                st.write("")
                sel_exp = st.selectbox("Inspect Full Memory Trajectory", [e.id for e in exps])
                if sel_exp:
                    target_e = next(e for e in exps if e.id == sel_exp)
                    with st.expander(f"Details for {sel_exp}", expanded=True):
                        st.markdown(f"**Service:** `{target_e.service}` | **Incident:** `{target_e.incident_id}`")
                        st.markdown(f"**Root Cause:** {target_e.root_cause}")
                        st.markdown(f"**Resolution Strategy:** {target_e.resolution_strategy}")
                        st.markdown(f"**Verified Successful Commands:**")
                        st.code(target_e.successful_commands or "[]", language="json")
                        st.markdown(f"**Post-Mortem Digest:** {target_e.post_mortem_summary}")

        with t2:
            st.markdown("#### 2. Entity Summaries (Synthesized Knowledge per Service)")
            st.markdown("Continuous rolling synthesis of each service's failure tendencies and preferred runbooks.")
            entities = session.query(EntitySummary).all()
            for ent in entities:
                st.markdown(f"""
                <div style="background-color: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: #60a5fa; font-size: 1.05rem;">{ent.entity_name} ({ent.entity_type})</span>
                        <span style="font-size: 0.8rem; color: #94a3b8;">Total Incidents: {ent.total_incidents} | Avg MTTR: {ent.avg_mttr_minutes}m</span>
                    </div>
                    <p style="color: #cbd5e1; margin-top: 6px; font-size: 0.9rem;">{ent.summary}</p>
                    <div style="font-size: 0.82rem; color: #94a3b8;">
                        <strong>Known Failure Modes:</strong> {ent.known_failure_modes} &nbsp;|&nbsp; 
                        <strong>Preferred Runbooks:</strong> {ent.preferred_runbooks}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with t3:
            st.markdown("#### 3. Evolving Beliefs (Agent Heuristics & Calibrated Wisdom)")
            st.markdown("Operational invariants and rules-of-thumb learned from successes and failures over time.")
            beliefs = session.query(EvolvingBelief).order_by(EvolvingBelief.confidence.desc()).all()
            for b in beliefs:
                conf_pct = int(b.confidence * 100)
                st.markdown(f"""
                <div style="background-color: #1e1b4b; border: 1px solid #4338ca; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-weight: 700; color: #c7d2fe;">Domain: {b.domain}</span>
                        <span style="font-weight: 700; color: #34d399;">Confidence: {conf_pct}% ({b.supporting_incident_count} cases)</span>
                    </div>
                    <p style="color: #e0e7ff; margin-top: 8px; font-size: 0.92rem; font-style: italic;">
                        "{b.belief_statement}"
                    </p>
                </div>
                """, unsafe_allow_html=True)

        with t4:
            st.markdown("#### 4. World Network (Architecture Topology, Constraints & SLAs)")
            st.markdown("Objective external facts about system architecture and operational boundaries.")
            facts = session.query(WorldFact).all()
            for f in facts:
                st.markdown(f"""
                <div style="background-color: #0f172a; border-left: 3px solid #3b82f6; padding: 10px 16px; margin-bottom: 10px; border-radius: 4px;">
                    <span style="font-size: 0.75rem; font-weight: 700; color: #60a5fa; text-transform: uppercase;">[{f.category}] {f.subject}</span><br/>
                    <span style="color: #cbd5e1; font-size: 0.9rem;">{f.fact_statement}</span>
                </div>
                """, unsafe_allow_html=True)

        # Trigger reflection button
        st.write("")
        st.write("---")
        ref_col1, ref_col2 = st.columns([3, 1])
        with ref_col1:
            st.info("Trigger Reflection to synthesize recent incident resolutions into updated entity profiles and domain beliefs.")
        with ref_col2:
            if st.button("⚡ Trigger Memory Reflection", use_container_width=True):
                with st.spinner("Synthesizing knowledge across experiences..."):
                    ref_res = asyncio.run(hindsight.reflect())
                st.success("Memory reflection complete! Entity summaries and evolving beliefs updated.")
                st.rerun()

    finally:
        session.close()
