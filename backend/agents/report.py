import logging
from typing import Dict, Any
from llm.provider import llm
from llm.prompts import REPORT_SYSTEM, REPORT_USER

logger = logging.getLogger(__name__)

class ReportAgent:
    async def generate_report(self, query: str, synthesis_data: Dict[str, Any]) -> str:
        """
        Takes the structured synthesis and original query and generates a polished markdown report.
        """
        import json
        messages = [
            {"role": "system", "content": REPORT_SYSTEM},
            {"role": "user", "content": REPORT_USER.format(
                query=query,
                synthesis=json.dumps(synthesis_data, indent=2)
            )}
        ]
        
        try:
            logger.info("Generating final markdown report...")
            report_markdown = await llm.generate(messages, temperature=0.4, enable_thinking=True)
            return report_markdown
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return f"**Error generating report**: {str(e)}"

report_agent = ReportAgent()
