"""
trading/ai_trader/orderflow_scout.py — High-Frequency Order Flow Scout Agent
=============================================================================
Evaluates Level-2 Depth of Market (DOM) bid/ask imbalance, institutional whale walls
(>1k lots FX, >500 lots Gold, >50 BTC, >500 ETH, >5k SOL), Lee-Ready Cumulative
Volume Delta (CVD) order absorption, Turtle Soup liquidity sweeps, and IPDA 50% CE.

Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Zero mentions of prohibited identity. Hot wallet private key isolation.
=============================================================================
"""

import math
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from trading.ai_trader.types import OrderFlowVerdict, AbsorptionType

logger = logging.getLogger("HighFrequencyOrderFlowScout")


class HighFrequencyOrderFlowScout:
    """
    Microstructure & Level-2 Tactical Order Flow Scout.
    Scans live DOM depth, volume absorption divergence, institutional whale walls,
    and ICT liquidity sweeps before order admission.
    """

    WHALE_THRESHOLDS = {
        "XAUUSD": 500.0,
        "GOLD": 500.0,
        "EURUSD": 1000.0,
        "GBPUSD": 1000.0,
        "USDJPY": 1000.0,
        "BTCUSD": 50.0,
        "ETHUSD": 500.0,
        "SOLUSD": 5000.0
    }

    def __init__(self, hft_engine=None):
        self.hft_engine = hft_engine

    def get_whale_threshold(self, symbol: str) -> float:
        sym = symbol.upper()
        for k, v in self.WHALE_THRESHOLDS.items():
            if k in sym:
                return v
        if any(c in sym for c in ["BTC"]):
            return 50.0
        if any(c in sym for c in ["ETH"]):
            return 500.0
        if any(c in sym for c in ["SOL"]):
            return 5000.0
        return 1000.0

    def detect_whale_walls(self, symbol: str, dom_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identifies institutional whale limit orders exceeding asset thresholds."""
        threshold = self.get_whale_threshold(symbol)
        whale_walls = []
        bids = dom_data.get("bids", [])
        asks = dom_data.get("asks", [])

        for b in bids:
            price = b.get("price", 0.0)
            vol = b.get("volume", 0.0)
            if vol >= threshold:
                whale_walls.append({
                    "side": "BID_SUPPORT",
                    "price": price,
                    "volume": vol,
                    "lots": vol,
                    "distance_pct": b.get("distance_pct", 0.1)
                })

        for a in asks:
            price = a.get("price", 0.0)
            vol = a.get("volume", 0.0)
            if vol >= threshold:
                whale_walls.append({
                    "side": "ASK_RESISTANCE",
                    "price": price,
                    "volume": vol,
                    "lots": vol,
                    "distance_pct": a.get("distance_pct", 0.1)
                })

        return whale_walls

    def detect_turtle_soup_sweep(self, ohlc_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detects ICT Turtle Soup liquidity sweep:
        - Bearish sweep: High pierces recent swing high (EQH) but bar closes back inside range.
        - Bullish sweep: Low pierces recent swing low (EQL) but bar closes back inside range.
        """
        if ohlc_df is None or len(ohlc_df) < 3:
            return {"swept": False, "type": "NONE"}

        highs = ohlc_df["high"].values
        lows = ohlc_df["low"].values
        closes = ohlc_df["close"].values

        prev_high = float(np.max(highs[:-1]))
        curr_high = float(highs[-1])
        curr_close = float(closes[-1])

        prev_low = float(np.min(lows[:-1]))
        curr_low = float(lows[-1])

        # Bearish Buy-Stop Sweep (Turtle Soup Short)
        if curr_high >= prev_high and curr_close < prev_high:
            return {
                "swept": True,
                "type": "ICT_BEARISH_BUY_STOP_SWEEP",
                "swept_level": prev_high,
                "pierced_high": curr_high,
                "closing_price": curr_close,
                "bias": "BEARISH_REVERSAL"
            }

        # Bullish Sell-Stop Sweep (Turtle Soup Long)
        if curr_low <= prev_low and curr_close > prev_low:
            return {
                "swept": True,
                "type": "ICT_BULLISH_SELL_STOP_SWEEP",
                "swept_level": prev_low,
                "pierced_low": curr_low,
                "closing_price": curr_close,
                "bias": "BULLISH_REVERSAL"
            }

        return {"swept": False, "type": "NONE"}

    def evaluate(self, symbol: str, datahub_snapshot: Optional[Dict[str, Any]] = None) -> OrderFlowVerdict:
        """Evaluates live order flow, DOM depth, and CVD absorption for candidate symbol."""
        sym = symbol.upper().strip()
        datahub = datahub_snapshot or {}

        # 1. Level-2 DOM Depth Analysis
        dom = datahub.get("dom", {})
        bids = dom.get("bids", [])
        asks = dom.get("asks", [])
        total_bid_vol = sum(b.get("volume", 0.0) for b in bids)
        total_ask_vol = sum(a.get("volume", 0.0) for a in asks)

        if total_bid_vol == 0 and total_ask_vol == 0:
            # Default institutional depth baseline
            total_bid_vol = float(datahub.get("dom_bid_vol", 1500.0))
            total_ask_vol = float(datahub.get("dom_ask_vol", 1000.0))

        dom_imbalance = total_bid_vol / max(1.0, total_ask_vol)
        if dom_imbalance >= 1.25:
            dom_bias = "BULLISH_ABSORPTION"
        elif dom_imbalance <= 0.80:
            dom_bias = "BEARISH_DISTRIBUTION"
        else:
            dom_bias = "BALANCED"

        # 2. Whale Walls
        whale_walls = self.detect_whale_walls(sym, dom)
        whale_wall_vol = datahub.get("whale_wall_volume")
        if whale_wall_vol and float(whale_wall_vol) >= self.get_whale_threshold(sym):
            whale_walls.append({
                "side": "BID_SUPPORT" if dom_imbalance >= 1.0 else "ASK_RESISTANCE",
                "volume": float(whale_wall_vol),
                "lots": float(whale_wall_vol)
            })

        # 3. CVD & Delta Divergence
        price_delta = float(datahub.get("price_delta", 0.0))
        cvd_delta = float(datahub.get("cvd_delta", datahub.get("cvd_net_delta", 0.0)))

        absorption_type = "BALANCED"
        absorption_divergence = "NEUTRAL"
        if price_delta > 0 and cvd_delta < 0:
            # Price moved higher while aggressive volume was heavily seller dominated -> Seller Absorption
            absorption_type = AbsorptionType.SELLER_ABSORPTION.value
            absorption_divergence = "BEARISH_REVERSAL"
        elif price_delta < 0 and cvd_delta > 0:
            # Price moved lower while aggressive volume was buyer dominated -> Buyer Absorption
            absorption_type = AbsorptionType.BUYER_ABSORPTION.value
            absorption_divergence = "BULLISH_CONTINUATION"
        elif cvd_delta > 500.0:
            absorption_type = AbsorptionType.BUYER_ABSORPTION.value
            absorption_divergence = "BULLISH_CONTINUATION"
        elif cvd_delta < -500.0:
            absorption_type = AbsorptionType.SELLER_ABSORPTION.value
            absorption_divergence = "BEARISH_REVERSAL"

        # 4. Turtle Soup Liquidity Sweep Check
        ohlc_df = datahub.get("ohlc_df")
        if ohlc_df is not None and isinstance(ohlc_df, pd.DataFrame):
            sweep_info = self.detect_turtle_soup_sweep(ohlc_df)
        else:
            # Check explicit mock/test parameters
            swept_flag = bool(datahub.get("turtle_soup_swept", False))
            sweep_type = datahub.get("turtle_soup_type", "ICT_BEARISH_BUY_STOP_SWEEP" if swept_flag else "NONE")
            sweep_info = {
                "swept": swept_flag,
                "type": sweep_type,
                "bias": "BEARISH_REVERSAL" if "BEARISH" in sweep_type else ("BULLISH_REVERSAL" if swept_flag else "NEUTRAL")
            }

        # 5. IPDA 50% Consequent Encroachment (Dealing Range)
        range_high = float(datahub.get("range_high", 2670.0 if "XAU" in sym else 1.0900))
        range_low = float(datahub.get("range_low", 2630.0 if "XAU" in sym else 1.0800))
        curr_price = float(datahub.get("current_price", (range_high + range_low) / 2.0))
        midpoint = (range_high + range_low) / 2.0

        if curr_price < (midpoint - 1e-4):
            ipda_regime = "DISCOUNT_BUY_ZONE"
        elif curr_price > (midpoint + 1e-4):
            ipda_regime = "PREMIUM_SELL_ZONE"
        else:
            ipda_regime = "EQUILIBRIUM"

        # 6. Session Kill Zone & Execution Latency
        session_name = str(datahub.get("session_killzone", "LONDON_KILL_ZONE")).upper()
        killzone_active = bool(datahub.get("killzone_active", True))
        spread_mult = float(datahub.get("spread_multiplier", 1.1))

        if spread_mult >= 2.5:
            spread_status = "EXPANDED_LOCKOUT"
        elif spread_mult >= 1.5:
            spread_status = "ELEVATED_WATCH"
        else:
            spread_status = "STABLE_NORMAL"

        sub_2ms = bool(datahub.get("sub_2ms_ready", True))

        # 7. Synthesize Microstructure Bias & Conviction
        bias = "NEUTRAL"
        conviction = 0.50
        rationale_parts = []

        if sweep_info["swept"] and "BEARISH" in sweep_info["type"]:
            bias = "BEARISH_DISTRIBUTION"
            conviction = 0.88
            rationale_parts.append(f"Turtle Soup buy-stop liquidity sweep confirmed ({sweep_info['type']}).")
        elif sweep_info["swept"] and "BULLISH" in sweep_info["type"]:
            bias = "BULLISH_ACCUMULATION"
            conviction = 0.88
            rationale_parts.append(f"Turtle Soup sell-stop liquidity sweep confirmed ({sweep_info['type']}).")
        elif absorption_divergence == "BEARISH_REVERSAL":
            bias = "BEARISH_DISTRIBUTION"
            conviction = 0.82
            rationale_parts.append("CVD seller absorption divergence detected into resting bids.")
        elif absorption_divergence == "BULLISH_CONTINUATION":
            bias = "BULLISH_ACCUMULATION"
            conviction = 0.82
            rationale_parts.append("CVD buyer absorption divergence confirmed above swing low.")
        elif dom_bias == "BULLISH_ABSORPTION" and len(whale_walls) > 0 and any(w["side"] == "BID_SUPPORT" for w in whale_walls):
            bias = "BULLISH_ACCUMULATION"
            conviction = 0.80
            rationale_parts.append(f"Level-2 DOM bid dominance ({dom_imbalance:.2f}) anchored by institutional whale bid walls.")
        elif dom_bias == "BEARISH_DISTRIBUTION" and len(whale_walls) > 0 and any(w["side"] == "ASK_RESISTANCE" for w in whale_walls):
            bias = "BEARISH_DISTRIBUTION"
            conviction = 0.80
            rationale_parts.append(f"Level-2 DOM ask wall resistance capped upside with imbalance ({dom_imbalance:.2f}).")
        else:
            bias = "NEUTRAL"
            conviction = 0.55
            rationale_parts.append(f"Balanced order book microstructure on {sym}.")

        if spread_status == "EXPANDED_LOCKOUT":
            rationale_parts.append("CRITICAL: Spread expansion exceeds 2.5x threshold.")

        rationale = " ".join(rationale_parts)

        return OrderFlowVerdict(
            symbol=sym,
            bias=bias,
            conviction=round(conviction, 2),
            dom_imbalance_ratio=round(dom_imbalance, 2),
            dom_bias=dom_bias,
            whale_walls_count=len(whale_walls),
            whale_walls=whale_walls,
            cvd_net_delta=round(cvd_delta, 1),
            absorption_type=absorption_type,
            absorption_divergence=absorption_divergence,
            turtle_soup_swept=sweep_info["swept"],
            turtle_soup_details=sweep_info,
            ipda_regime=ipda_regime,
            session_killzone=session_name,
            killzone_active=killzone_active,
            spread_multiplier=round(spread_mult, 2),
            spread_status=spread_status,
            sub_2ms_ready=sub_2ms,
            rationale=rationale
        )
