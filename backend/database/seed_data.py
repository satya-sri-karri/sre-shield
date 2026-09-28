import json
import datetime
from sqlalchemy import select
from backend.database.models import (
    Incident, Runbook, PostMortem, MemoryExperience, EntitySummary, EvolvingBelief, WorldFact, AuditLog, get_utc_now
)
from backend.database.connection import AsyncSessionLocal
from backend.runbooks.runbook_manager import INITIAL_RUNBOOKS

SAMPLE_INCIDENTS = [
    {
        "id": "INC-1001",
        "title": "Checkout API DB Connection Pool Exhaustion under Flash Sale Traffic",
        "service": "Checkout API",
        "severity": "CRITICAL",
        "status": "RESOLVED",
        "error_message": "HTTP 500 Internal Server Error: org.postgresql.util.PSQLException: FATAL: remaining connection slots are reserved for non-replication superuser connections",
        "symptoms": "Cart checkout failing with HTTP 500. p99 response time jumped from 180ms to 8400ms. Active DB connections peaked at 100/100.",
        "logs": """2026-09-15T14:22:01.104Z [ERROR] [checkout-api-7b89f-2m8q9] [pool-checkout] Connection acquisition timeout after 30000ms
2026-09-15T14:22:01.109Z [FATAL] [checkout-api-7b89f-2m8q9] org.postgresql.util.PSQLException: FATAL: remaining connection slots are reserved for non-replication superuser connections
2026-09-15T14:22:01.115Z [WARN]  [checkout-api-7b89f-4xplk] Circuit breaker [PostgresCheckout] state transitioned to OPEN
2026-09-15T14:22:02.001Z [ERROR] [checkout-api-7b89f-4xplk] Request to /api/v1/checkout failed with status 500""",
        "deployment_info": "Deployment checkout-api v2.4.1 rolled out 20 mins prior with default pool size 20.",
        "root_cause": "Database connection pool exhaustion caused by high concurrency flash sale traffic exceeding the uncalibrated pool limit (20 connections per pod), while idle sessions were not terminating promptly.",
        "suggested_action": "Increase DB connection pool size from 20 to 50 in ConfigMap, terminate leaked idle connections, and perform zero-downtime rolling restart.",
        "suggested_command": "kubectl patch configmap checkout-db-config --patch '{\"data\":{\"DB_POOL_MAX\":\"50\",\"DB_TIMEOUT\":\"5000\"}}' && kubectl rollout restart deployment/checkout-api",
        "risk_level": "MEDIUM",
        "confidence_score": 0.96,
        "recommended_runbook_id": "DB-CONNECTION-001",
        "execution_status": "VERIFIED",
        "execution_output": "ConfigMap patched successfully. Deployment checkout-api rolling restart complete. 4/4 pods Ready.",
        "verification_status": "PASS",
        "verification_output": "Health probe /healthz returned 200 OK. Connection pool saturation dropped to 32%. HTTP 500 error rate returned to 0.00%.",
        "mttr_seconds": 720, # 12 mins
        "days_ago": 13,
        "post_mortem": {
            "summary": "Major flash sale event overwhelmed the default PostgreSQL connection pool of Checkout API, causing cascading 500 errors across the store.",
            "impact": "4,120 customers experienced checkout failures over a 12-minute window. Revenue loss estimated at $18,400.",
            "timeline": json.dumps([
                {"time": "14:20", "event": "Traffic spiked by 380% due to push notification blast"},
                {"time": "14:22", "event": "Postgres connection pool exhausted; HTTP 500 error rate hit 46%"},
                {"time": "14:24", "event": "SRE-Shield alerted engineer with similar historical pattern"},
                {"time": "14:26", "event": "Approved and executed pool expansion patch and rolling restart"},
                {"time": "14:32", "event": "All 4 pods healthy, connection acquisition latency < 12ms, incident resolved"}
            ]),
            "root_cause": "Connection pool was hardcoded to 20 connections in checkout-db-config. Under flash sale spikes, all 20 connections were held by slow payment verification RPCs.",
            "resolution": "Updated DB_POOL_MAX to 50, added 5s idle connection timeout, and rolled out restart.",
            "commands_used": json.dumps([
                "kubectl patch configmap checkout-db-config --patch '{\"data\":{\"DB_POOL_MAX\":\"50\",\"DB_TIMEOUT\":\"5000\"}}'",
                "kubectl rollout restart deployment/checkout-api"
            ]),
            "what_worked": "Rapid ConfigMap patch without full redeployment; SRE-Shield memory recall accurately isolated the pool exhaustion within 60 seconds.",
            "what_failed": "Alert fired 2 minutes after users already saw failures. Autoscaling was disabled during the sale window.",
            "prevention": "Enable Horizontal Pod Autoscaler with DB pool capacity safety governor and load test up to 30,000 rps.",
            "recommended_monitoring": "Add Datadog / Prometheus alert when pool utilization exceeds 75% for 60 seconds.",
            "lessons_learned": "Never scale worker threads without proportionally checking downstream database max_connections."
        }
    },
    {
        "id": "INC-1002",
        "title": "Inventory Service CrashLoopBackOff due to JVM Heap OOMKilled",
        "service": "Inventory Service",
        "severity": "HIGH",
        "status": "RESOLVED",
        "error_message": "Kubernetes Pod OOMKilled (Exit Code 137) - container memory limit 1024Mi exceeded",
        "symptoms": "Inventory lookup pods dying repeatedly. Exit code 137. Sync batches failing.",
        "logs": """2026-09-17T09:12:44Z [INFO] java.lang.OutOfMemoryError: Java heap space
2026-09-17T09:12:45Z [WARN] Container inventory-worker terminated: OOMKilled (Exit Code 137)
2026-09-17T09:12:50Z [ERROR] Back-off restarting failed container in pod inventory-service-789bc-99x2q""",
        "deployment_info": "Batch catalog sync job introduced large unpaginated SQL query.",
        "root_cause": "A newly deployed batch sync job attempted to load 250,000 inventory items into memory at once, exceeding the 1024Mi container limit.",
        "suggested_action": "Scale container memory limit to 2560Mi and enforce JVM max heap fraction.",
        "suggested_command": "kubectl set resources deployment/inventory-service --limits=memory=2560Mi --requests=memory=1024Mi && kubectl rollout status deployment/inventory-service",
        "risk_level": "LOW",
        "confidence_score": 0.94,
        "recommended_runbook_id": "K8S-POD-OOM-002",
        "execution_status": "VERIFIED",
        "execution_output": "deployment.apps/inventory-service resource requirements updated. Rollout successful.",
        "verification_status": "PASS",
        "verification_output": "Container memory stabilized at 1.4Gi. Pod restarts stopped.",
        "mttr_seconds": 480,
        "days_ago": 11,
        "post_mortem": {
            "summary": "Inventory Service crashed during morning catalog sync due to unpaginated query loading entire product table.",
            "impact": "Warehouse fulfillment dispatch delayed by 18 minutes.",
            "timeline": json.dumps([{"time": "09:10", "event": "Catalog sync started"}, {"time": "09:12", "event": "OOMKilled pod crash"}, {"time": "09:18", "event": "Memory limit bumped and verified"}]),
            "root_cause": "Heap memory exhaustion from unpaginated query.",
            "resolution": "Increased container memory limit to 2.5Gi and patched pagination in repository layer.",
            "commands_used": json.dumps(["kubectl set resources deployment/inventory-service --limits=memory=2560Mi"]),
            "what_worked": "Kubernetes resource bump without code rollback.",
            "what_failed": "Lack of query pagination in v3.1 batch job.",
            "prevention": "Enforce static analysis rule against `findAll()` on tables over 10k rows.",
            "recommended_monitoring": "JVM Heap Utilization > 85% alert.",
            "lessons_learned": "Container limits must provide 30% headroom over average heap usage."
        }
    },
    {
        "id": "INC-1003",
        "title": "Redis Cluster Eviction Failure Causing Authentication Session Timeouts",
        "service": "Redis Cache",
        "severity": "HIGH",
        "status": "RESOLVED",
        "error_message": "RedisConnectionException: Command timed out after 3000ms: OOM command not allowed when used memory > 'maxmemory'",
        "symptoms": "Users logged out across frontend. Token refresh endpoints timing out with 504.",
        "logs": """2026-09-19T03:40:11Z [redis-node-1] # Out of memory allocating 16384 bytes!
2026-09-19T03:40:12Z [redis-node-1] # maxmemory-policy is 'noeviction'. Refusing writes!
2026-09-19T03:40:15Z [auth-service] [ERROR] RedisConnectionException: Command timed out after 3000ms""",
        "deployment_info": "Redis cluster migration to node group b-2 completed yesterday.",
        "root_cause": "Redis maxmemory-policy was inadvertently configured to 'noeviction' instead of 'allkeys-lru' during node migration.",
        "suggested_action": "Dynamically switch eviction policy to allkeys-lru and expand maxmemory to 8GB.",
        "suggested_command": "redis-cli -h redis-cluster.internal -p 6379 CONFIG SET maxmemory-policy allkeys-lru && redis-cli -h redis-cluster.internal -p 6379 CONFIG SET maxmemory 8gb",
        "risk_level": "MEDIUM",
        "confidence_score": 0.98,
        "recommended_runbook_id": "REDIS-TIMEOUT-003",
        "execution_status": "VERIFIED",
        "execution_output": "OK. Eviction policy updated to allkeys-lru. 1.2GB stale sessions reclaimed.",
        "verification_status": "PASS",
        "verification_output": "Redis latency 0.8ms. Authentication token validations succeeding 100%.",
        "mttr_seconds": 360,
        "days_ago": 9,
        "post_mortem": {
            "summary": "Redis stopped accepting writes because maxmemory was reached with noeviction policy.",
            "impact": "2,800 active sessions disconnected.",
            "timeline": json.dumps([{"time": "03:40", "event": "Memory reached 4GB limit"}, {"time": "03:43", "event": "Switched policy to allkeys-lru"}, {"time": "03:46", "event": "Sessions restored"}]),
            "root_cause": "Terraform default parameter group had maxmemory-policy=noeviction.",
            "resolution": "Updated config to allkeys-lru and increased memory to 8GB.",
            "commands_used": json.dumps(["redis-cli CONFIG SET maxmemory-policy allkeys-lru"]),
            "what_worked": "Online live CONFIG SET with zero Redis restart downtime.",
            "what_failed": "Terraform drift detection did not catch the default parameter group.",
            "prevention": "Lock Redis config via GitOps IaC compliance checks.",
            "recommended_monitoring": "Alert when Redis memory reaches 80% of maxmemory.",
            "lessons_learned": "Always enforce TTL on cache keys and verify eviction policies in staging."
        }
    },
    {
        "id": "INC-1004",
        "title": "User Auth Service HTTP 503 Ingress Upstream Saturation",
        "service": "User Auth Service",
        "severity": "HIGH",
        "status": "RESOLVED",
        "error_message": "HTTP 503 Service Temporarily Unavailable - NGINX Ingress controller no healthy upstream",
        "symptoms": "Login and signup pages showing 503 Service Unavailable. Pods CPU pinned at 98%.",
        "logs": """2026-09-20T18:05:01Z [ingress-nginx] [error] 4821#4821: *19284210 upstream timed out while connecting to upstream
2026-09-20T18:05:03Z [ingress-nginx] [warn] user-auth-service endpoint 10.244.2.42:8080 marked as UNHEALTHY
2026-09-20T18:05:04Z [ingress-nginx] 503 Service Temporarily Unavailable""",
        "deployment_info": "End of month payroll cycle triggered sudden login spike.",
        "root_cause": "Authentication service replicas were fixed at 3 pods, inadequate for 4x peak traffic during end-of-month logins.",
        "suggested_action": "Horizontally scale deployment to 8 pods immediately.",
        "suggested_command": "kubectl scale deployment/user-auth-service --replicas=8 && kubectl rollout status deployment/user-auth-service",
        "risk_level": "LOW",
        "confidence_score": 0.95,
        "recommended_runbook_id": "HTTP-503-INGRESS-004",
        "execution_status": "VERIFIED",
        "execution_output": "deployment.apps/user-auth-service scaled to 8 replicas. All pods ready.",
        "verification_status": "PASS",
        "verification_output": "Ingress upstream endpoints healthy. 503 error rate dropped to 0%.",
        "mttr_seconds": 300,
        "days_ago": 8,
        "post_mortem": {
            "summary": "Sudden traffic spike overwhelmed 3 auth pods, triggering Ingress 503 errors.",
            "impact": "1,200 users experienced temporary login delays for 5 minutes.",
            "timeline": json.dumps([{"time": "18:03", "event": "CPU spiked to 98%"}, {"time": "18:05", "event": "Ingress reported 503s"}, {"time": "18:08", "event": "Scaled to 8 replicas, service restored"}]),
            "root_cause": "Insufficient pod replicas and absence of HorizontalPodAutoscaler.",
            "resolution": "Scaled pods from 3 to 8.",
            "commands_used": json.dumps(["kubectl scale deployment/user-auth-service --replicas=8"]),
            "what_worked": "Fast horizontal scaling resolved upstream saturation in seconds.",
            "what_failed": "Manual scaling was required because HPA was misconfigured.",
            "prevention": "Configured HPA with target CPU 65% and min replicas 5.",
            "recommended_monitoring": "Alert when Ingress 5xx rate > 1% over 1 minute.",
            "lessons_learned": "Always provision autoscaling before predictable end-of-month peaks."
        }
    },
    {
        "id": "INC-1005",
        "title": "Payment Gateway v4.2 Release Startup Crash due to Missing Stripe API Key Secret",
        "service": "Payment Gateway",
        "severity": "CRITICAL",
        "status": "RESOLVED",
        "error_message": "Deployment Failure: Application startup failed - IllegalStateException: Missing required environment variable 'STRIPE_WEBHOOK_SECRET'",
        "symptoms": "All new pods in CrashLoopBackOff immediately following CI/CD deploy. 100% of checkout payments failing.",
        "logs": """2026-09-22T11:15:30Z [payment-gateway-69d8-p01] ERROR: Spring Application failed to start
2026-09-22T11:15:30Z [payment-gateway-69d8-p01] java.lang.IllegalStateException: Missing required secret 'STRIPE_WEBHOOK_SECRET'
2026-09-22T11:15:32Z [kubelet] Container failed liveness probe, restarting...""",
        "deployment_info": "Automated deployment pipeline pushed image tag `payment-gateway:v4.2.0` at 11:14Z.",
        "root_cause": "The v4.2.0 release required a new secret 'STRIPE_WEBHOOK_SECRET' which had not yet been provisioned in the production Kubernetes secret store.",
        "suggested_action": "Execute immediate rollback to previous stable deployment revision v4.1.2.",
        "suggested_command": "kubectl rollout undo deployment/payment-gateway && kubectl rollout status deployment/payment-gateway",
        "risk_level": "HIGH",
        "confidence_score": 0.99,
        "recommended_runbook_id": "DEPLOY-ROLLBACK-005",
        "execution_status": "VERIFIED",
        "execution_output": "Rollback to revision 41 successful. Pods running stable image v4.1.2.",
        "verification_status": "PASS",
        "verification_output": "Live transaction test passed. 0 payment errors.",
        "mttr_seconds": 240,
        "days_ago": 6,
        "post_mortem": {
            "summary": "Payment Gateway crashed on boot due to missing secret in production K8s namespace.",
            "impact": "Zero payments processed for 4 minutes during mid-day shopping.",
            "timeline": json.dumps([{"time": "11:14", "event": "v4.2.0 deployed"}, {"time": "11:15", "event": "All pods crashed"}, {"time": "11:17", "event": "Rollout undone, v4.1.2 active"}]),
            "root_cause": "Code depended on new secret before secret was applied to cluster.",
            "resolution": "Rolled back deployment revision to v4.1.2.",
            "commands_used": json.dumps(["kubectl rollout undo deployment/payment-gateway"]),
            "what_worked": "Kubernetes rollback undo command executed cleanly within 30 seconds.",
            "what_failed": "Pre-flight deploy check did not validate presence of required secrets.",
            "prevention": "Implement CI/CD secret validation pre-check step in GitHub Actions workflow.",
            "recommended_monitoring": "Deploy pipeline failure alert and pod crash alert.",
            "lessons_learned": "Never deploy code expecting new secrets before secrets are verified in the target namespace."
        }
    },
    {
        "id": "INC-1006",
        "title": "Order Processing Service Kafka Consumer Group Rebalance Storm",
        "service": "Order Processing",
        "severity": "HIGH",
        "status": "RESOLVED",
        "error_message": "CommitFailedException: Commit cannot be completed since the group has already rebalanced and assigned the partitions to another member",
        "symptoms": "Order fulfillment queue lagging by 15,000 messages. Processing latency 45 mins.",
        "logs": """2026-09-23T16:20:00Z [order-worker-1] CommitFailedException: Max poll interval 300000ms exceeded!
2026-09-23T16:20:05Z [kafka-coordinator] PreparingRebalance: consumer order-worker-1 left group 'orders-consumer'
2026-09-23T16:20:12Z [order-worker-2] Partitions revoked: [orders-topic-0, orders-topic-1]""",
        "deployment_info": "Heavy image processing step added to synchronous order pipeline.",
        "root_cause": "A slow synchronous PDF invoice generator caused message processing time to exceed max.poll.interval.ms, causing Kafka to assume the consumer was dead and triggering infinite rebalance loops.",
        "suggested_action": "Increase max.poll.interval.ms from 300s to 900s and lower max.poll.records to 50.",
        "suggested_command": "kubectl patch configmap order-worker-config --patch '{\"data\":{\"KAFKA_MAX_POLL_INTERVAL_MS\":\"900000\",\"KAFKA_MAX_POLL_RECORDS\":\"50\"}}' && kubectl rollout restart deployment/order-worker",
        "risk_level": "MEDIUM",
        "confidence_score": 0.93,
        "recommended_runbook_id": "DB-CONNECTION-001", # or similar
        "execution_status": "VERIFIED",
        "execution_output": "ConfigMap updated. Consumer group rebalances stabilized. All 12 partitions actively consumed.",
        "verification_status": "PASS",
        "verification_output": "Lag decreased from 15,000 to 120 messages in 4 minutes.",
        "mttr_seconds": 600,
        "days_ago": 5,
        "post_mortem": {
            "summary": "Kafka consumer rebalance storm caused by synchronous invoice generation exceeding poll interval.",
            "impact": "15,000 order fulfillments delayed by 30 minutes.",
            "timeline": json.dumps([{"time": "16:20", "event": "Rebalance storm started"}, {"time": "16:26", "event": "Applied config patch"}, {"time": "16:30", "event": "Queue drained"}]),
            "root_cause": "PDF invoice generation took 350s on complex orders, exceeding 300s poll timeout.",
            "resolution": "Bumped poll timeout to 900s and moved invoice generation to async queue.",
            "commands_used": json.dumps(["kubectl patch configmap order-worker-config"]),
            "what_worked": "Tunable poll parameters halted the rebalancing loop.",
            "what_failed": "Synchronous CPU-intensive workload in Kafka stream consumer thread.",
            "prevention": "Offload CPU intensive tasks to decoupled Celery/BullMQ workers.",
            "recommended_monitoring": "Kafka consumer lag alert > 500 messages.",
            "lessons_learned": "Never perform heavy I/O or PDF generation inside a Kafka poll loop."
        }
    },
    {
        "id": "INC-1007",
        "title": "Postgres Read-Replica Disk Space Exhaustion by Wal Logs",
        "service": "Database Cluster",
        "severity": "CRITICAL",
        "status": "RESOLVED",
        "error_message": "PANIC: could not write to file 'pg_wal/xlogtemp.1924': No space left on device",
        "symptoms": "Read replica shut down. All read-only reporting and search queries routed to master, causing master CPU to spike to 100%.",
        "logs": """2026-09-24T08:00:15Z [postgres-replica-1] PANIC: could not write to file 'pg_wal/xlogtemp.1924': No space left on device
2026-09-24T08:00:16Z [postgres-replica-1] LOG: database system was interrupted; startup will proceed
2026-09-24T08:00:20Z [postgres-primary] WARNING: replication slot 'replica_1' is inactive, accumulating WAL files""",
        "deployment_info": "Automated WAL archive script had permission failure on S3 bucket.",
        "root_cause": "WAL archive script hung due to an expired IAM role token, causing WAL files to accumulate on disk until the 200GB volume was 100% full.",
        "suggested_action": "Expand EBS volume to 400GB and purge verified archived WAL segments.",
        "suggested_command": "aws ec2 modify-volume --volume-id vol-0a1b2c3d4e5f6g --size 400 && pg_archivecleanup /var/lib/postgresql/data/pg_wal 000000010000019A00000042",
        "risk_level": "HIGH",
        "confidence_score": 0.97,
        "recommended_runbook_id": "DB-CONNECTION-001",
        "execution_status": "VERIFIED",
        "execution_output": "Volume resized to 400GB. Filesystem grown online. 48GB expired WAL cleaned.",
        "verification_status": "PASS",
        "verification_output": "Postgres replica running. Replication lag < 200ms. Master CPU dropped to 22%.",
        "mttr_seconds": 900,
        "days_ago": 4,
        "post_mortem": {
            "summary": "Database read replica ran out of disk space due to accumulated WAL segments.",
            "impact": "Search queries degraded for 15 minutes as load shifted to primary DB.",
            "timeline": json.dumps([{"time": "08:00", "event": "Disk 100% full, replica crashed"}, {"time": "08:08", "event": "EBS volume resized and WAL purged"}, {"time": "08:15", "event": "Replica caught up"}]),
            "root_cause": "Expired S3 IAM role stopped WAL archiving.",
            "resolution": "Resized disk volume and restored IAM role permissions.",
            "commands_used": json.dumps(["aws ec2 modify-volume", "pg_archivecleanup"]),
            "what_worked": "Online AWS EBS volume expansion without reboot.",
            "what_failed": "Disk space alert was set too high (95% instead of 80%).",
            "prevention": "Lower disk alert threshold to 75% and automate WAL cleanups.",
            "recommended_monitoring": "Disk usage > 75% alert and S3 archive heartbeat check.",
            "lessons_learned": "Monitor replication slot lag and WAL directory growth rates actively."
        }
    },
    {
        "id": "INC-1008",
        "title": "API Gateway TLS Certificate Expired Leading to Worldwide 526 Errors",
        "service": "API Gateway",
        "severity": "CRITICAL",
        "status": "RESOLVED",
        "error_message": "SSL_ERROR_EXPIRED_CERT_ALERT: SSL certificate expired on Sun, 27 Sep 2026 00:00:00 GMT",
        "symptoms": "All external mobile and web clients seeing TLS handshake failures. Ingress returning Cloudflare 526 Invalid SSL.",
        "logs": """2026-09-27T00:01:05Z [ingress-controller] SSL handshake failed: Certificate has expired
2026-09-27T00:01:10Z [cert-manager] Order api-cert-prod failed: ACME challenge DNS authorization timed out""",
        "deployment_info": "Cert-manager renewal cron job failed due to rate limit on Let's Encrypt DNS challenge.",
        "root_cause": "Cert-manager automated renewal failed silently due to changed Route53 IAM permissions, allowing the certificate to expire at midnight.",
        "suggested_action": "Force cert-manager certificate renewal using HTTP-01 challenge solver.",
        "suggested_command": "kubectl cert-manager renew api-tls-cert --namespace production",
        "risk_level": "LOW",
        "confidence_score": 0.99,
        "recommended_runbook_id": "DEPLOY-ROLLBACK-005",
        "execution_status": "VERIFIED",
        "execution_output": "Certificate api-tls-cert issued and synced to Ingress controller secret.",
        "verification_status": "PASS",
        "verification_output": "OpenSSL verification: Valid until 2026-12-26. 0 TLS handshake errors.",
        "mttr_seconds": 360,
        "days_ago": 1,
        "post_mortem": {
            "summary": "Production SSL certificate expired because cert-manager renewal failed silently.",
            "impact": "Full external traffic outage for 6 minutes.",
            "timeline": json.dumps([{"time": "00:00", "event": "Certificate expired"}, {"time": "00:02", "event": "SRE paged"}, {"time": "00:06", "event": "Forced renewal succeeded"}]),
            "root_cause": "Route53 DNS challenge permission denied; cert-manager retry loop was exhausted.",
            "resolution": "Triggered manual cert-manager renewal using HTTP solver fallback.",
            "commands_used": json.dumps(["kubectl cert-manager renew api-tls-cert"]),
            "what_worked": "Cert-manager CLI renewal command restored cert in 60s.",
            "what_failed": "Renewal failure 30 days prior had no alerting.",
            "prevention": "Set alert for any TLS cert with <= 14 days until expiration.",
            "recommended_monitoring": "External synthetic probe checking certificate expiration dates daily.",
            "lessons_learned": "Never rely solely on automated cert renewal without monitoring the certificate expiration cliff."
        }
    }
]

async def seed_database():
    """Seeds runbooks, incidents, and Hindsight 4-Network memories if database is empty"""
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        res = await session.execute(select(Runbook))
        existing_runbooks = res.scalars().all()
        if existing_runbooks:
            return # Already seeded

        now = get_utc_now()

        # 1. Seed Runbooks
        for rb_data in INITIAL_RUNBOOKS:
            rb = Runbook(
                id=f"RB-{rb_data['code']}",
                code=rb_data["code"],
                name=rb_data["name"],
                problem_type=rb_data["problem_type"],
                symptoms=json.dumps(rb_data["symptoms"]),
                investigation_steps=json.dumps(rb_data["investigation_steps"]),
                resolution_steps=json.dumps(rb_data["resolution_steps"]),
                cli_commands=json.dumps(rb_data["cli_commands"]),
                verification_steps=json.dumps(rb_data["verification_steps"]),
                risk_level=rb_data["risk_level"],
                success_count=rb_data["success_count"],
                failure_count=rb_data["failure_count"],
                created_at=now - datetime.timedelta(days=30)
            )
            session.add(rb)

        # 2. Seed Incidents and Post-Mortems
        for inc_data in SAMPLE_INCIDENTS:
            created_time = now - datetime.timedelta(days=inc_data.get("days_ago", 5), hours=3)
            resolved_time = created_time + datetime.timedelta(seconds=inc_data["mttr_seconds"])

            inc = Incident(
                id=inc_data["id"],
                title=inc_data["title"],
                service=inc_data["service"],
                severity=inc_data["severity"],
                status=inc_data["status"],
                error_message=inc_data["error_message"],
                symptoms=inc_data["symptoms"],
                logs=inc_data["logs"],
                deployment_info=inc_data["deployment_info"],
                root_cause=inc_data["root_cause"],
                suggested_action=inc_data["suggested_action"],
                suggested_command=inc_data["suggested_command"],
                risk_level=inc_data["risk_level"],
                confidence_score=inc_data["confidence_score"],
                recommended_runbook_id=inc_data["recommended_runbook_id"],
                similar_incident_ids="[]",
                reasoning_explanation="Diagnosed based on historical matching and pattern analysis.",
                approved_by="Lead SRE (Automated Demo)",
                approved_at=created_time + datetime.timedelta(minutes=3),
                execution_status=inc_data["execution_status"],
                execution_output=inc_data["execution_output"],
                verification_status=inc_data["verification_status"],
                verification_output=inc_data["verification_output"],
                mttr_seconds=inc_data["mttr_seconds"],
                created_at=created_time,
                resolved_at=resolved_time
            )
            session.add(inc)

            # Post-Mortem
            pm_data = inc_data["post_mortem"]
            pm = PostMortem(
                id=f"PM-{inc_data['id']}",
                incident_id=inc_data["id"],
                title=f"Post-Mortem: {inc_data['title']}",
                summary=pm_data["summary"],
                impact=pm_data["impact"],
                timeline=pm_data["timeline"],
                root_cause=pm_data["root_cause"],
                resolution=pm_data["resolution"],
                commands_used=pm_data["commands_used"],
                what_worked=pm_data["what_worked"],
                what_failed=pm_data["what_failed"],
                prevention=pm_data["prevention"],
                recommended_monitoring=pm_data["recommended_monitoring"],
                lessons_learned=pm_data["lessons_learned"],
                is_approved=True,
                approved_by="Principal SRE",
                created_at=resolved_time,
                approved_at=resolved_time + datetime.timedelta(hours=2)
            )
            session.add(pm)

            # Hindsight Network 1: MemoryExperience (Experience Network)
            search_corpus = (
                f"Service: {inc_data['service']}\n"
                f"Error: {inc_data['error_message']}\n"
                f"Symptoms: {inc_data['symptoms']}\n"
                f"Logs: {inc_data['logs']}\n"
                f"Root Cause: {inc_data['root_cause']}\n"
                f"Resolution: {inc_data['suggested_action']}\n"
                f"Lessons: {pm_data['lessons_learned']}"
            )
            exp = MemoryExperience(
                id=f"EXP-{inc_data['id']}",
                incident_id=inc_data["id"],
                service=inc_data["service"],
                error_signature=inc_data["error_message"][:250],
                symptoms=inc_data["symptoms"],
                root_cause=inc_data["root_cause"],
                resolution_strategy=inc_data["suggested_action"],
                successful_commands=pm_data["commands_used"],
                failed_commands="[]",
                runbook_code=inc_data["recommended_runbook_id"],
                outcome="SUCCESS",
                post_mortem_summary=pm_data["summary"],
                search_text=search_corpus,
                confidence_weight=1.0,
                recall_count=2,
                created_at=resolved_time
            )
            session.add(exp)

        # 3. Hindsight Network 2: Entity Summaries
        entities = [
            {
                "name": "Checkout API",
                "type": "SERVICE",
                "summary": "High-throughput e-commerce checkout service. Prone to database connection pool starvation under traffic surges (>15,000 rps). Requires pool size >= 50 and 5s idle connection timeouts.",
                "failure_modes": ["Database connection pool exhaustion", "Payment gateway RPC timeout", "Thread starvation"],
                "runbooks": ["DB-CONNECTION-001"],
                "total": 3,
                "mttr": 12.0
            },
            {
                "name": "Inventory Service",
                "type": "SERVICE",
                "summary": "Catalog stock and reservation service. JVM memory footprint is vulnerable to unpaginated bulk queries during warehouse sync.",
                "failure_modes": ["JVM Heap OOMKilled", "Unpaginated query heap bloat"],
                "runbooks": ["K8S-POD-OOM-002"],
                "total": 2,
                "mttr": 8.0
            },
            {
                "name": "Redis Cache",
                "type": "CACHE",
                "summary": "Cluster-wide distributed session and token cache. Must maintain allkeys-lru eviction policy and at least 8GB memory.",
                "failure_modes": ["OOM command not allowed", "Noeviction lockup", "Connection timeout"],
                "runbooks": ["REDIS-TIMEOUT-003"],
                "total": 1,
                "mttr": 6.0
            },
            {
                "name": "Payment Gateway",
                "type": "GATEWAY",
                "summary": "External payment processor integration. Highly sensitive to secret provisioning and mTLS cert expiration.",
                "failure_modes": ["Missing configuration secret", "Upstream TLS handshake failure"],
                "runbooks": ["DEPLOY-ROLLBACK-005"],
                "total": 2,
                "mttr": 4.0
            }
        ]
        for ent in entities:
            es = EntitySummary(
                id=f"ENT-{ent['name'].replace(' ', '_').upper()}",
                entity_name=ent["name"],
                entity_type=ent["type"],
                summary=ent["summary"],
                known_failure_modes=json.dumps(ent["failure_modes"]),
                preferred_runbooks=json.dumps(ent["runbooks"]),
                total_incidents=ent["total"],
                avg_mttr_minutes=ent["mttr"],
                updated_at=now
            )
            session.add(es)

        # 4. Hindsight Network 3: Evolving Beliefs
        beliefs = [
            {
                "domain": "Database",
                "statement": "When Checkout API reports HTTP 500 with 'pool exhausted', increasing pool size without restarting the deployment causes dangling sessions; always execute patch and rollout restart together.",
                "confidence": 0.96,
                "count": 4
            },
            {
                "domain": "Kubernetes",
                "statement": "Container Exit Code 137 is invariably OOMKilled; bumping memory limit by 2.5x immediately stops CrashLoopBackOff before deep heap analysis.",
                "confidence": 0.94,
                "count": 3
            },
            {
                "domain": "Caching",
                "statement": "Redis command timeouts during peak hours are 90% caused by maxmemory saturation with noeviction policy rather than network partitions.",
                "confidence": 0.92,
                "count": 2
            },
            {
                "domain": "Deployments",
                "statement": "Startup crashes within 5 minutes of a deployment rollout indicate missing environment secrets or schema mismatches; fast rollback has 100% MTTR superiority over live debugging.",
                "confidence": 0.98,
                "count": 5
            }
        ]
        for b in beliefs:
            eb = EvolvingBelief(
                id=f"BEL-{b['domain'].upper()}",
                domain=b["domain"],
                belief_statement=b["statement"],
                confidence=b["confidence"],
                supporting_incident_count=b["count"],
                created_at=now - datetime.timedelta(days=20),
                updated_at=now
            )
            session.add(eb)

        # 5. Hindsight Network 4: World Facts
        facts = [
            {"cat": "LIMIT", "subj": "Checkout API", "fact": "Checkout API production PostgreSQL pool maximum is 50 connections across 4 pods (200 total max on primary DB)."},
            {"cat": "SLO", "subj": "Checkout API", "fact": "Checkout API 99.9% availability SLO: error rate must stay below 0.1% over a 30-day rolling window."},
            {"cat": "TOPOLOGY", "subj": "Payment Gateway", "fact": "Payment Gateway communicates directly with Stripe and Adyen over mTLS via egress NAT gateway."},
            {"cat": "DEPENDENCY", "subj": "User Auth Service", "fact": "User Auth Service depends strictly on Redis Cluster for OAuth2 token validation."}
        ]
        for f in facts:
            wf = WorldFact(
                id=f"WF-{f['subj'].replace(' ', '_').upper()}-{f['cat']}",
                category=f["cat"],
                subject=f["subj"],
                fact_statement=f["fact"],
                created_at=now - datetime.timedelta(days=30)
            )
            session.add(wf)

        await session.commit()
