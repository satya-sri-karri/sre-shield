import streamlit as st
import asyncio
import json
import uuid
from backend.database.connection import SyncSessionLocal, AsyncSessionLocal
from backend.database.models import Incident, AuditLog, get_utc_now
from backend.security.sanitizer import memory_defense
from backend.agents.analyzer import analyzer

def show_incident_center():
    st.markdown("## 🚨 Incident Center & AI Diagnosis")
    st.markdown("Ingest production alerts or log manual outages. SRE-Shield applies Memory Defense, queries Hindsight Memory, and produces memory-grounded diagnosis.")
    st.write("")

    # Quick Scenario Loaders
    st.markdown("##### 🚀 1-Click Demo Scenarios")
    demo_col1, demo_col2, demo_col3 = st.columns(3)
    
    scenario_choice = None
    with demo_col1:
        if st.button("🔥 Checkout API: DB Pool Starvation (Main Demo)", use_container_width=True):
            st.session_state["form_service"] = "Checkout API"
            st.session_state["form_severity"] = "CRITICAL"
            st.session_state["form_error"] = "HTTP 500 Internal Server Error: org.postgresql.util.PSQLException: FATAL: remaining connection slots are reserved"
            st.session_state["form_deploy"] = "Traffic surged to 24,000 rps after holiday coupon push notification."
            st.session_state["form_logs"] = """2026-09-28T11:40:02.109Z [FATAL] [checkout-api-89c-01] org.postgresql.util.PSQLException: remaining connection slots are reserved
2026-09-28T11:40:02.115Z [ERROR] [checkout-api-89c-01] Connection pool exhausted! Max pool size 20 reached.
2026-09-28T11:40:02.120Z [DEBUG] DB_CONN_STR=postgresql://app_user:prodSecretPassword123@postgres-primary:5432/shopdb
2026-09-28T11:40:02.122Z [WARN] AuthToken=Bearer gsk_live_99998888777766665555444433332222"""
            st.rerun()

    with demo_col2:
        if st.button("💥 Inventory: JVM Heap OOMKilled", use_container_width=True):
            st.session_state["form_service"] = "Inventory Service"
            st.session_state["form_severity"] = "HIGH"
            st.session_state["form_error"] = "Container terminated with ExitCode 137 (OOMKilled) - memory limit 1024Mi exceeded"
            st.session_state["form_deploy"] = "Catalog warehouse sync initiated bulk unpaginated export."
            st.session_state["form_logs"] = """2026-09-28T10:15:00Z [INFO] java.lang.OutOfMemoryError: Java heap space
2026-09-28T10:15:02Z [WARN] Container inventory-worker terminated: OOMKilled (Exit Code 137)
2026-09-28T10:15:05Z [ERROR] Back-off restarting failed container"""
            st.rerun()

    with demo_col3:
        if st.button("⚡ Redis: Eviction Lockup & Timeout", use_container_width=True):
            st.session_state["form_service"] = "Redis Cache"
            st.session_state["form_severity"] = "HIGH"
            st.session_state["form_error"] = "RedisConnectionException: Command timed out after 3000ms: OOM command not allowed"
            st.session_state["form_deploy"] = "New user token TTL configuration rolled out."
            st.session_state["form_logs"] = """2026-09-28T08:30:11Z [redis-node-1] # Out of memory allocating bytes!
2026-09-28T08:30:12Z [redis-node-1] # maxmemory-policy is 'noeviction'. Refusing writes!"""
            st.rerun()

    st.write("")

    # Form inputs
    with st.form("incident_form"):
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            service = st.text_input("Service Name", value=st.session_state.get("form_service", "Checkout API"))
        with col_s2:
            severity = st.selectbox(
                "Severity",
                ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                index=["CRITICAL", "HIGH", "MEDIUM", "LOW"].index(st.session_state.get("form_severity", "CRITICAL"))
            )

        error_message = st.text_area(
            "Error Message / Alert Title",
            value=st.session_state.get("form_error", "HTTP 500 Internal Server Error: org.postgresql.util.PSQLException: FATAL: remaining connection slots are reserved"),
            height=70
        )

        deployment_info = st.text_input(
            "Recent Deployment / Configuration Changes",
            value=st.session_state.get("form_deploy", "Traffic surged 400% after push notification campaign.")
        )

        logs = st.text_area(
            "Raw Logs / Stack Trace",
            value=st.session_state.get("form_logs", "2026-09-28T11:40:02.109Z [FATAL] [checkout-api] Connection acquisition timeout after 30000ms\nDatabase connection pool exhausted"),
            height=130
        )

        submit_btn = st.form_submit_button("⚡ Analyze Incident with SRE-Shield", use_container_width=True)

    if submit_btn:
        with st.spinner("1. Sanitizing sensitive data (Memory Defense)... 2. Recalling Hindsight Memory... 3. Diagnosing root cause..."):
            # Step 1: Memory Defense Sanitization
            clean_err, err_sec = memory_defense.sanitize(error_message)
            clean_logs, logs_sec = memory_defense.sanitize(logs)
            clean_deploy, _ = memory_defense.sanitize(deployment_info)

            total_redactions = err_sec["redaction_count"] + logs_sec["redaction_count"]
            all_cats = list(set(err_sec["categories"] + logs_sec["categories"]))

            # Step 2: Hindsight Memory Recall & Dual AI Analysis
            analysis = asyncio.run(analyzer.analyze_incident(
                service=service,
                error_message=clean_err,
                symptoms=clean_deploy,
                logs=clean_logs,
                deployment_info=clean_deploy
            ))

            # Step 3: Persist Incident in DB
            new_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
            diag_mem = analysis["diagnosis_with_memory"]
            recalled = analysis["memory_recall"]

            sim_ids = [m["incident_id"] for m in recalled.get("experiences", [])]

            session = SyncSessionLocal()
            try:
                inc = Incident(
                    id=new_id,
                    title=f"{service}: {clean_err[:80]}",
                    service=service,
                    severity=severity,
                    status="AWAITING_APPROVAL",
                    error_message=clean_err,
                    symptoms=clean_deploy,
                    logs=clean_logs,
                    deployment_info=clean_deploy,
                    root_cause=diag_mem.get("root_cause", ""),
                    suggested_action=diag_mem.get("suggested_action", ""),
                    suggested_command=diag_mem.get("suggested_command", ""),
                    risk_level=diag_mem.get("risk_level", "MEDIUM"),
                    confidence_score=diag_mem.get("confidence_score", 0.95),
                    recommended_runbook_id=diag_mem.get("recommended_runbook_id", "DB-CONNECTION-001"),
                    similar_incident_ids=json.dumps(sim_ids),
                    reasoning_explanation=diag_mem.get("reasoning_explanation", ""),
                    execution_status="PENDING",
                    verification_status="NOT_RUN",
                    created_at=get_utc_now()
                )
                session.add(inc)

                audit = AuditLog(
                    id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                    incident_id=new_id,
                    action="INCIDENT_INGESTED",
                    actor="AlertIngestion",
                    details=f"Alert ingested and analyzed with Hindsight memory. Sanitized {total_redactions} secrets."
                )
                session.add(audit)
                session.commit()
            finally:
                session.close()

            # Store result in session state
            st.session_state["current_analysis"] = {
                "incident_id": new_id,
                "service": service,
                "severity": severity,
                "sanitization_report": {
                    "redacted": total_redactions > 0,
                    "count": total_redactions,
                    "categories": all_cats
                },
                "analysis": analysis
            }

    # Display Analysis Results
    if "current_analysis" in st.session_state:
        cur = st.session_state["current_analysis"]
        inc_id = cur["incident_id"]
        analysis = cur["analysis"]
        diag_mem = analysis["diagnosis_with_memory"]
        diag_nomem = analysis["diagnosis_without_memory"]
        recalled = analysis["memory_recall"]
        sec = cur["sanitization_report"]

        st.write("---")
        st.markdown(f"### 🛡️ Incident Analysis Result: `{inc_id}`")

        # Memory Defense Sanitization Banner
        if sec["redacted"]:
            st.success(
                f"🛡️ **Memory Defense Sanitization Active**: Safely detected and redacted **{sec['count']}** sensitive token(s) "
                f"({', '.join(sec['categories'])}) before storing into persistent memory."
            )
        else:
            st.info("🛡️ **Memory Defense Active**: Zero unmasked secrets detected in incident telemetry.")

        # Recalled Experiences Banner
        top_m = recalled.get("top_match")
        if top_m:
            st.markdown(f"""
            <div style="background-color: rgba(16, 185, 129, 0.15); border-left: 4px solid #10b981; padding: 14px 18px; border-radius: 6px; margin: 12px 0;">
                <span style="color: #34d399; font-weight: 700; font-size: 1rem;">🧠 Hindsight Memory Match Found!</span><br/>
                <span style="color: #e2e8f0;">
                    Identified past incident <strong>{top_m['incident_id']}</strong> with <strong>{top_m['similarity_pct']}% similarity</strong>.<br/>
                    <strong>Previous Root Cause:</strong> {top_m['root_cause']}<br/>
                    <strong>Verified Resolution:</strong> {top_m['resolution_strategy']} (Runbook: <code>{top_m['runbook_code']}</code>)
                </span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("No direct historical match found in memory bank. Operating in initial baseline mode.")

        # SIDE-BY-SIDE: WITH MEMORY vs WITHOUT MEMORY
        st.markdown("#### ⚖️ The Power of Persistent Memory: Side-by-Side Comparison")
        comp_col1, comp_col2 = st.columns(2)

        with comp_col1:
            st.markdown(f"""
            <div class="comparison-card-mem">
                <span style="color: #34d399; font-weight: 700; font-size: 1.05rem;">✅ SRE-Shield (With Hindsight Memory)</span>
                <p style="margin-top: 8px; color: #f1f5f9; font-size: 0.92rem;">
                    <strong>Root Cause:</strong> {diag_mem.get('root_cause', '')}<br/>
                    <strong>Confidence:</strong> <span style="color: #10b981; font-weight: 700;">{int(diag_mem.get('confidence_score', 0.95)*100)}%</span><br/>
                    <strong>Recommended Runbook:</strong> <code>{diag_mem.get('recommended_runbook_id', 'DB-CONNECTION-001')}</code><br/>
                    <strong>Explanation:</strong> {diag_mem.get('reasoning_explanation', '')}
                </p>
                <div style="background-color: #064e3b; padding: 8px 12px; border-radius: 4px; font-family: monospace; font-size: 0.85rem; color: #a7f3d0; word-break: break-all;">
                    {diag_mem.get('suggested_command', '')}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with comp_col2:
            st.markdown(f"""
            <div class="comparison-card-nomem">
                <span style="color: #f87171; font-weight: 700; font-size: 1.05rem;">❌ Stateless AI (Without Memory)</span>
                <p style="margin-top: 8px; color: #f1f5f9; font-size: 0.92rem;">
                    <strong>Root Cause:</strong> {diag_nomem.get('root_cause', '')}<br/>
                    <strong>Confidence:</strong> <span style="color: #f87171; font-weight: 700;">{int(diag_nomem.get('confidence_score', 0.45)*100)}% (Low/Guess)</span><br/>
                    <strong>Generic Suggestion:</strong> {diag_nomem.get('suggested_action', '')}<br/>
                    <strong>Limitation:</strong> {diag_nomem.get('reasoning_explanation', 'No memory of cluster configuration or past fixes.')}
                </p>
                <div style="background-color: #7f1d1d; padding: 8px 12px; border-radius: 4px; font-family: monospace; font-size: 0.85rem; color: #fecaca; word-break: break-all;">
                    {diag_nomem.get('suggested_command', 'reboot / manual triage')}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.write("")

        # Action Gateway
        st.markdown("#### 🎯 Human-in-the-Loop Next Steps")
        act_col1, act_col2 = st.columns([2, 1])
        with act_col1:
            st.info(f"Incident `{inc_id}` is staged in **AWAITING_APPROVAL** state. No destructive actions will run without engineer authorization.")
        with act_col2:
            if st.button("👉 Review & Approve Remediation Now", type="primary", use_container_width=True):
                st.session_state["nav_choice"] = "Human Approval & Execution"
                st.session_state["selected_incident_id"] = inc_id
                st.rerun()
