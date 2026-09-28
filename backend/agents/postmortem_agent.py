import json
import uuid
import datetime
from typing import Dict, Any, Optional
from sqlalchemy import select

from backend.agents.groq_client import groq_client
from backend.database.models import Incident, PostMortem, get_utc_now
from backend.database.connection import AsyncSessionLocal
from backend.memory.hindsight_engine import hindsight

class PostMortemAgent:
    """
    Automated SRE Post-Mortem Generator and Hindsight Memory Closer.
    """

    @classmethod
    async def generate_postmortem(cls, incident_id: str) -> Dict[str, Any]:
        """
        Generates comprehensive post-mortem draft for a resolved incident.
        """
        async with AsyncSessionLocal() as session:
            stmt = select(Incident).where(Incident.id == incident_id)
            res = await session.execute(stmt)
            inc = res.scalars().first()
            if not inc:
                raise ValueError(f"Incident {incident_id} not found")

            inc_data = {
                "id": inc.id,
                "title": inc.title,
                "service": inc.service,
                "severity": inc.severity,
                "error_message": inc.error_message,
                "root_cause": inc.root_cause,
                "execution_output": inc.execution_output,
                "suggested_command": inc.suggested_command,
                "mttr_seconds": inc.mttr_seconds or 300,
                "created_at": inc.created_at.strftime("%H:%M") if inc.created_at else "12:00",
                "resolved_at": inc.resolved_at.strftime("%H:%M") if inc.resolved_at else "12:05"
            }

        # Try Groq generation
        system_prompt = (
            "You are a Principal SRE conducting a blameless post-mortem analysis. "
            "Output JSON with keys: 'title', 'summary', 'impact', 'timeline' (list of dicts with 'time','event'), "
            "'root_cause', 'resolution', 'commands_used' (list of strings), 'what_worked', 'what_failed', "
            "'prevention', 'recommended_monitoring', 'lessons_learned'."
        )
        user_prompt = f"Incident details:\n{json.dumps(inc_data, indent=2)}\nGenerate a rigorous post-mortem."

        llm_response = await groq_client.call_groq_json(user_prompt, system_prompt)
        if llm_response and "root_cause" in llm_response:
            return llm_response

        # Resilient SRE Heuristic Template
        mttr_mins = round((inc_data["mttr_seconds"] / 60), 1)
        cmds = [inc_data["suggested_command"]] if inc_data.get("suggested_command") else ["kubectl rollout restart"]
        timeline = [
            {"time": inc_data["created_at"], "event": f"Alert triggered on {inc_data['service']}: {inc_data['error_message'][:80]}"},
            {"time": "Alert+2m", "event": "SRE-Shield recalled past historical incident from Hindsight memory"},
            {"time": "Alert+4m", "event": "Remediation command approved by engineer and safely executed in cluster"},
            {"time": inc_data["resolved_at"], "event": f"Automated health checks verified. MTTR: {mttr_mins} minutes."}
        ]

        return {
            "title": f"Post-Mortem: {inc_data['service']} - {inc_data['title']}",
            "summary": f"{inc_data['service']} experienced a {inc_data['severity']} degradation resulting in elevated error rates before automated SRE-Shield resolution.",
            "impact": f"Service availability degraded for approximately {mttr_mins} minutes. User requests failed with {inc_data['error_message'][:50]}.",
            "timeline": timeline,
            "root_cause": inc_data["root_cause"] or "Resource saturation and configuration mismatch under load.",
            "resolution": f"Applied verified remediation: {inc_data['suggested_command']}.",
            "commands_used": cmds,
            "what_worked": "Rapid recall from Hindsight memory identified verified runbook within seconds, avoiding lengthy triage.",
            "what_failed": "Telemetry threshold was reactionary rather than predictive.",
            "prevention": "Tune autoscaling thresholds and add pre-scale policies during anticipated traffic bursts.",
            "recommended_monitoring": "Deploy Prometheus alert for resource saturation when utilization exceeds 75% for >60s.",
            "lessons_learned": "Persistent memory drastically reduces MTTR by eliminating trial-and-error debugging."
        }

    @classmethod
    async def approve_and_save_postmortem(
        cls,
        incident_id: str,
        pm_content: Dict[str, Any],
        approved_by: str = "Lead SRE Engineer"
    ) -> Dict[str, Any]:
        """
        Saves approved post-mortem to the database and feeds the new experience
        into Hindsight Persistent Memory (Retain & Reflect).
        """
        now = get_utc_now()
        pm_id = f"PM-{uuid.uuid4().hex[:8].upper()}"

        timeline_str = (
            json.dumps(pm_content.get("timeline", []))
            if isinstance(pm_content.get("timeline"), list)
            else str(pm_content.get("timeline", "[]"))
        )
        cmds_str = (
            json.dumps(pm_content.get("commands_used", []))
            if isinstance(pm_content.get("commands_used"), list)
            else str(pm_content.get("commands_used", "[]"))
        )

        async with AsyncSessionLocal() as session:
            stmt = select(Incident).where(Incident.id == incident_id)
            res = await session.execute(stmt)
            incident = res.scalars().first()

            if not incident:
                raise ValueError(f"Incident {incident_id} not found")

            # Check existing post-mortem
            pm_stmt = select(PostMortem).where(PostMortem.incident_id == incident_id)
            pm_res = await session.execute(pm_stmt)
            existing_pm = pm_res.scalars().first()

            if existing_pm:
                existing_pm.summary = pm_content.get("summary", "")
                existing_pm.impact = pm_content.get("impact", "")
                existing_pm.timeline = timeline_str
                existing_pm.root_cause = pm_content.get("root_cause", "")
                existing_pm.resolution = pm_content.get("resolution", "")
                existing_pm.commands_used = cmds_str
                existing_pm.what_worked = pm_content.get("what_worked", "")
                existing_pm.what_failed = pm_content.get("what_failed", "")
                existing_pm.prevention = pm_content.get("prevention", "")
                existing_pm.recommended_monitoring = pm_content.get("recommended_monitoring", "")
                existing_pm.lessons_learned = pm_content.get("lessons_learned", "")
                existing_pm.is_approved = True
                existing_pm.approved_by = approved_by
                existing_pm.approved_at = now
                pm_id = existing_pm.id
            else:
                new_pm = PostMortem(
                    id=pm_id,
                    incident_id=incident_id,
                    title=pm_content.get("title", f"Post-Mortem: {incident.title}"),
                    summary=pm_content.get("summary", ""),
                    impact=pm_content.get("impact", ""),
                    timeline=timeline_str,
                    root_cause=pm_content.get("root_cause", ""),
                    resolution=pm_content.get("resolution", ""),
                    commands_used=cmds_str,
                    what_worked=pm_content.get("what_worked", ""),
                    what_failed=pm_content.get("what_failed", ""),
                    prevention=pm_content.get("prevention", ""),
                    recommended_monitoring=pm_content.get("recommended_monitoring", ""),
                    lessons_learned=pm_content.get("lessons_learned", ""),
                    is_approved=True,
                    approved_by=approved_by,
                    approved_at=now
                )
                session.add(new_pm)

            incident_dict = {
                "id": incident.id,
                "service": incident.service,
                "error_message": incident.error_message,
                "symptoms": incident.symptoms,
                "logs": incident.logs,
                "root_cause": pm_content.get("root_cause", incident.root_cause),
                "suggested_action": pm_content.get("resolution", incident.suggested_action),
                "suggested_command": incident.suggested_command,
                "recommended_runbook_id": incident.recommended_runbook_id
            }

            await session.commit()

        # Step 2: Feed back into Hindsight Agent Memory (Retain -> Sanitize -> Reflect -> Update)
        retention_result = await hindsight.retain(
            incident_data=incident_dict,
            post_mortem_data=pm_content,
            outcome="SUCCESS"
        )

        return {
            "status": "success",
            "post_mortem_id": pm_id,
            "incident_id": incident_id,
            "hindsight_retention": retention_result
        }

postmortem_agent = PostMortemAgent()
