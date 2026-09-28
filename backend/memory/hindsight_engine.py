import json
import uuid
import datetime
from typing import Dict, Any, List, Optional
import httpx
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database.models import (
    MemoryExperience, EntitySummary, EvolvingBelief, WorldFact, AuditLog, get_utc_now
)
from backend.database.connection import AsyncSessionLocal
from backend.security.sanitizer import memory_defense
from backend.memory.base import BaseMemoryEngine
from backend.memory.embeddings import HybridSearchEngine

class HindsightMemoryEngine(BaseMemoryEngine):
    """
    Implementation of the Hindsight Agent Memory architecture for SRE:
    4 Logical Networks:
      1. World Network: Objective system topology, limits, and facts
      2. Experience Network: Historical incidents, actions, and outcomes
      3. Entity Summaries: Synthesized operational knowledge per service
      4. Evolving Beliefs: Agent heuristics and calibrated beliefs over time

    3 Core Operations:
      - Retain: Store sanitized incident learnings
      - Recall: Retrieve relevant experiences, beliefs, and entity profiles
      - Reflect: Synthesize new beliefs and update entity profiles
    """

    def __init__(self):
        self.search_engine = HybridSearchEngine()
        self.is_initialized = False

    async def initialize(self):
        """Pre-warms the hybrid search index from the database"""
        async with AsyncSessionLocal() as session:
            stmt = select(MemoryExperience)
            result = await session.execute(stmt)
            experiences = result.scalars().all()

            docs = []
            for exp in experiences:
                docs.append({
                    "id": exp.id,
                    "text": exp.search_text or f"{exp.service} {exp.error_signature} {exp.symptoms} {exp.root_cause}"
                })
            self.search_engine.fit_corpus(docs)
            self.is_initialized = True

    async def retain(
        self,
        incident_data: Dict[str, Any],
        post_mortem_data: Optional[Dict[str, Any]] = None,
        outcome: str = "SUCCESS"
    ) -> Dict[str, Any]:
        """
        Retains an incident outcome into the Experience Network with Memory Defense sanitization.
        Then triggers reflection to update Entity Summaries and Evolving Beliefs.
        """
        # Step 1: Memory Defense Sanitization
        sanitized_incident, sec_report = memory_defense.sanitize_dict(incident_data)
        sanitized_pm, pm_sec_report = memory_defense.sanitize_dict(post_mortem_data or {})

        total_redactions = sec_report["redaction_count"] + pm_sec_report["redaction_count"]

        service = sanitized_incident.get("service", "UnknownService")
        error_msg = sanitized_incident.get("error_message", "")
        symptoms = sanitized_incident.get("symptoms", "")
        root_cause = sanitized_incident.get("root_cause", "")
        runbook_code = sanitized_incident.get("recommended_runbook_id", "")
        
        # Format successful commands
        successful_commands = []
        if sanitized_incident.get("suggested_command"):
            successful_commands.append(sanitized_incident.get("suggested_command"))
        if sanitized_pm.get("commands_used"):
            cmd_val = sanitized_pm.get("commands_used")
            if isinstance(cmd_val, list):
                successful_commands.extend(cmd_val)
            elif isinstance(cmd_val, str) and cmd_val:
                successful_commands.append(cmd_val)

        # Build consolidated search corpus text
        search_corpus = (
            f"Service: {service}\n"
            f"Error: {error_msg}\n"
            f"Symptoms: {symptoms}\n"
            f"Logs: {sanitized_incident.get('logs', '')}\n"
            f"Root Cause: {root_cause}\n"
            f"Resolution: {sanitized_incident.get('suggested_action', '')}\n"
            f"Lessons Learned: {sanitized_pm.get('lessons_learned', '')}"
        )

        experience_id = f"EXP-{uuid.uuid4().hex[:8].upper()}"

        async with AsyncSessionLocal() as session:
            # Check if this incident already has an experience entry
            inc_id = sanitized_incident.get("id")
            existing_exp = None
            if inc_id:
                stmt = select(MemoryExperience).where(MemoryExperience.incident_id == inc_id)
                res = await session.execute(stmt)
                existing_exp = res.scalars().first()

            if existing_exp:
                existing_exp.root_cause = root_cause
                existing_exp.resolution_strategy = sanitized_incident.get("suggested_action", "")
                existing_exp.successful_commands = json.dumps(list(set(successful_commands)))
                existing_exp.outcome = outcome
                existing_exp.search_text = search_corpus
                existing_exp.post_mortem_summary = sanitized_pm.get("summary", "")
                experience_id = existing_exp.id
            else:
                new_exp = MemoryExperience(
                    id=experience_id,
                    incident_id=inc_id or experience_id,
                    service=service,
                    error_signature=error_msg[:250],
                    symptoms=symptoms,
                    root_cause=root_cause,
                    resolution_strategy=sanitized_incident.get("suggested_action", ""),
                    successful_commands=json.dumps(list(set(successful_commands))),
                    failed_commands="[]",
                    runbook_code=runbook_code,
                    outcome=outcome,
                    post_mortem_summary=sanitized_pm.get("summary", ""),
                    search_text=search_corpus,
                    confidence_weight=1.0,
                    recall_count=0
                )
                session.add(new_exp)

            # Audit log
            audit = AuditLog(
                id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                incident_id=inc_id or experience_id,
                action="MEMORY_RETAINED",
                actor="HindsightEngine",
                details=f"Retained experience into Experience Network. Sanitized {total_redactions} secrets."
            )
            session.add(audit)
            await session.commit()

        # Re-index search engine
        await self.initialize()

        # Step 2: Trigger Reflection to update Entity Summaries and Evolving Beliefs
        reflection_report = await self.reflect(service_name=service)

        # Step 3: Optional remote Hindsight API integration
        remote_synced = False
        if settings.HINDSIGHT_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.post(
                        f"{settings.HINDSIGHT_ENDPOINT}/banks/{settings.HINDSIGHT_BANK_NAME}/retain",
                        headers={"Authorization": f"Bearer {settings.HINDSIGHT_API_KEY}"},
                        json={
                            "content": search_corpus,
                            "metadata": {
                                "service": service,
                                "incident_id": inc_id,
                                "outcome": outcome,
                                "experience_id": experience_id
                            }
                        }
                    )
                    if resp.status_code in (200, 201):
                        remote_synced = True
            except Exception:
                remote_synced = False

        return {
            "status": "success",
            "experience_id": experience_id,
            "sanitization_report": {
                "redacted": total_redactions > 0,
                "redaction_count": total_redactions,
                "categories": list(set(sec_report["categories"] + pm_sec_report["categories"]))
            },
            "reflection": reflection_report,
            "remote_hindsight_synced": remote_synced
        }

    async def recall(
        self,
        query_service: str,
        error_message: str,
        logs: str = "",
        top_k: int = 4
    ) -> Dict[str, Any]:
        """
        Recalls relevant knowledge from all 4 Hindsight Networks:
          - Experience Network: Historical similar incidents & solutions
          - Entity Summaries: Synthesized profile of the queried service
          - Evolving Beliefs: Operational rules of thumb and invariants
          - World Network: Architectural constraints & SLOs
        """
        if not self.is_initialized:
            await self.initialize()

        query_text = f"Service: {query_service}\nError: {error_message}\nLogs: {logs}"
        search_hits = self.search_engine.search(query_text, top_k=top_k, service_filter=query_service)

        similar_experiences = []
        async with AsyncSessionLocal() as session:
            # 1. Fetch matching experiences
            if search_hits:
                hit_ids = [hit[0] for hit in search_hits]
                scores_map = {hit[0]: hit[1] for hit in search_hits}

                stmt = select(MemoryExperience).where(MemoryExperience.id.in_(hit_ids))
                res = await session.execute(stmt)
                experiences = res.scalars().all()

                for exp in experiences:
                    # Increment recall counter
                    exp.recall_count += 1
                    try:
                        cmds = json.loads(exp.successful_commands or "[]")
                    except Exception:
                        cmds = [exp.successful_commands] if exp.successful_commands else []

                    similarity_score = scores_map.get(exp.id, 0.5)

                    similar_experiences.append({
                        "id": exp.id,
                        "incident_id": exp.incident_id,
                        "service": exp.service,
                        "similarity_score": similarity_score,
                        "similarity_pct": int(similarity_score * 100),
                        "error_signature": exp.error_signature,
                        "root_cause": exp.root_cause,
                        "resolution_strategy": exp.resolution_strategy,
                        "successful_commands": cmds,
                        "outcome": exp.outcome,
                        "runbook_code": exp.runbook_code,
                        "created_at": exp.created_at.strftime("%Y-%m-%d %H:%M") if exp.created_at else ""
                    })

                # Sort by similarity
                similar_experiences.sort(key=lambda x: x["similarity_score"], reverse=True)
                await session.commit()

            # 2. Fetch Entity Summary for the service
            entity_stmt = select(EntitySummary).where(EntitySummary.entity_name.ilike(f"%{query_service}%"))
            entity_res = await session.execute(entity_stmt)
            entity = entity_res.scalars().first()
            entity_data = None
            if entity:
                entity_data = {
                    "entity_name": entity.entity_name,
                    "entity_type": entity.entity_type,
                    "summary": entity.summary,
                    "total_incidents": entity.total_incidents,
                    "avg_mttr_minutes": entity.avg_mttr_minutes,
                    "known_failure_modes": json.loads(entity.known_failure_modes or "[]"),
                    "preferred_runbooks": json.loads(entity.preferred_runbooks or "[]")
                }

            # 3. Fetch Evolving Beliefs
            beliefs_stmt = select(EvolvingBelief).order_by(desc(EvolvingBelief.confidence)).limit(5)
            beliefs_res = await session.execute(beliefs_stmt)
            beliefs = [
                {
                    "domain": b.domain,
                    "belief_statement": b.belief_statement,
                    "confidence": b.confidence,
                    "supporting_incidents": b.supporting_incident_count
                }
                for b in beliefs_res.scalars().all()
            ]

            # 4. Fetch World Facts
            world_stmt = select(WorldFact).where(WorldFact.subject.ilike(f"%{query_service}%"))
            world_res = await session.execute(world_stmt)
            world_facts = [
                {
                    "category": wf.category,
                    "subject": wf.subject,
                    "fact": wf.fact_statement
                }
                for wf in world_res.scalars().all()
            ]

        return {
            "has_matches": len(similar_experiences) > 0,
            "match_count": len(similar_experiences),
            "experiences": similar_experiences,
            "entity_summary": entity_data,
            "evolving_beliefs": beliefs,
            "world_facts": world_facts,
            "top_match": similar_experiences[0] if similar_experiences else None
        }

    async def reflect(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Synthesizes recent experiences into updated Entity Summaries and Evolving Beliefs.
        """
        async with AsyncSessionLocal() as session:
            # Query experiences for the service
            if service_name:
                stmt = select(MemoryExperience).where(MemoryExperience.service == service_name)
            else:
                stmt = select(MemoryExperience)
            res = await session.execute(stmt)
            experiences = res.scalars().all()

            if not experiences:
                return {"status": "no_experiences_to_reflect"}

            # Group failure modes and runbooks
            failure_modes = []
            runbooks_used = set()
            for exp in experiences:
                if exp.root_cause and exp.root_cause not in failure_modes:
                    failure_modes.append(exp.root_cause)
                if exp.runbook_code:
                    runbooks_used.add(exp.runbook_code)

            # Update or create Entity Summary
            target_service = service_name or (experiences[0].service if experiences else "Core Service")
            entity_stmt = select(EntitySummary).where(EntitySummary.entity_name == target_service)
            entity_res = await session.execute(entity_stmt)
            entity = entity_res.scalars().first()

            summary_text = (
                f"{target_service} has logged {len(experiences)} incident(s). "
                f"Primary root causes identified: {'; '.join(failure_modes[:3])}. "
                f"Proven resolution runbooks: {', '.join(runbooks_used) if runbooks_used else 'Standard SRE'}"
            )

            if entity:
                entity.total_incidents = len(experiences)
                entity.summary = summary_text
                entity.known_failure_modes = json.dumps(failure_modes)
                entity.preferred_runbooks = json.dumps(list(runbooks_used))
                entity.updated_at = get_utc_now()
            else:
                entity = EntitySummary(
                    id=f"ENT-{uuid.uuid4().hex[:8].upper()}",
                    entity_name=target_service,
                    entity_type="SERVICE",
                    summary=summary_text,
                    known_failure_modes=json.dumps(failure_modes),
                    preferred_runbooks=json.dumps(list(runbooks_used)),
                    total_incidents=len(experiences),
                    avg_mttr_minutes=14.5
                )
                session.add(entity)

            # Evolve domain belief if recurring pattern found
            if any("connection pool" in exp.search_text.lower() for exp in experiences):
                belief_stmt = select(EvolvingBelief).where(EvolvingBelief.domain == "Database")
                belief_res = await session.execute(belief_stmt)
                b = belief_res.scalars().first()
                if b:
                    b.confidence = min(0.98, b.confidence + 0.05)
                    b.supporting_incident_count += 1
                    b.updated_at = get_utc_now()
                else:
                    new_b = EvolvingBelief(
                        id=f"BEL-{uuid.uuid4().hex[:8].upper()}",
                        domain="Database",
                        belief_statement="Database connection starvation on API gateways is typically triggered by traffic spikes coupled with slow unindexed queries; pool expansion and rollout restart effectively mitigate downtime.",
                        confidence=0.95,
                        supporting_incident_count=len(experiences)
                    )
                    session.add(new_b)

            await session.commit()

        return {
            "status": "reflected",
            "service": target_service,
            "total_experiences_analyzed": len(experiences),
            "updated_entity_summary": summary_text
        }

# Singleton instance
hindsight = HindsightMemoryEngine()
