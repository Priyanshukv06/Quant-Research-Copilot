"""
Synthesis Agent — Cross-references screening results with news intelligence.

Improvements over v1:
  - Input truncation: caps at 10 stocks, summarises news to counts + top headlines
  - Pre-formatted prompt inputs: sends human-readable summaries, not raw JSON blobs
  - Output schema validation: fills missing fields with sensible defaults
"""
import json
import logging
from typing import Dict, Any, List

from llm.provider import llm
from llm.prompts import SYNTHESIS_SYSTEM, SYNTHESIS_USER

logger = logging.getLogger(__name__)

MAX_STOCKS_FOR_SYNTHESIS = 10


class SynthesisAgent:

    def _prepare_screening_summary(self, screened_data: List[Dict[str, Any]]) -> str:
        """Truncate to top N stocks and format as readable text instead of raw JSON."""
        if not screened_data:
            return "(No screening results provided)"

        capped = screened_data[:MAX_STOCKS_FOR_SYNTHESIS]
        lines = []
        for i, row in enumerate(capped, 1):
            symbol = row.get("nse_symbol", "UNKNOWN")
            # Collect all numeric metrics
            metrics = {k: v for k, v in row.items()
                       if k != "nse_symbol" and isinstance(v, (int, float))}
            metric_str = ", ".join(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}"
                                  for k, v in metrics.items())
            lines.append(f"{i}. {symbol} — {metric_str}")

        summary = "\n".join(lines)
        if len(screened_data) > MAX_STOCKS_FOR_SYNTHESIS:
            summary += f"\n... and {len(screened_data) - MAX_STOCKS_FOR_SYNTHESIS} more (omitted for brevity)"
        return summary

    def _prepare_news_summary(self, news_data: Dict[str, Any]) -> Dict[str, str]:
        """Summarise news into counts + top headlines per level."""
        result = {
            "entity": "(No entity-level news)",
            "sector": "(No sector-level news)",
            "macro":  "(No macro-level news)",
        }
        if not news_data:
            return result

        # Entity news
        entity_news = news_data.get("entity_news", {})
        if entity_news and isinstance(entity_news, dict):
            parts = []
            for sym, articles in entity_news.items():
                if sym == "_warning" or not isinstance(articles, list):
                    continue
                if articles:
                    top = articles[:3]
                    headlines = "; ".join(a.get("title", "")[:80] for a in top)
                    sentiments = [a.get("sentiment", "NEUTRAL") for a in articles]
                    parts.append(f"{sym} ({len(articles)} articles, sentiments: {', '.join(sentiments[:5])}): {headlines}")
                else:
                    parts.append(f"{sym}: No articles found")
            if parts:
                result["entity"] = "\n".join(parts)

        # Sector news
        sector_news = news_data.get("sector_news", [])
        if sector_news and isinstance(sector_news, list):
            top = sector_news[:3]
            headlines = "; ".join(a.get("title", "")[:80] for a in top)
            sentiments = [a.get("sentiment", "NEUTRAL") for a in sector_news]
            result["sector"] = f"{len(sector_news)} articles (sentiments: {', '.join(sentiments[:5])}): {headlines}"

        # Macro news
        macro_news = news_data.get("macro_news", [])
        if macro_news and isinstance(macro_news, list):
            top = macro_news[:3]
            headlines = "; ".join(a.get("title", "")[:80] for a in top)
            sentiments = [a.get("sentiment", "NEUTRAL") for a in macro_news]
            result["macro"] = f"{len(macro_news)} articles (sentiments: {', '.join(sentiments[:5])}): {headlines}"

        return result

    def _validate_output(self, synthesis: Any, screened_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate and fill missing fields in the LLM output."""
        if not isinstance(synthesis, dict):
            synthesis = {}

        # Ensure stocks array exists
        if "stocks" not in synthesis or not isinstance(synthesis["stocks"], list):
            synthesis["stocks"] = []

        # Validate each stock entry
        screened_symbols = {row.get("nse_symbol") for row in screened_data}
        present_symbols = {s.get("symbol") for s in synthesis["stocks"]}

        for stock in synthesis["stocks"]:
            stock.setdefault("symbol", "UNKNOWN")
            stock.setdefault("signal", "WATCH")
            stock.setdefault("fundamental_summary", "Passed screening criteria")
            stock.setdefault("news_summary", "No specific news coverage found")
            stock.setdefault("risk_flags", [])
            if not isinstance(stock["risk_flags"], list):
                stock["risk_flags"] = []

        # Add missing stocks with WATCH default
        for row in screened_data[:MAX_STOCKS_FOR_SYNTHESIS]:
            sym = row.get("nse_symbol")
            if sym and sym not in present_symbols:
                synthesis["stocks"].append({
                    "symbol": sym,
                    "signal": "WATCH",
                    "fundamental_summary": "Passed screening criteria",
                    "news_summary": "No specific news coverage found",
                    "risk_flags": [],
                })

        synthesis.setdefault("sector_context", "No sector-specific news available")
        synthesis.setdefault("macro_context", "No macro news available")
        synthesis.setdefault("overall_market_stance", "NEUTRAL")

        return synthesis

    async def synthesize(
        self,
        screened_data: List[Dict[str, Any]],
        news_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Takes screener output and news output and uses the LLM to synthesize signals.
        """
        screening_summary = self._prepare_screening_summary(screened_data)
        news_summaries = self._prepare_news_summary(news_data)

        messages = [
            {"role": "system", "content": SYNTHESIS_SYSTEM},
            {"role": "user", "content": SYNTHESIS_USER.format(
                stock_count=min(len(screened_data), MAX_STOCKS_FOR_SYNTHESIS),
                screening_results=screening_summary,
                entity_news_summary=news_summaries["entity"],
                sector_news_summary=news_summaries["sector"],
                macro_news_summary=news_summaries["macro"],
            )}
        ]

        try:
            logger.info(
                "Starting synthesis for %d stocks (capped at %d)...",
                len(screened_data), MAX_STOCKS_FOR_SYNTHESIS
            )
            synthesis = await llm.generate_json(messages, temperature=0.2)
            validated = self._validate_output(synthesis, screened_data)
            logger.info(
                "Synthesis complete: %d stocks, stance=%s",
                len(validated["stocks"]),
                validated.get("overall_market_stance", "N/A"),
            )
            return validated
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            # Return a safe fallback instead of just an error string
            return self._validate_output({}, screened_data)


synthesis_agent = SynthesisAgent()
