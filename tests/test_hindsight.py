import unittest
import asyncio
from backend.memory.hindsight_engine import hindsight

class TestHindsightMemory(unittest.TestCase):

    def test_recall_and_reflect(self):
        async def _test():
            await hindsight.initialize()
            res = await hindsight.recall(
                query_service="Checkout API",
                error_message="HTTP 500 connection pool exhausted",
                top_k=2
            )
            self.assertTrue(res["has_matches"])
            self.assertIsNotNone(res["top_match"])
            self.assertEqual(res["top_match"]["incident_id"], "INC-1001")
            self.assertIn("connection pool", res["top_match"]["root_cause"].lower())

            # Test reflect
            reflect_res = await hindsight.reflect(service_name="Checkout API")
            self.assertEqual(reflect_res["status"], "reflected")

        asyncio.run(_test())

if __name__ == "__main__":
    unittest.main()
