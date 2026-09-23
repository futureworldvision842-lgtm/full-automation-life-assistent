"""
test_smc_cvd_engine.py — Comprehensive Test Suite for Smart Money Concepts (SMC) & CVD Engine.

Covers:
1. Fair Value Gaps (FVG) Detection, 50% Consequent Encroachment (CE), & Mitigation Tracking.
2. Order Blocks (OB) Detection, Institutional Demand/Supply Zones, Volume Validation, & Touch Trackers.
3. Optimal Trade Entry (OTE) Fibonacci Retracement Grids (50% EQ, 61.8%, 70.5% Sweet Spot, 78.6%).
4. Liquidity Sweeps & Stop-Hunt Markers (Equal Highs EQH / Equal Lows EQL sweeps, Turtle Soup liquidity runs).
5. Interbank IPDA Session Killzones (London Open, NY AM Displacement, NY PM Silver Bullet) Time Filters.
6. Tick-by-Tick Cumulative Volume Delta (CVD) based on the Lee-Ready algorithm (Quote Rule, Tick Test, Zero-Tick Carry-Forward).
7. Market Depth & Buyer/Seller Volume Ratio Calculations.
8. Real-Time Absorption Divergence Alerts (Bullish/Bearish Absorption & CVD Volume Surges).
9. Integration with `src.order_flow_quant` and `src.market_analyzer` (with Self-Contained Reference Models).
10. Multi-Tiered Verification (Tier 1 Canonical, Tier 2 Boundary, Tier 3 Pairwise, Tier 4 Institutional Scenarios).
"""

import math
from datetime import datetime, time, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest

from src.order_flow_quant import OrderFlowQuantEngine
from src.market_analyzer import MarketAnalyzer
from src.market_maker_game_engine import MarketMakerGameEngine


# ============================================================================
# SECTION 1: SELF-CONTAINED ALGORITHMIC REFERENCE MODELS (ORACLES)
# ============================================================================

class ReferenceFVGOracle:
    """
    Authoritative reference oracle for Fair Value Gap (FVG) detection,
    50% Consequent Encroachment (CE) level calculation, and mitigation tracking.
    """

    @staticmethod
    def calculate_ce(top: float, bottom: float) -> float:
        """Consequent Encroachment is the exact 50% midpoint of the imbalance."""
        return (top + bottom) / 2.0

    @classmethod
    def detect_fvgs_with_ce(
        cls,
        df: pd.DataFrame,
        min_gap_pips: float = 2.0,
        symbol: str = "EURUSD"
    ) -> List[Dict[str, Any]]:
        """
        Detects 3-candle imbalance gaps with exact 50% CE and tracks future mitigation.
        """
        fvgs = []
        if df is None or len(df) < 3:
            return fvgs

        pip_unit = 0.01 if "JPY" in symbol else (0.1 if symbol == "XAUUSD" else 0.0001)

        for i in range(2, len(df)):
            c1_high = float(df['high'].iloc[i - 2])
            c1_low = float(df['low'].iloc[i - 2])
            c3_high = float(df['high'].iloc[i])
            c3_low = float(df['low'].iloc[i])
            bar_time = df['time'].iloc[i] if 'time' in df.columns else i

            # Bullish FVG: Candle 3 Low > Candle 1 High
            if c3_low > c1_high:
                gap_size = (c3_low - c1_high) / pip_unit
                if gap_size >= min_gap_pips:
                    top = c3_low
                    bottom = c1_high
                    ce = cls.calculate_ce(top, bottom)

                    # Check mitigation in future candles (if any exist past bar i)
                    is_mitigated = False
                    is_partially_mitigated = False
                    if i + 1 < len(df):
                        future_lows = df['low'].iloc[i + 1:].values
                        if any(l <= ce for l in future_lows):
                            is_mitigated = True
                        elif any(l <= top for l in future_lows):
                            is_partially_mitigated = True

                    fvgs.append({
                        "type": "BULLISH_FVG",
                        "index": i,
                        "time": bar_time,
                        "top": top,
                        "bottom": bottom,
                        "ce": round(ce, 5),
                        "gap_pips": round(gap_size, 2),
                        "mitigated": is_mitigated,
                        "partially_mitigated": is_partially_mitigated
                    })

            # Bearish FVG: Candle 3 High < Candle 1 Low
            elif c3_high < c1_low:
                gap_size = (c1_low - c3_high) / pip_unit
                if gap_size >= min_gap_pips:
                    top = c1_low
                    bottom = c3_high
                    ce = cls.calculate_ce(top, bottom)

                    # Check mitigation in future candles
                    is_mitigated = False
                    is_partially_mitigated = False
                    if i + 1 < len(df):
                        future_highs = df['high'].iloc[i + 1:].values
                        if any(h >= ce for h in future_highs):
                            is_mitigated = True
                        elif any(h >= bottom for h in future_highs):
                            is_partially_mitigated = True

                    fvgs.append({
                        "type": "BEARISH_FVG",
                        "index": i,
                        "time": bar_time,
                        "top": top,
                        "bottom": bottom,
                        "ce": round(ce, 5),
                        "gap_pips": round(gap_size, 2),
                        "mitigated": is_mitigated,
                        "partially_mitigated": is_partially_mitigated
                    })

        return fvgs


class ReferenceOrderBlockOracle:
    """
    Authoritative reference oracle for Order Block (OB) demand/supply detection,
    volume validation, touch count tracking, and invalidation rules.
    """

    @staticmethod
    def detect_order_blocks_with_validation(
        df: pd.DataFrame,
        volume_threshold_multiplier: float = 1.0
    ) -> List[Dict[str, Any]]:
        obs = []
        if df is None or len(df) < 5:
            return obs

        has_vol = 'tick_volume' in df.columns or 'volume' in df.columns
        vol_col = 'tick_volume' if 'tick_volume' in df.columns else ('volume' if 'volume' in df.columns else None)

        for i in range(len(df) - 2):
            prev = df.iloc[i]
            c1 = df.iloc[i + 1]
            c2 = df.iloc[i + 2]

            # Bullish OB: down-candle before 2 up-candles breaking previous high
            if prev['close'] < prev['open']:
                if c1['close'] > c1['open'] and c2['close'] > c2['open'] and c2['close'] > prev['high']:
                    # Volume check if available
                    vol_valid = True
                    if has_vol and vol_col:
                        avg_vol = float(prev[vol_col])
                        disp_vol = float(max(c1[vol_col], c2[vol_col]))
                        vol_valid = disp_vol >= (avg_vol * volume_threshold_multiplier)

                    if vol_valid:
                        # Touch count & invalidation in subsequent bars
                        touch_count = 0
                        invalidated = False
                        if i + 3 < len(df):
                            for k in range(i + 3, len(df)):
                                sub_low = float(df['low'].iloc[k])
                                sub_close = float(df['close'].iloc[k])
                                if sub_low <= prev['high'] and sub_low >= prev['low']:
                                    touch_count += 1
                                if sub_close < prev['low']:
                                    invalidated = True

                        obs.append({
                            "type": "BULLISH_OB",
                            "index": i,
                            "time": prev['time'] if 'time' in prev else i,
                            "high": float(prev['high']),
                            "low": float(prev['low']),
                            "entry_price": float(prev['high']),
                            "sl_price": float(prev['low']),
                            "touch_count": touch_count,
                            "invalidated": invalidated
                        })

            # Bearish OB: up-candle before 2 down-candles breaking previous low
            elif prev['close'] > prev['open']:
                if c1['close'] < c1['open'] and c2['close'] < c2['open'] and c2['close'] < prev['low']:
                    vol_valid = True
                    if has_vol and vol_col:
                        avg_vol = float(prev[vol_col])
                        disp_vol = float(max(c1[vol_col], c2[vol_col]))
                        vol_valid = disp_vol >= (avg_vol * volume_threshold_multiplier)

                    if vol_valid:
                        touch_count = 0
                        invalidated = False
                        if i + 3 < len(df):
                            for k in range(i + 3, len(df)):
                                sub_high = float(df['high'].iloc[k])
                                sub_close = float(df['close'].iloc[k])
                                if sub_high >= prev['low'] and sub_high <= prev['high']:
                                    touch_count += 1
                                if sub_close > prev['high']:
                                    invalidated = True

                        obs.append({
                            "type": "BEARISH_OB",
                            "index": i,
                            "time": prev['time'] if 'time' in prev else i,
                            "high": float(prev['high']),
                            "low": float(prev['low']),
                            "entry_price": float(prev['low']),
                            "sl_price": float(prev['high']),
                            "touch_count": touch_count,
                            "invalidated": invalidated
                        })

        return obs


class ReferenceOTEOracle:
    """
    Authoritative reference oracle for Optimal Trade Entry (OTE) Fibonacci retracement arrays.
    """

    @staticmethod
    def compute_ote_grid(
        swing_high: float,
        swing_low: float,
        current_price: float,
        direction: str
    ) -> Dict[str, Any]:
        diff = swing_high - swing_low
        if diff <= 0:
            return {
                "in_ote_zone": False,
                "equilibrium": swing_high,
                "fib_618": swing_high,
                "fib_705_sweet_spot": swing_high,
                "fib_786": swing_high,
                "score_bonus": 0.0
            }

        eq = (swing_high + swing_low) / 2.0

        if direction.upper() == "BUY":
            fib_618 = swing_high - (0.618 * diff)
            fib_705 = swing_high - (0.705 * diff)
            fib_786 = swing_high - (0.786 * diff)
            in_zone = (fib_786 <= current_price <= fib_618)
        else:  # SELL
            fib_618 = swing_low + (0.618 * diff)
            fib_705 = swing_low + (0.705 * diff)
            fib_786 = swing_low + (0.786 * diff)
            in_zone = (fib_618 <= current_price <= fib_786)

        return {
            "in_ote_zone": in_zone,
            "equilibrium": round(eq, 5),
            "fib_618": round(fib_618, 5),
            "fib_705_sweet_spot": round(fib_705, 5),
            "fib_786": round(fib_786, 5),
            "score_bonus": 0.60 if in_zone else 0.0
        }


class ReferenceLeeReadyCVDOracle:
    """
    Authoritative reference oracle for the Lee-Ready tick classification algorithm,
    Cumulative Volume Delta (CVD), and Buyer/Seller volume ratios.
    """

    @staticmethod
    def compute_lee_ready_cvd(ticks: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not ticks or len(ticks) == 0:
            return {
                "cvd": 0,
                "net_delta": 0,
                "buyer_ratio": 0.50,
                "seller_ratio": 0.50,
                "total_volume": 0,
                "total_buy_vol": 0,
                "total_sell_vol": 0,
                "divergence": "NONE",
                "deltas_series": []
            }

        directions = []
        volumes = []
        last_direction = 0

        for i, tick in enumerate(ticks):
            bid = tick.get('bid', 0.0)
            ask = tick.get('ask', 0.0)
            mid = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else 0.0
            price = tick.get('last', tick.get('price', bid))
            vol = tick.get('volume_ext', tick.get('volume', 1.0))
            volumes.append(vol)

            # 1. Quote Rule
            if mid > 0 and price > mid:
                direction = 1
            elif mid > 0 and price < mid:
                direction = -1
            else:
                # 2. Tick Test Fallback
                if i == 0:
                    direction = 1  # Default initial tick
                else:
                    prev_price = ticks[i - 1].get('last', ticks[i - 1].get('price', ticks[i - 1].get('bid', price)))
                    if price > prev_price:
                        direction = 1
                    elif price < prev_price:
                        direction = -1
                    else:
                        # 3. Zero-Tick Carry-Forward
                        direction = last_direction if last_direction != 0 else 1

            directions.append(direction)
            last_direction = direction

        deltas = [d * v for d, v in zip(directions, volumes)]
        total_buy_vol = sum(v for d, v in zip(directions, volumes) if d == 1)
        total_sell_vol = sum(v for d, v in zip(directions, volumes) if d == -1)
        total_vol = total_buy_vol + total_sell_vol
        net_delta = sum(deltas)

        if total_vol <= 0:
            buyer_ratio = 0.50
            seller_ratio = 0.50
        else:
            buyer_ratio = total_buy_vol / total_vol
            seller_ratio = total_sell_vol / total_vol

        divergence = "NONE"
        if buyer_ratio >= 0.65:
            divergence = "BULLISH_CVD_SURGE"
        elif buyer_ratio <= 0.35:
            divergence = "BEARISH_CVD_SURGE"

        return {
            "cvd": int(round(net_delta)),
            "net_delta": int(round(net_delta)),
            "buyer_ratio": round(buyer_ratio, 2),
            "seller_ratio": round(seller_ratio, 2),
            "total_volume": total_vol,
            "total_buy_vol": total_buy_vol,
            "total_sell_vol": total_sell_vol,
            "divergence": divergence,
            "deltas_series": deltas
        }


class ReferenceIPDAKillzoneOracle:
    """
    Authoritative reference oracle for IPDA Interbank Session Killzones.
    """

    @staticmethod
    def evaluate_killzone(utc_time: time) -> Dict[str, Any]:
        if time(7, 0) <= utc_time <= time(10, 0):
            return {
                "killzone": "LONDON_OPEN_KILLZONE",
                "is_prime_killzone": True,
                "confluence_boost": 0.40,
                "session_name": "London Open Judas Window"
            }
        elif time(12, 0) <= utc_time <= time(15, 0):
            return {
                "killzone": "NY_AM_KILLZONE",
                "is_prime_killzone": True,
                "confluence_boost": 0.50,
                "session_name": "NY Morning AM Displacement"
            }
        elif time(18, 0) <= utc_time <= time(20, 0):
            return {
                "killzone": "NY_PM_KILLZONE",
                "is_prime_killzone": True,
                "confluence_boost": 0.30,
                "session_name": "NY Afternoon PM Silver Bullet"
            }
        else:
            return {
                "killzone": "OFF_HOURS",
                "is_prime_killzone": False,
                "confluence_boost": 0.0,
                "session_name": "Off-Hours Interbank Low Liquidity"
            }


# ============================================================================
# HELPER FUNCTIONS FOR TEST DATA GENERATION
# ============================================================================

def create_ohlcv_df(
    candles: List[Tuple[float, float, float, float, float]],
    start_time: str = "2026-08-14 08:00:00",
    freq: str = "15min"
) -> pd.DataFrame:
    """Creates a standardized OHLCV DataFrame from list of (open, high, low, close, volume)."""
    n = len(candles)
    dates = pd.date_range(start_time, periods=n, freq=freq)
    opens = [c[0] for c in candles]
    highs = [c[1] for c in candles]
    lows = [c[2] for c in candles]
    closes = [c[3] for c in candles]
    volumes = [c[4] for c in candles]

    return pd.DataFrame({
        "time": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "tick_volume": volumes,
        "volume": volumes
    })


def generate_synthetic_ticks(
    prices: List[float],
    spread: float = 0.20,
    volumes: Optional[List[float]] = None
) -> np.ndarray:
    """Generates structured tick array with bid, ask, last, volume, volume_ext."""
    if volumes is None:
        volumes = [1.0] * len(prices)

    dtype = [
        ('time', 'M8[s]'),
        ('bid', 'f8'),
        ('ask', 'f8'),
        ('last', 'f8'),
        ('volume', 'f8'),
        ('volume_ext', 'f8')
    ]
    ticks = np.empty(len(prices), dtype=dtype)
    base_time = np.datetime64('2026-08-14T08:00:00')

    for i, (p, v) in enumerate(zip(prices, volumes)):
        ticks[i] = (
            base_time + np.timedelta64(i, 's'),
            p - (spread / 2.0),
            p + (spread / 2.0),
            p,
            v,
            v
        )
    return ticks


# ============================================================================
# SECTION 2: DOMAIN 1 — FAIR VALUE GAPS (FVG) & 50% CE LEVEL TESTS
# ============================================================================

class TestFairValueGaps:
    """Comprehensive tests for FVG detection, 50% CE calculations, and mitigation tracking."""

    def test_bullish_fvg_canonical_3_candle_imbalance(self):
        """Validates Bullish FVG detection when Candle 3 Low > Candle 1 High."""
        # 5 candles: base, Candle 1 (high 2650), Candle 2 (displacement), Candle 3 (low 2655), follow-up
        data = [
            (2648.0, 2649.0, 2647.0, 2648.5, 100),
            (2648.5, 2650.0, 2648.0, 2649.5, 120),  # Candle 1: High = 2650.0
            (2649.5, 2658.0, 2649.0, 2657.0, 300),  # Candle 2: Impulsive displacement
            (2657.0, 2662.0, 2655.0, 2660.0, 180),  # Candle 3: Low = 2655.0
            (2660.0, 2663.0, 2659.0, 2661.0, 110),  # Candle 4: Holding above
        ]
        df = create_ohlcv_df(data)

        # 1. Test via MarketAnalyzer
        fvgs = MarketAnalyzer.detect_fvg(df, min_gap_pips=2.0, symbol="XAUUSD")
        assert len(fvgs) >= 1
        bullish = fvgs[0]
        assert bullish["type"] == "BULLISH_FVG"
        assert bullish["top"] == pytest.approx(2655.0)     # Candle 3 low
        assert bullish["bottom"] == pytest.approx(2650.0)  # Candle 1 high
        assert bullish["gap_pips"] == pytest.approx(50.0)  # (2655 - 2650) / 0.1 for XAUUSD = 50 pips

        # 2. Test exact 50% Consequent Encroachment (CE)
        ce = ReferenceFVGOracle.calculate_ce(bullish["top"], bullish["bottom"])
        assert ce == pytest.approx(2652.5)

    def test_bearish_fvg_canonical_3_candle_imbalance(self):
        """Validates Bearish FVG detection when Candle 3 High < Candle 1 Low."""
        # Candle 1 (low 1.0850), Candle 2 (bearish displacement), Candle 3 (high 1.0830)
        data = [
            (1.0860, 1.0865, 1.0855, 1.0858, 100),
            (1.0858, 1.0860, 1.0850, 1.0852, 110),  # Candle 1: Low = 1.0850
            (1.0852, 1.0855, 1.0820, 1.0825, 350),  # Candle 2: Heavy bearish drive
            (1.0825, 1.0830, 1.0815, 1.0820, 150),  # Candle 3: High = 1.0830
            (1.0820, 1.0825, 1.0810, 1.0815, 100),
        ]
        df = create_ohlcv_df(data)

        fvgs = MarketAnalyzer.detect_fvg(df, min_gap_pips=2.0, symbol="EURUSD")
        assert len(fvgs) >= 1
        bearish = fvgs[0]
        assert bearish["type"] == "BEARISH_FVG"
        assert bearish["top"] == pytest.approx(1.0850)     # Candle 1 low
        assert bearish["bottom"] == pytest.approx(1.0830)  # Candle 3 high
        assert bearish["gap_pips"] == pytest.approx(20.0)  # (1.0850 - 1.0830) / 0.0001 = 20 pips

        ce = ReferenceFVGOracle.calculate_ce(bearish["top"], bearish["bottom"])
        assert ce == pytest.approx(1.0840)

    def test_fvg_50_pct_ce_mathematical_precision(self):
        """Verifies 50% Consequent Encroachment (CE) level calculation across multiple symbols."""
        cases = [
            (2650.0, 2640.0, 2645.0),
            (1.08500, 1.08100, 1.08300),
            (155.500, 155.100, 155.300),
            (1.27800, 1.27200, 1.27500),
        ]
        for top, bottom, expected_ce in cases:
            ce = ReferenceFVGOracle.calculate_ce(top, bottom)
            assert ce == pytest.approx(expected_ce, abs=1e-5)

    def test_fvg_mitigation_tracking_unmitigated_vs_mitigated(self):
        """Verifies FVG mitigation tracking against future price action."""
        # Candle 1 (high 100), Candle 2 (disp), Candle 3 (low 110) -> FVG [100, 110], CE = 105
        # Case A: Future bars stay above 110 -> Unmitigated
        unmitigated_data = [
            (98, 100, 97, 99, 10),
            (99, 100, 98, 100, 10),  # Candle 1: High = 100
            (100, 112, 100, 111, 50), # Candle 2
            (111, 115, 110, 114, 20), # Candle 3: Low = 110
            (114, 118, 112, 117, 15), # Future: Low = 112 (> 110)
        ]
        df_unmitigated = create_ohlcv_df(unmitigated_data)
        fvgs_unmit = ReferenceFVGOracle.detect_fvgs_with_ce(df_unmitigated, min_gap_pips=1.0, symbol="EURUSD")
        assert len(fvgs_unmit) == 1
        assert fvgs_unmit[0]["mitigated"] is False
        assert fvgs_unmit[0]["partially_mitigated"] is False

        # Case B: Future bar penetrates to 104 (below CE 105) -> Fully Mitigated
        mitigated_data = unmitigated_data + [(117, 117, 104, 106, 30)]
        df_mitigated = create_ohlcv_df(mitigated_data)
        fvgs_mit = ReferenceFVGOracle.detect_fvgs_with_ce(df_mitigated, min_gap_pips=1.0, symbol="EURUSD")
        assert len(fvgs_mit) == 1
        assert fvgs_mit[0]["mitigated"] is True

        # Case C: Future bar penetrates to 108 (enters gap [100, 110] but above CE 105) -> Partially Mitigated
        partial_data = unmitigated_data + [(117, 117, 108, 109, 25)]
        df_partial = create_ohlcv_df(partial_data)
        fvgs_part = ReferenceFVGOracle.detect_fvgs_with_ce(df_partial, min_gap_pips=1.0, symbol="EURUSD")
        assert len(fvgs_part) == 1
        assert fvgs_part[0]["mitigated"] is False
        assert fvgs_part[0]["partially_mitigated"] is True

    def test_fvg_filtering_by_min_gap_pips(self):
        """Verifies that gaps smaller than min_gap_pips are filtered out."""
        # Gap size = 0.0001 (1 pip on EURUSD), min_gap_pips = 2.0 -> Should return empty
        data = [
            (1.0800, 1.0810, 1.0795, 1.0805, 50),
            (1.0805, 1.0810, 1.0800, 1.0808, 50),  # Candle 1: High = 1.0810
            (1.0808, 1.0820, 1.0807, 1.0819, 90),  # Candle 2
            (1.0819, 1.0825, 1.0811, 1.0822, 60),  # Candle 3: Low = 1.0811 (Gap = 0.0001 = 1 pip)
            (1.0822, 1.0830, 1.0820, 1.0828, 50),
        ]
        df = create_ohlcv_df(data)
        fvgs = MarketAnalyzer.detect_fvg(df, min_gap_pips=2.0, symbol="EURUSD")
        assert len(fvgs) == 0

        # With min_gap_pips = 0.5, gap is detected
        fvgs_low_tol = MarketAnalyzer.detect_fvg(df, min_gap_pips=0.5, symbol="EURUSD")
        assert len(fvgs_low_tol) == 1

    def test_fvg_edge_cases_empty_and_short_series(self):
        """Ensures FVG detection returns empty list on empty or insufficient DataFrames without error."""
        assert MarketAnalyzer.detect_fvg(pd.DataFrame()) == []
        assert MarketAnalyzer.detect_fvg(None) == []

        short_df = create_ohlcv_df([(100, 105, 95, 102, 10)] * 3)
        assert MarketAnalyzer.detect_fvg(short_df) == []


# ============================================================================
# SECTION 3: DOMAIN 2 — ORDER BLOCKS (OB) & VOLUME VALIDATION TESTS
# ============================================================================

class TestOrderBlocks:
    """Comprehensive tests for Order Block detection, volume validation, and touch tracking."""

    def test_bullish_order_block_detection(self):
        """Verifies detection of Bullish OB: down candle followed by 2 impulsive up candles breaking previous high."""
        data = [
            (2650.0, 2652.0, 2648.0, 2651.0, 100),
            (2651.0, 2653.0, 2649.0, 2650.0, 110),
            (2650.0, 2652.0, 2646.0, 2647.0, 150),
            (2647.0, 2648.0, 2644.0, 2645.0, 160),  # Index 3: Down-candle (Open 2647, Close 2645, High 2648, Low 2644)
            (2645.0, 2652.0, 2645.0, 2650.0, 280),  # Index 4: Up-candle 1 (Close 2650 > Open 2645)
            (2650.0, 2660.0, 2649.0, 2658.0, 420),  # Index 5: Up-candle 2 (Close 2658 > Open 2650 and > 2648)
            (2658.0, 2662.0, 2656.0, 2660.0, 200),
        ]
        df = create_ohlcv_df(data)

        obs = MarketAnalyzer.detect_order_blocks(df)
        assert len(obs) >= 1
        bullish_ob = next((ob for ob in obs if ob["type"] == "BULLISH_OB"), None)
        assert bullish_ob is not None
        assert bullish_ob["high"] == pytest.approx(2648.0)
        assert bullish_ob["low"] == pytest.approx(2644.0)
        assert bullish_ob["entry_price"] == pytest.approx(2648.0)
        assert bullish_ob["sl_price"] == pytest.approx(2644.0)

    def test_bearish_order_block_detection(self):
        """Verifies detection of Bearish OB: up candle followed by 2 impulsive down candles breaking previous low."""
        data = [
            (1.0800, 1.0810, 1.0790, 1.0805, 100),
            (1.0805, 1.0815, 1.0800, 1.0810, 110),
            (1.0810, 1.0820, 1.0808, 1.0815, 120),
            (1.0815, 1.0830, 1.0812, 1.0828, 180),  # Index 3: Up-candle (Open 1.0815, Close 1.0828, High 1.0830, Low 1.0812)
            (1.0828, 1.0829, 1.0795, 1.0798, 320),  # Index 4: Down-candle 1
            (1.0798, 1.0800, 1.0770, 1.0775, 450),  # Index 5: Down-candle 2 (Close 1.0775 < 1.0812)
            (1.0775, 1.0780, 1.0760, 1.0765, 150),
        ]
        df = create_ohlcv_df(data)

        obs = MarketAnalyzer.detect_order_blocks(df)
        assert len(obs) >= 1
        bearish_ob = next((ob for ob in obs if ob["type"] == "BEARISH_OB"), None)
        assert bearish_ob is not None
        assert bearish_ob["high"] == pytest.approx(1.0830)
        assert bearish_ob["low"] == pytest.approx(1.0812)
        assert bearish_ob["entry_price"] == pytest.approx(1.0812)
        assert bearish_ob["sl_price"] == pytest.approx(1.0830)

    def test_order_block_volume_validation(self):
        """Verifies that OB displacement candles exhibit volume expansion."""
        # Down candle with vol=100, displacement candles with vol=300 and 450 (> 2.0x volume)
        data = [
            (100, 102, 98, 101, 100),
            (101, 103, 99, 102, 100),
            (102, 104, 100, 101, 100),
            (101, 102, 95, 96, 100),   # OB Base candle: vol=100
            (96, 105, 96, 104, 300),   # Displacement 1: vol=300
            (104, 115, 103, 114, 450), # Displacement 2: vol=450
            (114, 116, 112, 115, 120),
        ]
        df = create_ohlcv_df(data)

        validated_obs = ReferenceOrderBlockOracle.detect_order_blocks_with_validation(df, volume_threshold_multiplier=2.0)
        assert len(validated_obs) >= 1
        assert validated_obs[0]["high"] == pytest.approx(102.0)
        assert validated_obs[0]["low"] == pytest.approx(95.0)

    def test_order_block_touch_count_and_invalidation(self):
        """Verifies touch count tracking and invalidation on close beyond OB zone."""
        # OB formed at base: high=102, low=95
        # Bar 6 touches into [95, 102] -> touch_count = 1
        # Bar 7 touches again -> touch_count = 2
        # Bar 8 closes at 93 (< 95) -> invalidated = True
        data = [
            (100, 102, 98, 101, 100),
            (101, 103, 99, 102, 100),
            (102, 104, 100, 101, 100),
            (101, 102, 95, 96, 100),   # OB: high=102, low=95
            (96, 105, 96, 104, 300),
            (104, 115, 103, 114, 450),
            (114, 114, 98, 105, 120),  # Low = 98 (inside [95, 102]) -> Touch 1
            (105, 106, 96, 101, 110),  # Low = 96 (inside [95, 102]) -> Touch 2
            (101, 101, 92, 93, 200),   # Close = 93 (< 95) -> Invalidated!
        ]
        df = create_ohlcv_df(data)
        obs = [o for o in ReferenceOrderBlockOracle.detect_order_blocks_with_validation(df) if o["type"] == "BULLISH_OB"]
        assert len(obs) >= 1
        ob = obs[0]
        assert ob["touch_count"] == 2
        assert ob["invalidated"] is True

    def test_order_block_edge_cases_short_dataframe(self):
        """Ensures OB detection gracefully handles short/empty series."""
        assert MarketAnalyzer.detect_order_blocks(pd.DataFrame()) == []
        assert MarketAnalyzer.detect_order_blocks(None) == []
        short_df = create_ohlcv_df([(100, 105, 95, 102, 10)] * 5)
        assert MarketAnalyzer.detect_order_blocks(short_df) == []


# ============================================================================
# SECTION 4: DOMAIN 3 — OPTIMAL TRADE ENTRY (OTE) RETRACEMENT GRIDS
# ============================================================================

class TestOptimalTradeEntry:
    """Comprehensive tests for OTE Fibonacci retracement grids (50% EQ, 61.8%, 70.5%, 78.6%)."""

    def setup_method(self):
        self.engine = OrderFlowQuantEngine()

    def test_ote_bullish_grid_calculations_and_sweet_spot(self):
        """Validates Bullish OTE grid: 61.8%, 70.5% Institutional Sweet Spot, and 78.6% levels."""
        # Range: High = 2000.0, Low = 1900.0, Diff = 100.0
        # Bullish retracement from high:
        # fib_618 = 2000 - 61.8 = 1938.2
        # fib_705 = 2000 - 70.5 = 1929.5 (Sweet Spot)
        # fib_786 = 2000 - 78.6 = 1921.4
        grid = ReferenceOTEOracle.compute_ote_grid(2000.0, 1900.0, 1930.0, "BUY")
        assert grid["equilibrium"] == pytest.approx(1950.0)
        assert grid["fib_618"] == pytest.approx(1938.2)
        assert grid["fib_705_sweet_spot"] == pytest.approx(1929.5)
        assert grid["fib_786"] == pytest.approx(1921.4)
        assert grid["in_ote_zone"] is True
        assert grid["score_bonus"] == pytest.approx(0.60)

    def test_ote_bearish_grid_calculations_and_sweet_spot(self):
        """Validates Bearish OTE grid: 61.8%, 70.5% Institutional Sweet Spot, and 78.6% levels."""
        # Range: High = 2000.0, Low = 1900.0, Diff = 100.0
        # Bearish retracement from low:
        # fib_618 = 1900 + 61.8 = 1961.8
        # fib_705 = 1900 + 70.5 = 1970.5 (Sweet Spot)
        # fib_786 = 1900 + 78.6 = 1978.6
        grid = ReferenceOTEOracle.compute_ote_grid(2000.0, 1900.0, 1970.0, "SELL")
        assert grid["equilibrium"] == pytest.approx(1950.0)
        assert grid["fib_618"] == pytest.approx(1961.8)
        assert grid["fib_705_sweet_spot"] == pytest.approx(1970.5)
        assert grid["fib_786"] == pytest.approx(1978.6)
        assert grid["in_ote_zone"] is True
        assert grid["score_bonus"] == pytest.approx(0.60)

    def test_order_flow_quant_engine_ote_buy_and_sell(self):
        """Tests OrderFlowQuantEngine.compute_ote_fibonacci_array with DataFrame."""
        # Generate 30 bars with high=2660.0 and low=2600.0 (diff=60.0)
        candles = [(2620, 2630, 2610, 2625, 100)] * 30
        candles[10] = (2620, 2660.0, 2610, 2650, 100)  # Max High = 2660.0
        candles[15] = (2620, 2630, 2600.0, 2605, 100)  # Min Low = 2600.0
        df = create_ohlcv_df(candles)

        # Bullish OTE: diff = 60.0
        # fib_618 = 2660 - (0.618 * 60) = 2622.92
        # fib_705 = 2660 - (0.705 * 60) = 2617.70
        # fib_786 = 2660 - (0.786 * 60) = 2612.84
        res_buy_in = self.engine.compute_ote_fibonacci_array(df, current_price=2618.0, direction="BUY")
        assert res_buy_in["in_ote_zone"] is True
        assert res_buy_in["fib_705_sweet_spot"] == pytest.approx(2617.70, abs=0.01)
        assert res_buy_in["score_bonus"] == pytest.approx(0.60)

        # Price outside OTE (e.g. 2650.0 > 2622.92)
        res_buy_out = self.engine.compute_ote_fibonacci_array(df, current_price=2650.0, direction="BUY")
        assert res_buy_out["in_ote_zone"] is False
        assert res_buy_out["score_bonus"] == pytest.approx(0.0)

        # Bearish OTE:
        # fib_618 = 2600 + (0.618 * 60) = 2637.08
        # fib_705 = 2600 + (0.705 * 60) = 2642.30
        # fib_786 = 2600 + (0.786 * 60) = 2647.16
        res_sell_in = self.engine.compute_ote_fibonacci_array(df, current_price=2642.0, direction="SELL")
        assert res_sell_in["in_ote_zone"] is True
        assert res_sell_in["fib_705_sweet_spot"] == pytest.approx(2642.30, abs=0.01)

    def test_premium_discount_50pct_equilibrium_matrix(self):
        """Verifies 50% Equilibrium Dealing Range classification."""
        candles = [(100, 110, 90, 100, 100)] * 20  # High=110, Low=90, EQ=100, Range=20
        df = create_ohlcv_df(candles)

        # 5% threshold = 1.0. Discount < 99.0, Premium > 101.0, Equilibrium in [99.0, 101.0]
        disc = self.engine.evaluate_premium_discount(df, current_price=95.0)
        assert disc["zone"] == "DISCOUNT"
        assert disc["is_buy_allowed"] is True
        assert disc["is_sell_allowed"] is False
        assert disc["equilibrium"] == pytest.approx(100.0)

        prem = self.engine.evaluate_premium_discount(df, current_price=105.0)
        assert prem["zone"] == "PREMIUM"
        assert prem["is_buy_allowed"] is False
        assert prem["is_sell_allowed"] is True

        eq = self.engine.evaluate_premium_discount(df, current_price=100.2)
        assert eq["zone"] == "EQUILIBRIUM"
        assert eq["is_buy_allowed"] is True
        assert eq["is_sell_allowed"] is True

    def test_ote_edge_cases_flat_range_and_short_series(self):
        """Ensures OTE calculations handle flat range (high==low) and short series gracefully."""
        flat_df = create_ohlcv_df([(100, 100, 100, 100, 10)] * 20)
        res = self.engine.compute_ote_fibonacci_array(flat_df, current_price=100.0, direction="BUY")
        assert res["in_ote_zone"] is False

        short_df = create_ohlcv_df([(100, 105, 95, 100, 10)] * 5)
        res_short = self.engine.compute_ote_fibonacci_array(short_df, current_price=100.0, direction="BUY")
        assert res_short["in_ote_zone"] is False


# ============================================================================
# SECTION 5: DOMAIN 4 — LIQUIDITY SWEEPS & STOP-HUNT MARKERS
# ============================================================================

class TestLiquiditySweeps:
    """Comprehensive tests for Equal Highs/Lows (EQH/EQL) and Turtle Soup liquidity sweeps."""

    def setup_method(self):
        self.engine = OrderFlowQuantEngine(pip_tolerance=2.0)
        self.mm_game = MarketMakerGameEngine()

    def test_bearish_eqh_sweep_turtle_soup_detection(self):
        """Verifies detection of Equal Highs (EQH) liquidity sweep and rejection."""
        # 35 candles: two distinct highs at 2650.0 within tolerance, followed by a sweep at 2651.5 closing at 2648.0
        candles = [(2640, 2645, 2635, 2642, 100)] * 35
        # High 1 at index 18: 2650.0
        candles[18] = (2645, 2650.0, 2644, 2648, 150)
        # High 2 at index 25: 2650.1 (within 2 pips = 0.2 on XAUUSD)
        candles[25] = (2646, 2650.1, 2645, 2647, 160)
        # Current bar at index 34: High pierced to 2652.0 (> 2650.1) but Closed at 2647.0 (< 2650.1)
        candles[34] = (2648, 2652.0, 2646, 2647.0, 300)
        df = create_ohlcv_df(candles)

        sweep = self.engine.detect_eqh_eql_inducement(df, symbol="XAUUSD")
        assert sweep["inducement_type"] == "BEARISH_EQH_SWEEP"
        assert sweep["is_swept"] is True
        assert sweep["level"] == pytest.approx(2650.1)

    def test_bullish_eql_sweep_turtle_soup_detection(self):
        """Verifies detection of Equal Lows (EQL) liquidity sweep and rejection."""
        # Two distinct lows at 1.0800, followed by a sweep at 1.0798 closing at 1.0805
        candles = [(1.0820, 1.0830, 1.0815, 1.0825, 100)] * 35
        # Low 1 at index 18: 1.0800
        candles[18] = (1.0815, 1.0820, 1.0800, 1.0810, 150)
        # Low 2 at index 26: 1.0801 (within 2 pips = 0.0002 on EURUSD)
        candles[26] = (1.0810, 1.0815, 1.0801, 1.0808, 140)
        # Current bar: Low pierced to 1.0795 (< 1.0800) but Closed at 1.0806 (> 1.0800)
        candles[34] = (1.0803, 1.0810, 1.0795, 1.0806, 280)
        df = create_ohlcv_df(candles)

        sweep = self.engine.detect_eqh_eql_inducement(df, symbol="EURUSD")
        assert sweep["inducement_type"] == "BULLISH_EQL_SWEEP"
        assert sweep["is_swept"] is True
        assert sweep["level"] == pytest.approx(1.0800)

    def test_market_maker_game_engine_bullish_liquidity_sweep(self):
        """Tests MarketMakerGameEngine.detect_liquidity_sweep for Bullish rejection wick."""
        # Lookback = 20 bars. Lowest low in range was 2640.0.
        # Prev bar pierced to 2638.0 and closed at 2644.0 with long lower wick (wick 6.0 > body 4.0)
        candles = [(2645, 2650, 2642, 2646, 100)] * 25
        candles[10] = (2644, 2648, 2640.0, 2645, 100)  # Recent low = 2640.0
        # Prev bar (index -2): Open 2640, Close 2644, Low 2638, High 2645 -> Wick = 2644 - 2638 = 6.0, Body = 4.0
        candles[23] = (2640.0, 2645.0, 2638.0, 2644.0, 250)
        # Latest bar (index -1)
        candles[24] = (2644.0, 2648.0, 2643.0, 2647.0, 150)
        df = create_ohlcv_df(candles)

        res = self.mm_game.detect_liquidity_sweep(df, lookback=20)
        assert res["sweep_detected"] is True
        assert res["type"] == "BULLISH_SWEEP"
        assert res["swept_level"] == pytest.approx(2640.0)
        assert res["rejection_wick_price"] == pytest.approx(2638.0)

    def test_market_maker_game_engine_bearish_liquidity_sweep(self):
        """Tests MarketMakerGameEngine.detect_liquidity_sweep for Bearish rejection wick."""
        # Lookback = 20 bars. Highest high in range was 2660.0.
        # Prev bar pierced to 2665.0 and closed at 2658.0 (Open 2659, Close 2658) -> Wick = 2665 - 2658 = 7.0, Body = 1.0
        candles = [(2650, 2655, 2648, 2652, 100)] * 25
        candles[12] = (2652, 2660.0, 2650, 2656, 100)  # Recent high = 2660.0
        candles[23] = (2659.0, 2665.0, 2657.0, 2658.0, 300)
        candles[24] = (2658.0, 2659.0, 2654.0, 2655.0, 120)
        df = create_ohlcv_df(candles)

        res = self.mm_game.detect_liquidity_sweep(df, lookback=20)
        assert res["sweep_detected"] is True
        assert res["type"] == "BEARISH_SWEEP"
        assert res["swept_level"] == pytest.approx(2660.0)
        assert res["rejection_wick_price"] == pytest.approx(2665.0)

    def test_judas_swing_session_open_manipulation(self):
        """Tests detection of ICT Judas Swing fakeout at session open."""
        # Bearish Judas: Open=100.0, High reaches 100.25 (> 100 * 1.0015 = 100.15), then Closes at 99.80 (< 100.0)
        candles = [
            (100.0, 100.25, 99.95, 100.10, 100),
            (100.10, 100.25, 99.85, 99.90, 150),
            (99.90, 99.95, 99.70, 99.80, 200),
        ]
        df = create_ohlcv_df(candles)
        res = self.mm_game.detect_judas_swing(df, session_name="LONDON")
        assert res["judas_detected"] is True
        assert res["type"] == "BEARISH_JUDAS_SWING"

    def test_clean_breakout_does_not_trigger_sweep(self):
        """Ensures full body breakout closing beyond level is NOT classified as a rejection sweep."""
        candles = [(2645, 2650, 2642, 2646, 100)] * 25
        candles[10] = (2644, 2648, 2640.0, 2645, 100)  # Low = 2640.0
        # Prev bar cleanly breaks and closes AT 2635.0 (< 2640.0) with no rejection
        candles[23] = (2639.0, 2640.0, 2634.0, 2635.0, 300)
        candles[24] = (2635.0, 2636.0, 2632.0, 2633.0, 200)
        df = create_ohlcv_df(candles)

        res = self.mm_game.detect_liquidity_sweep(df, lookback=20)
        assert res["sweep_detected"] is False


# ============================================================================
# SECTION 6: DOMAIN 5 — INTERBANK IPDA SESSION KILLZONES
# ============================================================================

class TestIPDAKillzones:
    """Comprehensive tests for IPDA Interbank Session Killzone time filters and transitions."""

    def setup_method(self):
        self.engine = OrderFlowQuantEngine()

    @pytest.mark.parametrize("test_time,expected_zone,expected_prime,expected_boost", [
        (time(7, 0, 0), "LONDON_OPEN_KILLZONE", True, 0.40),
        (time(8, 30, 0), "LONDON_OPEN_KILLZONE", True, 0.40),
        (time(10, 0, 0), "LONDON_OPEN_KILLZONE", True, 0.40),
        (time(12, 0, 0), "NY_AM_KILLZONE", True, 0.50),
        (time(13, 30, 0), "NY_AM_KILLZONE", True, 0.50),
        (time(15, 0, 0), "NY_AM_KILLZONE", True, 0.50),
        (time(18, 0, 0), "NY_PM_KILLZONE", True, 0.30),
        (time(19, 15, 0), "NY_PM_KILLZONE", True, 0.30),
        (time(20, 0, 0), "NY_PM_KILLZONE", True, 0.30),
        (time(3, 0, 0), "OFF_HOURS", False, 0.0),
        (time(10, 1, 0), "OFF_HOURS", False, 0.0),
        (time(16, 0, 0), "OFF_HOURS", False, 0.0),
        (time(22, 30, 0), "OFF_HOURS", False, 0.0),
    ])
    def test_ipda_killzone_oracle_evaluations(self, test_time, expected_zone, expected_prime, expected_boost):
        """Verifies killzone identification across representative 24h time points."""
        res = ReferenceIPDAKillzoneOracle.evaluate_killzone(test_time)
        assert res["killzone"] == expected_zone
        assert res["is_prime_killzone"] == expected_prime
        assert res["confluence_boost"] == pytest.approx(expected_boost)

    def test_order_flow_quant_engine_get_active_killzone(self):
        """Tests OrderFlowQuantEngine.get_active_killzone with mocked UTC system time."""
        with patch("src.order_flow_quant.datetime") as mock_dt:
            # 1. London Open (08:30 UTC)
            mock_dt.now.return_value = datetime(2026, 8, 14, 8, 30, 0, tzinfo=timezone.utc)
            res_london = self.engine.get_active_killzone()
            assert res_london["killzone"] == "LONDON_OPEN_KILLZONE"
            assert res_london["is_prime_killzone"] is True
            assert res_london["confluence_boost"] == pytest.approx(0.40)

            # 2. NY Morning AM (13:45 UTC)
            mock_dt.now.return_value = datetime(2026, 8, 14, 13, 45, 0, tzinfo=timezone.utc)
            res_ny_am = self.engine.get_active_killzone()
            assert res_ny_am["killzone"] == "NY_AM_KILLZONE"
            assert res_ny_am["is_prime_killzone"] is True
            assert res_ny_am["confluence_boost"] == pytest.approx(0.50)

            # 3. NY Afternoon PM Silver Bullet (19:00 UTC)
            mock_dt.now.return_value = datetime(2026, 8, 14, 19, 0, 0, tzinfo=timezone.utc)
            res_ny_pm = self.engine.get_active_killzone()
            assert res_ny_pm["killzone"] == "NY_PM_KILLZONE"
            assert res_ny_pm["is_prime_killzone"] is True
            assert res_ny_pm["confluence_boost"] == pytest.approx(0.30)

            # 4. Off-Hours (23:00 UTC)
            mock_dt.now.return_value = datetime(2026, 8, 14, 23, 0, 0, tzinfo=timezone.utc)
            res_off = self.engine.get_active_killzone()
            assert res_off["killzone"] == "OFF_HOURS"
            assert res_off["is_prime_killzone"] is False
            assert res_off["confluence_boost"] == pytest.approx(0.0)


# ============================================================================
# SECTION 7: DOMAIN 6 — LEE-READY CUMULATIVE VOLUME DELTA (CVD) TESTS
# ============================================================================

class TestCumulativeVolumeDelta:
    """Comprehensive tests for Lee-Ready tick classification, CVD, and volume delta summation."""

    def setup_method(self):
        self.engine = OrderFlowQuantEngine()

    def test_lee_ready_quote_rule_bid_ask_classification(self):
        """Verifies Quote Rule: price > mid classified as Buy (+1), price < mid as Sell (-1)."""
        # Mid = 2650.0. Price 2650.20 -> Buy. Price 2649.80 -> Sell.
        ticks = [
            {"bid": 2649.90, "ask": 2650.10, "last": 2650.20, "volume": 10},  # > Mid -> Buy (+10)
            {"bid": 2649.90, "ask": 2650.10, "last": 2649.80, "volume": 5},   # < Mid -> Sell (-5)
            {"bid": 2649.90, "ask": 2650.10, "last": 2650.20, "volume": 15},  # > Mid -> Buy (+15)
        ]
        res = ReferenceLeeReadyCVDOracle.compute_lee_ready_cvd(ticks)
        assert res["net_delta"] == 20  # 10 - 5 + 15 = 20
        assert res["total_buy_vol"] == 25
        assert res["total_sell_vol"] == 5
        assert res["buyer_ratio"] == pytest.approx(25 / 30, abs=0.01)

    def test_lee_ready_tick_test_uptick_downtick(self):
        """Verifies Tick Test fallback when price equals mid or mid is unavailable."""
        # Prices: 100 -> 101 (uptick +) -> 99 (downtick -) -> 102 (uptick +)
        ticks = [
            {"bid": 100.0, "ask": 100.0, "last": 100.0, "volume": 5},   # initial
            {"bid": 100.0, "ask": 100.0, "last": 101.0, "volume": 10},  # uptick -> +10
            {"bid": 100.0, "ask": 100.0, "last": 99.0, "volume": 8},    # downtick -> -8
            {"bid": 100.0, "ask": 100.0, "last": 102.0, "volume": 12},  # uptick -> +12
        ]
        res = ReferenceLeeReadyCVDOracle.compute_lee_ready_cvd(ticks)
        # Expected deltas: +5, +10, -8, +12 -> Sum = 19
        assert res["net_delta"] == 19
        assert res["total_buy_vol"] == 27
        assert res["total_sell_vol"] == 8

    def test_lee_ready_zero_tick_carry_forward(self):
        """Verifies Zero-Tick carry forward: unchanged price retains direction of previous trade."""
        # Price moves 100 -> 102 (uptick: buy) -> 102 (zero-tick: continues buy) -> 102 (zero-tick: continues buy)
        ticks = [
            {"bid": 100.0, "ask": 100.0, "last": 100.0, "volume": 1},
            {"bid": 102.0, "ask": 102.0, "last": 102.0, "volume": 5},  # uptick (+5)
            {"bid": 102.0, "ask": 102.0, "last": 102.0, "volume": 7},  # zero-tick (+7)
            {"bid": 102.0, "ask": 102.0, "last": 102.0, "volume": 8},  # zero-tick (+8)
            {"bid": 101.0, "ask": 101.0, "last": 101.0, "volume": 10}, # downtick (-10)
            {"bid": 101.0, "ask": 101.0, "last": 101.0, "volume": 6},  # zero-tick (-6)
        ]
        res = ReferenceLeeReadyCVDOracle.compute_lee_ready_cvd(ticks)
        # Deltas: +1, +5, +7, +8, -10, -6 -> Sum = 5
        assert res["net_delta"] == 5
        assert res["total_buy_vol"] == 21
        assert res["total_sell_vol"] == 16

    def test_order_flow_quant_compute_tick_cvd_with_numpy_array(self):
        """Tests OrderFlowQuantEngine.compute_tick_cvd on structured numpy tick records."""
        # 20 ticks: 15 buys at ask (mid=2650.0, price=2650.10), 5 sells at bid (price=2649.90)
        dtype = [('time', 'M8[s]'), ('bid', 'f8'), ('ask', 'f8'), ('last', 'f8'), ('volume', 'f8'), ('volume_ext', 'f8')]
        ticks_arr = np.empty(20, dtype=dtype)
        base_time = np.datetime64('2026-08-14T08:00:00')
        for i in range(15):
            ticks_arr[i] = (base_time + np.timedelta64(i, 's'), 2649.90, 2650.10, 2650.10, 2.0, 2.0)
        for i in range(15, 20):
            ticks_arr[i] = (base_time + np.timedelta64(i, 's'), 2649.90, 2650.10, 2649.90, 2.0, 2.0)

        cvd_res = self.engine.compute_tick_cvd(ticks_arr)
        # 15 * 2 = 30 buy vol, 5 * 2 = 10 sell vol. Net delta = 20. Total vol = 40. Buyer ratio = 30/40 = 0.75
        assert cvd_res["net_delta"] == 20
        assert cvd_res["buyer_ratio"] == pytest.approx(0.75)
        assert cvd_res["divergence"] == "BULLISH_CVD_SURGE"  # >= 0.65

    def test_cvd_extreme_burst_volume(self):
        """Verifies CVD computation handles large institutional block trades without overflow."""
        ticks = [
            {"bid": 2650.0, "ask": 2650.2, "last": 2650.2, "volume": 50000.0},
            {"bid": 2650.0, "ask": 2650.2, "last": 2650.2, "volume": 75000.0},
            {"bid": 2650.0, "ask": 2650.2, "last": 2649.9, "volume": 25000.0},
        ]
        res = ReferenceLeeReadyCVDOracle.compute_lee_ready_cvd(ticks)
        assert res["net_delta"] == 100000
        assert res["total_volume"] == 150000.0
        assert res["buyer_ratio"] == pytest.approx(125000 / 150000, abs=0.01)

    def test_cvd_empty_and_short_series_graceful_handling(self):
        """Ensures compute_tick_cvd handles empty or short arrays safely."""
        res_none = self.engine.compute_tick_cvd(None)
        assert res_none["cvd"] == 0
        assert res_none["buyer_ratio"] == 0.50
        assert res_none["divergence"] == "NONE"

        short_arr = generate_synthetic_ticks([2650.0] * 4)
        res_short = self.engine.compute_tick_cvd(short_arr)
        assert res_short["cvd"] == 0
        assert res_short["buyer_ratio"] == 0.50


# ============================================================================
# SECTION 8: DOMAIN 7 — MARKET DEPTH & BUYER/SELLER RATIOS
# ============================================================================

class TestMarketDepthAndBuyerSellerRatio:
    """Comprehensive tests for Level 2 orderbook depth, buyer/seller volume proportions and imbalance."""

    @staticmethod
    def aggregate_orderbook_depth(
        bids: List[Tuple[float, float]],
        asks: List[Tuple[float, float]]
    ) -> Dict[str, Any]:
        """
        Aggregates L2 order book bids [(price, size), ...] and asks.
        Calculates total depth, spread, VWAP, and buyer/seller depth ratio.
        """
        total_bid_vol = sum(size for _, size in bids) if bids else 0.0
        total_ask_vol = sum(size for _, size in asks) if asks else 0.0
        total_depth = total_bid_vol + total_ask_vol

        best_bid = max(price for price, _ in bids) if bids else 0.0
        best_ask = min(price for price, _ in asks) if asks else 0.0
        spread = round(best_ask - best_bid, 5) if (best_bid > 0 and best_ask > 0) else 0.0

        buyer_pct = (total_bid_vol / max(total_depth, 1e-6)) * 100.0
        seller_pct = (total_ask_vol / max(total_depth, 1e-6)) * 100.0
        imbalance_ratio = total_bid_vol / max(total_ask_vol, 1e-6)

        return {
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "total_bid_vol": round(total_bid_vol, 2),
            "total_ask_vol": round(total_ask_vol, 2),
            "total_depth": round(total_depth, 2),
            "buyer_pct": round(buyer_pct, 1),
            "seller_pct": round(seller_pct, 1),
            "imbalance_ratio": round(imbalance_ratio, 2)
        }

    def test_orderbook_balanced_depth(self):
        """Verifies balanced 50/50 orderbook depth."""
        bids = [(2650.0 - i * 0.1, 100.0) for i in range(5)]
        asks = [(2650.1 + i * 0.1, 100.0) for i in range(5)]
        depth = self.aggregate_orderbook_depth(bids, asks)

        assert depth["best_bid"] == pytest.approx(2650.0)
        assert depth["best_ask"] == pytest.approx(2650.1)
        assert depth["spread"] == pytest.approx(0.1)
        assert depth["total_bid_vol"] == pytest.approx(500.0)
        assert depth["total_ask_vol"] == pytest.approx(500.0)
        assert depth["buyer_pct"] == pytest.approx(50.0)
        assert depth["seller_pct"] == pytest.approx(50.0)
        assert depth["imbalance_ratio"] == pytest.approx(1.0)

    def test_orderbook_heavy_bid_absorption_depth(self):
        """Verifies depth metrics under heavy institutional bid wall (80% buy depth)."""
        bids = [(2650.0 - i * 0.1, 400.0) for i in range(5)]  # 2000 total bid
        asks = [(2650.1 + i * 0.1, 100.0) for i in range(5)]  # 500 total ask
        depth = self.aggregate_orderbook_depth(bids, asks)

        assert depth["total_bid_vol"] == pytest.approx(2000.0)
        assert depth["total_ask_vol"] == pytest.approx(500.0)
        assert depth["buyer_pct"] == pytest.approx(80.0)
        assert depth["seller_pct"] == pytest.approx(20.0)
        assert depth["imbalance_ratio"] == pytest.approx(4.0)

    def test_orderbook_zero_division_resilience(self):
        """Ensures empty orderbook returns 0.0 / default percentages without error."""
        depth = self.aggregate_orderbook_depth([], [])
        assert depth["total_depth"] == 0.0
        assert depth["buyer_pct"] == 0.0
        assert depth["seller_pct"] == 0.0


# ============================================================================
# SECTION 9: DOMAIN 8 — REAL-TIME ABSORPTION DIVERGENCE ALERTS
# ============================================================================

class TestAbsorptionDivergence:
    """Comprehensive tests for Real-Time Price/CVD Absorption Divergence and VSA alerts."""

    @staticmethod
    def detect_absorption_divergence(
        price_swing_1: float,
        price_swing_2: float,
        cvd_swing_1: float,
        cvd_swing_2: float
    ) -> Dict[str, Any]:
        """
        Detects absorption divergences:
        - Bearish Absorption: Price makes Higher High (P2 > P1) but CVD makes Lower High (CVD2 < CVD1)
        - Bullish Absorption: Price makes Lower Low (P2 < P1) but CVD makes Higher Low (CVD2 > CVD1)
        """
        # Price HH with CVD LH (Limit Sellers absorbing Market Buyers)
        if price_swing_2 > price_swing_1 and cvd_swing_2 < cvd_swing_1:
            return {
                "divergence_active": True,
                "type": "BEARISH_ABSORPTION_DIVERGENCE",
                "description": "Institutional limit sellers absorbed aggressive market buyers at new price high."
            }
        # Price LL with CVD HL (Limit Buyers absorbing Market Sellers)
        elif price_swing_2 < price_swing_1 and cvd_swing_2 > cvd_swing_1:
            return {
                "divergence_active": True,
                "type": "BULLISH_ABSORPTION_DIVERGENCE",
                "description": "Institutional limit buyers absorbed aggressive market sellers at new price low."
            }
        else:
            return {
                "divergence_active": False,
                "type": "NONE",
                "description": "Price and CVD are moving in healthy convergence."
            }

    def test_bearish_absorption_divergence(self):
        """Validates Bearish Absorption: Price HH (2650 -> 2665) while CVD forms LH (1500 -> 600)."""
        res = self.detect_absorption_divergence(
            price_swing_1=2650.0,
            price_swing_2=2665.0,
            cvd_swing_1=1500.0,
            cvd_swing_2=600.0
        )
        assert res["divergence_active"] is True
        assert res["type"] == "BEARISH_ABSORPTION_DIVERGENCE"

    def test_bullish_absorption_divergence(self):
        """Validates Bullish Absorption: Price LL (2650 -> 2635) while CVD forms HL (-1200 -> -300)."""
        res = self.detect_absorption_divergence(
            price_swing_1=2650.0,
            price_swing_2=2635.0,
            cvd_swing_1=-1200.0,
            cvd_swing_2=-300.0
        )
        assert res["divergence_active"] is True
        assert res["type"] == "BULLISH_ABSORPTION_DIVERGENCE"

    def test_convergent_trend_no_divergence(self):
        """Validates that healthy trending price and CVD do not trigger divergence alerts."""
        res = self.detect_absorption_divergence(
            price_swing_1=2650.0,
            price_swing_2=2665.0,
            cvd_swing_1=1000.0,
            cvd_swing_2=1800.0
        )
        assert res["divergence_active"] is False
        assert res["type"] == "NONE"

    def test_vsa_volume_absorption_small_candle_body(self):
        """Validates VSA detection of institutional absorption (high volume + small body)."""
        # 25 candles with baseline volume 100. Latest candle has volume 300 (3.0x SMA) with tiny body (0.2 range)
        candles = [(2650, 2652, 2648, 2651, 100)] * 25
        # Range = 2655 - 2645 = 10.0. Body = |2650.5 - 2650.0| = 0.5 <= 0.45 * 10 = 4.5
        candles[-1] = (2650.0, 2655.0, 2645.0, 2650.5, 300)
        df = create_ohlcv_df(candles)

        res = MarketAnalyzer.detect_volume_absorption(df, symbol="XAUUSD")
        assert res["is_absorption"] is True
        assert res["type"] in ["BULLISH_ABSORPTION", "BEARISH_ABSORPTION"]
        assert res["volume_ratio"] >= 1.6

    def test_vsa_volume_absorption_long_rejection_wick(self):
        """Validates VSA detection of institutional rejection wick absorption."""
        # Range = 2650 - 2630 = 20.0. Close = 2648.0, Low = 2630.0 -> Lower wick = 18.0 (90% of range >= 60%)
        candles = [(2650, 2652, 2648, 2651, 100)] * 25
        candles[-1] = (2645.0, 2650.0, 2630.0, 2648.0, 350)
        df = create_ohlcv_df(candles)

        res = MarketAnalyzer.detect_volume_absorption(df, symbol="XAUUSD")
        assert res["is_absorption"] is True
        assert res["type"] == "BULLISH_ABSORPTION"


# ============================================================================
# SECTION 10: DOMAIN 9 — INTEGRATION & CROSS-VALIDATION TESTS
# ============================================================================

class TestEngineIntegration:
    """End-to-end integration tests between OrderFlowQuantEngine, MarketAnalyzer, and Reference Models."""

    def setup_method(self):
        self.config = {
            "magic_number": 888123,
            "symbols": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"],
            "risk_per_trade_pct": 0.50
        }
        self.market_analyzer = MarketAnalyzer(self.config)
        self.of_quant = OrderFlowQuantEngine()

    def test_market_analyzer_full_pipeline_structure(self):
        """Verifies MarketAnalyzer.analyze_symbol returns all required SMC keys without exceptions."""
        candles_h1 = [(2640 + i, 2645 + i, 2638 + i, 2644 + i, 500) for i in range(40)]
        candles_m15 = [(2650 + i * 0.5, 2653 + i * 0.5, 2649 + i * 0.5, 2652 + i * 0.5, 200) for i in range(40)]
        candles_daily = [(2600 + i * 5, 2620 + i * 5, 2595 + i * 5, 2615 + i * 5, 5000) for i in range(20)]

        df_trend = create_ohlcv_df(candles_h1, freq="1h")
        df_entry = create_ohlcv_df(candles_m15, freq="15min")
        df_daily = create_ohlcv_df(candles_daily, freq="1d")

        res = self.market_analyzer.analyze_symbol(
            symbol="XAUUSD",
            df_trend=df_trend,
            df_entry=df_entry,
            df_daily=df_daily
        )

        expected_keys = [
            "symbol", "current_price", "trend_direction", "rsi", "atr",
            "bullish_fvg", "bearish_fvg", "bullish_ob", "bearish_ob",
            "active_support", "active_resistance", "support_levels", "resistance_levels",
            "liquidity_sweep", "judas_swing", "gold_intel", "adr_intel", "vsa_intel",
            "premium_discount", "ote_buy", "ote_sell", "inducement", "killzone"
        ]
        for key in expected_keys:
            assert key in res, f"Missing expected key: {key}"

        assert res["symbol"] == "XAUUSD"
        assert res["trend_direction"] in ["BULLISH", "BEARISH", "NEUTRAL"]
        assert isinstance(res["support_levels"], list)
        assert isinstance(res["resistance_levels"], list)

    def test_gold_institutional_zones_psychological_grid(self):
        """Verifies $25, $50, $100 psychological round number magnets on Gold (XAUUSD)."""
        df_h1 = create_ohlcv_df([(2650, 2660, 2640, 2655, 100)] * 30)
        df_m15 = create_ohlcv_df([(2650, 2655, 2648, 2651.5, 100)] * 30)

        gold_intel = MarketAnalyzer.detect_gold_institutional_zones(
            current_price=2651.50,
            df_trend=df_h1,
            df_entry=df_m15
        )

        assert gold_intel["nearest_psychological_25"] == pytest.approx(2650.0)
        assert gold_intel["nearest_psychological_50"] == pytest.approx(2650.0)
        assert gold_intel["nearest_psychological_100"] == pytest.approx(2700.0)
        assert gold_intel["at_psychological_level"] is True  # Within $3 of 2650.0
        assert gold_intel["psychological_dist"] == pytest.approx(1.5)

    def test_adr_14_calculation_and_exhaustion(self):
        """Verifies 14-day Average Daily Range (ADR) calculation and 120% exhaustion threshold."""
        # 14 days of $20 daily range -> ADR_14 = 20.0
        daily_candles = [(2600, 2620, 2600, 2615, 1000)] * 14
        # Today's range = 2630 - 2600 = 30.0 (150% of ADR -> Exhausted!)
        daily_candles.append((2600, 2630, 2600, 2625, 1500))
        df_daily = create_ohlcv_df(daily_candles, freq="1D")

        adr_res = MarketAnalyzer.calculate_adr(df_daily, current_price=2625.0, symbol="XAUUSD")
        assert adr_res["adr_14"] == pytest.approx(20.0)
        assert adr_res["today_range"] == pytest.approx(30.0)
        assert adr_res["adr_pct_consumed"] == pytest.approx(150.0)
        assert adr_res["is_adr_exhausted"] is True

    def test_key_support_resistance_pivots(self):
        """Verifies extraction of major structural H1 and M15 swing support/resistance levels."""
        # Create clear V-shaped swing low at index 10 and inverted V-shaped swing high at index 20
        h1_candles = [(100, 105, 95, 100, 10)] * 30
        h1_candles[10] = (95, 96, 80.0, 92, 20)  # Major Swing Low at 80.0
        h1_candles[20] = (105, 120.0, 104, 115, 20) # Major Swing High at 120.0

        m15_candles = [(100, 102, 98, 100, 10)] * 30
        df_h1 = create_ohlcv_df(h1_candles)
        df_m15 = create_ohlcv_df(m15_candles)

        sr_res = MarketAnalyzer.detect_key_support_resistance(
            df_trend=df_h1,
            df_entry=df_m15,
            current_price=82.0,
            atr=2.0,
            symbol="EURUSD"
        )
        assert any(lvl[0] == pytest.approx(80.0) for lvl in sr_res["support_levels"])
        assert any(lvl[0] == pytest.approx(120.0) for lvl in sr_res["resistance_levels"])
        assert sr_res["active_support"] is not None
        assert sr_res["active_support"]["level"] == pytest.approx(80.0)


# ============================================================================
# SECTION 11: MULTI-TIER TEST MATRICES (TIERS 1 TO 4)
# ============================================================================

class TestTier1CanonicalEquivalence:
    """Tier 1: Feature Equivalence Class Representatives (>=5 canonical tests per feature)."""

    def test_f3_canonical_fvg_representation(self):
        """Canonical representative for F3: Fair Value Gap detection."""
        candles = [
            (100, 102, 99, 101, 10),
            (101, 104, 100, 103, 10),  # C1: High = 104
            (103, 115, 102, 114, 50),  # C2: Impulsive
            (114, 118, 108, 116, 20),  # C3: Low = 108 (Gap [104, 108])
            (116, 119, 115, 118, 10),
        ]
        df = create_ohlcv_df(candles)
        fvgs = MarketAnalyzer.detect_fvg(df, min_gap_pips=1.0, symbol="EURUSD")
        assert len(fvgs) == 1
        assert fvgs[0]["top"] == pytest.approx(108.0)
        assert fvgs[0]["bottom"] == pytest.approx(104.0)

    def test_f4_canonical_order_block_representation(self):
        """Canonical representative for F4: Order Block detection."""
        candles = [
            (100, 102, 98, 101, 10),
            (101, 102, 95, 96, 10),    # OB down-candle
            (96, 104, 96, 103, 50),    # C1 up
            (103, 112, 102, 110, 60),  # C2 up breaking 102
            (110, 112, 108, 111, 10),
        ]
        df = create_ohlcv_df(candles)
        obs = MarketAnalyzer.detect_order_blocks(df)
        assert len(obs) == 1
        assert obs[0]["type"] == "BULLISH_OB"
        assert obs[0]["high"] == pytest.approx(102.0)

    def test_f5_canonical_ote_grid_representation(self):
        """Canonical representative for F5: OTE retracement grid."""
        grid = ReferenceOTEOracle.compute_ote_grid(100.0, 0.0, 30.0, "BUY")
        assert grid["fib_705_sweet_spot"] == pytest.approx(29.5)
        assert grid["in_ote_zone"] is True

    def test_f6_canonical_liquidity_sweep_representation(self):
        """Canonical representative for F6: Liquidity Sweep."""
        candles = [(100, 105, 95, 102, 10)] * 25
        candles[10] = (100, 105, 90.0, 100, 10)  # Low = 90.0
        candles[23] = (92.0, 95.0, 88.0, 93.0, 50)  # Wick to 88, close at 93
        candles[24] = (93.0, 96.0, 92.0, 95.0, 10)
        df = create_ohlcv_df(candles)
        sweep = MarketMakerGameEngine.detect_liquidity_sweep(df, lookback=20)
        assert sweep["sweep_detected"] is True
        assert sweep["type"] == "BULLISH_SWEEP"

    def test_f7_canonical_killzone_representation(self):
        """Canonical representative for F7: IPDA Killzones."""
        res = ReferenceIPDAKillzoneOracle.evaluate_killzone(time(8, 0))
        assert res["killzone"] == "LONDON_OPEN_KILLZONE"

    def test_f8_canonical_cvd_representation(self):
        """Canonical representative for F8: Lee-Ready CVD."""
        ticks = [{"bid": 100, "ask": 102, "last": 102, "volume": 10}] * 10
        res = ReferenceLeeReadyCVDOracle.compute_lee_ready_cvd(ticks)
        assert res["net_delta"] == 100


class TestTier2BoundaryAndAdversarial:
    """Tier 2: Boundary Value Analysis & Adversarial Stress Cases."""

    def test_fvg_exact_zero_gap_boundary(self):
        """Boundary: Candle 3 Low == Candle 1 High (0 gap). Should detect 0 FVGs."""
        candles = [
            (100, 103.0, 99, 101, 10),
            (101, 105.0, 100, 104, 10),  # C1 High = 105.0
            (104, 110, 103, 109, 20),
            (109, 112, 105.0, 111, 10),  # C3 Low = 105.0 (0 gap)
            (111, 113, 110, 112, 10),
        ]
        df = create_ohlcv_df(candles)
        fvgs = MarketAnalyzer.detect_fvg(df, min_gap_pips=0.1, symbol="EURUSD")
        assert len(fvgs) == 0

    def test_ote_exact_boundary_prices(self):
        """Boundary: Price exactly on 61.8% and 78.6% boundary edges."""
        # Range: High=100, Low=0. fib_618=38.2, fib_786=21.4
        grid_high = ReferenceOTEOracle.compute_ote_grid(100.0, 0.0, 38.2, "BUY")
        assert grid_high["in_ote_zone"] is True

        grid_low = ReferenceOTEOracle.compute_ote_grid(100.0, 0.0, 21.4, "BUY")
        assert grid_low["in_ote_zone"] is True

        grid_above = ReferenceOTEOracle.compute_ote_grid(100.0, 0.0, 38.21, "BUY")
        assert grid_above["in_ote_zone"] is False

        grid_below = ReferenceOTEOracle.compute_ote_grid(100.0, 0.0, 21.39, "BUY")
        assert grid_below["in_ote_zone"] is False

    def test_killzone_exact_second_transitions(self):
        """Boundary: Exact second boundaries of IPDA Killzones."""
        # 06:59:59 -> OFF_HOURS, 07:00:00 -> LONDON, 10:00:00 -> LONDON, 10:00:01 -> OFF_HOURS
        assert ReferenceIPDAKillzoneOracle.evaluate_killzone(time(6, 59, 59))["killzone"] == "OFF_HOURS"
        assert ReferenceIPDAKillzoneOracle.evaluate_killzone(time(7, 0, 0))["killzone"] == "LONDON_OPEN_KILLZONE"
        assert ReferenceIPDAKillzoneOracle.evaluate_killzone(time(10, 0, 0))["killzone"] == "LONDON_OPEN_KILLZONE"
        assert ReferenceIPDAKillzoneOracle.evaluate_killzone(time(10, 0, 1))["killzone"] == "OFF_HOURS"

    def test_cvd_single_tick_and_zero_volume(self):
        """Boundary: Single tick and zero-volume tick stream."""
        ticks = [{"bid": 100, "ask": 101, "last": 101, "volume": 0.0}] * 5
        res = ReferenceLeeReadyCVDOracle.compute_lee_ready_cvd(ticks)
        assert res["net_delta"] == 0
        assert res["buyer_ratio"] == 0.50

    def test_market_depth_single_sided_book(self):
        """Boundary: Book with bids only or asks only."""
        bids = [(100.0, 50.0)]
        depth = TestMarketDepthAndBuyerSellerRatio.aggregate_orderbook_depth(bids, [])
        assert depth["buyer_pct"] == 100.0
        assert depth["seller_pct"] == 0.0


class TestTier3CrossFeaturePairwise:
    """Tier 3: Cross-Feature Pairwise Interactions."""

    def test_pairwise_london_killzone_with_bullish_fvg_and_cvd_surge(self):
        """Pairwise: London Open Killzone + Bullish FVG at 50% CE + Bullish CVD Surge."""
        # 1. Killzone active
        kz = ReferenceIPDAKillzoneOracle.evaluate_killzone(time(8, 30))
        assert kz["is_prime_killzone"] is True

        # 2. Bullish FVG
        candles = [
            (2640, 2644.0, 2638, 2640, 100),
            (2640, 2645, 2639, 2644, 100),  # C1 High = 2645.0
            (2644, 2658, 2643, 2656, 300),  # C2
            (2656, 2660, 2650, 2658, 150),  # C3 Low = 2650.0 (Gap [2645, 2650], CE = 2647.5)
            (2658, 2659, 2648, 2649, 100),  # Retracing near CE 2647.5
        ]
        df = create_ohlcv_df(candles)
        fvgs = ReferenceFVGOracle.detect_fvgs_with_ce(df, symbol="XAUUSD")
        assert len(fvgs) == 1
        assert fvgs[0]["ce"] == pytest.approx(2647.5)

        # 3. CVD Surge
        ticks = [{"bid": 2647.4, "ask": 2647.6, "last": 2647.6, "volume": 20}] * 10
        cvd = ReferenceLeeReadyCVDOracle.compute_lee_ready_cvd(ticks)
        assert cvd["divergence"] == "BULLISH_CVD_SURGE"

        # Confluence check: All 3 signals agree on institutional buying
        confluence_score = kz["confluence_boost"] + 0.50 + 0.30
        assert confluence_score >= 1.0

    def test_pairwise_ny_am_killzone_with_eqh_sweep_and_bearish_ob(self):
        """Pairwise: NY AM Killzone + EQH Sweep + Bearish Order Block Formation."""
        # 1. Killzone
        kz = ReferenceIPDAKillzoneOracle.evaluate_killzone(time(13, 30))
        assert kz["killzone"] == "NY_AM_KILLZONE"

        # 2. Bearish OB with EQH sweep
        candles = [
            (1.0800, 1.0820, 1.0795, 1.0815, 100),
            (1.0815, 1.0850, 1.0810, 1.0845, 120),  # High 1 at 1.0850
            (1.0845, 1.0851, 1.0830, 1.0835, 110),  # High 2 at 1.0851 (EQH)
            (1.0835, 1.0860, 1.0830, 1.0855, 200),  # OB Up-candle: Swept EQH at 1.0860! (High=1.0860, Low=1.0830)
            (1.0855, 1.0856, 1.0820, 1.0822, 350),  # C1 Down
            (1.0822, 1.0825, 1.0790, 1.0795, 450),  # C2 Down breaking 1.0830
            (1.0795, 1.0800, 1.0785, 1.0790, 150),
        ]
        df = create_ohlcv_df(candles)
        obs = MarketAnalyzer.detect_order_blocks(df)
        assert len(obs) >= 1
        bearish_ob = next((ob for ob in obs if ob["type"] == "BEARISH_OB"), None)
        assert bearish_ob is not None
        assert bearish_ob["high"] == pytest.approx(1.0860)


class TestTier4InstitutionalScenarios:
    """Tier 4: Full Lifecycle Institutional Trading Scenarios."""

    def test_scenario_london_open_judas_sweep_to_ote_scale_in(self):
        """
        Scenario S1: London Open (08:00 UTC) EQH sweep on XAUUSD, triggers OTE 70.5% sweet spot entry,
        streams live CVD delta, and validates order block formation.
        """
        # Step 1: Confirm London Open Killzone
        kz = ReferenceIPDAKillzoneOracle.evaluate_killzone(time(8, 0, 0))
        assert kz["killzone"] == "LONDON_OPEN_KILLZONE"
        assert kz["is_prime_killzone"] is True

        # Step 2: Asian Session High set at 2650.0, Judas swing pierces to 2653.0 and dumps to 2620.0
        # Swing High = 2653.0, Swing Low = 2620.0. Range = 33.0
        # OTE Sell Retracement:
        # fib_618 = 2620 + 0.618 * 33 = 2640.39
        # fib_705 = 2620 + 0.705 * 33 = 2643.26 (Sweet Spot)
        # fib_786 = 2620 + 0.786 * 33 = 2645.94
        ote_res = ReferenceOTEOracle.compute_ote_grid(2653.0, 2620.0, 2643.0, "SELL")
        assert ote_res["in_ote_zone"] is True
        assert ote_res["fib_705_sweet_spot"] == pytest.approx(2643.26, abs=0.02)

        # Step 3: Stream CVD showing aggressive institutional seller absorption (delta = -450)
        ticks = [{"bid": 2643.0, "ask": 2643.2, "last": 2643.0, "volume": 30}] * 15
        cvd_res = ReferenceLeeReadyCVDOracle.compute_lee_ready_cvd(ticks)
        assert cvd_res["net_delta"] == -450
        assert cvd_res["divergence"] == "BEARISH_CVD_SURGE"

    def test_scenario_high_impact_news_fvg_retest_and_mitigation(self):
        """
        Scenario S2: High-impact CPI news creates a massive 3-candle FVG,
        price pulls back to 50% Consequent Encroachment (CE), and mitigates smoothly.
        """
        # Pre-news base at 1.0800, massive expansion to 1.0890
        # C1 High = 1.0820, C2 = 1.0820 -> 1.0880, C3 Low = 1.0860 (Gap: [1.0820, 1.0860], CE = 1.0840)
        candles = [
            (1.0800, 1.0816, 1.0795, 1.0802, 100),
            (1.0802, 1.0820, 1.0800, 1.0818, 150),  # C1 High = 1.0820
            (1.0818, 1.0885, 1.0815, 1.0880, 800),  # C2 News candle
            (1.0880, 1.0895, 1.0860, 1.0890, 400),  # C3 Low = 1.0860
            (1.0890, 1.0892, 1.0840, 1.0855, 350),  # Retracement touching CE 1.0840!
            (1.0855, 1.0890, 1.0850, 1.0885, 250),  # Expansion resume
        ]
        df = create_ohlcv_df(candles)
        fvgs = ReferenceFVGOracle.detect_fvgs_with_ce(df, symbol="EURUSD")
        assert len(fvgs) == 1
        fvg = fvgs[0]
        assert fvg["type"] == "BULLISH_FVG"
        assert fvg["ce"] == pytest.approx(1.0840)
        assert fvg["mitigated"] is True  # Low touched 1.0840 (CE)

    def test_scenario_fomc_absorption_divergence_at_round_number(self):
        """
        Scenario S3: FOMC volatility push to $2700 Gold psychological round number,
        VSA flags volume absorption and CVD divergence flags exhaustion.
        """
        # 1. Gold Institutional Psychological Magnet
        df_h1 = create_ohlcv_df([(2690, 2702, 2685, 2698, 500)] * 25)
        df_m15 = create_ohlcv_df([(2695, 2701.5, 2692, 2699.0, 200)] * 25)
        gold_zones = MarketAnalyzer.detect_gold_institutional_zones(2700.50, df_h1, df_m15)
        assert gold_zones["nearest_psychological_100"] == pytest.approx(2700.0)
        assert gold_zones["at_psychological_level"] is True

        # 2. VSA Absorption (Volume surge with long upper rejection wick at 2701.5)
        df_m15.iloc[-1] = pd.Series({
            "time": df_m15.iloc[-1]["time"],
            "open": 2696.0,
            "high": 2701.5,
            "low": 2694.0,
            "close": 2696.5,
            "tick_volume": 1200,
            "volume": 1200
        })
        vsa = MarketAnalyzer.detect_volume_absorption(df_m15, symbol="XAUUSD")
        assert vsa["is_absorption"] is True
        assert vsa["type"] == "BEARISH_ABSORPTION"

        # 3. CVD Divergence: Price went from 2690 -> 2701 (HH) while CVD delta dropped from +2000 -> +300 (LH)
        div = TestAbsorptionDivergence.detect_absorption_divergence(
            price_swing_1=2690.0,
            price_swing_2=2701.5,
            cvd_swing_1=2000.0,
            cvd_swing_2=300.0
        )
        assert div["divergence_active"] is True
        assert div["type"] == "BEARISH_ABSORPTION_DIVERGENCE"
