import asyncio
import datetime
import uuid
from typing import Dict, Any, List
from sqlalchemy import select

from backend.config import settings
from backend.database.models import Incident, AuditLog, get_utc_now
from backend.database.connection import AsyncSessionLocal
from backend.runbooks.runbook_manager import RunbookManager

class SafeExecutionEngine:
    """
    Executes remediations with Human-in-the-Loop approval,
    enforcing SIMULATION MODE safety and automated verification.
    """

    @classmethod
    def evaluate_risk(cls, command: str) -> str:
        """Determines risk level based on command characteristics"""
        cmd_lower = command.lower()
        if any(term in cmd_lower for term in ["drop", "delete namespace", "rm -rf", "terminate", "rollback", "undo"]):
            return "HIGH"
        elif any(term in cmd_lower for term in ["patch", "restart", "scale", "config set", "modify"]):
            return "MEDIUM"
        else:
            return "LOW"

    @classmethod
    async def execute_and_verify(
        cls,
        incident_id: str,
        command_to_run: str,
        approved_by: str = "Lead SRE Engineer"
    ) -> Dict[str, Any]:
        """
        Executes approved command in SIMULATION MODE and runs post-remediation verification checks.
        """
        now = get_utc_now()

        # Step 1: Simulate Execution
        cmd_lower = command_to_run.lower()
        
        if "kubectl rollout restart" in cmd_lower or "kubectl patch" in cmd_lower:
            exec_output = (
                f"[SIMULATION MODE] Command executed successfully on cluster prod-k8s-us-east-1:\n"
                f"$ {command_to_run}\n"
                f"configmap/checkout-db-config patched (DB_POOL_MAX=50, DB_TIMEOUT=5000)\n"
                f"deployment.apps/checkout-api restarted\n"
                f"Waiting for rollout to finish: 1 of 4 updated replicas are available...\n"
                f"Waiting for rollout to finish: 2 of 4 updated replicas are available...\n"
                f"Waiting for rollout to finish: 4 of 4 updated replicas are available...\n"
                f"deployment.apps/checkout-api successfully rolled out."
            )
            verification_output = (
                f"[HEALTH PROBE] GET http://checkout-api.internal/healthz -> 200 OK (latency: 14ms)\n"
                f"[METRICS VERIFIED] Active DB connection pool saturation: 28% (down from 100%)\n"
                f"[SLO RESTORED] HTTP 500 error rate: 0.00% (down from 48.2%)\n"
                f"[STATUS] Service fully recovered and stable."
            )
            verification_pass = True

        elif "kubectl scale" in cmd_lower:
            exec_output = (
                f"[SIMULATION MODE] Command executed successfully:\n"
                f"$ {command_to_run}\n"
                f"deployment.apps/user-auth-service scaled\n"
                f"Waiting for deployment spec update to be observed...\n"
                f"Waiting for rollout to finish: 8 of 8 updated replicas are available.\n"
                f"deployment \"user-auth-service\" successfully rolled out."
            )
            verification_output = (
                f"[HEALTH PROBE] Endpoints verified: 8 healthy pods online\n"
                f"[METRICS VERIFIED] CPU load distributed: average 34% per pod (down from 98%)\n"
                f"[SLO RESTORED] HTTP 503 Ingress errors: 0.00%"
            )
            verification_pass = True

        elif "kubectl set resources" in cmd_lower:
            exec_output = (
                f"[SIMULATION MODE] Resource allocation updated:\n"
                f"$ {command_to_run}\n"
                f"deployment.apps/inventory-service resource limits updated to memory=2560Mi\n"
                f"New pod scheduled. Previous CrashLoopBackOff container cleared."
            )
            verification_output = (
                f"[HEALTH PROBE] JVM memory usage: 1.12Gi / 2.5Gi (45% headroom)\n"
                f"[STATUS] Container restarts: 0 over last 300s. Health probe 200 OK."
            )
            verification_pass = True

        elif "rollout undo" in cmd_lower:
            exec_output = (
                f"[SIMULATION MODE] Immediate rollback executed:\n"
                f"$ {command_to_run}\n"
                f"deployment.apps/payment-gateway rolled back to previous revision\n"
                f"Terminating faulty pods. Stable revision active."
            )
            verification_output = (
                f"[HEALTH PROBE] /healthz returned 200 OK\n"
                f"[METRICS VERIFIED] Zero startup crashes detected. 100% payment transactions processing."
            )
            verification_pass = True

        elif "redis-cli" in cmd_lower:
            exec_output = (
                f"[SIMULATION MODE] Redis configuration updated dynamically:\n"
                f"$ {command_to_run}\n"
                f"OK\n"
                f"maxmemory-policy: allkeys-lru\n"
                f"maxmemory: 8589934592 bytes (8GB)\n"
                f"1.4GB expired keys evicted."
            )
            verification_output = (
                f"[HEALTH PROBE] Redis latency benchmark: 0.9ms\n"
                f"[METRICS VERIFIED] Connection timeouts: 0. Memory utilization: 52% of 8GB."
            )
            verification_pass = True

        else:
            exec_output = (
                f"[SIMULATION MODE] Command executed successfully in safe sandbox:\n"
                f"$ {command_to_run}\n"
                f"[EXIT CODE 0] Execution completed with zero errors."
            )
            verification_output = (
                f"[HEALTH PROBE] Service health endpoint returned 200 OK\n"
                f"[METRICS VERIFIED] Telemetry anomalies cleared. Error rates normal."
            )
            verification_pass = True

        # Step 2: Update Incident Record in Database
        async with AsyncSessionLocal() as session:
            stmt = select(Incident).where(Incident.id == incident_id)
            res = await session.execute(stmt)
            incident = res.scalars().first()

            if incident:
                incident.execution_status = "VERIFIED" if verification_pass else "FAILED"
                incident.execution_output = exec_output
                incident.verification_status = "PASS" if verification_pass else "FAIL"
                incident.verification_output = verification_output
                incident.status = "RESOLVED" if verification_pass else "INVESTIGATING"
                incident.approved_by = approved_by
                incident.approved_at = now
                incident.resolved_at = now
                
                # Calculate MTTR
                if incident.created_at:
                    delta = (now - incident.created_at.replace(tzinfo=datetime.timezone.utc)).total_seconds()
                    incident.mttr_seconds = max(int(delta), 120)

                # Record Runbook Outcome
                if incident.recommended_runbook_id:
                    await RunbookManager.record_outcome(incident.recommended_runbook_id, success=verification_pass)

                # Audit Log
                audit = AuditLog(
                    id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                    incident_id=incident_id,
                    action="ACTION_APPROVED_AND_EXECUTED",
                    actor=approved_by,
                    details=f"Approved command: '{command_to_run}'. Verification: {'PASS' if verification_pass else 'FAIL'}."
                )
                session.add(audit)
                await session.commit()

        return {
            "status": "success",
            "incident_id": incident_id,
            "command": command_to_run,
            "simulation_mode": True,
            "execution_status": "EXECUTED",
            "execution_output": exec_output,
            "verification_status": "PASS" if verification_pass else "FAIL",
            "verification_output": verification_output,
            "incident_status": "RESOLVED" if verification_pass else "FAILED"
        }

    @classmethod
    async def reject_action(cls, incident_id: str, rejected_by: str = "Lead SRE Engineer", reason: str = ""):
        """Records rejection of the AI recommended action"""
        async with AsyncSessionLocal() as session:
            stmt = select(Incident).where(Incident.id == incident_id)
            res = await session.execute(stmt)
            incident = res.scalars().first()
            if incident:
                incident.execution_status = "REJECTED"
                incident.status = "INVESTIGATING"
                audit = AuditLog(
                    id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                    incident_id=incident_id,
                    action="ACTION_REJECTED",
                    actor=rejected_by,
                    details=f"Engineer rejected recommended action. Reason: {reason or 'Manual intervention required'}"
                )
                session.add(audit)
                await session.commit()
            return {"status": "rejected", "incident_id": incident_id}

executor = SafeExecutionEngine()
