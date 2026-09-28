import json
import logging
from typing import Dict, Any, List, Optional
from groq import AsyncGroq
from backend.config import settings

logger = logging.getLogger(__name__)

class GroqResilientClient:
    """
    Groq LLM Client with automatic fallback to local SRE Heuristics
    if API keys are missing, network is unavailable, or rate limits are reached.
    """

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.client = AsyncGroq(api_key=self.api_key) if self.api_key else None

    async def call_groq_json(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        """Invokes Groq LLM requesting JSON output"""
        if not self.client:
            return None
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt + " Output ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=1500
            )
            raw = response.choices[0].message.content
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Groq API call failed or unavailable ({e}). Using intelligent SRE heuristic engine.")
            return None

    async def call_groq_text(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Invokes Groq LLM requesting standard text output"""
        if not self.client:
            return None
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Groq text call failed ({e}). Falling back to heuristic text.")
            return None

groq_client = GroqResilientClient()
