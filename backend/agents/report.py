"""
Report Agent — Generates a polished markdown research report.

Improvements over v1:
  - Accepts raw screening metrics alongside synthesis for actual numbers
  - Adds report metadata (timestamp, query echo, stock count)
  - Truncates synthesis input to a safe token budget
  - Returns structured response: { markdown, metadata }
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

from llm.provider import llm
from llm.prompts import REPORT_SYSTEM, REPORT_USER

logger = logging.getLogger(__name__)

MAX_SYNTHESIS_CHARS = 6000  # Keep synthesis under ~1500 tokens


class ReportAgent:

    def _prepare_screening_metrics(self, screened_data: List[Dict[str, Any]]) -> str:
        """Format raw screening data as a concise text table for the LLM."""
        if not screened_data:
            return "(No screening data available)"

        # Cap at 10 stocks
        capped = screened_data[:10]
        lines = []
        for row in capped:
            symbol = row.get("nse_symbol", "UNKNOWN")
            metrics = {k: v for k, v in row.items()
                       if k != "nse_symbol" and isinstance(v, (int, float))}
            metric_str = ", ".join(
                f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}"
                for k, v in metrics.items()
            )
            lines.append(f"- {symbol}: {metric_str}")
        return "\n".join(lines)

    def _truncate_synthesis(self, synthesis_data: Dict[str, Any]) -> str:
        """JSON-serialize synthesis and truncate if too long."""
        text = json.dumps(synthesis_data, indent=2, default=str)
        if len(text) > MAX_SYNTHESIS_CHARS:
            text = text[:MAX_SYNTHESIS_CHARS] + "\n... (truncated)"
        return text

    async def generate_report(
        self,
        query: str,
        synthesis_data: Dict[str, Any],
        screened_data: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Takes the structured synthesis, raw screening data, and original query
        and generates a polished markdown report with metadata.

        Returns:
            {
                "markdown": "...",
                "metadata": {
                    "generated_at": "2026-09-13T03:00:00",
                    "stocks_analyzed": 5,
                    "query": "...",
                    "signal_distribution": {"STRONG": 2, "WATCH": 2, "CAUTION": 1}
                }
            }
        """
        screened_data = screened_data or []
        now = datetime.now()
        date_str = now.strftime("%B %d, %Y at %I:%M %p")

        # Build signal distribution from synthesis
        signal_dist = {"STRONG": 0, "WATCH": 0, "CAUTION": 0}
        for stock in synthesis_data.get("stocks", []):
            sig = stock.get("signal", "WATCH").upper()
            if sig in signal_dist:
                signal_dist[sig] += 1

        synthesis_text = self._truncate_synthesis(synthesis_data)
        metrics_text = self._prepare_screening_metrics(screened_data)

        messages = [
            {"role": "system", "content": REPORT_SYSTEM},
            {"role": "user", "content": REPORT_USER.format(
                query=query,
                date=date_str,
                synthesis=synthesis_text,
                screening_metrics=metrics_text,
            )}
        ]

        metadata = {
            "generated_at": now.isoformat(),
            "stocks_analyzed": len(synthesis_data.get("stocks", [])),
            "query": query,
            "signal_distribution": signal_dist,
            "overall_market_stance": synthesis_data.get("overall_market_stance", "NEUTRAL"),
        }

        try:
            logger.info(
                "Generating report for %d stocks (signals: %s)...",
                metadata["stocks_analyzed"],
                signal_dist,
            )
            report_markdown = await llm.generate(messages, temperature=0.4, enable_thinking=True)
            logger.info("Report generation complete (%d chars)", len(report_markdown))
            return {
                "markdown": report_markdown,
                "metadata": metadata,
            }
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {
                "markdown": f"**Error generating report**: {str(e)}",
                "metadata": metadata,
            }


report_agent = ReportAgent()
