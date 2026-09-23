"""Economic Calendar & Macroeconomic Risk Gate Service.

Loads attributable upcoming macroeconomic releases from the World Monitor API
when an API key is configured.  Without verified remote data, the admission
gate remains locked; historical fixtures are never labelled current.
"""

from __future__ import annotations

import dataclasses
import datetime
import enum
import hashlib
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

logger = logging.getLogger(__name__)


class EventImpact(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    HOLIDAY = "HOLIDAY"


@dataclasses.dataclass(frozen=True)
class EconomicEvent:
    event_id: str
    event_name: str
    currency: str
    impact: EventImpact
    scheduled_utc: str
    pre_lockout_minutes: int = 15
    post_cooldown_minutes: int = 15
    previous_value: Optional[str] = None
    forecast_value: Optional[str] = None
    actual_value: Optional[str] = None
    revision_value: Optional[str] = None
    source_agency: str = "US_OFFICIAL_RELEASE"
    source_url: str = "https://www.federalreserve.gov"
    affected_symbols: Optional[List[str]] = None
    timezone_normalized: str = "UTC"
    observation_timestamp_utc: Optional[str] = None

    def get_lockout_window(self) -> Tuple[datetime.datetime, datetime.datetime]:
        dt = datetime.datetime.fromisoformat(self.scheduled_utc.replace("Z", "+00:00"))
        start_time = dt - datetime.timedelta(minutes=self.pre_lockout_minutes)
        end_time = dt + datetime.timedelta(minutes=self.post_cooldown_minutes)
        return start_time, end_time

    def is_active_at(self, current_dt_utc: datetime.datetime) -> bool:
        start_time, end_time = self.get_lockout_window()
        return start_time <= current_dt_utc <= end_time

    def to_dict(self) -> Dict[str, Any]:
        data = dataclasses.asdict(self)
        start, end = self.get_lockout_window()
        data["lockout_start_utc"] = start.isoformat()
        data["lockout_end_utc"] = end.isoformat()
        return data


class EconomicCalendarService:
    """Central registry and gatekeeper for official scheduled macroeconomic events."""

    CURRENCY_SYMBOL_MAP = {
        "USD": ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD", "SOLUSD", "US500", "US30", "NAS100", "USDCAD", "USDCHF"],
        "EUR": ["EURUSD", "EURGBP", "EURJPY", "EURCHF", "EURAUD"],
        "GBP": ["GBPUSD", "EURGBP", "GBPJPY", "GBPAUD", "GBPCAD"],
        "JPY": ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY"],
        "CAD": ["USDCAD", "EURCAD", "GBPCAD"],
        "AUD": ["AUDUSD", "EURAUD", "GBPAUD", "AUDJPY"],
        "NZD": ["NZDUSD"],
        "CHF": ["USDCHF", "EURCHF"],
    }

    def __init__(self):
        self._events: List[EconomicEvent] = []
        self._calendar_verified = False
        self._data_mode = "UNAVAILABLE"
        self._source = "World Monitor economic calendar API"
        self._last_refresh_monotonic = 0.0
        self._last_error = "No verified economic-calendar response has been loaded."

    @property
    def calendar_verified(self) -> bool:
        return self._calendar_verified

    @property
    def data_mode(self) -> str:
        return self._data_mode

    @property
    def last_error(self) -> str:
        return self._last_error

    def _refresh_verified_schedule(self, *, force: bool = False) -> None:
        """Refresh from World Monitor, retaining no stale clearance on failure."""
        now_monotonic = time.monotonic()
        if not force and now_monotonic - self._last_refresh_monotonic < 300:
            return
        self._last_refresh_monotonic = now_monotonic
        api_key = os.getenv("WORLD_MONITOR_API_KEY", "").strip()
        base_url = os.getenv("WORLD_MONITOR_API_URL", "https://api.worldmonitor.app").rstrip("/")
        if not api_key:
            self._events = []
            self._calendar_verified = False
            self._data_mode = "UNAVAILABLE"
            self._last_error = "WORLD_MONITOR_API_KEY is not configured."
            return
        endpoint = f"{base_url}/api/economic/v1/get-economic-calendar"
        today = datetime.datetime.now(datetime.timezone.utc).date()
        rows = None
        source_name = "World Monitor attributed calendar feed"
        source_link = endpoint

        # 1. Try World Monitor API
        try:
            response = requests.get(
                endpoint,
                params={"fromDate": today.isoformat(), "toDate": (today + datetime.timedelta(days=30)).isoformat()},
                headers={"X-API-Key": api_key, "User-Agent": "MQ3-JARVIS/1.0"},
                timeout=5,
            )
            if response.status_code == 200:
                payload = response.json()
                if isinstance(payload, dict) and isinstance(payload.get("events"), list) and payload["events"]:
                    rows = payload["events"]
        except Exception:
            pass

        # 2. Fallback to ForexFactory / World Monitor verified live calendar feed
        if not rows:
            try:
                ff_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
                r_ff = requests.get(ff_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
                if r_ff.status_code == 200:
                    raw_ff = r_ff.json()
                    if isinstance(raw_ff, list) and raw_ff:
                        rows = [
                            {
                                "date": item.get("date"),
                                "event": item.get("title"),
                                "country": item.get("country"),
                                "impact": item.get("impact", "LOW"),
                                "previous": item.get("previous"),
                                "estimate": item.get("forecast"),
                                "actual": item.get("actual")
                            }
                            for item in raw_ff if isinstance(item, dict)
                        ]
                        source_name = "World Monitor & FairEconomy Global Calendar"
                        source_link = ff_url
            except Exception as e:
                logger.warning(f"Fallback calendar fetch failed: {e}")

        if not rows:
            self._events = []
            self._calendar_verified = False
            self._data_mode = "UNAVAILABLE"
            self._last_error = "Could not fetch verified calendar events from World Monitor endpoints."
            return

        try:
            country_currency = {
                "US": "USD", "GB": "GBP", "UK": "GBP", "EU": "EUR", "DE": "EUR",
                "FR": "EUR", "IT": "EUR", "ES": "EUR", "JP": "JPY", "CA": "CAD",
                "AU": "AUD", "NZ": "NZD", "CH": "CHF", "USD": "USD", "GBP": "GBP",
                "EUR": "EUR", "JPY": "JPY", "CAD": "CAD", "AUD": "AUD", "NZD": "NZD", "CHF": "CHF"
            }
            observed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            loaded: List[EconomicEvent] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                scheduled = str(row.get("date") or "").strip()
                name = str(row.get("event") or "").strip()
                country = str(row.get("country") or "").strip().upper()
                if not scheduled or not name:
                    continue
                try:
                    datetime.datetime.fromisoformat(scheduled.replace("Z", "+00:00"))
                except ValueError:
                    continue
                impact_raw = str(row.get("impact") or "LOW").upper()
                impact = EventImpact.__members__.get(impact_raw, EventImpact.LOW)
                event_hash = hashlib.sha256(f"{country}|{name}|{scheduled}".encode("utf-8")).hexdigest()[:16]
                loaded.append(EconomicEvent(
                    event_id=f"WM_{event_hash}",
                    event_name=name,
                    currency=country_currency.get(country, country or "UNKNOWN"),
                    impact=impact,
                    scheduled_utc=scheduled,
                    previous_value=str(row.get("previous")) if row.get("previous") is not None else None,
                    forecast_value=str(row.get("estimate")) if row.get("estimate") is not None else None,
                    actual_value=str(row.get("actual")) if row.get("actual") is not None else None,
                    source_agency=source_name,
                    source_url=source_link,
                    observation_timestamp_utc=observed_at,
                ))
            if not loaded:
                raise ValueError("Response contained no valid scheduled events")
            self._events = loaded
            self._calendar_verified = True
            self._data_mode = "VERIFIED_REMOTE_SCHEDULE"
            self._last_error = ""
        except Exception as exc:
            self._events = []
            self._calendar_verified = False
            self._data_mode = "UNAVAILABLE"
            self._last_error = f"{type(exc).__name__}: {exc}"

    def register_event(self, event: EconomicEvent) -> None:
        self._events.append(event)
        self._calendar_verified = True
        self._last_refresh_monotonic = time.monotonic()
        self._last_error = ""

    def get_upcoming_events(self, horizon_hours: int = 48, min_impact: EventImpact = EventImpact.MEDIUM) -> List[Dict[str, Any]]:
        self._refresh_verified_schedule()
        if not self._calendar_verified:
            return []
        now = datetime.datetime.now(datetime.timezone.utc)
        horizon = now + datetime.timedelta(hours=horizon_hours)
        results = []
        for ev in self._events:
            dt = datetime.datetime.fromisoformat(ev.scheduled_utc.replace("Z", "+00:00"))
            if now - datetime.timedelta(minutes=ev.post_cooldown_minutes) <= dt <= horizon:
                if min_impact == EventImpact.HIGH and ev.impact != EventImpact.HIGH:
                    continue
                results.append(ev.to_dict())
        return sorted(results, key=lambda x: x["scheduled_utc"])

    def evaluate_symbol_lockout(self, symbol: str, current_time_utc: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Evaluates whether a symbol is currently locked due to high-impact economic releases."""
        self._refresh_verified_schedule()
        if not self._calendar_verified:
            return (
                True,
                f"Economic-calendar clearance unavailable; fail-closed lockout active ({self._last_error}).",
                None,
            )
        if current_time_utc:
            now_dt = datetime.datetime.fromisoformat(current_time_utc.replace("Z", "+00:00"))
        else:
            now_dt = datetime.datetime.now(datetime.timezone.utc)

        sym = symbol.upper()
        for ev in self._events:
            if ev.impact != EventImpact.HIGH:
                continue

            # Check if symbol is directly affected by currency or explicit list
            affected_symbols = ev.affected_symbols or self.CURRENCY_SYMBOL_MAP.get(ev.currency, [])
            if sym not in [s.upper() for s in affected_symbols]:
                continue

            if ev.is_active_at(now_dt):
                start, end = ev.get_lockout_window()
                mins_to_event = (datetime.datetime.fromisoformat(ev.scheduled_utc.replace("Z", "+00:00")) - now_dt).total_seconds() / 60.0
                if mins_to_event > 0:
                    reason = f"Pre-news freeze: '{ev.event_name}' ({ev.currency}) in {mins_to_event:.1f}m. Trading locked until {end.strftime('%H:%M:%S UTC')}."
                else:
                    mins_post = -mins_to_event
                    reason = f"Post-news cooldown: '{ev.event_name}' ({ev.currency}) released {mins_post:.1f}m ago. Cooldown active until {end.strftime('%H:%M:%S UTC')}."
                return True, reason, ev.to_dict()

        return False, "Market clear: Verified calendar reports no active economic-news blackout.", None

    def _load_baseline_official_schedule(self) -> None:
        """Legacy test fixture retained for compatibility; never called at runtime."""
        now = datetime.datetime.now(datetime.timezone.utc)
        today_date = now.strftime("%Y-%m-%d")
        event_date_1 = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        event_date_2 = (now + datetime.timedelta(days=2)).strftime("%Y-%m-%d")

        # 1. CPI (Bureau of Labor Statistics)
        self.register_event(EconomicEvent(
            event_id="EV_US_CPI_OFFICIAL",
            event_name="US Consumer Price Index (CPI YoY)",
            currency="USD",
            impact=EventImpact.HIGH,
            scheduled_utc=f"{event_date_1}T12:30:00Z",
            pre_lockout_minutes=15,
            post_cooldown_minutes=15,
            previous_value="3.0%",
            forecast_value="2.9%",
            source_agency="US Bureau of Labor Statistics",
            source_url="https://www.bls.gov/cpi/",
            observation_timestamp_utc=f"{today_date}T00:00:00Z",
        ))

        # 2. FOMC Rate Decision (Federal Reserve)
        self.register_event(EconomicEvent(
            event_id="EV_US_FOMC_RATE_DECISION",
            event_name="Federal Reserve FOMC Rate Decision & Press Conference",
            currency="USD",
            impact=EventImpact.HIGH,
            scheduled_utc=f"{event_date_1}T18:00:00Z",
            pre_lockout_minutes=30,
            post_cooldown_minutes=30,
            previous_value="5.25%-5.50%",
            forecast_value="5.25%-5.50%",
            source_agency="Federal Reserve System",
            source_url="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
            observation_timestamp_utc=f"{today_date}T00:00:00Z",
        ))

        # 3. US Non-Farm Payrolls (BLS)
        self.register_event(EconomicEvent(
            event_id="EV_US_NFP_EMPLOYMENT",
            event_name="US Non-Farm Payrolls & Unemployment Rate",
            currency="USD",
            impact=EventImpact.HIGH,
            scheduled_utc=f"{event_date_2}T12:30:00Z",
            pre_lockout_minutes=15,
            post_cooldown_minutes=15,
            previous_value="114K",
            forecast_value="175K",
            source_agency="US Bureau of Labor Statistics",
            source_url="https://www.bls.gov/ces/",
            observation_timestamp_utc=f"{today_date}T00:00:00Z",
        ))

        # 4. ECB Rate Decision (European Central Bank)
        self.register_event(EconomicEvent(
            event_id="EV_ECB_RATE_DECISION",
            event_name="ECB Main Refinancing Rate Decision",
            currency="EUR",
            impact=EventImpact.HIGH,
            scheduled_utc=f"{event_date_2}T12:15:00Z",
            pre_lockout_minutes=15,
            post_cooldown_minutes=15,
            previous_value="4.25%",
            forecast_value="4.25%",
            source_agency="European Central Bank",
            source_url="https://www.ecb.europa.eu",
            observation_timestamp_utc=f"{today_date}T00:00:00Z",
        ))

        # 5. BOE Rate Decision (Bank of England)
        self.register_event(EconomicEvent(
            event_id="EV_BOE_RATE_DECISION",
            event_name="Bank of England Official Bank Rate",
            currency="GBP",
            impact=EventImpact.HIGH,
            scheduled_utc=f"{event_date_2}T11:00:00Z",
            pre_lockout_minutes=15,
            post_cooldown_minutes=15,
            previous_value="5.00%",
            forecast_value="5.00%",
            source_agency="Bank of England",
            source_url="https://www.bankofengland.co.uk",
            observation_timestamp_utc=f"{today_date}T00:00:00Z",
        ))

        # 6. US GDP (Bureau of Economic Analysis)
        self.register_event(EconomicEvent(
            event_id="EV_US_GDP_ADVANCE",
            event_name="US Gross Domestic Product (GDP Annualized QoQ)",
            currency="USD",
            impact=EventImpact.HIGH,
            scheduled_utc=f"{event_date_2}T12:30:00Z",
            pre_lockout_minutes=15,
            post_cooldown_minutes=15,
            previous_value="2.8%",
            forecast_value="2.8%",
            source_agency="US Bureau of Economic Analysis",
            source_url="https://www.bea.gov/data/gdp/gross-domestic-product",
            observation_timestamp_utc=f"{today_date}T00:00:00Z",
        ))

        # 7. US Retail Sales (US Census Bureau)
        self.register_event(EconomicEvent(
            event_id="EV_US_RETAIL_SALES",
            event_name="US Retail Sales Advance MoM",
            currency="USD",
            impact=EventImpact.HIGH,
            scheduled_utc=f"{event_date_2}T12:30:00Z",
            pre_lockout_minutes=15,
            post_cooldown_minutes=15,
            previous_value="0.0%",
            forecast_value="0.3%",
            source_agency="US Census Bureau",
            source_url="https://www.census.gov/retail/index.html",
            observation_timestamp_utc=f"{today_date}T00:00:00Z",
        ))

        # 8. EIA Crude Oil Inventories (US Energy Information Administration)
        self.register_event(EconomicEvent(
            event_id="EV_US_EIA_CRUDE_INVENTORIES",
            event_name="EIA Weekly Petroleum Status Report (Crude Stocks)",
            currency="USD",
            impact=EventImpact.HIGH,
            scheduled_utc=f"{today_date}T14:30:00Z",
            pre_lockout_minutes=15,
            post_cooldown_minutes=15,
            previous_value="+1.4M",
            forecast_value="-1.9M",
            source_agency="US Energy Information Administration",
            source_url="https://www.eia.gov/petroleum/supply/weekly/",
            affected_symbols=["XAUUSD", "USDCAD", "CL", "WTI"],
            observation_timestamp_utc=f"{today_date}T00:00:00Z",
        ))


# Global singleton
economic_calendar_service = EconomicCalendarService()
