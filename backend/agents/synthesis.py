import logging
from typing import Dict, Any, List

from llm.provider import llm
from llm.prompts import SYNTHESIS_SYSTEM, SYNTHESIS_USER

logger = logging.getLogger(__name__)

class SynthesisAgent:
    async def synthesize(self, screened_data: List[Dict[str, Any]], news_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes screener output and news output and uses the LLM to synthesize signals.
        """
        messages = [
            {"role": "system", "content": SYNTHESIS_SYSTEM},
            {"role": "user", "content": SYNTHESIS_USER.format(
                screening_results=screened_data,
                news_results=news_data
            )}
        ]
        
        try:
            logger.info("Starting synthesis generation...")
            synthesis = await llm.generate_json(messages, temperature=0.2)
            return synthesis
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return {"error": str(e)}

synthesis_agent = SynthesisAgent()
