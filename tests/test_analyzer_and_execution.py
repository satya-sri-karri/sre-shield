import unittest
import asyncio
from backend.execution.executor import executor
from backend.agents.analyzer import analyzer

class TestAnalyzerAndExecution(unittest.TestCase):

    def test_analyzer_with_and_without_memory(self):
        async def _run():
            analysis = await analyzer.analyze_incident(
                service="Checkout API",
                error_message="HTTP 500 FATAL: remaining connection slots are reserved",
                symptoms="High checkout traffic surge",
                logs="Connection pool exhausted after 30000ms"
            )
            # Memory advantage should be true
            self.assertTrue(analysis["has_memory_advantage"])
            # With memory should recommend DB-CONNECTION-001 with high confidence
            mem_diag = analysis["diagnosis_with_memory"]
            self.assertGreaterEqual(mem_diag["confidence_score"], 0.85)
            self.assertEqual(mem_diag["recommended_runbook_id"], "DB-CONNECTION-001")

            # Without memory should have lower confidence and generic advice
            no_mem_diag = analysis["diagnosis_without_memory"]
            self.assertLessEqual(no_mem_diag["confidence_score"], 0.60)

        asyncio.run(_run())

    def test_safe_execution_simulation(self):
        async def _run():
            res = await executor.execute_and_verify(
                incident_id="INC-1001",
                command_to_run="kubectl patch configmap checkout-db-config --patch '{\"data\":{\"DB_POOL_MAX\":\"50\"}}' && kubectl rollout restart deployment/checkout-api",
                approved_by="Test Suite Runner"
            )
            self.assertEqual(res["status"], "success")
            self.assertTrue(res["simulation_mode"])
            self.assertEqual(res["verification_status"], "PASS")
            self.assertEqual(res["incident_status"], "RESOLVED")

        asyncio.run(_run())

if __name__ == "__main__":
    unittest.main()
