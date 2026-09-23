"""
news_filter.py — Global Macroeconomic News Guard for MQ3 Trading Bot.
Consolidated with EconomicCalendarRadar for unified 15-minute circuit breaker state machine.
"""

import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple

from src.economic_calendar_radar import EconomicCalendarRadar

logger = logging.getLogger(__name__)


class NewsFilter:
    """
    Global Macroeconomic News Guard for Funded Accounts.
    Monitors economic calendar and prevents trade entry during high-impact news windows.
    Backed by EconomicCalendarRadar for single-source-of-truth circuit breakers.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = (config or {}).get("news_guard", {})
        self.enabled = cfg.get("enabled", True)
        self.buffer_before_minutes = cfg.get("buffer_before_minutes", 15)
        self.buffer_after_minutes = cfg.get("buffer_after_minutes", 15)
        self.radar = EconomicCalendarRadar(
            blackout_minutes_before=self.buffer_before_minutes,
            blackout_minutes_after=self.buffer_after_minutes
        )

    def fetch_economic_calendar(self):
        """Fetches live economic calendar events via EconomicCalendarRadar."""
        if not self.enabled:
            return
        self.radar.fetch_live_calendar()

    @property
    def high_impact_events(self) -> List[Dict[str, Any]]:
        """Returns list of high impact events from radar."""
        return self.radar.cached_events + self.radar.manual_events

    def is_news_active(self, symbol: str) -> Tuple[bool, str]:
        """
        Checks if there is active high-impact news for currencies in symbol within buffer window.
        Returns (is_active, description_message).
        """
        if not self.enabled:
            return False, "News Guard disabled."

        clearance = self.radar.evaluate_news_clearance(symbol)
        if clearance.get("is_blackout", False):
            msg = clearance.get("lockout_reason", "NEWS GUARD LOCKOUT ACTIVE.")
            logger.info(f"[NewsFilter] {symbol}: {msg}")
            return True, msg

        return False, "No high-impact news in window."

    def evaluate_news_clearance(self, symbol: str) -> Dict[str, Any]:
        """Direct pass-through to EconomicCalendarRadar."""
        if not self.enabled:
            return {
                "is_cleared": True,
                "is_blackout": False,
                "lockout_reason": "NEWS_GUARD_DISABLED",
                "active_event": None,
                "upcoming_events_count": 0,
                "high_impact_events": [],
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        return self.radar.evaluate_news_clearance(symbol)
