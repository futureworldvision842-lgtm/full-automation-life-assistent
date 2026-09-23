"""Source Registry & Data Provenance Service for MQ3 Trading Platform.

Enforces the non-negotiable Data-Provenance Contract:
Every source must declare:
- Stable source ID
- Source name
- Official URL or API documentation
- Provider
- Venue
- Asset scope
- Data type
- Live, delayed, weekly, historical, simulated, or model-output mode
- Observation time
- Ingestion time
- Freshness threshold
- Current age
- Timezone
- License or terms note
- Current health
- Last successful observation
- Last error
- Known limitations
- Whether it may influence research
- Whether it may influence execution
"""

from __future__ import annotations

import dataclasses
import datetime
import enum
import json
import logging
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SourceDataMode(str, enum.Enum):
    LIVE = "LIVE"
    DELAYED = "DELAYED"
    WEEKLY = "WEEKLY"
    HISTORICAL = "HISTORICAL"
    SIMULATED = "SIMULATED"
    MODEL_OUTPUT = "MODEL_OUTPUT"
    UNAVAILABLE = "UNAVAILABLE"


class SourceHealth(str, enum.Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    UNCONFIGURED = "UNCONFIGURED"


@dataclasses.dataclass
class SourceRecord:
    source_id: str
    source_name: str
    official_url: Optional[str]
    provider: str
    venue: str
    asset_scope: List[str]
    data_type: str
    mode: SourceDataMode
    freshness_threshold_seconds: float
    timezone: str = "UTC"
    license_note: str = ""
    known_limitations: str = ""
    influences_research: bool = True
    influences_execution: bool = False
    current_health: SourceHealth = SourceHealth.HEALTHY
    last_observation_utc: Optional[str] = None
    last_ingestion_utc: Optional[str] = None
    last_error: Optional[str] = None

    def get_age_seconds(self, current_time_utc: Optional[datetime.datetime] = None) -> Optional[float]:
        if not self.last_observation_utc:
            return None
        try:
            obs_dt = datetime.datetime.fromisoformat(self.last_observation_utc.replace("Z", "+00:00"))
            now_dt = current_time_utc or datetime.datetime.now(datetime.timezone.utc)
            return max(0.0, (now_dt - obs_dt).total_seconds())
        except (ValueError, TypeError):
            return None

    def evaluate_freshness(self, current_time_utc: Optional[datetime.datetime] = None) -> Tuple[bool, str]:
        if self.mode == SourceDataMode.UNAVAILABLE:
            return False, f"Source {self.source_id} is UNAVAILABLE"
        age = self.get_age_seconds(current_time_utc)
        if age is None:
            return False, f"Source {self.source_id} has no valid observation timestamp"
        if age > self.freshness_threshold_seconds:
            return False, f"Source {self.source_id} is stale: age {age:.1f}s > threshold {self.freshness_threshold_seconds:.1f}s"
        return True, "Fresh"

    def to_dict(self) -> Dict[str, Any]:
        age = self.get_age_seconds()
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "official_url": self.official_url,
            "provider": self.provider,
            "venue": self.venue,
            "asset_scope": self.asset_scope,
            "data_type": self.data_type,
            "mode": self.mode.value,
            "freshness_threshold_seconds": self.freshness_threshold_seconds,
            "age_seconds": round(age, 2) if age is not None else None,
            "timezone": self.timezone,
            "license_note": self.license_note,
            "known_limitations": self.known_limitations,
            "influences_research": self.influences_research,
            "influences_execution": self.influences_execution,
            "current_health": self.current_health.value,
            "last_observation_utc": self.last_observation_utc,
            "last_ingestion_utc": self.last_ingestion_utc,
            "last_error": self.last_error,
        }


class SourceRegistryService:
    """Central registry and health monitor for all external market data sources."""

    def __init__(self, registry_file: Optional[str] = None):
        self.registry_file = registry_file or str(Path(__file__).resolve().parents[1] / "data" / "source_registry.json")
        self._sources: Dict[str, SourceRecord] = {}
        self._load_sources()

    def register_source(self, source: SourceRecord) -> None:
        self._sources[source.source_id] = source

    def get_source(self, source_id: str) -> Optional[SourceRecord]:
        return self._sources.get(source_id)

    def record_observation(self, source_id: str, observation_utc: str, error: Optional[str] = None) -> None:
        src = self._sources.get(source_id)
        if src:
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            src.last_ingestion_utc = now_iso
            if error:
                src.last_error = error
                src.current_health = SourceHealth.DEGRADED
            else:
                src.last_observation_utc = observation_utc
                src.last_error = None
                src.current_health = SourceHealth.HEALTHY

    def list_sources(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._sources.values()]

    def _load_sources(self) -> None:
        """Initializes canonical verified official and broker sources."""
        # 1. MT5 Broker Native
        self.register_source(SourceRecord(
            source_id="mt5_broker",
            source_name="MetaTrader 5 Broker Gateway",
            official_url="https://www.mql5.com/en/docs/python_metatrader5",
            provider="MetaQuotes / Attached Broker (Funding Pips / Demo)",
            venue="MT5 Broker Gateway",
            asset_scope=["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"],
            data_type="OHLCV Candles, Bid/Ask Ticks, Account Telemetry, Symbol Specs",
            mode=SourceDataMode.LIVE,
            freshness_threshold_seconds=5.0,
            license_note="Licensed broker client terminal connector",
            known_limitations="Execution quotes and liquidity are specific to the attached broker; not a global exchange composite.",
            influences_research=True,
            influences_execution=True,
            current_health=SourceHealth.HEALTHY,
        ))

        # 2. Binance Spot Microstructure
        self.register_source(SourceRecord(
            source_id="binance_market_data",
            source_name="Binance Public Spot API",
            official_url="https://developers.binance.com/en/docs/catalog",
            provider="Binance Public API",
            venue="Binance Spot Exchange",
            asset_scope=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            data_type="Single-venue L2 Order Book Depth, Trades, Klines",
            mode=SourceDataMode.LIVE,
            freshness_threshold_seconds=15.0,
            license_note="Official free public API terms",
            known_limitations="Single-venue crypto spot snapshot. Does not represent global crypto liquidity, offshore derivatives, or participant identity.",
            influences_research=True,
            influences_execution=False,
            current_health=SourceHealth.HEALTHY,
        ))

        # 3. CFTC Commitments of Traders
        self.register_source(SourceRecord(
            source_id="cftc_cot",
            source_name="CFTC Commitments of Traders (CoT)",
            official_url="https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm",
            provider="US Commodity Futures Trading Commission",
            venue="CME / COMEX / NYMEX Futures Exchanges",
            asset_scope=["Gold", "Euro", "British Pound", "Japanese Yen", "WTI Crude"],
            data_type="Weekly aggregate commercial & institutional positioning",
            mode=SourceDataMode.WEEKLY,
            freshness_threshold_seconds=7 * 86400.0,
            license_note="US Government Public Domain",
            known_limitations="Reported on Friday for positions held on prior Tuesday. Slow macro aggregate; cannot identify individual traders or intraday order flow.",
            influences_research=True,
            influences_execution=False,
            current_health=SourceHealth.HEALTHY,
        ))

        # 4. Federal Reserve Official Releases
        self.register_source(SourceRecord(
            source_id="federal_reserve_official",
            source_name="Federal Reserve Board Press Releases & Policy",
            official_url="https://www.federalreserve.gov/feeds/press_all.xml",
            provider="Board of Governors of the Federal Reserve System",
            venue="Federal Reserve",
            asset_scope=["USD", "US Interest Rates", "Macro Policy"],
            data_type="Official Monetary Policy Statements, FOMC Minutes, Press Releases",
            mode=SourceDataMode.DELAYED,
            freshness_threshold_seconds=86400.0,
            license_note="US Government Public Domain",
            known_limitations="Official policy statements and historical decisions; not a live tick stream or upcoming predictive calendar.",
            influences_research=True,
            influences_execution=False,
            current_health=SourceHealth.HEALTHY,
        ))

        # 5. US Bureau of Labor Statistics (BLS)
        self.register_source(SourceRecord(
            source_id="us_bls_official",
            source_name="US Bureau of Labor Statistics Official Data",
            official_url="https://www.bls.gov/",
            provider="US Department of Labor",
            venue="US Official Government Data",
            asset_scope=["CPI", "Core CPI", "NFP", "Unemployment Rate", "PPI"],
            data_type="Official macroeconomic releases and inflation time series",
            mode=SourceDataMode.DELAYED,
            freshness_threshold_seconds=86400.0 * 30,
            license_note="US Government Public Domain",
            known_limitations="Historical benchmark series and scheduled releases. Subject to official revisions.",
            influences_research=True,
            influences_execution=False,
            current_health=SourceHealth.HEALTHY,
        ))

        # 6. European Central Bank (ECB)
        self.register_source(SourceRecord(
            source_id="ecb_official",
            source_name="European Central Bank Monetary Decisions",
            official_url="https://www.ecb.europa.eu",
            provider="European Central Bank",
            venue="Eurosystem",
            asset_scope=["EUR", "Main Refinancing Rate", "Deposit Facility Rate"],
            data_type="Official monetary policy decisions and press releases",
            mode=SourceDataMode.DELAYED,
            freshness_threshold_seconds=86400.0 * 14,
            license_note="Official public domain / open access",
            known_limitations="Official monetary decisions; not a tick quote feed.",
            influences_research=True,
            influences_execution=False,
            current_health=SourceHealth.HEALTHY,
        ))

        # 7. Bank of England (BOE)
        self.register_source(SourceRecord(
            source_id="boe_official",
            source_name="Bank of England Monetary Policy",
            official_url="https://www.bankofengland.co.uk",
            provider="Bank of England",
            venue="United Kingdom Central Bank",
            asset_scope=["GBP", "Official Bank Rate", "MPC Votes"],
            data_type="Official interest rate decisions and monetary policy summaries",
            mode=SourceDataMode.DELAYED,
            freshness_threshold_seconds=86400.0 * 14,
            license_note="Crown Copyright / Open Government Licence",
            known_limitations="Scheduled policy rate announcements only.",
            influences_research=True,
            influences_execution=False,
            current_health=SourceHealth.HEALTHY,
        ))

        # 8. US Treasury Yield Context
        self.register_source(SourceRecord(
            source_id="us_treasury_yields",
            source_name="US Department of the Treasury Yield Curve Rates",
            official_url="https://home.treasury.gov/resource-center/data-chart-center/interest-rates",
            provider="US Department of the Treasury",
            venue="US Government Bond Market",
            asset_scope=["US10Y", "US02Y", "10Y-2Y Yield Curve Spread"],
            data_type="Daily Treasury Par Yield Curve Rates",
            mode=SourceDataMode.DELAYED,
            freshness_threshold_seconds=86400.0 * 2,
            license_note="US Government Public Domain",
            known_limitations="Daily official settlement yields, not live interdealer tick stream.",
            influences_research=True,
            influences_execution=False,
            current_health=SourceHealth.HEALTHY,
        ))

        # 9. Global Attributable Order Flow (Explicitly Unavailable)
        self.register_source(SourceRecord(
            source_id="global_order_flow_attribution",
            source_name="Global Cross-Venue Attributable Order Flow",
            official_url=None,
            provider="Institutional Commercial Feeds (Unavailable)",
            venue="Global Multi-Venue Composite",
            asset_scope=["Global Multi-Asset"],
            data_type="Institutional participant identity and global aggregate DOM",
            mode=SourceDataMode.UNAVAILABLE,
            freshness_threshold_seconds=0.0,
            license_note="Proprietary commercial license required",
            known_limitations="No free or single-broker feed provides complete legally attributable global order flow or participant identity. Fails closed.",
            influences_research=False,
            influences_execution=False,
            current_health=SourceHealth.UNAVAILABLE,
        ))


source_registry_service = SourceRegistryService()
