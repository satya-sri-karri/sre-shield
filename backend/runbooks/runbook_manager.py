import json
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from backend.database.models import Runbook
from backend.database.connection import AsyncSessionLocal

INITIAL_RUNBOOKS = [
    {
        "code": "DB-CONNECTION-001",
        "name": "Database Connection Pool Starvation Remediation",
        "problem_type": "Database Connection Pool Exhaustion",
        "risk_level": "MEDIUM",
        "symptoms": [
            "HTTP 500 Internal Server Error spikes",
            "Logs contain 'remaining connection slots are reserved' or 'pool exhausted'",
            "Application p99 response times exceed 5000ms",
            "Checkout API unable to acquire JDBC/asyncpg session"
        ],
        "investigation_steps": [
            "Check database active connection metrics: `SELECT count(*) FROM pg_stat_activity;`",
            "Inspect idle-in-transaction connections and blocking locks",
            "Verify current max_connections limit in configmap",
            "Identify top client IP and service holding open pools"
        ],
        "resolution_steps": [
            "1. Patch service ConfigMap to increase POOL_MAX_SIZE from 20 to 50",
            "2. Terminate idle connection sessions exceeding 300 seconds",
            "3. Perform rolling restart of the affected service pods",
            "4. Verify connection acquisition latency drops below 15ms"
        ],
        "cli_commands": [
            {
                "command": "kubectl patch configmap checkout-db-config --patch '{\"data\":{\"DB_POOL_MAX\":\"50\",\"DB_TIMEOUT\":\"5000\"}}' && kubectl rollout restart deployment/checkout-api",
                "description": "Increase connection pool size to 50 and trigger zero-downtime rolling restart",
                "risk": "MEDIUM"
            },
            {
                "command": "psql -h postgres-primary -U postgres -d shopdb -c \"SELECT pid, state, query_start FROM pg_stat_activity WHERE state != 'idle';\"",
                "description": "Inspect currently executing queries and active client connections",
                "risk": "LOW"
            }
        ],
        "verification_steps": [
            "Verify pod status: `kubectl get pods -l app=checkout-api` (all Running/Ready)",
            "Run health check probe: `curl -s -o /dev/null -w '%{http_code}' http://checkout-api.internal/healthz` -> 200",
            "Validate active pool metrics via Prometheus/Grafana: Pool Utilization < 45%",
            "Verify error rate drops from >40% down to 0.00%"
        ],
        "success_count": 14,
        "failure_count": 0
    },
    {
        "code": "K8S-POD-OOM-002",
        "name": "Kubernetes Pod OOMKilled & CrashLoopBackOff",
        "problem_type": "Memory Limit Exceeded / OOMKilled",
        "risk_level": "LOW",
        "symptoms": [
            "Pod terminated with ExitCode 137 (OOMKilled)",
            "Kubernetes events show 'Back-off restarting failed container'",
            "Memory usage graph hits 100% of container limit prior to crash",
            "Intermittent 502/504 Bad Gateway from Ingress controller"
        ],
        "investigation_steps": [
            "Inspect container termination reason via `kubectl describe pod`",
            "Check heap dump and garbage collector metrics in Prometheus",
            "Verify recent container memory limit changes in GitOps repo"
        ],
        "resolution_steps": [
            "1. Temporarily increase memory limit from 1Gi to 2.5Gi",
            "2. Trigger rolling restart to purge stale heap buffers",
            "3. Enable aggressive GC flags in container JVM/Node runtime"
        ],
        "cli_commands": [
            {
                "command": "kubectl set resources deployment/inventory-service --limits=memory=2560Mi --requests=memory=1024Mi && kubectl rollout status deployment/inventory-service",
                "description": "Scale memory limit to 2.5Gi to stop OOM terminations and observe rollout",
                "risk": "LOW"
            }
        ],
        "verification_steps": [
            "Confirm container restart count remains 0 for 5 minutes",
            "Execute synthetic inventory check payload: HTTP 200 response",
            "Monitor memory usage stabilizing at ~55% of the new 2.5Gi limit"
        ],
        "success_count": 11,
        "failure_count": 1
    },
    {
        "code": "REDIS-TIMEOUT-003",
        "name": "Redis Cache Eviction & Connection Saturation",
        "problem_type": "Redis Cache OOM / Latency Spike",
        "risk_level": "MEDIUM",
        "symptoms": [
            "Application logs: 'RedisConnectionException: Command timed out after 3000ms'",
            "User session validation failures across Web and Mobile",
            "Redis memory usage exceeds maxmemory setting",
            "Cache hit ratio drops from 92% to 11%"
        ],
        "investigation_steps": [
            "Run `redis-cli INFO memory` to inspect used_memory vs maxmemory",
            "Check client connection count via `redis-cli CLIENT LIST | wc -l`",
            "Inspect slow queries using `redis-cli SLOWLOG GET 10`"
        ],
        "resolution_steps": [
            "1. Switch Redis eviction policy to allkeys-lru to reclaim idle sessions",
            "2. Increase Redis maxmemory from 4GB to 8GB",
            "3. Flush transient telemetry keys from database 3"
        ],
        "cli_commands": [
            {
                "command": "redis-cli -h redis-cluster.internal -p 6379 CONFIG SET maxmemory-policy allkeys-lru && redis-cli -h redis-cluster.internal -p 6379 CONFIG SET maxmemory 8gb",
                "description": "Adjust eviction policy to LRU and expand memory quota dynamically",
                "risk": "MEDIUM"
            }
        ],
        "verification_steps": [
            "Verify latency: `redis-cli --latency` reports < 1.2ms",
            "Check application session lookups returning HTTP 200 within 4ms"
        ],
        "success_count": 9,
        "failure_count": 0
    },
    {
        "code": "HTTP-503-INGRESS-004",
        "name": "Ingress Controller Upstream Service Unavailable",
        "problem_type": "HTTP 503 Ingress Upstream Saturation",
        "risk_level": "LOW",
        "symptoms": [
            "NGINX Ingress logs: '503 Service Temporarily Unavailable'",
            "Upstream endpoint list in Ingress controller empty or flapping",
            "Target service pods failing readiness probes during peak traffic"
        ],
        "investigation_steps": [
            "Check Kubernetes endpoints: `kubectl get endpoints user-auth-service`",
            "Examine pod readiness probe logs for timeout or connection refused"
        ],
        "resolution_steps": [
            "1. Scale deployment replicas from 3 to 8 pods",
            "2. Relax readiness probe initialDelaySeconds from 5s to 15s"
        ],
        "cli_commands": [
            {
                "command": "kubectl scale deployment/user-auth-service --replicas=8 && kubectl rollout status deployment/user-auth-service",
                "description": "Horizontally scale pods to absorb traffic surge and register ready endpoints",
                "risk": "LOW"
            }
        ],
        "verification_steps": [
            "Verify endpoints populated: `kubectl get endpoints user-auth-service` shows 8 IPs",
            "Ingress 503 error rate drops to 0.0% within 45 seconds"
        ],
        "success_count": 18,
        "failure_count": 0
    },
    {
        "code": "DEPLOY-ROLLBACK-005",
        "name": "Broken Deployment Fast Rollback & Config Reversion",
        "problem_type": "Faulty Release / Bad Config Deployment",
        "risk_level": "HIGH",
        "symptoms": [
            "Incident started immediately after automated CI/CD deployment",
            "NullPointerException or MissingConfigurationKey on container startup",
            "Application healthz returns 500 across 100% of newly launched replicas"
        ],
        "investigation_steps": [
            "Check git commit history and CI/CD release tag",
            "Diff previous configmap values with newly deployed release"
        ],
        "resolution_steps": [
            "1. Rollback deployment to previous stable revision immediately",
            "2. Notify engineering team to lock deployment pipeline"
        ],
        "cli_commands": [
            {
                "command": "kubectl rollout undo deployment/payment-gateway && kubectl rollout status deployment/payment-gateway",
                "description": "Immediate rollback to the previous known good Kubernetes deployment revision",
                "risk": "HIGH"
            }
        ],
        "verification_steps": [
            "Inspect rollout status: revision rolled back successfully",
            "Live transaction processing resumes: 0 payment errors"
        ],
        "success_count": 15,
        "failure_count": 1
    }
]

class RunbookManager:
    """Provides runbook discovery, retrieval, and recommendation"""

    @classmethod
    async def get_all_runbooks(cls) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            stmt = select(Runbook)
            res = await session.execute(stmt)
            runbooks = res.scalars().all()
            return [
                {
                    "id": rb.id,
                    "code": rb.code,
                    "name": rb.name,
                    "problem_type": rb.problem_type,
                    "risk_level": rb.risk_level,
                    "symptoms": json.loads(rb.symptoms or "[]"),
                    "investigation_steps": json.loads(rb.investigation_steps or "[]"),
                    "resolution_steps": json.loads(rb.resolution_steps or "[]"),
                    "cli_commands": json.loads(rb.cli_commands or "[]"),
                    "verification_steps": json.loads(rb.verification_steps or "[]"),
                    "success_count": rb.success_count,
                    "failure_count": rb.failure_count,
                    "success_rate": round(
                        (rb.success_count / (rb.success_count + rb.failure_count) * 100)
                        if (rb.success_count + rb.failure_count) > 0 else 100.0,
                        1
                    )
                }
                for rb in runbooks
            ]

    @classmethod
    async def get_by_code(cls, code: str) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            stmt = select(Runbook).where(Runbook.code == code)
            res = await session.execute(stmt)
            rb = res.scalars().first()
            if not rb:
                return None
            return {
                "id": rb.id,
                "code": rb.code,
                "name": rb.name,
                "problem_type": rb.problem_type,
                "risk_level": rb.risk_level,
                "symptoms": json.loads(rb.symptoms or "[]"),
                "investigation_steps": json.loads(rb.investigation_steps or "[]"),
                "resolution_steps": json.loads(rb.resolution_steps or "[]"),
                "cli_commands": json.loads(rb.cli_commands or "[]"),
                "verification_steps": json.loads(rb.verification_steps or "[]"),
                "success_count": rb.success_count,
                "failure_count": rb.failure_count
            }

    @classmethod
    async def record_outcome(cls, code: str, success: bool):
        async with AsyncSessionLocal() as session:
            stmt = select(Runbook).where(Runbook.code == code)
            res = await session.execute(stmt)
            rb = res.scalars().first()
            if rb:
                if success:
                    rb.success_count += 1
                else:
                    rb.failure_count += 1
                await session.commit()
