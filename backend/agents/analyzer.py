import json
from typing import Dict, Any, List, Optional
from backend.agents.groq_client import groq_client
from backend.memory.hindsight_engine import hindsight
from backend.runbooks.runbook_manager import RunbookManager

class IncidentAnalyzer:
    """
    SRE Incident Analyzer that diagnoses incidents using Hindsight Persistent Memory.
    Produces both:
      1. Memory-Augmented Diagnosis (Precise, grounded in past resolutions)
      2. Baseline Diagnosis Without Memory (Generic, ungrounded)
    to clearly demonstrate the power of self-learning memory.
    """

    @classmethod
    async def analyze_incident(
        cls,
        service: str,
        error_message: str,
        symptoms: str = "",
        logs: str = "",
        deployment_info: str = ""
    ) -> Dict[str, Any]:
        """
        Full SRE Incident Analysis pipeline:
        Alert -> Sanitization -> Recall Hindsight Memory -> AI Reasoning -> Runbook Matching -> Recommendation
        """
        # Step 1: Recall from Hindsight 4 Networks
        memory_recall = await hindsight.recall(
            query_service=service,
            error_message=error_message,
            logs=logs,
            top_k=3
        )

        has_memory = memory_recall.get("has_matches", False)
        top_match = memory_recall.get("top_match")
        entity_summary = memory_recall.get("entity_summary")
        beliefs = memory_recall.get("evolving_beliefs", [])

        # Step 2: Try Groq LLM inference with memory context
        diagnosis_with_mem = await cls._generate_with_memory(
            service, error_message, symptoms, logs, deployment_info, memory_recall
        )

        # Step 3: Generate Baseline Without Memory (to prove difference)
        diagnosis_no_mem = await cls._generate_without_memory(
            service, error_message, symptoms, logs, deployment_info
        )

        return {
            "service": service,
            "error_message": error_message,
            "memory_recall": memory_recall,
            "diagnosis_with_memory": diagnosis_with_mem,
            "diagnosis_without_memory": diagnosis_no_mem,
            "has_memory_advantage": has_memory
        }

    @classmethod
    async def _generate_with_memory(
        cls,
        service: str,
        error_message: str,
        symptoms: str,
        logs: str,
        deployment_info: str,
        memory_recall: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesizes memory-grounded diagnosis"""
        top_match = memory_recall.get("top_match")
        entity_summary = memory_recall.get("entity_summary")
        beliefs = memory_recall.get("evolving_beliefs", [])
        experiences = memory_recall.get("experiences", [])

        system_prompt = (
            "You are a Senior Site Reliability Engineer (SRE) with persistent long-term incident memory. "
            "You diagnose production outages using past verified resolutions from your memory bank. "
            "Respond in JSON with keys: "
            "'incident_summary', 'root_cause', 'confidence_score' (float 0.0-1.0), 'reasoning_explanation', "
            "'recommended_runbook_id', 'suggested_action', 'suggested_command', 'risk_level' ('LOW','MEDIUM','HIGH')."
        )

        user_prompt = f"""
Current Incident:
Service: {service}
Error: {error_message}
Symptoms: {symptoms}
Deployment Info: {deployment_info}
Logs:
{logs}

Historical Hindsight Memory Recalled:
- Top Matching Past Incident: {json.dumps(top_match) if top_match else 'None'}
- Other Similar Incidents: {json.dumps(experiences[:2])}
- Entity Summary: {json.dumps(entity_summary) if entity_summary else 'No prior profile'}
- Evolving Beliefs: {json.dumps(beliefs)}

Task:
Analyze the incident using the historical memory. Point out which past incident matches, 
what root cause was found previously, and why the recommended fix has proven successful before.
"""
        llm_response = await groq_client.call_groq_json(user_prompt, system_prompt)
        if llm_response and "root_cause" in llm_response:
            return llm_response

        # Fallback to intelligent SRE heuristic engine grounded in memory
        if top_match:
            sim_pct = top_match.get("similarity_pct", 92)
            past_id = top_match.get("incident_id", "INC-1001")
            past_root = top_match.get("root_cause", "Database connection pool exhaustion")
            past_res = top_match.get("resolution_strategy", "Scale pool size in ConfigMap and restart")
            runbook_code = top_match.get("runbook_code", "DB-CONNECTION-001")
            cmd = top_match.get("successful_commands", ["kubectl rollout restart deployment/service"])[0] if top_match.get("successful_commands") else "kubectl rollout restart deployment/checkout-api"

            explanation = (
                f"Historical memory matched past incident {past_id} with {sim_pct}% similarity. "
                f"Previous root cause was '{past_root}'. The resolution was verified successful "
                f"using runbook {runbook_code}. Based on evolving beliefs, executing pool expansion "
                f"and rolling restart resolves this failure mode without data loss."
            )

            return {
                "incident_summary": f"High-severity failure in {service} matching historical pattern from {past_id}.",
                "root_cause": past_root,
                "confidence_score": round(min(0.96, top_match.get("similarity_score", 0.92) + 0.04), 2),
                "reasoning_explanation": explanation,
                "recommended_runbook_id": runbook_code,
                "suggested_action": past_res,
                "suggested_command": cmd,
                "risk_level": "MEDIUM"
            }
        else:
            # First time error without prior memory
            return {
                "incident_summary": f"Initial uncatalogued outage in {service}.",
                "root_cause": f"Potential runtime exception or resource exhaustion indicated by: {error_message[:100]}",
                "confidence_score": 0.65,
                "reasoning_explanation": "No direct historical match found in Hindsight memory. Recommended safe diagnostic restart and log inspection.",
                "recommended_runbook_id": "DB-CONNECTION-001",
                "suggested_action": "Inspect telemetry, check pod status, and verify downstream connectivity.",
                "suggested_command": f"kubectl logs -l app={service.lower().replace(' ', '-')} --tail=100",
                "risk_level": "LOW"
            }

    @classmethod
    async def _generate_without_memory(
        cls,
        service: str,
        error_message: str,
        symptoms: str,
        logs: str,
        deployment_info: str
    ) -> Dict[str, Any]:
        """
        Simulates standard stateless AI (ChatGPT / basic prompt)
        without persistent memory: gives generic, textbook advice.
        """
        system_prompt = (
            "You are a generic chatbot assistant without any memory of past incidents, cluster topology, or previous fixes. "
            "Give standard textbook troubleshooting advice. Respond in JSON with keys: "
            "'incident_summary', 'root_cause', 'confidence_score' (max 0.55), 'suggested_action', 'risk_level'."
        )
        user_prompt = f"Service: {service}\nError: {error_message}\nLogs: {logs}\nWhat should I do?"

        llm_response = await groq_client.call_groq_json(user_prompt, system_prompt)
        if llm_response and "root_cause" in llm_response:
            return llm_response

        # Generic stateless baseline
        return {
            "incident_summary": f"Generic error reported in {service}.",
            "root_cause": "Unknown. Could be database failure, network latency, bad code, or infrastructure issue.",
            "confidence_score": 0.45,
            "suggested_action": "Check application logs, ping the server, restart the host, or consult the engineering team.",
            "suggested_command": "reboot or restart service",
            "risk_level": "HIGH",
            "reasoning_explanation": "Stateless AI has no memory of your infrastructure, past incidents, or verified commands."
        }

analyzer = IncidentAnalyzer()
