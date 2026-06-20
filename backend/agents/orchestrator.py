"""
Orchestrator Agent
Parses raw user intent and delegates to sub-agents.
"""
import logging
from typing import Dict, Any

from llm.provider import llm
from llm.prompts import ORCHESTRATOR_SYSTEM, ORCHESTRATOR_USER

logger = logging.getLogger(__name__)

class OrchestratorAgent:
    async def parse_intent(self, query: str) -> Dict[str, Any]:
        """
        Uses the LLM to parse user query into structured JSON action.
        """
        messages = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM},
            {"role": "user", "content": ORCHESTRATOR_USER.format(query=query)}
        ]
        
        try:
            result = await llm.generate_json(messages, temperature=0.1)
            logger.info(f"Orchestrator parsed intent: {result.get('action')}")
            return result
        except Exception as e:
            logger.error(f"Orchestrator failed to parse intent: {e}")
            raise

orchestrator_agent = OrchestratorAgent()
