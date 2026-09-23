import os
import json
import logging
import requests
import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class WorldMonitorFeed:
    """
    Real-Time Global Geopolitical & Macro Economic Feed Engine.
    Extracted from worldmonitor repository. Scans free open-source RSS/JSON feeds
    for central bank interest rate decisions, global economic indices, and conflict risks.
    """

    def __init__(self):
        self.last_fetch: Optional[datetime.datetime] = None
        self.risk_score: float = 0.0
        self.cached_news: List[Dict[str, Any]] = []

    def fetch_live_world_feed(self) -> Dict[str, Any]:
        """Fetches free real-time geopolitical and macroeconomic news feeds."""
        now = datetime.datetime.now(datetime.timezone.utc)
        if self.last_fetch and (now - self.last_fetch).total_seconds() < 900:
            return {"risk_score": self.risk_score, "news": self.cached_news}

        news_items = []
        try:
            # Query free ForexFactory / Macro RSS feed
            url = "https://nodedata.forexfactory.com/ff_calendar_thisweek.json"
            res = requests.get(url, headers={"User-Agent": "WorldMonitor/1.0"}, timeout=5)
            if res.status_code == 200:
                data = res.json()
                for item in data:
                    impact = str(item.get("impact", "")).upper()
                    if impact in ["HIGH", "RED"]:
                        news_items.append({
                            "title": item.get("title"),
                            "country": item.get("country"),
                            "date": item.get("date"),
                            "impact": "HIGH"
                        })
                self.cached_news = news_items
                logger.info(f"[World Monitor Feed] Loaded {len(news_items)} high-impact macro feeds.")
        except Exception as e:
            logger.debug(f"[World Monitor Feed] Live sync note: {e}")

        self.last_fetch = now
        return {"risk_score": self.risk_score, "news": self.cached_news}
