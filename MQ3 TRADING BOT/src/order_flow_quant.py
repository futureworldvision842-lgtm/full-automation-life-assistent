"""
src/order_flow_quant.py — Institutional Order Flow & Smart Money Concepts Quant Engine.
Implements Wall Street / London Interbank ICT & SMC Mathematical Models.

Key Capabilities:
  1. Premium vs Discount 50% Equilibrium Dealing Range Filter.
  2. Optimal Trade Entry (OTE: 62% - 79% with 70.5% Institutional Sweet Spot).
  3. Fair Value Gap Consequent Encroachment (50% CE Midpoint).
  4. Lee-Ready Cumulative Volume Delta (CVD) Divergence & Order Absorption Classifier.
  5. Turtle Soup Equal Highs / Lows (EQH / EQL) Inducement Sweep Detection.
  6. Interbank IPDA Killzones Time Matrix (London Open, NY Morning, NY Afternoon).
"""

from datetime import datetime, timezone, time
import numpy as np
import pandas as pd
import logging
from typing import Dict, Any, List, Optional, Tuple, Union

logger = logging.getLogger("OrderFlowQuant")


class OrderFlowQuantEngine:
    """
    Quantitative Institutional Order Flow & SMC Engine.
    Enforces interbank pricing models, Lee-Ready CVD absorption, and Turtle Soup sweeps.
    """

    PIP_MAP = {
        "XAUUSD": 0.10, "GOLD": 0.10,
        "XAGUSD": 0.01, "SILVER": 0.01,
        "BTCUSD": 1.0, "BTCUSDT": 1.0, "BTC": 1.0,
        "ETHUSD": 1.0, "ETHUSDT": 1.0, "ETH": 1.0,
        "SOLUSD": 0.10, "SOLUSDT": 0.10, "SOL": 0.10,
        "WIFUSD": 0.01, "WIFUSDT": 0.01, "WIF": 0.01,
        "PEPEUSD": 0.0000001, "PEPEUSDT": 0.0000001, "PEPE": 0.0000001,
        "BONKUSD": 0.0000001, "BONKUSDT": 0.0000001, "BONK": 0.0000001,
        "USDJPY": 0.01, "EURJPY": 0.01, "GBPJPY": 0.01, "JPY": 0.01,
        "EURUSD": 0.0001, "GBPUSD": 0.0001, "AUDUSD": 0.0001, "USDCAD": 0.0001
    }

    def __init__(self, pip_tolerance: float = 2.0):
        self.pip_tolerance = pip_tolerance

    def get_pip_unit(self, symbol: str) -> float:
        """Resolves asset-specific pip unit for multi-asset scaling."""
        sym_u = symbol.upper()
        for k, v in self.PIP_MAP.items():
            if k in sym_u:
                return v
        return 0.0001

    # ── 1. Premium vs Discount 50% Equilibrium Array ───────────────────────────

    def evaluate_premium_discount(self, df_range: pd.DataFrame, current_price: float) -> Dict[str, Any]:
        """
        Divides the active dealing range at 50% Equilibrium.
        Rule: Buying in Premium is prohibited; Selling in Discount is prohibited.
        """
        if df_range is None or len(df_range) < 10:
            return {
                "zone": "EQUILIBRIUM",
                "equilibrium": current_price,
                "is_buy_allowed": True,
                "is_sell_allowed": True,
                "range_high": current_price,
                "range_low": current_price
            }

        range_high = float(df_range['high'].max())
        range_low = float(df_range['low'].min())
        eq = (range_high + range_low) / 2.0
        total_range = range_high - range_low

        if total_range <= 0:
            return {"zone": "EQUILIBRIUM", "equilibrium": eq, "is_buy_allowed": True, "is_sell_allowed": True}

        # Pricing Zone
        if current_price < (eq - 0.05 * total_range):
            zone = "DISCOUNT"
            is_buy_allowed = True
            is_sell_allowed = False
        elif current_price > (eq + 0.05 * total_range):
            zone = "PREMIUM"
            is_buy_allowed = False
            is_sell_allowed = True
        else:
            zone = "EQUILIBRIUM"
            is_buy_allowed = True
            is_sell_allowed = True

        return {
            "zone": zone,
            "range_high": range_high,
            "range_low": range_low,
            "equilibrium": round(eq, 5),
            "is_buy_allowed": is_buy_allowed,
            "is_sell_allowed": is_sell_allowed,
            "discount_pct": round(((range_high - current_price) / total_range) * 100.0, 1)
        }

    # ── 2. Optimal Trade Entry (OTE 70.5% Fibonacci Array) ─────────────────────

    def compute_ote_fibonacci_array(
        self,
        df_entry: pd.DataFrame,
        current_price: float,
        direction: str
    ) -> Dict[str, Any]:
        """
        Computes 61.8%, 70.5% (institutional sweet spot), and 78.6% OTE levels.
        Checks if current price is situated inside the Optimal Trade Entry zone.
        """
        if df_entry is None or len(df_entry) < 15:
            return {"in_ote_zone": False, "ote_sweet_spot": current_price, "score_bonus": 0.0}

        recent_high = float(df_entry['high'].tail(25).max())
        recent_low = float(df_entry['low'].tail(25).min())
        diff = recent_high - recent_low

        if diff <= 0:
            return {"in_ote_zone": False, "ote_sweet_spot": current_price, "score_bonus": 0.0}

        if direction == "BUY":
            fib_618 = recent_high - (0.618 * diff)
            fib_705 = recent_high - (0.705 * diff)  # Institutional Golden Pocket
            fib_786 = recent_high - (0.786 * diff)
            in_ote = (fib_786 <= current_price <= fib_618)
        else:  # SELL
            fib_618 = recent_low + (0.618 * diff)
            fib_705 = recent_low + (0.705 * diff)
            fib_786 = recent_low + (0.786 * diff)
            in_ote = (fib_618 <= current_price <= fib_786)

        return {
            "in_ote_zone": in_ote,
            "fib_618": round(fib_618, 5),
            "fib_705_sweet_spot": round(fib_705, 5),
            "fib_786": round(fib_786, 5),
            "score_bonus": 0.60 if in_ote else 0.0
        }

    # ── 3. Lee-Ready Cumulative Volume Delta (CVD) & Order Absorption ──────────

    def compute_tick_cvd(self, ticks: Optional[Union[np.ndarray, List[Dict], pd.DataFrame]]) -> Dict[str, Any]:
        """
        Computes tick-by-tick buyer vs seller Volume Delta using the Lee-Ready (1991) algorithm:
        Quote Rule: Price > Mid -> Buy (+1), Price < Mid -> Sell (-1)
        Tick Test fallback: Uptick (+1), Downtick (-1), Zero-tick carry-forward.
        Identifies BUYER_ABSORPTION and SELLER_ABSORPTION divergence states.
        """
        default_resp = {
            "cvd": 0,
            "net_delta": 0,
            "buyer_ratio": 0.50,
            "seller_ratio": 0.50,
            "total_volume": 0.0,
            "total_buy_vol": 0.0,
            "total_sell_vol": 0.0,
            "divergence": "NONE",
            "absorption_type": "NONE",
            "is_absorption_divergence": False,
            "description": "No tick data available"
        }

        if ticks is None or len(ticks) == 0:
            return default_resp

        try:
            if isinstance(ticks, pd.DataFrame):
                df = ticks.copy()
            elif isinstance(ticks, np.ndarray) or isinstance(ticks, list):
                df = pd.DataFrame(ticks)
            else:
                return default_resp

            if 'bid' not in df.columns or 'ask' not in df.columns:
                return default_resp

            bid = df['bid'].values.astype(float)
            ask = df['ask'].values.astype(float)
            mid = (bid + ask) / 2.0

            if 'last' in df.columns and float(df['last'].iloc[0]) > 0:
                prices = df['last'].values.astype(float)
            else:
                prices = bid

            if 'volume_ext' in df.columns:
                volumes = df['volume_ext'].values.astype(float)
            elif 'volume' in df.columns:
                volumes = df['volume'].values.astype(float)
            else:
                volumes = np.ones(len(df), dtype=float)

            n = len(df)
            directions = np.zeros(n, dtype=int)

            # If all prices are flat on midpoint with zero movement
            if np.all(prices == mid) and (len(prices) == 1 or np.all(prices == prices[0])):
                return default_resp

            # Quote Rule
            directions[prices > mid] = 1
            directions[prices < mid] = -1

            # Initial tick fallback
            if directions[0] == 0:
                directions[0] = 1

            # Tick Test & Zero-tick carry-forward
            for i in range(1, n):
                if directions[i] == 0:
                    if prices[i] > prices[i-1]:
                        directions[i] = 1
                    elif prices[i] < prices[i-1]:
                        directions[i] = -1
                    else:
                        directions[i] = directions[i-1]

            deltas = directions * volumes
            total_buy_vol = float(np.sum(volumes[directions == 1]))
            total_sell_vol = float(np.sum(volumes[directions == -1]))
            net_delta = float(np.sum(deltas))
            total_vol = total_buy_vol + total_sell_vol

            buyer_ratio = 0.50 if total_vol <= 0 else (total_buy_vol / total_vol)
            seller_ratio = 1.0 - buyer_ratio

            # Divergence & Absorption Classification
            divergence = "NONE"
            absorption_type = "NONE"
            is_absorption = False

            if buyer_ratio >= 0.65:
                divergence = "BULLISH_CVD_SURGE"
                absorption_type = "BUYER_ABSORPTION"
                is_absorption = True
                desc = f"Institutional Buyer Absorption: Aggressive market buying ({buyer_ratio:.0%}) absorbed by liquidity."
            elif seller_ratio >= 0.65 or buyer_ratio <= 0.35:
                divergence = "BEARISH_CVD_SURGE"
                absorption_type = "SELLER_ABSORPTION"
                is_absorption = True
                desc = f"Institutional Seller Absorption: Aggressive market selling ({seller_ratio:.0%}) absorbed by liquidity."
            else:
                desc = f"Neutral CVD flow (Buy: {buyer_ratio:.0%}, Sell: {seller_ratio:.0%})"

            return {
                "cvd": int(net_delta),
                "net_delta": int(net_delta),
                "buyer_ratio": round(buyer_ratio, 2),
                "seller_ratio": round(seller_ratio, 2),
                "total_volume": round(total_vol, 2),
                "total_buy_vol": round(total_buy_vol, 2),
                "total_sell_vol": round(total_sell_vol, 2),
                "divergence": divergence,
                "absorption_type": absorption_type,
                "is_absorption_divergence": is_absorption,
                "description": desc
            }
        except Exception as e:
            logger.warning(f"Error computing tick CVD: {e}")
            return default_resp

    def detect_absorption_divergence(
        self,
        price_swing_1: float,
        price_swing_2: float,
        cvd_swing_1: float,
        cvd_swing_2: float
    ) -> Dict[str, Any]:
        """
        Evaluates structural divergence between price swings and CVD swings:
        - Buyer Absorption: Price Lower Low (or equal) while CVD makes Higher Low.
        - Seller Absorption: Price Higher High (or equal) while CVD makes Lower High.
        """
        is_buyer_absorption = (price_swing_2 <= price_swing_1) and (cvd_swing_2 > cvd_swing_1)
        is_seller_absorption = (price_swing_2 >= price_swing_1) and (cvd_swing_2 < cvd_swing_1)

        if is_buyer_absorption:
            return {
                "absorption_detected": True,
                "type": "BUYER_ABSORPTION",
                "bias": "BULLISH_REVERSAL",
                "description": "Bullish Buyer Absorption: Price made Lower Low while CVD formed Higher Low."
            }
        elif is_seller_absorption:
            return {
                "absorption_detected": True,
                "type": "SELLER_ABSORPTION",
                "bias": "BEARISH_REVERSAL",
                "description": "Bearish Seller Absorption: Price made Higher High while CVD formed Lower High."
            }

        return {
            "absorption_detected": False,
            "type": "NONE",
            "bias": "NEUTRAL",
            "description": "No significant price/CVD absorption divergence."
        }

    # ── 4. Equal Highs / Lows (EQH / EQL) Inducement Sweeps ────────────────────

    def detect_eqh_eql_inducement(self, df_entry: pd.DataFrame, symbol: str = "EURUSD") -> Dict[str, Any]:
        """
        Detects Equal Highs (EQH) or Equal Lows (EQL) engineered liquidity pools
        and Turtle Soup liquidity sweeps across multi-asset instruments.
        """
        if df_entry is None or len(df_entry) < 15:
            return {
                "inducement_type": "NONE",
                "level": 0.0,
                "is_swept": False,
                "sweep_wick_price": 0.0,
                "pip_distance": 0.0,
                "lookback_bars": 0
            }

        pip_unit = self.get_pip_unit(symbol)
        tol = self.pip_tolerance * pip_unit

        highs = df_entry['high'].values.astype(float)
        lows = df_entry['low'].values.astype(float)
        closes = df_entry['close'].values.astype(float)
        opens = df_entry['open'].values.astype(float) if 'open' in df_entry.columns else closes.copy()

        curr_high = highs[-1]
        curr_low = lows[-1]
        curr_open = opens[-1]
        curr_close = closes[-1]
        curr_range = max(curr_high - curr_low, 1e-6)

        lookback = min(len(df_entry), 30)

        # 1. Search for Equal Highs (EQH)
        unswept_eqh = None
        for i in range(len(highs) - lookback, len(highs) - 2):
            if i < 0:
                continue
            for j in range(i + 2, len(highs) - 1):
                if abs(highs[i] - highs[j]) <= tol:
                    eqh_level = float(max(highs[i], highs[j]))
                    # Turtle Soup Sweep: Pierced EQH and closed back below with rejection wick
                    if curr_high > eqh_level and curr_close < eqh_level:
                        upper_wick = curr_high - max(curr_open, curr_close)
                        if upper_wick >= 0.35 * curr_range or upper_wick >= abs(curr_close - curr_open):
                            return {
                                "inducement_type": "BEARISH_EQH_SWEEP",
                                "level": round(eqh_level, 5),
                                "is_swept": True,
                                "sweep_wick_price": round(curr_high, 5),
                                "pip_distance": round(abs(curr_close - eqh_level) / pip_unit, 1),
                                "lookback_bars": lookback
                            }
                    elif curr_high <= eqh_level and unswept_eqh is None:
                        unswept_eqh = {
                            "inducement_type": "EQH_UNSWEPT",
                            "level": round(eqh_level, 5),
                            "is_swept": False,
                            "sweep_wick_price": 0.0,
                            "pip_distance": round(abs(curr_close - eqh_level) / pip_unit, 1),
                            "lookback_bars": lookback
                        }

        # 2. Search for Equal Lows (EQL)
        unswept_eql = None
        for i in range(len(lows) - lookback, len(lows) - 2):
            if i < 0:
                continue
            for j in range(i + 2, len(lows) - 1):
                if abs(lows[i] - lows[j]) <= tol:
                    eql_level = float(min(lows[i], lows[j]))
                    # Turtle Soup Sweep: Pierced EQL and closed back above with rejection wick
                    if curr_low < eql_level and curr_close > eql_level:
                        lower_wick = min(curr_open, curr_close) - curr_low
                        if lower_wick >= 0.35 * curr_range or lower_wick >= abs(curr_close - curr_open):
                            return {
                                "inducement_type": "BULLISH_EQL_SWEEP",
                                "level": round(eql_level, 5),
                                "is_swept": True,
                                "sweep_wick_price": round(curr_low, 5),
                                "pip_distance": round(abs(curr_close - eql_level) / pip_unit, 1),
                                "lookback_bars": lookback
                            }
                    elif curr_low >= eql_level and unswept_eql is None:
                        unswept_eql = {
                            "inducement_type": "EQL_UNSWEPT",
                            "level": round(eql_level, 5),
                            "is_swept": False,
                            "sweep_wick_price": 0.0,
                            "pip_distance": round(abs(curr_close - eql_level) / pip_unit, 1),
                            "lookback_bars": lookback
                        }

        if unswept_eqh is not None:
            return unswept_eqh
        if unswept_eql is not None:
            return unswept_eql

        return {
            "inducement_type": "NONE",
            "level": 0.0,
            "is_swept": False,
            "sweep_wick_price": 0.0,
            "pip_distance": 0.0,
            "lookback_bars": lookback
        }

    # ── 5. Interbank Killzones Time Matrix ─────────────────────────────────────

    def get_active_killzone(self, current_time: Optional[Any] = None) -> Dict[str, Any]:
        """
        Returns active IPDA Interbank Killzone Window:
          - London Open: 07:00 - 10:00 UTC (Judas Swing / Manipulation)
          - NY Morning:  12:00 - 15:00 UTC (Displacement / Trend Continuation)
          - NY Afternoon: 18:00 - 20:00 UTC (Silver Bullet / Continuation)
          - Off-Hours / Session Rollover: Low liquidity
        """
        if current_time is not None:
            if hasattr(current_time, "time"):
                now_utc = current_time.time()
            elif isinstance(current_time, (int, float)):
                now_utc = datetime.fromtimestamp(current_time, timezone.utc).time()
            else:
                try:
                    now_utc = pd.to_datetime(current_time, utc=True).time()
                except Exception:
                    now_utc = datetime.now(timezone.utc).time()
        else:
            now_utc = datetime.now(timezone.utc).time()

        if time(7, 0) <= now_utc <= time(10, 0):
            return {"killzone": "LONDON_OPEN_KILLZONE", "is_prime_killzone": True, "confluence_boost": 0.40}
        elif time(12, 0) <= now_utc <= time(15, 0):
            return {"killzone": "NY_AM_KILLZONE", "is_prime_killzone": True, "confluence_boost": 0.50}
        elif time(18, 0) <= now_utc <= time(20, 0):
            return {"killzone": "NY_PM_KILLZONE", "is_prime_killzone": True, "confluence_boost": 0.30}

        return {"killzone": "OFF_HOURS", "is_prime_killzone": False, "confluence_boost": 0.0}
