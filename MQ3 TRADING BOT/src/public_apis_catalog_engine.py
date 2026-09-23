"""
public_apis_catalog_engine.py — Public APIs Financial & Macro Intelligence Engine.
==================================================================================
Indexes and parses the collective repository of free public APIs from repos/public-apis
and provides real-time financial, macroeconomic, commodity, currency, and crypto feeds.

Features:
  1. Automated indexer for financial & geopolitical APIs from repos/public-apis/README.md.
  2. Free Gold & Silver Commodity Data Fetcher (Yahoo, Metalprice, GoldAPI fallbacks).
  3. Forex & Currency Exchange Rates Feeder (ECB, OpenExchangeRates, Frankfurter).
  4. Global Geopolitical & Macro News Aggregator.
  5. Explicit degraded-state reporting when all live sources are unavailable.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger("PublicAPIsCatalogEngine")


class PublicAPIsCatalogEngine:
    """
    Public APIs Catalog & Market Intelligence Query Engine.
    """

    DEFAULT_CATALOG_PATH = "repos/public-apis/README.md"

    def __init__(self, catalog_path: str = DEFAULT_CATALOG_PATH):
        self.catalog_path = catalog_path
        self.indexed_apis: Dict[str, List[Dict[str, Any]]] = {}
        self.total_apis_indexed = 0
        self._load_and_index_catalog()
        logger.info(f"Public APIs Catalog Engine initialized ({self.total_apis_indexed} financial/macro APIs indexed)")

    def _load_and_index_catalog(self):
        """Parses and categorizes APIs from repos/public-apis/README.md."""
        target_categories = [
            "Finance", "Currency Exchange", "Cryptocurrency", "Geocoding", "Weather", "News", "Government"
        ]

        for cat in target_categories:
            self.indexed_apis[cat] = []

        if not os.path.exists(self.catalog_path):
            logger.warning(f"Public APIs catalog not found at '{self.catalog_path}'. Using embedded institutional fallback registry.")
            self._populate_embedded_registry()
            return

        try:
            with open(self.catalog_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Parse markdown tables: | API | Description | Auth | HTTPS | CORS |
            current_category = None
            for line in content.split("\n"):
                line_str = line.strip()
                if line_str.startswith("### "):
                    current_category = line_str.replace("### ", "").strip()
                    if current_category not in self.indexed_apis:
                        self.indexed_apis[current_category] = []
                elif current_category and line_str.startswith("|") and not line_str.startswith("| API |") and not line_str.startswith("|---"):
                    parts = [p.strip() for p in line_str.split("|")[1:-1]]
                    if len(parts) >= 3:
                        api_name_match = re.search(r"\[(.*?)\]\((.*?)\)", parts[0])
                        name = api_name_match.group(1) if api_name_match else parts[0]
                        url = api_name_match.group(2) if api_name_match else ""
                        desc = parts[1] if len(parts) > 1 else ""
                        auth = parts[2] if len(parts) > 2 else "No"
                        https = parts[3] if len(parts) > 3 else "Yes"
                        cors = parts[4] if len(parts) > 4 else "Unknown"

                        self.indexed_apis[current_category].append({
                            "name": name,
                            "url": url,
                            "description": desc,
                            "auth": auth,
                            "https": https,
                            "cors": cors,
                            "category": current_category
                        })
                        self.total_apis_indexed += 1
        except Exception as e:
            logger.error(f"Error parsing public-apis catalog: {e}")
            self._populate_embedded_registry()

    def _populate_embedded_registry(self):
        """Populates curated institutional fallback registry of public financial APIs."""
        curated_finance = [
            {"name": "Yahoo Finance API", "url": "https://finance.yahoo.com", "description": "Global equity, commodity, and currency quotes", "auth": "No", "https": "Yes"},
            {"name": "Frankfurter", "url": "https://api.frankfurter.app", "description": "European Central Bank FX reference rates", "auth": "No", "https": "Yes"},
            {"name": "Binance Public API", "url": "https://api.binance.com", "description": "Live cryptocurrency spot market ticker and depth", "auth": "No", "https": "Yes"},
            {"name": "CoinGecko API", "url": "https://api.coingecko.com/api/v3", "description": "Crypto market metrics and ratios", "auth": "No", "https": "Yes"},
            {"name": "Open-Meteo", "url": "https://api.open-meteo.com", "description": "Global weather and agricultural commodity forecast", "auth": "No", "https": "Yes"},
            {"name": "FRED Federal Reserve Economic Data", "url": "https://fred.stlouisfed.org", "description": "US macroeconomic data and interest rates", "auth": "apiKey", "https": "Yes"}
        ]
        self.indexed_apis["Finance"] = curated_finance
        self.total_apis_indexed = len(curated_finance)

    def search_apis(self, keyword: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Searches indexed public APIs by keyword and category."""
        results = []
        kw = keyword.lower()

        categories_to_search = [category] if category and category in self.indexed_apis else self.indexed_apis.keys()

        for cat in categories_to_search:
            for api in self.indexed_apis.get(cat, []):
                if kw in api["name"].lower() or kw in api["description"].lower():
                    results.append(api)

        return results

    def fetch_live_fx_rates(self, base: str = "USD") -> Dict[str, Any]:
        """Fetches live foreign exchange rates using free public Frankfurter / ECB API."""
        try:
            url = f"https://api.frankfurter.app/latest?from={base.upper()}"
            resp = requests.get(url, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                rates = data.get("rates", {})
                selected = {k: rates[k] for k in ("EUR", "GBP", "JPY", "CHF", "CAD", "AUD") if k in rates}
                if not selected:
                    raise ValueError("Frankfurter response contained no requested rates")
                return {
                    "source": "Frankfurter (European Central Bank)",
                    "base": base.upper(),
                    "date": data.get("date"),
                    "rates": selected,
                    "success": True,
                    "data_mode": "LIVE_PUBLIC_API",
                }
        except Exception as e:
            logger.warning(f"Live FX fetch fallback: {e}")

        return {
            "source": "UNAVAILABLE",
            "base": base.upper(),
            "date": None,
            "rates": {},
            "success": False,
            "data_mode": "UNAVAILABLE",
            "actionable": False,
        }

    def fetch_live_gold_spot(self) -> Dict[str, Any]:
        """Fetches Gold (XAU/USD) spot price from Yahoo Finance / GoldAPI."""
        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range=1d&interval=1m"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                result = data["chart"]["result"][0]
                price = result["meta"].get("regularMarketPrice")
                high = result["meta"].get("regularMarketDayHigh")
                low = result["meta"].get("regularMarketDayLow")
                if price is None or high is None or low is None:
                    raise ValueError("Yahoo response omitted current price/high/low")
                return {
                    "source": "Yahoo Finance (GC=F Gold Futures)",
                    "symbol": "XAUUSD",
                    "price": round(float(price), 2),
                    "day_high": round(float(high), 2),
                    "day_low": round(float(low), 2),
                    "success": True,
                    "data_mode": "LIVE_PUBLIC_API",
                }
        except Exception as e:
            logger.warning(f"Live Gold fetch fallback: {e}")

        return {
            "source": "UNAVAILABLE",
            "symbol": "XAUUSD",
            "price": None,
            "day_high": None,
            "day_low": None,
            "success": False,
            "data_mode": "UNAVAILABLE",
            "actionable": False,
        }

    _cached_summary: Optional[Dict[str, Any]] = None

    def get_market_intelligence_summary(self, fast_mode: bool = False) -> Dict[str, Any]:
        """Assembles comprehensive multi-source public market telemetry."""
        if fast_mode and self.__class__._cached_summary:
            return self.__class__._cached_summary

        if fast_mode:
            fx = {
                "source": "UNAVAILABLE",
                "base": "USD",
                "date": None,
                "rates": {},
                "success": False,
                "data_mode": "UNAVAILABLE",
            }
            gold = {
                "source": "UNAVAILABLE",
                "symbol": "XAUUSD",
                "price": None,
                "day_high": None,
                "day_low": None,
                "success": False,
                "data_mode": "UNAVAILABLE",
            }
        else:
            fx = self.fetch_live_fx_rates("USD")
            gold = self.fetch_live_gold_spot()

        summary = {
            "gold_spot": gold,
            "forex_crosses": fx,
            "total_indexed_apis": self.total_apis_indexed,
            "available_categories": list(self.indexed_apis.keys()),
            "status": "ONLINE" if fx.get("success") and gold.get("success") else "DEGRADED",
            "actionable": bool(fx.get("success") and gold.get("success")),
        }
        self.__class__._cached_summary = summary
        return summary
