import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(50), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    service = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="HIGH", index=True) # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String(30), nullable=False, default="NEW", index=True)     # NEW, INVESTIGATING, AWAITING_APPROVAL, EXECUTING, VERIFYING, RESOLVED, FAILED

    error_message = Column(Text, nullable=False)
    symptoms = Column(Text, default="")
    logs = Column(Text, default="")
    deployment_info = Column(Text, default="")

    # AI Diagnosis & Memory Recall
    root_cause = Column(Text, default="")
    suggested_action = Column(Text, default="")
    suggested_command = Column(Text, default="")
    risk_level = Column(String(20), default="MEDIUM") # LOW, MEDIUM, HIGH
    confidence_score = Column(Float, default=0.0)
    recommended_runbook_id = Column(String(50), default="")
    similar_incident_ids = Column(Text, default="[]") # JSON list of similar incident IDs
    reasoning_explanation = Column(Text, default="")

    # Execution & Verification
    approved_by = Column(String(100), default="")
    approved_at = Column(DateTime, nullable=True)
    execution_status = Column(String(30), default="PENDING") # PENDING, APPROVED, REJECTED, EXECUTED, VERIFIED, FAILED
    execution_output = Column(Text, default="")
    verification_status = Column(String(30), default="NOT_RUN") # NOT_RUN, PASS, FAIL
    verification_output = Column(Text, default="")
    
    # Timing & Metrics
    mttr_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now, index=True)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    post_mortem = relationship("PostMortem", back_populates="incident", uselist=False)

class Runbook(Base):
    __tablename__ = "runbooks"

    id = Column(String(50), primary_key=True, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True) # e.g. DB-CONNECTION-001
    name = Column(String(255), nullable=False)
    problem_type = Column(String(150), nullable=False, index=True)
    symptoms = Column(Text, default="[]") # JSON list
    investigation_steps = Column(Text, default="[]") # JSON list
    resolution_steps = Column(Text, default="[]") # JSON list
    cli_commands = Column(Text, default="[]") # JSON list of dicts: {command, description, risk}
    verification_steps = Column(Text, default="[]") # JSON list
    risk_level = Column(String(20), default="MEDIUM")
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now)

class PostMortem(Base):
    __tablename__ = "post_mortems"

    id = Column(String(50), primary_key=True, index=True)
    incident_id = Column(String(50), ForeignKey("incidents.id"), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text, default="")
    impact = Column(Text, default="")
    timeline = Column(Text, default="[]") # JSON list of timeline events
    root_cause = Column(Text, default="")
    resolution = Column(Text, default="")
    commands_used = Column(Text, default="[]")
    what_worked = Column(Text, default="")
    what_failed = Column(Text, default="")
    prevention = Column(Text, default="")
    recommended_monitoring = Column(Text, default="")
    lessons_learned = Column(Text, default="")
    
    is_approved = Column(Boolean, default=False)
    approved_by = Column(String(100), default="SRE Lead")
    created_at = Column(DateTime, default=get_utc_now)
    approved_at = Column(DateTime, nullable=True)

    incident = relationship("Incident", back_populates="post_mortem")

# -------------------------------------------------------------
# HINDSIGHT AGENT MEMORY - 4 LOGICAL NETWORKS
# -------------------------------------------------------------

class MemoryExperience(Base):
    """Network 1: Experience Network - The agent's first-person action history"""
    __tablename__ = "memory_experiences"

    id = Column(String(50), primary_key=True, index=True)
    incident_id = Column(String(50), index=True)
    service = Column(String(100), nullable=False, index=True)
    error_signature = Column(String(255), nullable=False, index=True)
    symptoms = Column(Text, default="")
    root_cause = Column(Text, default="")
    resolution_strategy = Column(Text, default="")
    successful_commands = Column(Text, default="[]") # JSON list
    failed_commands = Column(Text, default="[]")     # JSON list
    runbook_code = Column(String(50), default="")
    outcome = Column(String(20), default="SUCCESS")  # SUCCESS, FAILED
    post_mortem_summary = Column(Text, default="")
    search_text = Column(Text, default="")           # Consolidated searchable corpus
    confidence_weight = Column(Float, default=1.0)
    recall_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now, index=True)

class EntitySummary(Base):
    """Network 2: Entity Summaries - Rolling synthesized operational profile per service/system"""
    __tablename__ = "entity_summaries"

    id = Column(String(50), primary_key=True, index=True)
    entity_name = Column(String(100), unique=True, nullable=False, index=True) # e.g. Checkout API
    entity_type = Column(String(50), default="SERVICE")                        # SERVICE, DATABASE, QUEUE, GATEWAY
    summary = Column(Text, default="")
    known_failure_modes = Column(Text, default="[]")                          # JSON list
    preferred_runbooks = Column(Text, default="[]")                           # JSON list
    total_incidents = Column(Integer, default=0)
    avg_mttr_minutes = Column(Float, default=0.0)
    last_incident_id = Column(String(50), default="")
    updated_at = Column(DateTime, default=get_utc_now)

class EvolvingBelief(Base):
    """Network 3: Evolving Beliefs - Stable, calibrated point-of-view and heuristics developed over time"""
    __tablename__ = "evolving_beliefs"

    id = Column(String(50), primary_key=True, index=True)
    domain = Column(String(100), nullable=False, index=True)                   # Database, Kubernetes, Network, Memory
    belief_statement = Column(Text, nullable=False)
    confidence = Column(Float, default=0.85)
    supporting_incident_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now)

class WorldFact(Base):
    """Network 4: World Network - Objective external facts, architecture topology, SLAs and limits"""
    __tablename__ = "world_facts"

    id = Column(String(50), primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True)                  # TOPOLOGY, LIMIT, DEPENDENCY, SLO
    subject = Column(String(100), nullable=False, index=True)
    fact_statement = Column(Text, nullable=False)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=get_utc_now)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(50), primary_key=True, index=True)
    incident_id = Column(String(50), index=True)
    action = Column(String(100), nullable=False)
    actor = Column(String(100), default="System")
    details = Column(Text, default="")
    created_at = Column(DateTime, default=get_utc_now, index=True)
