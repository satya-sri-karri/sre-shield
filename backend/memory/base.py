from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseMemoryEngine(ABC):
    """
    Abstract interface for Persistent SRE Incident Memory.
    """

    @abstractmethod
    async def retain(
        self,
        incident_data: Dict[str, Any],
        post_mortem_data: Optional[Dict[str, Any]] = None,
        outcome: str = "SUCCESS"
    ) -> Dict[str, Any]:
        """
        Store a new or resolved incident into long-term memory.
        Must run Memory Defense sanitization before persistence.
        """
        pass

    @abstractmethod
    async def recall(
        self,
        query_service: str,
        error_message: str,
        logs: str = "",
        top_k: int = 4
    ) -> Dict[str, Any]:
        """
        Recall similar historical incidents, entity summaries, and evolving beliefs.
        """
        pass

    @abstractmethod
    async def reflect(
        self,
        service_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesize recent experiences into evolving beliefs and entity summaries.
        """
        pass
