import uuid
import json
import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import (
    Incident, Runbook, PostMortem, MemoryExperience, EntitySummary, EvolvingBelief, WorldFact, AuditLog, get_utc_now
)
from backend.database.connection import get_db
from backend.memory.hindsight_engine import hindsight
from backend.agents.analyzer import analyzer
from backend.agents.postmortem_agent import postmortem_agent
from backend.agents.assistant import assistant_agent
from backend.execution.executor import executor
from backend.runbooks.runbook_manager import RunbookManager
from backend.security.sanitizer import memory_defense

router = APIRouter(prefix="/api", tags=["SRE-Shield"])

# ----------------- PYDANTIC SCHEMAS -----------------

class IncidentCreateRequest(BaseModel):
    service: str
    severity: str = "HIGH"
    error_message: str
    symptoms: Optional[str] = ""
    logs: Optional[str] = ""
    deployment_info: Optional[str] = ""

class ExecutionApprovalRequest(BaseModel):
    command: Optional[str] = None
    approved_by: str = "Lead SRE Engineer"

class ExecutionRejectionRequest(BaseModel):
    reason: Optional[str] = "Command rejected by on-call engineer"
    rejected_by: str = "Lead SRE Engineer"

class PostMortemApprovalRequest(BaseModel):
    title: Optional[str] = None
    summary: str
    impact: str
    timeline: List[Dict[str, str]]
    root_cause: str
    resolution: str
    commands_used: List[str]
    what_worked: str
    what_failed: str
    prevention: str
    recommended_monitoring: str
    lessons_learned: str
    approved_by: str = "Principal SRE"

class AskAssistantRequest(BaseModel):
    question: str

# ----------------- ROUTES -----------------

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "SRE-Shield",
        "version": "1.0.0",
        "memory_engine": "Hindsight Agent Memory (4-Network Architecture)",
        "sanitization": "Memory Defense Active",
        "simulation_mode": True
    }

@router.get("/dashboard")
async def get_dashboard_metrics(db: AsyncSession = Depends(get_db)):
    """Summary dashboard metrics"""
    # Active incidents
    active_stmt = select(Incident).where(Incident.status.in_(["NEW", "INVESTIGATING", "AWAITING_APPROVAL", "EXECUTING", "VERIFYING"]))
    active_res = await db.execute(active_stmt)
    active_incidents = active_res.scalars().all()

    # Resolved incidents
    resolved_stmt = select(Incident).where(Incident.status == "RESOLVED")
    resolved_res = await db.execute(resolved_stmt)
    resolved_incidents = resolved_res.scalars().all()

    # Average MTTR (in minutes)
    mttr_stmt = select(func.avg(Incident.mttr_seconds)).where(Incident.status == "RESOLVED")
    mttr_res = await db.execute(mttr_stmt)
    avg_mttr_sec = mttr_res.scalar() or 600

    # Recent incidents
    recent_stmt = select(Incident).order_by(desc(Incident.created_at)).limit(8)
    recent_res = await db.execute(recent_stmt)
    recent_incidents = recent_res.scalars().all()

    # Total memories in Hindsight
    mem_stmt = select(func.count(MemoryExperience.id))
    mem_res = await db.execute(mem_stmt)
    total_memories = mem_res.scalar() or 0

    return {
        "active_incidents_count": len(active_incidents),
        "resolved_incidents_count": len(resolved_incidents),
        "avg_mttr_minutes": round(avg_mttr_sec / 60, 1),
        "total_historical_memories": total_memories,
        "active_incidents": [
            {
                "id": inc.id,
                "title": inc.title,
                "service": inc.service,
                "severity": inc.severity,
                "status": inc.status,
                "created_at": inc.created_at.strftime("%Y-%m-%d %H:%M") if inc.created_at else ""
            }
            for inc in active_incidents
        ],
        "recent_incidents": [
            {
                "id": inc.id,
                "title": inc.title,
                "service": inc.service,
                "severity": inc.severity,
                "status": inc.status,
                "root_cause": inc.root_cause,
                "mttr_minutes": round((inc.mttr_seconds or 0) / 60, 1),
                "created_at": inc.created_at.strftime("%Y-%m-%d %H:%M") if inc.created_at else ""
            }
            for inc in recent_incidents
        ]
    }

@router.get("/incidents")
async def list_incidents(
    service: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Incident).order_by(desc(Incident.created_at))
    if service:
        stmt = stmt.where(Incident.service.ilike(f"%{service}%"))
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if status:
        stmt = stmt.where(Incident.status == status)

    res = await db.execute(stmt)
    incidents = res.scalars().all()
    return [
        {
            "id": inc.id,
            "title": inc.title,
            "service": inc.service,
            "severity": inc.severity,
            "status": inc.status,
            "error_message": inc.error_message,
            "root_cause": inc.root_cause,
            "recommended_runbook_id": inc.recommended_runbook_id,
            "confidence_score": inc.confidence_score,
            "mttr_seconds": inc.mttr_seconds,
            "created_at": inc.created_at.strftime("%Y-%m-%d %H:%M:%S") if inc.created_at else "",
            "resolved_at": inc.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if inc.resolved_at else None
        }
        for inc in incidents
    ]

@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Incident).where(Incident.id == incident_id)
    res = await db.execute(stmt)
    inc = res.scalars().first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    pm_stmt = select(PostMortem).where(PostMortem.incident_id == incident_id)
    pm_res = await db.execute(pm_stmt)
    pm = pm_res.scalars().first()

    return {
        "id": inc.id,
        "title": inc.title,
        "service": inc.service,
        "severity": inc.severity,
        "status": inc.status,
        "error_message": inc.error_message,
        "symptoms": inc.symptoms,
        "logs": inc.logs,
        "deployment_info": inc.deployment_info,
        "root_cause": inc.root_cause,
        "suggested_action": inc.suggested_action,
        "suggested_command": inc.suggested_command,
        "risk_level": inc.risk_level,
        "confidence_score": inc.confidence_score,
        "recommended_runbook_id": inc.recommended_runbook_id,
        "reasoning_explanation": inc.reasoning_explanation,
        "execution_status": inc.execution_status,
        "execution_output": inc.execution_output,
        "verification_status": inc.verification_status,
        "verification_output": inc.verification_output,
        "mttr_seconds": inc.mttr_seconds,
        "created_at": inc.created_at.strftime("%Y-%m-%d %H:%M:%S") if inc.created_at else "",
        "resolved_at": inc.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if inc.resolved_at else None,
        "post_mortem": {
            "id": pm.id,
            "title": pm.title,
            "summary": pm.summary,
            "impact": pm.impact,
            "timeline": json.loads(pm.timeline or "[]"),
            "root_cause": pm.root_cause,
            "resolution": pm.resolution,
            "commands_used": json.loads(pm.commands_used or "[]"),
            "what_worked": pm.what_worked,
            "what_failed": pm.what_failed,
            "prevention": pm.prevention,
            "recommended_monitoring": pm.recommended_monitoring,
            "lessons_learned": pm.lessons_learned,
            "is_approved": pm.is_approved
        } if pm else None
    }

@router.post("/incidents")
async def create_incident(req: IncidentCreateRequest, db: AsyncSession = Depends(get_db)):
    """
    Ingests alert, sanitizes sensitive data via Memory Defense,
    recalls Hindsight memory, runs AI diagnosis, and creates incident in AWAITING_APPROVAL state.
    """
    # Step 1: Memory Defense Sanitization
    clean_error, err_sec = memory_defense.sanitize(req.error_message)
    clean_logs, logs_sec = memory_defense.sanitize(req.logs or "")
    clean_symptoms, symp_sec = memory_defense.sanitize(req.symptoms or "")

    incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
    title = f"{req.service}: {clean_error[:80]}"

    # Step 2: Hindsight Memory Recall & AI Diagnosis
    analysis = await analyzer.analyze_incident(
        service=req.service,
        error_message=clean_error,
        symptoms=clean_symptoms,
        logs=clean_logs,
        deployment_info=req.deployment_info or ""
    )

    diag = analysis["diagnosis_with_memory"]
    similar_ids = [m["incident_id"] for m in analysis["memory_recall"].get("experiences", [])]

    # Step 3: Persist Incident
    new_inc = Incident(
        id=incident_id,
        title=title,
        service=req.service,
        severity=req.severity,
        status="AWAITING_APPROVAL",
        error_message=clean_error,
        symptoms=clean_symptoms,
        logs=clean_logs,
        deployment_info=req.deployment_info or "",
        root_cause=diag.get("root_cause", ""),
        suggested_action=diag.get("suggested_action", ""),
        suggested_command=diag.get("suggested_command", ""),
        risk_level=diag.get("risk_level", "MEDIUM"),
        confidence_score=diag.get("confidence_score", 0.85),
        recommended_runbook_id=diag.get("recommended_runbook_id", ""),
        similar_incident_ids=json.dumps(similar_ids),
        reasoning_explanation=diag.get("reasoning_explanation", ""),
        execution_status="PENDING",
        verification_status="NOT_RUN",
        created_at=get_utc_now()
    )
    db.add(new_inc)

    # Audit Log
    audit = AuditLog(
        id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
        incident_id=incident_id,
        action="INCIDENT_INGESTED",
        actor="AlertIngestionPipeline",
        details=f"Alert ingested and analyzed with Hindsight memory. Sanitized {err_sec['redaction_count'] + logs_sec['redaction_count']} secrets."
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "created",
        "incident_id": incident_id,
        "title": title,
        "analysis": analysis,
        "sanitization_report": {
            "redacted": err_sec["redacted"] or logs_sec["redacted"],
            "count": err_sec["redaction_count"] + logs_sec["redaction_count"]
        }
    }

@router.post("/incidents/{incident_id}/approve")
async def approve_and_execute_incident(
    incident_id: str,
    req: ExecutionApprovalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Human-in-the-Loop approval: Executes the remediation command safely in SIMULATION MODE and verifies.
    """
    stmt = select(Incident).where(Incident.id == incident_id)
    res = await db.execute(stmt)
    inc = res.scalars().first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    cmd_to_run = req.command or inc.suggested_command
    if not cmd_to_run:
        raise HTTPException(status_code=400, detail="No command provided to execute")

    # Safe execution and verification
    result = await executor.execute_and_verify(
        incident_id=incident_id,
        command_to_run=cmd_to_run,
        approved_by=req.approved_by
    )

    return result

@router.post("/incidents/{incident_id}/reject")
async def reject_incident_action(
    incident_id: str,
    req: ExecutionRejectionRequest
):
    result = await executor.reject_action(
        incident_id=incident_id,
        rejected_by=req.rejected_by,
        reason=req.reason or "Rejected by engineer"
    )
    return result

@router.post("/incidents/{incident_id}/postmortem/generate")
async def generate_postmortem_draft(incident_id: str):
    draft = await postmortem_agent.generate_postmortem(incident_id)
    return draft

@router.post("/incidents/{incident_id}/postmortem/approve")
async def approve_and_retain_postmortem(
    incident_id: str,
    req: PostMortemApprovalRequest
):
    result = await postmortem_agent.approve_and_save_postmortem(
        incident_id=incident_id,
        pm_content=req.model_dump(),
        approved_by=req.approved_by
    )
    return result

@router.get("/runbooks")
async def list_runbooks():
    return await RunbookManager.get_all_runbooks()

@router.get("/runbooks/{code}")
async def get_runbook(code: str):
    rb = await RunbookManager.get_by_code(code)
    if not rb:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return rb

@router.get("/memory/networks")
async def inspect_memory_networks(db: AsyncSession = Depends(get_db)):
    """Deep inspection of the 4 Hindsight Networks"""
    exp_res = await db.execute(select(MemoryExperience).order_by(desc(MemoryExperience.created_at)).limit(20))
    ent_res = await db.execute(select(EntitySummary))
    bel_res = await db.execute(select(EvolvingBelief).order_by(desc(EvolvingBelief.confidence)))
    wld_res = await db.execute(select(WorldFact))

    return {
        "network_1_experience": [
            {
                "id": exp.id,
                "incident_id": exp.incident_id,
                "service": exp.service,
                "error_signature": exp.error_signature,
                "root_cause": exp.root_cause,
                "resolution": exp.resolution_strategy,
                "commands": json.loads(exp.successful_commands or "[]"),
                "outcome": exp.outcome,
                "recall_count": exp.recall_count,
                "created_at": exp.created_at.strftime("%Y-%m-%d %H:%M") if exp.created_at else ""
            }
            for exp in exp_res.scalars().all()
        ],
        "network_2_entity_summaries": [
            {
                "id": ent.id,
                "entity_name": ent.entity_name,
                "entity_type": ent.entity_type,
                "summary": ent.summary,
                "total_incidents": ent.total_incidents,
                "avg_mttr": ent.avg_mttr_minutes,
                "known_failure_modes": json.loads(ent.known_failure_modes or "[]"),
                "preferred_runbooks": json.loads(ent.preferred_runbooks or "[]")
            }
            for ent in ent_res.scalars().all()
        ],
        "network_3_evolving_beliefs": [
            {
                "id": b.id,
                "domain": b.domain,
                "belief_statement": b.belief_statement,
                "confidence": b.confidence,
                "supporting_incidents": b.supporting_incident_count
            }
            for b in bel_res.scalars().all()
        ],
        "network_4_world_facts": [
            {
                "id": wf.id,
                "category": wf.category,
                "subject": wf.subject,
                "fact": wf.fact_statement
            }
            for wf in wld_res.scalars().all()
        ]
    }

@router.post("/assistant/ask")
async def ask_sre_assistant(req: AskAssistantRequest):
    return await assistant_agent.ask(req.question)

@router.get("/analytics")
async def get_analytics(db: AsyncSession = Depends(get_db)):
    """Computes SRE analytics: MTTR trends, service distributions, recurrence metrics"""
    stmt = select(Incident).order_by(Incident.created_at)
    res = await db.execute(stmt)
    all_incidents = res.scalars().all()

    services_count: Dict[str, int] = {}
    severity_count: Dict[str, int] = {}
    mttr_timeline: List[Dict[str, Any]] = []

    for inc in all_incidents:
        # Service count
        services_count[inc.service] = services_count.get(inc.service, 0) + 1
        # Severity count
        severity_count[inc.severity] = severity_count.get(inc.severity, 0) + 1
        # MTTR point
        if inc.status == "RESOLVED" and inc.resolved_at:
            mttr_timeline.append({
                "date": inc.resolved_at.strftime("%Y-%m-%d"),
                "service": inc.service,
                "mttr_minutes": round((inc.mttr_seconds or 300) / 60, 1),
                "incident_id": inc.id
            })

    runbooks = await RunbookManager.get_all_runbooks()

    return {
        "services_distribution": services_count,
        "severity_distribution": severity_count,
        "mttr_timeline": mttr_timeline,
        "runbook_performance": [
            {
                "code": rb["code"],
                "name": rb["name"],
                "success_count": rb["success_count"],
                "failure_count": rb["failure_count"],
                "success_rate": rb["success_rate"]
            }
            for rb in runbooks
        ]
    }
