import logging
import feedparser
import urllib.parse
from typing import List, Dict, Any

from llm.provider import llm
from llm.prompts import NEWS_RELEVANCE_SYSTEM, NEWS_RELEVANCE_USER

logger = logging.getLogger(__name__)

class NewsAgent:
    def __init__(self):
        # We will use Google News RSS as the primary feed for arbitrary queries
        self.google_news_base = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        # ET Markets RSS for broad market updates
        self.et_markets_rss = "https://economictimes.indiatimes.com/markets/rssfeeds/2146842.cms"

    def fetch_rss(self, query: str = None, limit: int = 5) -> List[Dict[str, str]]:
        """
        Fetches the top `limit` articles from RSS for a given query.
        If no query is provided, fetches general ET Markets news.
        """
        if query:
            encoded_query = urllib.parse.quote(query + " stock market India")
            url = self.google_news_base.format(query=encoded_query)
            source = "Google News"
        else:
            url = self.et_markets_rss
            source = "ET Markets"
            
        logger.info(f"Fetching RSS from {source}: {url}")
        
        try:
            feed = feedparser.parse(url)
            articles = []
            for entry in feed.entries[:limit]:
                articles.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": source
                })
            return articles
        except Exception as e:
            logger.error(f"Failed to fetch RSS: {e}")
            return []

    async def classify_article(self, target: str, article: Dict[str, str]) -> Dict[str, Any]:
        """
        Uses the LLM to classify an article's relevance and sentiment.
        """
        messages = [
            {"role": "system", "content": NEWS_RELEVANCE_SYSTEM},
            {"role": "user", "content": NEWS_RELEVANCE_USER.format(
                target=target,
                title=article["title"],
                source=article["source"],
                snippet="" # RSS usually just has title/link, so snippet is empty unless we scrape
            )}
        ]
        
        try:
            classification = await llm.generate_json(messages, temperature=0.2)
            # Merge classification with the original article
            return {**article, **classification}
        except Exception as e:
            logger.error(f"Failed to classify article '{article['title']}': {e}")
            return {**article, "relevant": False, "error": str(e)}

    async def get_intelligence(self, symbols: List[str], sector: str = None) -> Dict[str, Any]:
        """
        Master orchestration function for fetching and classifying news.
        Enforces the 3-stock limit rule to prevent API burnout.
        """
        news_results = {
            "entity_news": {},
            "sector_news": [],
            "macro_news": []
        }
        
        # 1. Fetch Entity-Level News (only if <= 3 symbols)
        if symbols and len(symbols) <= 3:
            for sym in symbols:
                articles = self.fetch_rss(query=sym, limit=3)
                classified = []
                for art in articles:
                    res = await self.classify_article(target=sym, article=art)
                    if res.get("relevant", False):
                        classified.append(res)
                news_results["entity_news"][sym] = classified
        elif symbols and len(symbols) > 3:
            news_results["entity_news"]["_warning"] = f"Skipped entity-level news for {len(symbols)} stocks to conserve API limits."

        # 2. Fetch Sector-Level News
        if sector:
            articles = self.fetch_rss(query=f"{sector} sector", limit=4)
            classified = []
            for art in articles:
                res = await self.classify_article(target=sector, article=art)
                if res.get("relevant", False):
                    classified.append(res)
            news_results["sector_news"] = classified
            
        # 3. Fetch Macro-Level News (if no symbols/sector, or just as a baseline)
        if not symbols and not sector:
            articles = self.fetch_rss(limit=5) # uses ET Markets
            classified = []
            for art in articles:
                res = await self.classify_article(target="Indian Stock Market", article=art)
                if res.get("relevant", False):
                    classified.append(res)
            news_results["macro_news"] = classified

        return news_results

news_agent = NewsAgent()
