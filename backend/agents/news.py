"""
News Agent v2 — Multi-source intelligence pipeline.

Replaces the original single-source RSS scraper with:
  1. Multi-source aggregation (RSS + API)
  2. Parallel fetching via asyncio.gather
  3. Fuzzy title deduplication (difflib, stdlib)
  4. Batch LLM classification (single call for all articles)
  5. In-memory TTL cache (avoids redundant API + LLM calls)
  6. Always-on macro context baseline
"""

import asyncio
import hashlib
import logging
import time
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from config import settings
from llm.provider import llm
from llm.prompts import (
    NEWS_BATCH_CLASSIFY_SYSTEM,
    NEWS_BATCH_CLASSIFY_USER,
    NEWS_RELEVANCE_SYSTEM,
    NEWS_RELEVANCE_USER,
)
from agents.sources import Article, build_source_registry

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# In-memory TTL cache
# ──────────────────────────────────────────────

class _NewsCache:
    """Simple dict-based cache with per-key TTL expiry."""

    def __init__(self, ttl_seconds: int = 900):
        self._store: Dict[str, tuple[float, Any]] = {}
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry and (time.time() - entry[0]) < self.ttl:
            logger.info("Cache HIT for key=%s", key[:12])
            return entry[1]
        if entry:
            del self._store[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time(), value)

    @staticmethod
    def make_key(*args) -> str:
        raw = "|".join(str(a) for a in args)
        return hashlib.md5(raw.encode()).hexdigest()


# ──────────────────────────────────────────────
# Deduplication
# ──────────────────────────────────────────────

def _deduplicate(articles: List[Article], threshold: float = 0.75) -> List[Article]:
    """
    Remove near-duplicate articles using title similarity.
    Uses difflib.SequenceMatcher (stdlib, no extra deps).
    Keeps the first occurrence (typically from the highest-priority source).
    """
    unique: List[Article] = []
    for art in articles:
        is_dup = False
        title_lower = art.title.lower().strip()
        for existing in unique:
            ratio = SequenceMatcher(
                None, title_lower, existing.title.lower().strip()
            ).ratio()
            if ratio >= threshold:
                is_dup = True
                break
        if not is_dup:
            unique.append(art)
    return unique


# ──────────────────────────────────────────────
# News Agent v2
# ──────────────────────────────────────────────

class NewsAgent:
    """
    Multi-source news intelligence pipeline.

    Fetches from RSS + API sources in parallel, deduplicates, classifies
    via a single batch LLM call, and caches results.
    """

    def __init__(self):
        self.sources = build_source_registry(
            gnews_key=getattr(settings, "GNEWS_API_KEY", ""),
            newsdata_key=getattr(settings, "NEWSDATA_API_KEY", ""),
        )
        self.cache = _NewsCache(
            ttl_seconds=getattr(settings, "NEWS_CACHE_TTL_SECONDS", 900)
        )
        active = [s.name for s in self.sources if s.is_available()]
        logger.info("NewsAgent v2 initialized — sources: %s", ", ".join(active))

    # ── parallel multi-source fetch ──────────────────────────

    async def _fetch_from_all(self, query: str, limit_per_source: int = 5) -> List[Article]:
        """Hit every active source in parallel and merge results."""
        tasks = [
            source.fetch(query, limit=limit_per_source)
            for source in self.sources
            if source.is_available()
        ]
        if not tasks:
            logger.warning("No news sources available")
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles: List[Article] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Source fetch error: %s", result)
                continue
            all_articles.extend(result)

        logger.info(
            "Fetched %d raw articles from %d sources",
            len(all_articles), len(tasks)
        )
        return all_articles

    # ── batch LLM classification ─────────────────────────────

    async def _batch_classify(
        self, target: str, articles: List[Article]
    ) -> List[Dict[str, Any]]:
        """
        Classify ALL articles in a single LLM call instead of one-per-article.

        Falls back to per-article classification if batch fails
        (e.g., too many articles for context window).
        """
        if not articles:
            return []

        # Build the numbered article list for the batch prompt
        article_entries = []
        for i, art in enumerate(articles, 1):
            snippet = art.description[:200] if art.description else "(no description)"
            article_entries.append(
                f"{i}. [{art.source_name}] {art.title}\n   {snippet}"
            )
        articles_text = "\n".join(article_entries)

        messages = [
            {"role": "system", "content": NEWS_BATCH_CLASSIFY_SYSTEM},
            {"role": "user", "content": NEWS_BATCH_CLASSIFY_USER.format(
                target=target,
                articles=articles_text,
                count=len(articles),
            )},
        ]

        try:
            classifications = await llm.generate_json(messages, temperature=0.2)

            # Expect a list of {index, relevant, sentiment, category, summary}
            if not isinstance(classifications, list):
                # Sometimes LLM wraps in {"articles": [...]}
                if isinstance(classifications, dict) and "articles" in classifications:
                    classifications = classifications["articles"]
                else:
                    raise ValueError("LLM returned non-list for batch classify")

            # Merge classifications with article data
            classified = []
            for entry in classifications:
                idx = entry.get("index", 0) - 1  # 1-indexed in prompt
                if 0 <= idx < len(articles):
                    art = articles[idx]
                    classified.append({
                        **art.to_dict(),
                        "relevant": entry.get("relevant", False),
                        "sentiment": entry.get("sentiment", "NEUTRAL"),
                        "category": entry.get("category", "OTHER"),
                        "summary": entry.get("summary", art.title),
                    })

            logger.info(
                "Batch classified %d articles, %d relevant",
                len(articles),
                sum(1 for c in classified if c.get("relevant")),
            )
            return [c for c in classified if c.get("relevant", False)]

        except Exception as e:
            logger.warning("Batch classification failed (%s), falling back to per-article", e)
            return await self._per_article_classify(target, articles)

    async def _per_article_classify(
        self, target: str, articles: List[Article]
    ) -> List[Dict[str, Any]]:
        """
        Fallback: classify each article individually (original v1 approach).
        Used when batch classification fails.
        """
        classified = []
        for art in articles:
            messages = [
                {"role": "system", "content": NEWS_RELEVANCE_SYSTEM},
                {"role": "user", "content": NEWS_RELEVANCE_USER.format(
                    target=target,
                    title=art.title,
                    source=art.source_name,
                    snippet=art.description[:200] if art.description else "",
                )},
            ]
            try:
                result = await llm.generate_json(messages, temperature=0.2)
                if result.get("relevant", False):
                    classified.append({**art.to_dict(), **result})
            except Exception as e:
                logger.error("Per-article classify failed for '%s': %s", art.title[:40], e)

        return classified

    # ── main orchestration ───────────────────────────────────

    async def get_intelligence(
        self,
        symbols: List[str] = None,
        sector: str = None,
    ) -> Dict[str, Any]:
        """
        Master orchestration: fetch + deduplicate + classify news at three levels.

        Levels:
          - entity_news:  per-symbol (max 3 symbols to conserve API)
          - sector_news:  sector-level context
          - macro_news:   always-on market baseline (even when symbols/sector given)

        All results are cached by query signature for NEWS_CACHE_TTL_SECONDS.
        """
        symbols = symbols or []
        cache_key = self.cache.make_key("intel", sorted(symbols), sector)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        news_results: Dict[str, Any] = {
            "entity_news": {},
            "sector_news": [],
            "macro_news": [],
            "sources_used": [],
        }

        active_sources = [s.name for s in self.sources if s.is_available()]
        news_results["sources_used"] = active_sources

        # ── 1. Entity-level news (per-symbol, max 3) ──
        if symbols and len(symbols) <= 3:
            for sym in symbols:
                query = f"{sym} stock India"
                raw = await self._fetch_from_all(query, limit_per_source=3)
                deduped = _deduplicate(raw)
                classified = await self._batch_classify(target=sym, articles=deduped)
                news_results["entity_news"][sym] = classified
        elif symbols and len(symbols) > 3:
            news_results["entity_news"]["_warning"] = (
                f"Skipped entity-level news for {len(symbols)} stocks "
                "to conserve API limits. Showing sector/macro only."
            )

        # ── 2. Sector-level news ──
        if sector:
            query = f"{sector} sector India stock market"
            raw = await self._fetch_from_all(query, limit_per_source=4)
            deduped = _deduplicate(raw)
            classified = await self._batch_classify(target=sector, articles=deduped)
            news_results["sector_news"] = classified

        # ── 3. Macro-level news (ALWAYS fetched as baseline) ──
        query = "Indian stock market Sensex Nifty"
        raw = await self._fetch_from_all(query, limit_per_source=3)
        deduped = _deduplicate(raw)
        classified = await self._batch_classify(
            target="Indian Stock Market", articles=deduped
        )
        news_results["macro_news"] = classified

        # Cache the assembled result
        self.cache.set(cache_key, news_results)

        _log_summary(news_results)
        return news_results


def _log_summary(results: Dict[str, Any]) -> None:
    """Log a compact summary of what the news pipeline returned."""
    entity_count = sum(
        len(v) for k, v in results.get("entity_news", {}).items()
        if isinstance(v, list)
    )
    sector_count = len(results.get("sector_news", []))
    macro_count = len(results.get("macro_news", []))
    logger.info(
        "News intelligence summary — entity: %d, sector: %d, macro: %d, sources: %s",
        entity_count, sector_count, macro_count,
        ", ".join(results.get("sources_used", [])),
    )


# Singleton
news_agent = NewsAgent()
