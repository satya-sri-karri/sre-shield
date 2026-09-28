import unittest
from backend.security.sanitizer import MemoryDefenseSanitizer

class TestMemoryDefense(unittest.TestCase):

    def test_password_redaction(self):
        text = "Database failed with password=SuperSecretPassword123! in connection string"
        clean, report = MemoryDefenseSanitizer.sanitize(text)
        self.assertTrue(report["redacted"])
        self.assertIn("password=[REDACTED_SECRET]", clean)
        self.assertNotIn("SuperSecretPassword123!", clean)

    def test_bearer_token_redaction(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeak"
        clean, report = MemoryDefenseSanitizer.sanitize(text)
        self.assertTrue(report["redacted"])
        self.assertIn("Bearer [REDACTED_BEARER_TOKEN]", clean)

    def test_api_key_redaction(self):
        text = "Calling Groq with key gsk_live_99998888777766665555444433332222 failed"
        clean, report = MemoryDefenseSanitizer.sanitize(text)
        self.assertTrue(report["redacted"])
        self.assertIn("[REDACTED_API_KEY]", clean)
        self.assertNotIn("gsk_live_99998888777766665555444433332222", clean)

    def test_aws_key_redaction(self):
        text = "AWS credentials: AKIAIOSFODNN7EXAMPLE"
        clean, report = MemoryDefenseSanitizer.sanitize(text)
        self.assertTrue(report["redacted"])
        self.assertIn("[REDACTED_AWS_KEY_ID]", clean)

if __name__ == "__main__":
    unittest.main()
