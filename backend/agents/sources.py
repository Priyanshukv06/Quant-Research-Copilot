"""
Multi-source news adapter registry.

Each adapter normalises raw provider output into a common Article schema so the
NewsAgent pipeline can treat all sources identically downstream.

Sources
-------
RSS (feedparser, no key required):
    - Google News RSS        — broad real-time coverage
    - ET Markets RSS         — Indian market focus
    - Moneycontrol RSS       — Indian market focus, includes descriptions

REST API (key required, free-tier):
    - GNews (gnews.io)       — 100 req/day, article descriptions + full content
    - NewsData.io            — 200 credits/day, India filter, built-in sentiment
"""

import asyncio
import logging
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Protocol

import feedparser

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Common article schema
# ──────────────────────────────────────────────

@dataclass
class Article:
    """Normalised article that every source adapter must produce."""
    title: str
    description: str          # body snippet — may be empty for bare RSS
    url: str
    source_name: str          # human-readable source label
    published_at: str         # ISO-ish string or raw date string
    image_url: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "source": self.source_name,
            "published": self.published_at,
            "image_url": self.image_url,
        }


# ──────────────────────────────────────────────
# Source adapter protocol
# ──────────────────────────────────────────────

class NewsSource(Protocol):
    """All source adapters must implement this."""
    name: str

    async def fetch(self, query: str, limit: int = 5) -> List[Article]:
        ...

    def is_available(self) -> bool:
        ...


# ──────────────────────────────────────────────
# RSS adapters (no key required)
# ──────────────────────────────────────────────

class GoogleNewsRSS:
    """Google News RSS — broad real-time coverage, title + link."""
    name = "Google News"

    def __init__(self):
        self.base_url = (
            "https://news.google.com/rss/search?"
            "q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        )

    def is_available(self) -> bool:
        return True

    async def fetch(self, query: str, limit: int = 5) -> List[Article]:
        encoded = urllib.parse.quote(query)
        url = self.base_url.format(query=encoded)
        logger.info("GoogleNewsRSS: fetching %s", url)

        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, url)

        articles: List[Article] = []
        for entry in feed.entries[:limit]:
            articles.append(Article(
                title=entry.get("title", ""),
                description=entry.get("summary", ""),
                url=entry.get("link", ""),
                source_name=self.name,
                published_at=entry.get("published", ""),
            ))
        return articles


class ETMarketsRSS:
    """Economic Times Markets RSS — Indian market focus."""
    name = "ET Markets"

    def __init__(self):
        self.feed_urls = {
            "markets": "https://economictimes.indiatimes.com/markets/rssfeeds/2146842.cms",
            "stocks":  "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146843.cms",
        }

    def is_available(self) -> bool:
        return True

    async def fetch(self, query: str, limit: int = 5) -> List[Article]:
        # Use the stocks feed for entity queries, markets for general
        feed_url = self.feed_urls["stocks"] if query else self.feed_urls["markets"]
        logger.info("ETMarketsRSS: fetching %s", feed_url)

        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, feed_url)

        # Filter entries by query keywords if provided
        query_lower = query.lower() if query else ""
        articles: List[Article] = []

        for entry in feed.entries:
            if len(articles) >= limit:
                break
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            # If query is provided, do a simple keyword match
            if query_lower and query_lower not in title.lower() and query_lower not in summary.lower():
                continue
            articles.append(Article(
                title=title,
                description=summary,
                url=entry.get("link", ""),
                source_name=self.name,
                published_at=entry.get("published", ""),
            ))

        # If keyword filter yielded nothing, return top entries unfiltered
        if not articles and query:
            for entry in feed.entries[:limit]:
                articles.append(Article(
                    title=entry.get("title", ""),
                    description=entry.get("summary", ""),
                    url=entry.get("link", ""),
                    source_name=self.name,
                    published_at=entry.get("published", ""),
                ))
        return articles


class MoneycontrolRSS:
    """Moneycontrol RSS — Indian market, includes article descriptions."""
    name = "Moneycontrol"

    def __init__(self):
        self.feed_urls = {
            "market": "https://www.moneycontrol.com/rss/marketreports.xml",
            "business": "https://www.moneycontrol.com/rss/business.xml",
            "stocks": "https://www.moneycontrol.com/rss/latestnews.xml",
        }

    def is_available(self) -> bool:
        return True

    async def fetch(self, query: str, limit: int = 5) -> List[Article]:
        feed_url = self.feed_urls["stocks"] if query else self.feed_urls["market"]
        logger.info("MoneycontrolRSS: fetching %s", feed_url)

        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, feed_url)

        query_lower = query.lower() if query else ""
        articles: List[Article] = []

        for entry in feed.entries:
            if len(articles) >= limit:
                break
            title = entry.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))
            if query_lower and query_lower not in title.lower() and query_lower not in summary.lower():
                continue
            articles.append(Article(
                title=title,
                description=summary,
                url=entry.get("link", ""),
                source_name=self.name,
                published_at=entry.get("published", ""),
            ))

        if not articles and query:
            for entry in feed.entries[:limit]:
                articles.append(Article(
                    title=entry.get("title", ""),
                    description=entry.get("summary", entry.get("description", "")),
                    url=entry.get("link", ""),
                    source_name=self.name,
                    published_at=entry.get("published", ""),
                ))
        return articles


# ──────────────────────────────────────────────
# API adapters (key required, free-tier)
# ──────────────────────────────────────────────

class GNewsAPI:
    """GNews (gnews.io) — 100 req/day free, returns description + content."""
    name = "GNews"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = "https://gnews.io/api/v4/search"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def fetch(self, query: str, limit: int = 5) -> List[Article]:
        if not self.is_available():
            return []

        import aiohttp

        params = {
            "q": query,
            "lang": "en",
            "country": "in",
            "max": str(min(limit, 10)),
            "apikey": self.api_key,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        logger.warning("GNews API returned %d", resp.status)
                        return []
                    data = await resp.json()
        except Exception as e:
            logger.error("GNews API error: %s", e)
            return []

        articles: List[Article] = []
        for item in data.get("articles", [])[:limit]:
            articles.append(Article(
                title=item.get("title", ""),
                description=item.get("description", ""),
                url=item.get("url", ""),
                source_name=f"GNews ({item.get('source', {}).get('name', 'Unknown')})",
                published_at=item.get("publishedAt", ""),
                image_url=item.get("image"),
            ))
        return articles


class NewsDataAPI:
    """NewsData.io — 200 credits/day free, India filter, built-in sentiment."""
    name = "NewsData"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = "https://newsdata.io/api/1/latest"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def fetch(self, query: str, limit: int = 5) -> List[Article]:
        if not self.is_available():
            return []

        import aiohttp

        params = {
            "apikey": self.api_key,
            "q": query,
            "country": "in",
            "language": "en",
            "category": "business",
            "size": str(min(limit, 10)),
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        logger.warning("NewsData API returned %d", resp.status)
                        return []
                    data = await resp.json()
        except Exception as e:
            logger.error("NewsData API error: %s", e)
            return []

        articles: List[Article] = []
        for item in data.get("results", [])[:limit]:
            articles.append(Article(
                title=item.get("title", ""),
                description=item.get("description", ""),
                url=item.get("link", ""),
                source_name=f"NewsData ({item.get('source_id', 'Unknown')})",
                published_at=item.get("pubDate", ""),
                image_url=item.get("image_url"),
            ))
        return articles


# ──────────────────────────────────────────────
# Source registry
# ──────────────────────────────────────────────

def build_source_registry(gnews_key: str = "", newsdata_key: str = "") -> List:
    """
    Build the ordered list of news sources.
    RSS sources are always available; API sources activate only with valid keys.
    """
    sources = [
        GoogleNewsRSS(),
        ETMarketsRSS(),
        MoneycontrolRSS(),
        GNewsAPI(api_key=gnews_key),
        NewsDataAPI(api_key=newsdata_key),
    ]
    active = [s for s in sources if s.is_available()]
    logger.info(
        "News sources active: %s",
        ", ".join(s.name for s in active)
    )
    return sources  # return all — fetch() on unavailable ones returns []
