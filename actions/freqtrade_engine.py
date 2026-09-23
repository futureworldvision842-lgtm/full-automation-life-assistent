"""Read-only crypto observations. No synthetic prices, signals, or portfolios."""
from __future__ import annotations
import json
import math
import re
import time
from datetime import datetime, timezone
from threading import Lock
import requests

_CACHE = {}
_LOCK = Lock()
COINS = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","BNB":"binancecoin","XRP":"ripple"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _number(value, positive=False):
    number = float(value)
    if not math.isfinite(number) or (positive and number <= 0):
        raise ValueError("invalid market number")
    return number


def _get(url, params, ttl=30):
    key = url + json.dumps(params, sort_keys=True)
    with _LOCK:
        cached = _CACHE.get(key)
        if cached and time.monotonic() - cached[0] < ttl:
            return cached[1], cached[2]
    response = requests.get(url, params=params, timeout=(2, 6), headers={"User-Agent":"Jarvis-Local-Research/1.0"})
    response.raise_for_status()
    data, received = response.json(), _now()
    with _LOCK:
        if len(_CACHE) >= 100:
            _CACHE.clear()
        _CACHE[key] = (time.monotonic(), data, received)
    return data, received


class QuantitativeCryptoEngine:
    def __init__(self, base_portfolio_usd=500.0):
        self.base_portfolio = base_portfolio_usd

    def get_market_overview(self):
        url = "https://api.coingecko.com/api/v3/simple/price"
        try:
            data, received = _get(url, {"ids":",".join(COINS.values()),"vs_currencies":"usd",
                "include_24hr_change":"true","include_last_updated_at":"true"}, ttl=60)
            assets = {}
            for ticker, coin in COINS.items():
                row = data.get(coin, {})
                try:
                    price = _number(row.get("usd"), positive=True)
                    updated = _number(row.get("last_updated_at"), positive=True)
                    fresh = -60 <= time.time() - updated <= 600
                    assets[ticker] = {"price":price if fresh else None,
                        "change_24h":_number(row["usd_24h_change"]) if fresh and row.get("usd_24h_change") is not None else None,
                        "observed_at":datetime.fromtimestamp(updated, timezone.utc).isoformat(),
                        "available":fresh, "data_mode":"OBSERVED" if fresh else "STALE"}
                except (ValueError, TypeError, OverflowError, OSError):
                    assets[ticker] = {"price":None,"available":False,"data_mode":"UNAVAILABLE"}
            ok = any(row["available"] for row in assets.values())
            return {"ok":ok,"source":"CoinGecko","source_url":url,"received_at":received,
                    "data_mode":"OBSERVED" if ok else "UNAVAILABLE","assets":assets,"executed":False}
        except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
            return {"ok":False,"source":"CoinGecko","source_url":url,"data_mode":"UNAVAILABLE",
                    "assets":{},"error":type(exc).__name__,"executed":False}

    def evaluate_spot_allocation(self, portfolio_usd=None):
        cap = float(portfolio_usd or self.base_portfolio or 500.0)
        return {
            "ok": True,
            "executed": False,
            "total_capital_usd": cap,
            "allocations": [
                {"symbol": "BTC", "pct": 40.0, "amount_usd": round(cap * 0.40, 2), "rationale": "Core macro store of value"},
                {"symbol": "ETH", "pct": 30.0, "amount_usd": round(cap * 0.30, 2), "rationale": "Smart contract infrastructure"},
                {"symbol": "SOL", "pct": 20.0, "amount_usd": round(cap * 0.20, 2), "rationale": "High throughput liquidity"},
                {"symbol": "USDT", "pct": 10.0, "amount_usd": round(cap * 0.10, 2), "rationale": "Dry powder opportunity reserve"},
            ],
            "data_mode": "MODEL_PORTFOLIO",
            "model_name": "Conservative Institutional Spot Allocation",
            "reason": "Deterministic 4-tier asset allocation model for risk-balanced crypto portfolio."
        }

    def scan_order_book_imbalances(self, symbol="BTCUSDT"):
        symbol = str(symbol).upper()
        url = "https://data-api.binance.vision/api/v3/depth"
        if not re.fullmatch(r"[A-Z0-9]{5,20}", symbol):
            return {"ok":False,"error":"invalid_symbol","executed":False}
        try:
            data, received = _get(url, {"symbol":symbol,"limit":100}, ttl=10)
            bids = [(_number(p, True), _number(q, True)) for p,q in data["bids"]]
            asks = [(_number(p, True), _number(q, True)) for p,q in data["asks"]]
            if not bids or not asks or bids[0][0] >= asks[0][0]:
                raise ValueError("Empty or crossed book")
            bid_total = sum(p*q for p,q in bids)
            ask_total = sum(p*q for p,q in asks)
            return {"ok":True,"symbol":symbol,"source":"Binance public spot order book","source_url":url,
                "data_mode":"OBSERVED_SNAPSHOT","received_at":received,"last_update_id":data.get("lastUpdateId"),
                "best_bid":bids[0][0],"best_ask":asks[0][0],"spread":asks[0][0]-bids[0][0],
                "bid_notional_quote":bid_total,"ask_notional_quote":ask_total,
                "bid_ask_imbalance_ratio":bid_total/ask_total,"levels_per_side":min(len(bids),len(asks)),
                "executed":False,"recommendation":None,
                "warning":"A limited-depth, single-exchange snapshot; orders can be cancelled or spoofed. This does not identify whales or predict a trade."}
        except (requests.RequestException, ValueError, TypeError, KeyError, IndexError) as exc:
            return {"ok":False,"symbol":symbol,"source_url":url,"data_mode":"UNAVAILABLE",
                    "error":type(exc).__name__,"executed":False}


_ENGINE = QuantitativeCryptoEngine()


def get_crypto_engine():
    return _ENGINE


def freqtrade_engine(params=None):
    params = params or {}
    action = params.get("action","overview").lower()
    if action in {"depth","orderbook","dom"}:
        data = _ENGINE.scan_order_book_imbalances(params.get("symbol","BTCUSDT"))
    elif action in {"portfolio","allocation","spot"}:
        data = _ENGINE.evaluate_spot_allocation()
    else:
        data = _ENGINE.get_market_overview()
    return json.dumps(data, ensure_ascii=False, indent=2)
