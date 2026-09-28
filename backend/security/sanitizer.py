import re
from typing import Dict, Any, Tuple, List

class MemoryDefenseSanitizer:
    """
    Sanitization layer that detects and masks sensitive information
    before storing logs, incident data, or command output in persistent memory.
    """

    # Compiled patterns for high performance
    PATTERNS = [
        # Passwords in key-value format (password=..., "password": "...", etc.)
        (
            re.compile(r'(?i)(password|passwd|pwd|db_pass|secret_key|api_secret|auth_token)\s*[:=]\s*["\']?([^"\'\s,;]+)["\']?'),
            r'\1=[REDACTED_SECRET]'
        ),
        # Basic auth URLs: http(s)://user:pass@host
        (
            re.compile(r'(https?://[^:]+:)([^@]+)(@)'),
            r'\1[REDACTED_AUTH]\3'
        ),
        # Bearer tokens & JWTs
        (
            re.compile(r'(?i)bearer\s+[a-zA-Z0-9_\-\.=]{15,}'),
            'Bearer [REDACTED_BEARER_TOKEN]'
        ),
        (
            re.compile(r'\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b'),
            '[REDACTED_JWT_TOKEN]'
        ),
        # API Keys (Generic, OpenAI, Groq, GitHub, Slack, AWS)
        (
            re.compile(r'\b(gsk_[a-zA-Z0-9_]{20,}|sk-[a-zA-Z0-9_\-]{20,}|ghp_[a-zA-Z0-9]{36}|xox[baprs]-[a-zA-Z0-9\-]{10,})\b'),
            '[REDACTED_API_KEY]'
        ),
        # AWS Access Key ID
        (
            re.compile(r'\b(AKIA[0-9A-Z]{16})\b'),
            '[REDACTED_AWS_KEY_ID]'
        ),
        # Private Keys
        (
            re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
            '[REDACTED_PRIVATE_KEY_BLOCK]'
        ),
        # Credit Card Numbers
        (
            re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            '[REDACTED_CREDIT_CARD]'
        ),
        # Email Addresses (PII)
        (
            re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'),
            '[REDACTED_EMAIL]'
        ),
        # Connection strings with credentials
        (
            re.compile(r'(postgres(?:ql)?|mysql|mongodb|redis)://([^:]+):([^@]+)@'),
            r'\1://\2:[REDACTED_PASSWORD]@'
        )
    ]

    @classmethod
    def sanitize(cls, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Sanitizes text and returns the cleaned text along with a detailed report
        of redacted items.
        """
        if not text:
            return "", {"redacted": False, "redaction_count": 0, "categories": []}

        sanitized = text
        redaction_count = 0
        categories: List[str] = []

        for pattern, replacement in cls.PATTERNS:
            matches = list(pattern.finditer(sanitized))
            if matches:
                redaction_count += len(matches)
                # Infer category from replacement string
                cat = replacement.split('[REDACTED_')[-1].split(']')[0] if '[REDACTED_' in replacement else 'SECRET'
                if cat not in categories:
                    categories.append(cat)
                sanitized = pattern.sub(replacement, sanitized)

        report = {
            "redacted": redaction_count > 0,
            "redaction_count": redaction_count,
            "categories": categories,
            "original_length": len(text),
            "sanitized_length": len(sanitized)
        }
        return sanitized, report

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Recursively sanitizes dictionary strings.
        """
        clean_data = {}
        total_redactions = 0
        all_categories = set()

        for k, v in data.items():
            if isinstance(v, str):
                cleaned_str, rep = cls.sanitize(v)
                clean_data[k] = cleaned_str
                total_redactions += rep["redaction_count"]
                all_categories.update(rep["categories"])
            elif isinstance(v, dict):
                cleaned_sub, rep = cls.sanitize_dict(v)
                clean_data[k] = cleaned_sub
                total_redactions += rep["redaction_count"]
                all_categories.update(rep["categories"])
            elif isinstance(v, list):
                cleaned_list = []
                for item in v:
                    if isinstance(item, str):
                        c_str, rep = cls.sanitize(item)
                        cleaned_list.append(c_str)
                        total_redactions += rep["redaction_count"]
                        all_categories.update(rep["categories"])
                    else:
                        cleaned_list.append(item)
                clean_data[k] = cleaned_list
            else:
                clean_data[k] = v

        overall_report = {
            "redacted": total_redactions > 0,
            "redaction_count": total_redactions,
            "categories": list(all_categories)
        }
        return clean_data, overall_report

# Singleton instance
memory_defense = MemoryDefenseSanitizer()
