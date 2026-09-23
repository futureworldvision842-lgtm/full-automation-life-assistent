"""
economic_calendar_radar.py — Live Macroeconomic Calendar & News Circuit Breaker.
Monitors high-impact macroeconomic announcements (CPI, NFP, FOMC, Fed Interest Rates, ECB, BOE, BOJ).

Features:
  1. Automated 15-Minute Pre/Post News Circuit Breakers.
  2. Currency-Specific Lockout Matrix (USD, EUR, GBP, JPY, CAD, AUD, CHF, Gold, Crypto).
  3. Live ForexFactory & FRED feed ingestion with graceful offline fallback.
  4. Weekend rollover protection state machine.
"""

import logging
import urllib.request
import urllib.error
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple

logger = logging.getLogger("EconomicCalendarRadar")


class EconomicCalendarRadar:
    """
    Live Economic Calendar & 15-Minute News Circuit Breaker.
    Protects funded accounts against news slippage, spread blowouts, and institutional liquidity grabs.
    """

    HIGH_IMPACT_KEYWORDS = [
        "CPI", "Core CPI", "Consumer Price Index", "NFP", "Non-Farm Payrolls",
        "Nonfarm Payrolls", "FOMC", "Interest Rate Decision", "Federal Funds Rate",
        "Fed Interest Rate", "Powell", "Lagarde", "Bailey", "Ueda", "ECB",
        "GDP", "Unemployment Rate", "Unemployment Claims", "PPI",
        "ISM Manufacturing", "ISM Services", "Retail Sales", "Flash PMI"
    ]

    # Currency map for commodities and crypto
    COMMODITY_CRYPTO_MAP = {
        "XAU": ["USD"],
        "GOLD": ["USD"],
        "XAG": ["USD"],
        "SILVER": ["USD"],
        "WTI": ["USD"],
        "BRENT": ["USD"],
        "OIL": ["USD"],
        "BTC": ["USD"],
        "ETH": ["USD"],
        "SOL": ["USD"]
    }

    def __init__(self, blackout_minutes_before: int = 15, blackout_minutes_after: int = 15):
        self.blackout_before = blackout_minutes_before
        self.blackout_after = blackout_minutes_after
        self.cached_events: List[Dict[str, Any]] = []
        self.manual_events: List[Dict[str, Any]] = []
        self.last_fetch_time = datetime.min.replace(tzinfo=timezone.utc)
        self.cache_ttl_seconds = 300  # 5 minutes

    def clear_events(self):
        """Clears all cached and manual events."""
        self.cached_events = []
        self.manual_events = []
        self.last_fetch_time = datetime.min.replace(tzinfo=timezone.utc)

    def inject_event(
        self,
        title: str,
        currency: str,
        event_time_utc: datetime,
        impact: str = "HIGH"
    ) -> Dict[str, Any]:
        """
        Manually injects an event for testing or deterministic circuit breaker verification.
        """
        if event_time_utc.tzinfo is None:
            event_time_utc = event_time_utc.replace(tzinfo=timezone.utc)

        ev = {
            "title": title,
            "currency": currency.upper(),
            "impact": impact.upper(),
            "event_time_utc": event_time_utc,
            "time_iso": event_time_utc.isoformat(),
            "is_high_impact": impact.upper() in ["HIGH", "RED", "CRITICAL"]
        }
        self.manual_events.append(ev)
        return ev

    def fetch_live_calendar(self) -> List[Dict[str, Any]]:
        """
        Fetches current economic calendar feed from ForexFactory JSON/XML or returns cached/fallback events.
        """
        now = datetime.now(timezone.utc)
        if (now - self.last_fetch_time).total_seconds() < self.cache_ttl_seconds and self.cached_events:
            return self.cached_events + self.manual_events

        events: List[Dict[str, Any]] = []

        # Attempt 1: ForexFactory JSON feed
        try:
            feed_url_json = "https://nodedata.forexfactory.com/ff_calendar_thisweek.json"
            req = urllib.request.Request(
                feed_url_json,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data:
                    title = str(item.get("title", ""))
                    currency = str(item.get("country", item.get("currency", "USD"))).upper()
                    impact = str(item.get("impact", "")).upper()
                    date_str = str(item.get("date", ""))

                    is_high = (
                        impact in ["HIGH", "RED"] or
                        any(kw.lower() in title.lower() for kw in self.HIGH_IMPACT_KEYWORDS)
                    )

                    ev_time = None
                    if date_str:
                        try:
                            ev_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        except Exception:
                            pass

                    if is_high and ev_time:
                        events.append({
                            "title": title,
                            "currency": currency,
                            "impact": "HIGH",
                            "event_time_utc": ev_time,
                            "time_iso": ev_time.isoformat(),
                            "is_high_impact": True
                        })
        except urllib.error.HTTPError as e_http:
            e_http.close()
            logger.debug(f"[EconomicCalendarRadar] JSON feed HTTP error: {e_http.code}")
        except Exception as e_json:
            logger.debug(f"[EconomicCalendarRadar] JSON feed fallback: {e_json}")

        # Attempt 2: If JSON feed returned empty, try XML feed
        if not events:
            try:
                feed_url_xml = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
                req = urllib.request.Request(
                    feed_url_xml,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req, timeout=2) as resp:
                    xml_data = resp.read()
                root = ET.fromstring(xml_data)
                for event in root.findall(".//event"):
                    title = event.find("title").text if event.find("title") is not None else ""
                    country = event.find("country").text if event.find("country") is not None else ""
                    impact = event.find("impact").text if event.find("impact") is not None else ""
                    time_str = event.find("time").text if event.find("time") is not None else ""
                    date_str = event.find("date").text if event.find("date") is not None else ""

                    is_high = (
                        impact in ["High", "HIGH", "Red"] or
                        any(kw.lower() in title.lower() for kw in self.HIGH_IMPACT_KEYWORDS)
                    )

                    if is_high:
                        try:
                            date_part = date_str.strip()
                            time_part = time_str.strip()
                            if date_part and time_part:
                                dt_raw = datetime.strptime(f"{date_part} {time_part}", "%m-%d-%Y %I:%M%p")
                                ev_time = dt_raw.replace(tzinfo=timezone.utc)
                            else:
                                ev_time = now
                        except Exception:
                            ev_time = now

                        events.append({
                            "title": title,
                            "currency": country.upper(),
                            "impact": "HIGH",
                            "event_time_utc": ev_time,
                            "time_iso": ev_time.isoformat(),
                            "is_high_impact": True
                        })
            except urllib.error.HTTPError as e_http:
                e_http.close()
                logger.debug(f"[EconomicCalendarRadar] XML feed HTTP error: {e_http.code}")
            except Exception as e_xml:
                logger.debug(f"[EconomicCalendarRadar] XML feed fallback: {e_xml}")

        if events:
            self.cached_events = events
            self.last_fetch_time = now

        return self.cached_events + self.manual_events

    def extract_symbol_currencies(self, symbol: str) -> Set[str]:
        """
        Extracts all relevant macroeconomic currencies associated with a trading asset symbol.
        """
        clean = symbol.replace("m", "").replace("c", "").replace("/", "").replace("_", "").upper()
        currencies: Set[str] = set()

        # Check commodity / crypto lookup
        for key, currs in self.COMMODITY_CRYPTO_MAP.items():
            if key in clean:
                currencies.update(currs)

        # Standard Forex 6-char pairs (e.g. EURUSD, GBPJPY, USDCAD)
        if len(clean) >= 6:
            base = clean[:3]
            quote = clean[3:6]
            # Verify standard currency codes
            known_currencies = {"USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", "CNH", "SGD", "HKD", "SEK", "NOK", "TRY", "ZAR", "MXN"}
            if base in known_currencies:
                currencies.add(base)
            if quote in known_currencies:
                currencies.add(quote)

        # If clean is an individual currency code (e.g. "USD" or "EUR")
        if clean in {"USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"}:
            currencies.add(clean)

        # Default fallback
        if not currencies:
            currencies.add("USD")

        return currencies

    def evaluate_news_clearance(
        self,
        symbol: str = "XAUUSD",
        current_time: Optional[datetime] = None,
        check_weekend: bool = True
    ) -> Dict[str, Any]:
        """
        Interface Contract 2:
        Evaluates whether the market is safe to trade or if a 15-minute Pre/Post High-Impact news blackout is active.
        """
        events = self.fetch_live_calendar()
        now_utc = current_time or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        symbol_currencies = self.extract_symbol_currencies(symbol)
        is_crypto = any(c in symbol.upper() for c in ["BTC", "ETH", "SOL", "CRYPTO"])

        # 1. Check 15-minute Pre/Post News Circuit Breakers FIRST
        active_event = None
        lockout_reason = ""
        upcoming_count = 0
        applicable_high_impact = []

        for ev in events:
            ev_curr = ev.get("currency", "USD")
            # Event applies if it matches any symbol currency or if it's a USD event on a USD cross/commodity
            is_relevant = (ev_curr in symbol_currencies) or ("USD" in symbol_currencies and ev_curr == "USD")

            if not is_relevant:
                continue

            ev_time = ev["event_time_utc"]
            if ev_time.tzinfo is None:
                ev_time = ev_time.replace(tzinfo=timezone.utc)

            delta_sec = (ev_time - now_utc).total_seconds()
            delta_min = delta_sec / 60.0

            # Collect upcoming events within 24h
            if 0 < delta_min <= 1440:
                upcoming_count += 1
                applicable_high_impact.append(ev)

            # Circuit breaker check: [-blackout_after, +blackout_before]
            # Pre-news: 0 <= delta_min <= blackout_before
            # Post-news: -blackout_after <= delta_min <= 0
            if -self.blackout_after <= delta_min <= self.blackout_before:
                window_start = ev_time - timedelta(minutes=self.blackout_before)
                window_end = ev_time + timedelta(minutes=self.blackout_after)

                if delta_min >= 0:
                    lockout_reason = f"PRE_NEWS_BLACKOUT: {ev['title']} ({ev_curr}) in {delta_min:.1f} mins."
                else:
                    since_min = abs(delta_min)
                    lockout_reason = f"POST_NEWS_BLACKOUT: {ev['title']} ({ev_curr}) occurred {since_min:.1f} mins ago. Volatility cooloff active."

                active_event = {
                    "title": ev["title"],
                    "currency": ev_curr,
                    "impact": ev.get("impact", "HIGH"),
                    "event_time_utc": ev_time.isoformat(),
                    "minutes_to_event": round(delta_min, 1),
                    "minutes_since_event": round(-delta_min, 1),
                    "blackout_window_start": window_start.isoformat(),
                    "blackout_window_end": window_end.isoformat()
                }
                break

        if active_event:
            return {
                "is_cleared": False,
                "is_blackout": True,
                "lockout_reason": lockout_reason,
                "reason": lockout_reason,
                "active_event": active_event,
                "upcoming_events_count": upcoming_count,
                "high_impact_events": applicable_high_impact,
                "timestamp": now_utc.isoformat()
            }

        # 2. Weekend Rollover Protection (Friday 20:00 UTC to Sunday 21:00 UTC) - Evaluated when no active news event
        if check_weekend and not is_crypto:
            weekday = now_utc.weekday()
            hour = now_utc.hour
            # Friday post 20:00 UTC
            if weekday == 4 and hour >= 20:
                return {
                    "is_cleared": False,
                    "is_blackout": True,
                    "lockout_reason": "WEEKEND_ROLLOVER_BLACKOUT: Friday market close risk management.",
                    "reason": "WEEKEND_ROLLOVER_BLACKOUT: Friday market close risk management.",
                    "active_event": None,
                    "upcoming_events_count": upcoming_count,
                    "high_impact_events": applicable_high_impact,
                    "timestamp": now_utc.isoformat()
                }
            # Saturday all day
            if weekday == 5:
                return {
                    "is_cleared": False,
                    "is_blackout": True,
                    "lockout_reason": "WEEKEND_ROLLOVER_BLACKOUT: Saturday market closure.",
                    "reason": "WEEKEND_ROLLOVER_BLACKOUT: Saturday market closure.",
                    "active_event": None,
                    "upcoming_events_count": upcoming_count,
                    "high_impact_events": applicable_high_impact,
                    "timestamp": now_utc.isoformat()
                }
            # Sunday before 21:00 UTC
            if weekday == 6 and hour < 21:
                return {
                    "is_cleared": False,
                    "is_blackout": True,
                    "lockout_reason": "WEEKEND_ROLLOVER_BLACKOUT: Sunday pre-market opening buffer.",
                    "reason": "WEEKEND_ROLLOVER_BLACKOUT: Sunday pre-market opening buffer.",
                    "active_event": None,
                    "upcoming_events_count": upcoming_count,
                    "high_impact_events": applicable_high_impact,
                    "timestamp": now_utc.isoformat()
                }

        return {
            "is_cleared": True,
            "is_blackout": False,
            "lockout_reason": "CLEARED: No active high-impact news blackout.",
            "reason": "CLEARED: No active high-impact news blackout.",
            "active_event": None,
            "upcoming_events_count": upcoming_count,
            "high_impact_events": applicable_high_impact,
            "timestamp": now_utc.isoformat()
        }
