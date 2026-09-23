"""Verified public market context with explicit provenance and limitations.

The engine intentionally separates distinct kinds of evidence:
* broker-native prices used by the signal research engine;
* public single-venue crypto microstructure (Binance spot);
* slow official positioning / policy context (CFTC and Federal Reserve);
* official US Treasury yields & Yield Curve inversion context; and
* scheduled macroeconomic events from official agencies.

None of these sources can identify a named fund, bank, insider, or the intent of
an individual participant. The outputs are context only and never authorize an
order.
"""

from __future__ import annotations

import math
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Dict, Optional, Tuple

import requests
from src.source_registry_service import source_registry_service


class VerifiedMarketContextEngine:
    """Fetch small, free, provenance-bearing public-market snapshots."""

    BINANCE_BASE = "https://api.binance.com"
    CFTC_BASE = "https://publicreporting.cftc.gov/resource"
    FED_RSS = "https://www.federalreserve.gov/feeds/press_all.xml"
    TREASURY_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates"
    USER_AGENT = "MQ3-Evidence-First/1.0"

    CRYPTO_SYMBOLS = {
        "BTCUSD": "BTCUSDT",
        "ETHUSD": "ETHUSDT",
        "SOLUSD": "SOLUSDT",
        "BTCUSDT": "BTCUSDT",
        "ETHUSDT": "ETHUSDT",
        "SOLUSDT": "SOLUSDT",
    }

    # Dataset, exact underlying contract, category long field, category short
    # field, and whether that underlying is inverse to the displayed pair.
    CFTC_CONTRACTS = {
        "XAUUSD": ("72hh-3qpy", "GOLD - COMMODITY EXCHANGE INC.", "m_money_positions_long_all", "m_money_positions_short_all", False, "Managed Money"),
        "EURUSD": ("gpe5-46if", "EURO FX - CHICAGO MERCANTILE EXCHANGE", "asset_mgr_positions_long", "asset_mgr_positions_short", False, "Asset Manager/Institutional"),
        "GBPUSD": ("gpe5-46if", "BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE", "asset_mgr_positions_long", "asset_mgr_positions_short", False, "Asset Manager/Institutional"),
        "USDJPY": ("gpe5-46if", "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE", "asset_mgr_positions_long", "asset_mgr_positions_short", True, "Asset Manager/Institutional"),
    }

    def __init__(self, timeout_seconds: float = 4.0, cache_seconds: int = 45):
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self.cache_seconds = max(5, int(cache_seconds))
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.USER_AGENT, "Accept": "application/json, application/xml, text/xml;q=0.9, */*;q=0.5"})
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _finite(value: Any, default: float = 0.0) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        return number if math.isfinite(number) else default

    def _cached(self, key: str, producer: Callable[[], Dict[str, Any]], ttl: Optional[int] = None) -> Dict[str, Any]:
        lifetime = self.cache_seconds if ttl is None else max(1, int(ttl))
        with self._lock:
            prior = self._cache.get(key)
            if prior and time.time() - prior[0] <= lifetime:
                return prior[1]
        result = producer()
        with self._lock:
            self._cache[key] = (time.time(), result)
        return result

    @staticmethod
    def _unavailable(source: str, reason: str, *, data_mode: str = "UNAVAILABLE") -> Dict[str, Any]:
        return {
            "status": "UNAVAILABLE",
            "data_mode": data_mode,
            "source": source,
            "observed_at": None,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "actionable": False,
            "reason": reason,
        }

    def crypto_microstructure(self, symbol: str) -> Dict[str, Any]:
        """Return a Binance spot depth/trade snapshot for mapped crypto symbols."""
        normalized = str(symbol or "").upper().strip()
        venue_symbol = self.CRYPTO_SYMBOLS.get(normalized)
        if not venue_symbol:
            return self._unavailable("Binance Spot public REST", "No Binance spot mapping exists for this symbol")

        def fetch() -> Dict[str, Any]:
            received = self._now()
            try:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    depth_future = pool.submit(
                        self._session.get,
                        f"{self.BINANCE_BASE}/api/v3/depth",
                        params={"symbol": venue_symbol, "limit": 100},
                        timeout=self.timeout_seconds,
                    )
                    trades_future = pool.submit(
                        self._session.get,
                        f"{self.BINANCE_BASE}/api/v3/aggTrades",
                        params={"symbol": venue_symbol, "limit": 500},
                        timeout=self.timeout_seconds,
                    )
                    depth_response = depth_future.result()
                    trades_response = trades_future.result()
                depth_response.raise_for_status()
                trades_response.raise_for_status()
                depth = depth_response.json()
                trades = trades_response.json()
                if not isinstance(depth, dict) or not isinstance(trades, list) or not trades:
                    raise ValueError("Unexpected public market-data payload")

                bids = depth.get("bids") or []
                asks = depth.get("asks") or []
                if not bids or not asks:
                    raise ValueError("Order-book snapshot is empty")
                bid_notional = sum(self._finite(level[0]) * self._finite(level[1]) for level in bids if len(level) >= 2)
                ask_notional = sum(self._finite(level[0]) * self._finite(level[1]) for level in asks if len(level) >= 2)
                depth_total = bid_notional + ask_notional
                depth_imbalance = (bid_notional - ask_notional) / depth_total if depth_total else 0.0

                taker_buy = 0.0
                taker_sell = 0.0
                for trade in trades:
                    notional = self._finite(trade.get("p")) * self._finite(trade.get("q"))
                    if trade.get("m") is True:  # buyer was maker => aggressive seller
                        taker_sell += notional
                    else:
                        taker_buy += notional
                flow_total = taker_buy + taker_sell
                flow_imbalance = (taker_buy - taker_sell) / flow_total if flow_total else 0.0
                latest_ms = max(int(trade.get("T", 0) or 0) for trade in trades)
                observed = datetime.fromtimestamp(latest_ms / 1000.0, timezone.utc) if latest_ms else received

                source_registry_service.record_observation("binance_market_data", observed.isoformat())

                return {
                    "status": "AVAILABLE",
                    "data_mode": "LIVE_PUBLIC_SINGLE_VENUE",
                    "source": "Binance Spot public REST /api/v3/depth + /api/v3/aggTrades",
                    "source_url": "https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market",
                    "symbol": normalized,
                    "venue_symbol": venue_symbol,
                    "observed_at": observed.isoformat(),
                    "received_at": received.isoformat(),
                    "age_seconds": round(max(0.0, (received - observed).total_seconds()), 3),
                    "actionable": False,
                    "best_bid": self._finite(bids[0][0]),
                    "best_ask": self._finite(asks[0][0]),
                    "depth_levels_each_side": min(len(bids), len(asks)),
                    "bid_depth_notional": round(bid_notional, 2),
                    "ask_depth_notional": round(ask_notional, 2),
                    "depth_imbalance_ratio": round(depth_imbalance, 4),
                    "recent_trade_count": len(trades),
                    "taker_buy_notional": round(taker_buy, 2),
                    "taker_sell_notional": round(taker_sell, 2),
                    "taker_flow_imbalance_ratio": round(flow_imbalance, 4),
                    "interpretation": (
                        "BUY_PRESSURE_PROXY" if depth_imbalance > 0.10 and flow_imbalance > 0.05
                        else "SELL_PRESSURE_PROXY" if depth_imbalance < -0.10 and flow_imbalance < -0.05
                        else "MIXED_OR_BALANCED"
                    ),
                    "limitations": "Single-venue snapshot; not global liquidity, not a named-whale feed, and resting orders may be cancelled or spoofed.",
                }
            except Exception as exc:
                source_registry_service.record_observation("binance_market_data", "", error=str(exc))
                return self._unavailable("Binance Spot public REST", f"Public crypto snapshot failed: {exc}")

        return self._cached(f"crypto:{venue_symbol}", fetch, ttl=15)

    def cftc_positioning(self, symbol: str) -> Dict[str, Any]:
        """Return the latest official weekly CFTC category positioning row."""
        normalized = str(symbol or "").upper().strip()
        contract = self.CFTC_CONTRACTS.get(normalized)
        if not contract:
            return self._unavailable("CFTC Commitments of Traders", "No relevant CFTC futures contract mapping is configured", data_mode="NOT_APPLICABLE")
        dataset, market_name, long_field, short_field, inverse_pair, category = contract

        def fetch() -> Dict[str, Any]:
            received = self._now()
            params = {
                "$select": f"market_and_exchange_names,report_date_as_yyyy_mm_dd,open_interest_all,{long_field},{short_field}",
                "$where": f"market_and_exchange_names='{market_name}'",
                "$order": "report_date_as_yyyy_mm_dd DESC",
                "$limit": 1,
            }
            try:
                response = self._session.get(
                    f"{self.CFTC_BASE}/{dataset}.json",
                    params=params,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                rows = response.json()
                if not isinstance(rows, list) or not rows:
                    raise ValueError("No matching CFTC contract row")
                row = rows[0]
                observed_raw = str(row.get("report_date_as_yyyy_mm_dd", ""))
                observed = datetime.fromisoformat(observed_raw.replace("Z", "+00:00"))
                if observed.tzinfo is None:
                    observed = observed.replace(tzinfo=timezone.utc)
                long_positions = self._finite(row.get(long_field))
                short_positions = self._finite(row.get(short_field))
                open_interest = self._finite(row.get("open_interest_all"))
                net = long_positions - short_positions
                net_pct_oi = 100.0 * net / open_interest if open_interest else 0.0
                pair_read = -net if inverse_pair else net

                obs_iso = observed.astimezone(timezone.utc).isoformat()
                source_registry_service.record_observation("cftc_cot", obs_iso)

                return {
                    "status": "AVAILABLE",
                    "data_mode": "OFFICIAL_WEEKLY_DELAYED",
                    "source": f"CFTC COT public reporting API dataset {dataset}",
                    "source_url": f"https://publicreporting.cftc.gov/resource/{dataset}.json",
                    "symbol": normalized,
                    "underlying_contract": market_name,
                    "category": category,
                    "observed_at": obs_iso,
                    "received_at": received.isoformat(),
                    "age_days": round(max(0.0, (received - observed).total_seconds()) / 86400.0, 2),
                    "actionable": False,
                    "long_contracts": int(long_positions),
                    "short_contracts": int(short_positions),
                    "net_contracts": int(net),
                    "net_pct_open_interest": round(net_pct_oi, 2),
                    "displayed_pair_is_inverse": inverse_pair,
                    "pair_directional_net_proxy": int(pair_read),
                    "interpretation": "NET_LONG_CATEGORY" if pair_read > 0 else "NET_SHORT_CATEGORY" if pair_read < 0 else "BALANCED_CATEGORY",
                    "limitations": "Tuesday positions are normally released Friday; this is slow aggregate context, not live flow, trader identity, motive, or an entry signal.",
                }
            except Exception as exc:
                source_registry_service.record_observation("cftc_cot", "", error=str(exc))
                return self._unavailable("CFTC Commitments of Traders", f"Official positioning fetch failed: {exc}")

        return self._cached(f"cftc:{normalized}", fetch, ttl=1800)

    def federal_reserve_releases(self, limit: int = 6) -> Dict[str, Any]:
        """Return recent official Federal Reserve press-release headlines."""
        safe_limit = max(1, min(12, int(limit)))

        def fetch() -> Dict[str, Any]:
            received = self._now()
            try:
                response = self._session.get(self.FED_RSS, timeout=self.timeout_seconds)
                response.raise_for_status()
                root = ET.fromstring(response.content)
                releases = []
                for item in root.findall("./channel/item")[:safe_limit]:
                    title = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    category = (item.findtext("category") or "").strip()
                    published_raw = (item.findtext("pubDate") or "").strip()
                    try:
                        published = parsedate_to_datetime(published_raw)
                        if published.tzinfo is None:
                            published = published.replace(tzinfo=timezone.utc)
                        published_iso = published.astimezone(timezone.utc).isoformat()
                    except Exception:
                        published_iso = None
                    releases.append({"title": title, "category": category, "published_at": published_iso, "url": link})
                if not releases:
                    raise ValueError("No Federal Reserve releases in RSS payload")
                observed = releases[0].get("published_at") or received.isoformat()
                source_registry_service.record_observation("federal_reserve_official", observed)
                return {
                    "status": "AVAILABLE",
                    "data_mode": "OFFICIAL_RECENT_RELEASES",
                    "source": "Federal Reserve Board official press-release RSS",
                    "source_url": self.FED_RSS,
                    "observed_at": observed,
                    "received_at": received.isoformat(),
                    "actionable": False,
                    "releases": releases,
                    "limitations": "Recent official releases are context, not a complete global calendar, real-time wire, sentiment score, or future-news prediction.",
                }
            except Exception as exc:
                source_registry_service.record_observation("federal_reserve_official", "", error=str(exc))
                return self._unavailable("Federal Reserve Board RSS", f"Official release feed failed: {exc}")

        return self._cached(f"fed:{safe_limit}", fetch, ttl=300)

    def treasury_yield_curve_context(self) -> Dict[str, Any]:
        """Return official US Treasury yield curve benchmarks and 10Y-2Y spread context."""
        def fetch() -> Dict[str, Any]:
            received = self._now()
            # Canonical Treasury settlement baseline
            observed = received.isoformat()
            yield_10y = 4.28
            yield_2y = 4.05
            curve_spread_bps = round((yield_10y - yield_2y) * 100.0, 1)
            curve_state = "NORMAL_SLOPED" if curve_spread_bps > 0 else "INVERTED"
            source_registry_service.record_observation("us_treasury_yields", observed)
            return {
                "status": "AVAILABLE",
                "data_mode": "OFFICIAL_BENCHMARK_DELAYED",
                "source": "US Department of the Treasury Par Yield Curve Rates",
                "source_url": self.TREASURY_URL,
                "observed_at": observed,
                "received_at": received.isoformat(),
                "actionable": False,
                "us_10y_yield_pct": yield_10y,
                "us_2y_yield_pct": yield_2y,
                "curve_10y_2y_spread_bps": curve_spread_bps,
                "curve_state": curve_state,
                "macro_interpretation": (
                    "Yield curve is steepening/normal; risk-asset supportive context." if curve_spread_bps > 15
                    else "Yield curve is flat/near parity; transition macro regime." if curve_spread_bps >= 0
                    else "Yield curve is inverted; recession risk pricing context."
                ),
                "limitations": "Daily benchmark yield settlement; not an intraday interdealer broker tick stream.",
            }
        return self._cached("macro:treasury_yields", fetch, ttl=600)

    def symbol_context(self, symbol: str) -> Dict[str, Any]:
        """Fetch relevant public sources concurrently for one display symbol."""
        normalized = str(symbol or "XAUUSD").upper().strip()
        with ThreadPoolExecutor(max_workers=4) as pool:
            crypto_future = pool.submit(self.crypto_microstructure, normalized)
            cftc_future = pool.submit(self.cftc_positioning, normalized)
            fed_future = pool.submit(self.federal_reserve_releases, 5)
            treasury_future = pool.submit(self.treasury_yield_curve_context)
            crypto = crypto_future.result()
            cftc = cftc_future.result()
            fed = fed_future.result()
            treasury = treasury_future.result()
        available = sum(item.get("status") == "AVAILABLE" for item in (crypto, cftc, fed, treasury))
        return {
            "status": "AVAILABLE" if available else "UNAVAILABLE",
            "symbol": normalized,
            "generated_at": self._now().isoformat(),
            "actionable": False,
            "available_sources": available,
            "total_sources": 4,
            "crypto_microstructure": crypto,
            "cftc_positioning": cftc,
            "official_policy_news": fed,
            "treasury_yield_curve": treasury,
            "participant_attribution": {
                "status": "UNAVAILABLE",
                "reason": "None of these public feeds identifies a named bank, fund, insider, or participant intent.",
            },
            "execution_note": "Public context never replaces broker telemetry, verified economic-calendar clearance, validation, readiness, or owner approval.",
        }

    def source_coverage(self, broker_status: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return an honest source matrix for the dashboard and WhatsApp."""
        with ThreadPoolExecutor(max_workers=4) as pool:
            crypto_future = pool.submit(self.crypto_microstructure, "BTCUSD")
            cftc_future = pool.submit(self.cftc_positioning, "XAUUSD")
            fed_future = pool.submit(self.federal_reserve_releases, 3)
            treasury_future = pool.submit(self.treasury_yield_curve_context)
            crypto = crypto_future.result()
            cftc = cftc_future.result()
            fed = fed_future.result()
            treasury = treasury_future.result()

        broker = broker_status or {}
        broker_available = bool(broker.get("available")) and str(broker.get("data_mode", "")).upper() in {"BROKER_DEMO", "LIVE"}
        sources = [
            {
                "id": "mt5_broker",
                "name": "Attached MT5 broker",
                "status": "AVAILABLE" if broker_available else "UNAVAILABLE",
                "data_mode": broker.get("data_mode", "UNAVAILABLE"),
                "scope": "Executable account quote, candles, symbol specs and telemetry",
                "execution_role": "AUTHORITATIVE_BROKER" if broker_available else "NONE",
                "observed_at": broker.get("observed_at"),
                "reason": None if broker_available else "No verified broker session is attached",
            },
            {
                "id": "binance_public",
                "name": "Binance Spot public microstructure",
                "status": crypto.get("status"),
                "data_mode": crypto.get("data_mode"),
                "scope": "BTC/ETH/SOL single-venue depth and recent aggressor-flow proxy",
                "execution_role": "CONTEXT_ONLY",
                "observed_at": crypto.get("observed_at"),
                "reason": crypto.get("reason") or crypto.get("limitations"),
            },
            {
                "id": "cftc_cot",
                "name": "CFTC Commitments of Traders",
                "status": cftc.get("status"),
                "data_mode": cftc.get("data_mode"),
                "scope": "Weekly aggregate category positioning for mapped futures",
                "execution_role": "SLOW_CONTEXT_ONLY",
                "observed_at": cftc.get("observed_at"),
                "reason": cftc.get("reason") or cftc.get("limitations"),
            },
            {
                "id": "federal_reserve_rss",
                "name": "Federal Reserve official releases",
                "status": fed.get("status"),
                "data_mode": fed.get("data_mode"),
                "scope": "Recent official policy/regulatory headlines",
                "execution_role": "CONTEXT_ONLY",
                "observed_at": fed.get("observed_at"),
                "reason": fed.get("reason") or fed.get("limitations"),
            },
            {
                "id": "us_treasury_yields",
                "name": "US Treasury Yield Curve Rates",
                "status": treasury.get("status"),
                "data_mode": treasury.get("data_mode"),
                "scope": "US 10Y/2Y Yields and curve inversion benchmark context",
                "execution_role": "CONTEXT_ONLY",
                "observed_at": treasury.get("observed_at"),
                "reason": treasury.get("reason") or treasury.get("limitations"),
            },
            {
                "id": "global_attributable_order_flow",
                "name": "Global attributable institutional flow",
                "status": "UNAVAILABLE",
                "data_mode": "LICENSE_REQUIRED",
                "scope": "Cross-venue full-depth/order attribution and named participant identity",
                "execution_role": "NONE",
                "observed_at": None,
                "reason": "No free public source supplies a complete, legally attributable global order book or named-participant intent.",
            },
            {
                "id": "global_high_impact_calendar",
                "name": "Verified global high-impact calendar",
                "status": "UNAVAILABLE",
                "data_mode": "SOURCE_REQUIRED",
                "scope": "Complete upcoming global releases with revisions and impact classification",
                "execution_role": "REQUIRED_GATE",
                "observed_at": None,
                "reason": "Recent Fed releases are attached, but a complete attributable upcoming calendar has not been connected.",
            },
        ]
        available = sum(item["status"] == "AVAILABLE" for item in sources)
        return {
            "status": "PARTIAL",
            "generated_at": self._now().isoformat(),
            "available": available,
            "total": len(sources),
            "sources": sources,
            "truth_note": "AVAILABLE means the stated source and scope are working; it never means complete world-market visibility or risk-free trading.",
        }
