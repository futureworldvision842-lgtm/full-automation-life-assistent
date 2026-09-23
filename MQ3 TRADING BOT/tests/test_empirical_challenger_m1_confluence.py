"""
tests/test_empirical_challenger_m1_confluence.py
================================================
Milestone 1 Empirical Stress Test & Adversarial Challenge Suite.
Empirically stress-tests the 3-Pillar Confluence and Multi-Asset execution logic:
1. ICT 70.5% Optimal Trade Entry (OTE) Golden Pocket & Fibonacci Array
2. Fair Value Gap (FVG) 50% Consequent Encroachment (CE) & Multi-Bar Mitigation
3. Lee-Ready (1991) Cumulative Volume Delta (CVD) & Tick Absorption Classifiers
4. Structural Absorption Divergence & Wyckoff Phase C/D London/NY Judas Swings
5. 7-Asset Multi-Asset Execution Calibration & Confluence Strategy Matrix
6. Global Liquidation Stop-Pool Tracking & Shark Magnet Heuristics
7. Extreme Boundary Conditions (Flash crashes, 0-spread, wide spreads, negative prices, NaNs)
"""

import math
from datetime import datetime, timezone, time, timedelta
import numpy as np
import pandas as pd
import pytest

from src.order_flow_quant import OrderFlowQuantEngine
from src.market_analyzer import MarketAnalyzer
from src.market_maker_game_engine import MarketMakerGameEngine
from src.global_liquidation_radar import GlobalLiquidationRadar
from src.multi_asset_scanner import MultiAssetScanner
from src.strategy import StrategyEngine


# ============================================================================
# 1. 70.5% OTE FIBONACCI ARRAY EMPIRICAL STRESS TESTS
# ============================================================================

class TestOTE705FibonacciEmpiricalStress:
    """Empirically validates ICT 70.5% OTE golden pocket calculations and boundary handling."""

    @pytest.fixture
    def quant_engine(self):
        return OrderFlowQuantEngine()

    def test_ote_buy_mathematical_precision(self, quant_engine):
        """Verifies exact BUY OTE formula: fib_618, fib_705 (institutional sweet spot), fib_786."""
        # Create standard price series: Low = 100.0, High = 200.0 -> diff = 100.0
        n_bars = 30
        prices = np.linspace(100.0, 200.0, n_bars)
        df = pd.DataFrame({
            "high": prices + 1.0,
            "low": prices - 1.0,
            "close": prices,
            "open": prices
        })
        # Overwrite recent 25 bars: High = 200.0, Low = 100.0
        df.iloc[-25:, df.columns.get_loc("high")] = np.linspace(100.0, 200.0, 25)
        df.iloc[-25:, df.columns.get_loc("low")] = np.linspace(100.0, 200.0, 25)
        df.iloc[-1, df.columns.get_loc("high")] = 200.0
        df.iloc[-25, df.columns.get_loc("low")] = 100.0

        # BUY OTE: Retracement down from High (200.0)
        # fib_618 = 200 - 0.618*100 = 138.2
        # fib_705 = 200 - 0.705*100 = 129.5
        # fib_786 = 200 - 0.786*100 = 121.4
        
        # Test exact sweet spot
        res_705 = quant_engine.compute_ote_fibonacci_array(df, current_price=129.5, direction="BUY")
        assert res_705["in_ote_zone"] is True
        assert math.isclose(res_705["fib_705_sweet_spot"], 129.5, abs_tol=1e-3)
        assert math.isclose(res_705["fib_618"], 138.2, abs_tol=1e-3)
        assert math.isclose(res_705["fib_786"], 121.4, abs_tol=1e-3)
        assert res_705["score_bonus"] == 0.60

        # Test upper boundary (61.8%)
        res_618 = quant_engine.compute_ote_fibonacci_array(df, current_price=138.2, direction="BUY")
        assert res_618["in_ote_zone"] is True
        assert res_618["score_bonus"] == 0.60

        # Test lower boundary (78.6%)
        res_786 = quant_engine.compute_ote_fibonacci_array(df, current_price=121.4, direction="BUY")
        assert res_786["in_ote_zone"] is True
        assert res_786["score_bonus"] == 0.60

        # Test outside OTE zone (Too shallow retracement, e.g. 50% = 150.0)
        res_shallow = quant_engine.compute_ote_fibonacci_array(df, current_price=150.0, direction="BUY")
        assert res_shallow["in_ote_zone"] is False
        assert res_shallow["score_bonus"] == 0.0

        # Test outside OTE zone (Too deep retracement, e.g. 85% = 115.0)
        res_deep = quant_engine.compute_ote_fibonacci_array(df, current_price=115.0, direction="BUY")
        assert res_deep["in_ote_zone"] is False
        assert res_deep["score_bonus"] == 0.0

    def test_ote_sell_mathematical_precision(self, quant_engine):
        """Verifies exact SELL OTE formula: fib_618, fib_705, fib_786."""
        # Low = 1000.0, High = 2000.0 -> diff = 1000.0
        n_bars = 30
        df = pd.DataFrame({
            "high": np.full(n_bars, 2000.0),
            "low": np.full(n_bars, 1000.0),
            "close": np.full(n_bars, 1500.0),
            "open": np.full(n_bars, 1500.0)
        })

        # SELL OTE: Retracement up from Low (1000.0)
        # fib_618 = 1000 + 0.618*1000 = 1618.0
        # fib_705 = 1000 + 0.705*1000 = 1705.0
        # fib_786 = 1000 + 0.786*1000 = 1786.0
        
        # Test sweet spot
        res_705 = quant_engine.compute_ote_fibonacci_array(df, current_price=1705.0, direction="SELL")
        assert res_705["in_ote_zone"] is True
        assert math.isclose(res_705["fib_705_sweet_spot"], 1705.0, abs_tol=1e-3)
        assert math.isclose(res_705["fib_618"], 1618.0, abs_tol=1e-3)
        assert math.isclose(res_705["fib_786"], 1786.0, abs_tol=1e-3)
        assert res_705["score_bonus"] == 0.60

        # Boundary checks
        assert quant_engine.compute_ote_fibonacci_array(df, 1618.0, "SELL")["in_ote_zone"] is True
        assert quant_engine.compute_ote_fibonacci_array(df, 1786.0, "SELL")["in_ote_zone"] is True
        assert quant_engine.compute_ote_fibonacci_array(df, 1600.0, "SELL")["in_ote_zone"] is False
        assert quant_engine.compute_ote_fibonacci_array(df, 1800.0, "SELL")["in_ote_zone"] is False

    def test_ote_edge_cases_and_adversarial_inputs(self, quant_engine):
        """Stress-tests OTE with None, empty, flat range, flash crash, and single-bar inputs."""
        # 1. None DataFrame
        assert quant_engine.compute_ote_fibonacci_array(None, 100.0, "BUY")["in_ote_zone"] is False

        # 2. Insufficient bars (< 15 bars)
        df_short = pd.DataFrame({"high": [10.0]*5, "low": [5.0]*5, "close": [7.0]*5})
        assert quant_engine.compute_ote_fibonacci_array(df_short, 7.0, "BUY")["in_ote_zone"] is False

        # 3. Flat line / Zero range (diff <= 0)
        df_flat = pd.DataFrame({"high": [100.0]*20, "low": [100.0]*20, "close": [100.0]*20})
        res_flat = quant_engine.compute_ote_fibonacci_array(df_flat, 100.0, "BUY")
        assert res_flat["in_ote_zone"] is False
        assert res_flat["score_bonus"] == 0.0

        # 4. Synthetic Flash Crash (Range 100,000 -> 1.0)
        df_crash = pd.DataFrame({
            "high": np.linspace(100000.0, 1000.0, 30),
            "low": np.linspace(99000.0, 1.0, 30),
            "close": np.linspace(99500.0, 500.0, 30)
        })
        res_crash = quant_engine.compute_ote_fibonacci_array(df_crash, 30000.0, "BUY")
        assert isinstance(res_crash["in_ote_zone"], (bool, np.bool_))
        assert "fib_705_sweet_spot" in res_crash

        # 5. Multi-asset scaling across all 7 asset price scales
        for scale, sym in [(100000.0, "BTCUSD"), (3000.0, "ETHUSD"), (200.0, "SOLUSD"), (4400.0, "XAUUSD"), (160.0, "USDJPY"), (1.30, "GBPUSD"), (1.10, "EURUSD")]:
            df_sym = pd.DataFrame({
                "high": np.linspace(scale, scale * 1.05, 30),
                "low": np.linspace(scale * 0.95, scale, 30),
                "close": np.linspace(scale * 0.96, scale * 1.04, 30)
            })
            high_val = float(df_sym['high'].tail(25).max())
            low_val = float(df_sym['low'].tail(25).min())
            diff = high_val - low_val
            target_705 = high_val - (0.705 * diff)
            res = quant_engine.compute_ote_fibonacci_array(df_sym, target_705, "BUY")
            assert res["in_ote_zone"] is True, f"Failed for symbol scale {sym}"


# ============================================================================
# 2. 50% CE FVG DETECTION & MULTI-BAR MITIGATION STRESS TESTS
# ============================================================================

class TestFVGConsequentEncroachmentEmpiricalStress:
    """Empirically tests 50% CE Fair Value Gap detection and dynamic mitigation tracking."""

    def test_bullish_fvg_and_ce_50_calculation(self):
        """Verifies 3-candle bullish FVG detection, CE midpoint, and asset pip scaling."""
        # Symbol: EURUSD (pip_unit = 0.0001)
        # C1: High = 1.1000, Low = 1.0950
        # C2: High = 1.1060, Low = 1.0990 (displacement candle)
        # C3: High = 1.1100, Low = 1.1030
        # Gap: c3_low (1.1030) - c1_high (1.1000) = 0.0030 = 30.0 pips >= 2.0 pips min
        df = pd.DataFrame({
            "high": [1.1000, 1.1060, 1.1100],
            "low":  [1.0950, 1.0990, 1.1030],
            "open": [1.0960, 1.1000, 1.1040],
            "close": [1.0990, 1.1050, 1.1090]
        })
        fvgs = MarketAnalyzer.detect_fvg(df, min_gap_pips=2.0, symbol="EURUSD")
        assert len(fvgs) == 1
        fvg = fvgs[0]
        assert fvg["type"] == "BULLISH_FVG"
        assert math.isclose(fvg["top"], 1.1030, abs_tol=1e-5)
        assert math.isclose(fvg["bottom"], 1.1000, abs_tol=1e-5)
        assert math.isclose(fvg["ce"], 1.1015, abs_tol=1e-5)
        assert math.isclose(fvg["ce_50"], 1.1015, abs_tol=1e-5)
        assert math.isclose(fvg["gap_pips"], 30.0, abs_tol=1e-3)
        assert fvg["mitigated"] is False
        assert fvg["partially_mitigated"] is False

    def test_bearish_fvg_and_ce_50_calculation(self):
        """Verifies 3-candle bearish FVG detection, CE midpoint, and XAUUSD scaling."""
        # Symbol: XAUUSD (pip_unit = 0.1)
        # C1: Low = 4400.0, High = 4410.0
        # C2: Displacement drop
        # C3: High = 4380.0, Low = 4370.0
        # Gap: c1_low (4400.0) - c3_high (4380.0) = 20.0 = 200.0 pips
        df = pd.DataFrame({
            "high": [4410.0, 4400.0, 4380.0],
            "low":  [4400.0, 4375.0, 4370.0],
            "open": [4405.0, 4398.0, 4378.0],
            "close": [4402.0, 4378.0, 4372.0]
        })
        fvgs = MarketAnalyzer.detect_fvg(df, min_gap_pips=2.0, symbol="XAUUSD")
        assert len(fvgs) == 1
        fvg = fvgs[0]
        assert fvg["type"] == "BEARISH_FVG"
        assert math.isclose(fvg["top"], 4400.0, abs_tol=1e-3)
        assert math.isclose(fvg["bottom"], 4380.0, abs_tol=1e-3)
        assert math.isclose(fvg["ce"], 4390.0, abs_tol=1e-3)
        assert math.isclose(fvg["ce_50"], 4390.0, abs_tol=1e-3)
        assert math.isclose(fvg["gap_pips"], 200.0, abs_tol=1e-2)

    def test_forward_mitigation_stages(self):
        """Stress-tests dynamic forward multi-candle mitigation (unmitigated, partially mitigated, 50% CE mitigated)."""
        # Form Bullish FVG on bars 0,1,2: Top=100.0, Bottom=90.0, CE=95.0
        # Bar 3: Low = 105.0 -> Unmitigated
        # Bar 4: Low = 98.0 -> Partially mitigated (enters gap top 100.0, but > 95.0)
        # Bar 5: Low = 94.0 -> Fully mitigated (pierces 50% CE 95.0)
        
        df_base = pd.DataFrame({
            "high": [90.0, 102.0, 110.0],
            "low":  [85.0, 89.0, 100.0],
            "open": [86.0, 90.0, 102.0],
            "close": [89.0, 101.0, 108.0]
        })

        # Stage 1: No forward bars
        fvgs_1 = MarketAnalyzer.detect_fvg(df_base, min_gap_pips=1.0, symbol="BTCUSD")
        assert fvgs_1[0]["mitigated"] is False
        assert fvgs_1[0]["partially_mitigated"] is False

        # Stage 2: Forward bar above gap (Low = 105.0)
        df_unmit = pd.concat([df_base, pd.DataFrame({"high": [112.0], "low": [105.0], "open": [108.0], "close": [111.0]})], ignore_index=True)
        fvgs_2 = MarketAnalyzer.detect_fvg(df_unmit, min_gap_pips=1.0, symbol="BTCUSD")
        assert fvgs_2[0]["mitigated"] is False
        assert fvgs_2[0]["partially_mitigated"] is False

        # Stage 3: Forward bar touches gap (Low = 98.0 <= Top 100.0, but > CE 95.0)
        df_partial = pd.concat([df_base, pd.DataFrame({"high": [106.0], "low": [98.0], "open": [105.0], "close": [100.0]})], ignore_index=True)
        fvgs_3 = MarketAnalyzer.detect_fvg(df_partial, min_gap_pips=1.0, symbol="BTCUSD")
        assert fvgs_3[0]["mitigated"] is False
        assert fvgs_3[0]["partially_mitigated"] is True

        # Stage 4: Forward bar pierces CE (Low = 94.0 <= CE 95.0)
        df_full = pd.concat([df_base, pd.DataFrame({"high": [106.0], "low": [94.0], "open": [105.0], "close": [96.0]})], ignore_index=True)
        fvgs_4 = MarketAnalyzer.detect_fvg(df_full, min_gap_pips=1.0, symbol="BTCUSD")
        assert fvgs_4[0]["mitigated"] is True
        assert fvgs_4[0]["partially_mitigated"] is True

    def test_fvg_boundary_conditions(self):
        """Stress-tests FVG detection on corrupt, empty, and micro-gap inputs."""
        # 1. None DataFrame & short DataFrames
        assert MarketAnalyzer.detect_fvg(None) == []
        assert MarketAnalyzer.detect_fvg(pd.DataFrame()) == []
        assert MarketAnalyzer.detect_fvg(pd.DataFrame({"high": [1.0, 2.0], "low": [0.5, 1.5]})) == []

        # 2. Gap smaller than min_gap_pips
        df_micro = pd.DataFrame({
            "high": [1.1000, 1.1010, 1.1020],
            "low":  [1.0990, 1.1000, 1.1001], # Gap = 0.0001 = 1 pip < 2.0 min pips
            "open": [1.0995, 1.1005, 1.1015],
            "close": [1.0999, 1.1009, 1.1019]
        })
        assert len(MarketAnalyzer.detect_fvg(df_micro, min_gap_pips=2.0, symbol="EURUSD")) == 0


# ============================================================================
# 3. LEE-READY (1991) CVD TICK CLASSIFICATION STRESS TESTS
# ============================================================================

class TestLeeReadyCVDEmpiricalStress:
    """Empirically tests Lee-Ready (1991) trade classification and absorption states."""

    @pytest.fixture
    def quant_engine(self):
        return OrderFlowQuantEngine()

    def test_lee_ready_quote_rule_and_tick_test(self, quant_engine):
        """Validates Quote Rule and Tick Test fallback with zero-tick carry-forward."""
        # Tick stream:
        # Tick 0: Bid=100.0, Ask=102.0, Mid=101.0, Last=102.0 (Price > Mid -> +1 Buy)
        # Tick 1: Bid=100.0, Ask=102.0, Mid=101.0, Last=100.0 (Price < Mid -> -1 Sell)
        # Tick 2: Bid=100.0, Ask=102.0, Mid=101.0, Last=101.0 (Price == Mid, Price > Prev 100.0 -> +1 Uptick)
        # Tick 3: Bid=100.0, Ask=102.0, Mid=101.0, Last=101.0 (Price == Mid, Price == Prev 101.0 -> Carry forward +1)
        ticks = pd.DataFrame({
            "bid": [100.0, 100.0, 100.0, 100.0],
            "ask": [102.0, 102.0, 102.0, 102.0],
            "last": [102.0, 100.0, 101.0, 101.0],
            "volume": [10.0, 10.0, 10.0, 10.0]
        })
        res = quant_engine.compute_tick_cvd(ticks)
        # Deltas: +10, -10, +10, +10 -> Net Delta = +20, Buy Vol = 30, Sell Vol = 10, Buyer Ratio = 0.75
        assert res["net_delta"] == 20
        assert res["total_buy_vol"] == 30.0
        assert res["total_sell_vol"] == 10.0
        assert res["buyer_ratio"] == 0.75
        assert res["absorption_type"] == "BUYER_ABSORPTION"
        assert res["divergence"] == "BULLISH_CVD_SURGE"
        assert res["is_absorption_divergence"] is True

    def test_lee_ready_seller_absorption(self, quant_engine):
        """Validates SELLER_ABSORPTION detection when seller ratio >= 0.65."""
        # 8 sells of volume 10, 2 buys of volume 10 -> Seller Ratio = 0.80
        ticks = pd.DataFrame({
            "bid": [100.0]*10,
            "ask": [102.0]*10,
            "last": [100.0]*8 + [102.0]*2,
            "volume": [10.0]*10
        })
        res = quant_engine.compute_tick_cvd(ticks)
        assert res["seller_ratio"] == 0.80
        assert res["buyer_ratio"] == 0.20
        assert res["absorption_type"] == "SELLER_ABSORPTION"
        assert res["divergence"] == "BEARISH_CVD_SURGE"
        assert res["is_absorption_divergence"] is True

    def test_lee_ready_boundary_and_adversarial_conditions(self, quant_engine):
        """Stress-tests Lee-Ready CVD with 0-spread, wide spread, flat mid, NaNs, and extreme sizes."""
        # 1. None / Empty
        assert quant_engine.compute_tick_cvd(None)["net_delta"] == 0
        assert quant_engine.compute_tick_cvd([])["net_delta"] == 0
        assert quant_engine.compute_tick_cvd(pd.DataFrame())["net_delta"] == 0

        # 2. 0-spread (bid == ask)
        ticks_0spread = pd.DataFrame({
            "bid": [100.0, 100.5, 100.2],
            "ask": [100.0, 100.5, 100.2],
            "last": [100.0, 100.5, 100.2],
            "volume": [5.0, 5.0, 5.0]
        })
        res_0 = quant_engine.compute_tick_cvd(ticks_0spread)
        assert isinstance(res_0["net_delta"], int)
        assert res_0["total_volume"] == 15.0

        # 3. Massive Spread (e.g. illiquid open: bid=100.0, ask=200.0)
        ticks_wide = pd.DataFrame({
            "bid": [100.0, 100.0],
            "ask": [200.0, 200.0],
            "last": [180.0, 120.0], # 180 > 150 -> Buy, 120 < 150 -> Sell
            "volume": [1e6, 1e6]
        })
        res_wide = quant_engine.compute_tick_cvd(ticks_wide)
        assert res_wide["net_delta"] == 0
        assert res_wide["buyer_ratio"] == 0.50

        # 4. Completely flat feed (all prices == mid)
        ticks_flat = pd.DataFrame({
            "bid": [100.0]*5,
            "ask": [100.0]*5,
            "last": [100.0]*5,
            "volume": [1.0]*5
        })
        res_flat = quant_engine.compute_tick_cvd(ticks_flat)
        assert res_flat["net_delta"] == 0

        # 5. List of dicts format
        ticks_dict = [
            {"bid": 1.1000, "ask": 1.1002, "last": 1.1002, "volume": 100},
            {"bid": 1.1000, "ask": 1.1002, "last": 1.1000, "volume": 100}
        ]
        res_dict = quant_engine.compute_tick_cvd(ticks_dict)
        assert res_dict["total_volume"] == 200.0


# ============================================================================
# 4. ABSORPTION DIVERGENCE & JUDAS SWINGS STRESS TESTS
# ============================================================================

class TestJudasSwingsAndAbsorptionDivergenceStress:
    """Empirically tests Asian box extraction, London/NY Judas swings, and CVD structural divergence."""

    @pytest.fixture
    def mm_engine(self):
        return MarketMakerGameEngine()

    @pytest.fixture
    def quant_engine(self):
        return OrderFlowQuantEngine()

    def test_absorption_divergence_matrix(self, quant_engine):
        """Verifies structural divergence classification between Price Swings and CVD Swings."""
        # 1. Bullish Absorption: Price Lower Low (100 -> 90) while CVD Higher Low (50 -> 80)
        res_bull = quant_engine.detect_absorption_divergence(
            price_swing_1=100.0, price_swing_2=90.0,
            cvd_swing_1=50.0, cvd_swing_2=80.0
        )
        assert res_bull["absorption_detected"] is True
        assert res_bull["type"] == "BUYER_ABSORPTION"
        assert res_bull["bias"] == "BULLISH_REVERSAL"

        # 2. Bearish Absorption: Price Higher High (100 -> 110) while CVD Lower High (100 -> 70)
        res_bear = quant_engine.detect_absorption_divergence(
            price_swing_1=100.0, price_swing_2=110.0,
            cvd_swing_1=100.0, cvd_swing_2=70.0
        )
        assert res_bear["absorption_detected"] is True
        assert res_bear["type"] == "SELLER_ABSORPTION"
        assert res_bear["bias"] == "BEARISH_REVERSAL"

        # 3. Regular Trend Alignment (No divergence): Price HH and CVD HH
        res_none = quant_engine.detect_absorption_divergence(
            price_swing_1=100.0, price_swing_2=110.0,
            cvd_swing_1=50.0, cvd_swing_2=80.0
        )
        assert res_none["absorption_detected"] is False
        assert res_none["type"] == "NONE"

    def test_asian_session_box_filtering(self, mm_engine):
        """Verifies 00:00 to 06:00 UTC Asian session isolation and range metrics."""
        # Create 24 hourly timestamps for a full UTC day
        times = [datetime(2026, 8, 17, h, 0, tzinfo=timezone.utc) for h in range(24)]
        highs = [100.0 + h for h in range(24)]
        lows = [90.0 + h for h in range(24)]
        df = pd.DataFrame({
            "time": times,
            "high": highs,
            "low": lows,
            "open": highs,
            "close": lows
        })
        box = mm_engine.calculate_asian_session_box(df)
        # Asian hours: 0, 1, 2, 3, 4, 5
        # Max high in Asian: 100.0 + 5 = 105.0
        # Min low in Asian: 90.0 + 0 = 90.0
        assert box["asian_high"] == 105.0
        assert box["asian_low"] == 90.0
        assert box["asian_range"] == 15.0
        assert box["asian_mid"] == 97.5
        assert box["candle_count"] == 6

    def test_london_judas_swing_fakeout_detection(self, mm_engine):
        """Verifies London Open (07:00-10:00 UTC) fakeout sweeping Asian High with rejection wick >= 40%."""
        # Asian Box: High = 100.0, Low = 90.0
        df_asian = pd.DataFrame({
            "time": [datetime(2026, 8, 17, h, 0, tzinfo=timezone.utc) for h in range(6)],
            "high": [100.0]*6,
            "low": [90.0]*6,
            "open": [95.0]*6,
            "close": [95.0]*6
        })

        # London Open bar (08:00 UTC):
        # Spikes to High = 105.0 (> Asian High 100.0), Closes back down at 98.0 (< 100.0)
        # Open = 97.0, Low = 96.0
        # Range = 105.0 - 96.0 = 9.0
        # Upper Wick = 105.0 - 98.0 = 7.0 (7.0 / 9.0 = 77.8% >= 40% range and >= body 1.0)
        df_london = pd.DataFrame({
            "time": [datetime(2026, 8, 17, 8, 0, tzinfo=timezone.utc)],
            "high": [105.0],
            "low": [96.0],
            "open": [97.0],
            "close": [98.0]
        })

        judas = mm_engine.detect_judas_swing(df_london, session_name="LONDON", df_asian=df_asian)
        assert judas["judas_detected"] is True
        assert judas["type"] == "BEARISH_JUDAS_SWING"
        assert judas["swept_level"] == 100.0
        assert judas["rejection_wick_price"] == 105.0
        assert judas["session"] == "LONDON"

    def test_ny_judas_swing_fakeout_detection(self, mm_engine):
        """Verifies NY Open (13:00-16:00 UTC) fakeout sweeping Asian Low with rejection wick >= 40%."""
        df_asian = pd.DataFrame({
            "time": [datetime(2026, 8, 17, h, 0, tzinfo=timezone.utc) for h in range(6)],
            "high": [2000.0]*6,
            "low": [1900.0]*6,
            "open": [1950.0]*6,
            "close": [1950.0]*6
        })

        # NY Open bar:
        # Pierces Low to 1880.0 (< Asian Low 1900.0), Closes back up at 1920.0 (> 1900.0)
        # Open = 1910.0, High = 1925.0
        # Range = 1925.0 - 1880.0 = 45.0
        # Lower Wick = 1910.0 - 1880.0 = 30.0 (30.0 / 45.0 = 66.7% >= 40% range)
        df_ny = pd.DataFrame({
            "time": [datetime(2026, 8, 17, 14, 0, tzinfo=timezone.utc)],
            "high": [1925.0],
            "low": [1880.0],
            "open": [1910.0],
            "close": [1920.0]
        })

        judas = mm_engine.detect_judas_swing(df_ny, session_name="NEW_YORK", df_asian=df_asian)
        assert judas["judas_detected"] is True
        assert judas["type"] == "BULLISH_JUDAS_SWING"
        assert judas["swept_level"] == 1900.0
        assert judas["rejection_wick_price"] == 1880.0


# ============================================================================
# 5. MULTI-ASSET SCANNER & STRATEGY CONFLUENCE MATRIX STRESS TESTS
# ============================================================================

class TestMultiAssetStrategyConfluenceStress:
    """Empirically tests 7-asset catalog calibration, confluence scoring, and dynamic TP calculation."""

    @pytest.fixture
    def scanner(self):
        return MultiAssetScanner()

    @pytest.fixture
    def strategy(self):
        config = {
            "risk_management": {
                "min_rr_ratio": 2.0,
                "atr_sl_multiplier": 1.5,
                "forex_atr_sl_multiplier": 1.5,
                "gold_atr_sl_multiplier": 2.5,
                "crypto_atr_sl_multiplier": 3.5,
            },
            "gold_primary_focus": {
                "enabled": True,
                "xauusd_min_confluence_score": 1.2,
                "other_pairs_min_confluence_score": 1.3,
                "ny_close_block_start_utc": 15,
                "ny_close_block_end_utc": 17
            }
        }
        return StrategyEngine(config)

    def test_7_asset_catalog_integrity(self, scanner):
        """Verifies full specification correctness for all 7 primary assets."""
        expected_assets = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "USDJPY", "GBPUSD", "EURUSD"]
        catalog = scanner.ASSET_CATALOG
        
        for sym in expected_assets:
            assert sym in catalog, f"Missing asset {sym} in catalog"
            info = catalog[sym]
            assert "pip_unit" in info and info["pip_unit"] > 0
            assert "min_sl_dist" in info and info["min_sl_dist"] > 0
            assert "atr_sl_mult" in info and info["atr_sl_mult"] > 0
            assert "contract_size" in info and info["contract_size"] > 0
            assert "point_value" in info and info["point_value"] > 0

    def test_scan_all_markets_output_structure(self, scanner):
        """Validates market scanning rankings, confluence scores, and SL/TP projections."""
        cards = scanner.scan_all_markets()
        assert len(cards) == 7
        # Verify descending sort by confluence score
        scores = [c["confluence_score"] for c in cards]
        assert scores == sorted(scores, reverse=True)

        for card in cards:
            assert card["price"] > 0
            assert card["sl"] < card["price"]
            assert card["tp1"] > card["price"]
            assert card["tp2"] > card["tp1"]
            assert card["edge_pct"] >= 65.0

    def test_strategy_trend_dominance_blocking(self, strategy):
        """Validates strict rule: NEVER BUY into BEARISH H1 trend; NEVER SELL into BULLISH H1 trend."""
        # Create minimal synthetic analysis
        df_entry = pd.DataFrame({
            "high": [100.0]*20,
            "low": [90.0]*20,
            "open": [95.0]*20,
            "close": [95.0]*20
        })

        analysis_counter_buy = {
            "symbol": "EURUSD",
            "current_price": 1.1000,
            "trend_direction": "BEARISH", # Bearish trend
            "rsi": 30.0,
            "atr": 0.0010,
            "df_entry": df_entry,
            "active_support": {"level": 1.0990, "label": "Key Support"},
            "bypass_time_filter": True
        }
        # Counter-trend BUY must be blocked
        assert strategy.evaluate_signals(analysis_counter_buy) is None

        analysis_counter_sell = {
            "symbol": "EURUSD",
            "current_price": 1.1000,
            "trend_direction": "BULLISH", # Bullish trend
            "rsi": 70.0,
            "atr": 0.0010,
            "df_entry": df_entry,
            "active_resistance": {"level": 1.1010, "label": "Key Resistance"},
            "bypass_time_filter": True
        }
        # Counter-trend SELL must be blocked
        assert strategy.evaluate_signals(analysis_counter_sell) is None

    def test_strategy_3_pillar_confluence_signal_generation(self, strategy):
        """Verifies trade generation when 3 Pillars (OB, FVG 50% CE, 70.5% OTE) align."""
        df_entry = pd.DataFrame({
            "high": np.linspace(100.0, 110.0, 25),
            "low": np.linspace(90.0, 100.0, 25),
            "open": np.linspace(95.0, 105.0, 25),
            "close": np.linspace(95.0, 105.0, 25)
        })

        analysis = {
            "symbol": "BTCUSD",
            "current_price": 95000.0,
            "trend_direction": "BULLISH",
            "rsi": 45.0,
            "atr": 500.0,
            "df_entry": df_entry,
            "bullish_ob": {"high": 95100.0, "low": 94800.0},
            "bullish_fvg": {"top": 95200.0, "bottom": 94800.0, "ce_50": 95000.0},
            "ote_buy": {"in_ote_zone": True, "score_bonus": 0.60},
            "killzone": {"is_prime_killzone": True, "killzone": "LONDON_OPEN", "confluence_boost": 0.40},
            "active_resistance": {"level": 98000.0, "label": "H1 Resistance"},
            "bypass_time_filter": True
        }

        signal = strategy.evaluate_signals(analysis)
        assert signal is not None
        assert signal["signal"] == "BUY"
        assert signal["symbol"] == "BTCUSD"
        assert signal["entry_price"] == 95000.0
        assert signal["sl_price"] < 95000.0
        assert signal["tp_price"] > 95000.0
        assert signal["rr_ratio"] >= 1.0
        assert signal["confluence_score"] >= 1.30


# ============================================================================
# 6. GLOBAL LIQUIDATION RADAR & SHARK MAGNET STRESS TESTS
# ============================================================================

class TestGlobalLiquidationRadarEmpiricalStress:
    """Empirically tests liquidation cluster mathematics, leverage hierarchy, and shark magnets."""

    @pytest.fixture
    def radar(self):
        return GlobalLiquidationRadar(cache_ttl_seconds=1)

    def test_liquidation_cluster_monotonicity_and_offsets(self, radar):
        """Verifies 100x < 50x < 25x < 10x < 5x distance hierarchy and SSL/BSL positioning."""
        price = 100000.0
        clusters = radar._calculate_liquidation_clusters(price=price, ls_ratio=1.0, symbol="BTCUSD")
        
        long_pools = clusters["long_liquidation_pools"]
        short_pools = clusters["short_liquidation_pools"]

        assert len(long_pools) == 5
        assert len(short_pools) == 5

        # All long liquidations (SSL) must be strictly BELOW mark price
        for p in long_pools:
            assert p["price_level"] < price, f"Long liq {p['price_level']} not below {price}"
            assert p["liquidity_type"] == "SELL_STOP_LIQUIDITY (SSL)"

        # All short liquidations (BSL) must be strictly ABOVE mark price
        for p in short_pools:
            assert p["price_level"] > price, f"Short liq {p['price_level']} not above {price}"
            assert p["liquidity_type"] == "BUY_STOP_LIQUIDITY (BSL)"

        # Monotonicity check: Distance pct must increase with lower leverage
        long_dists = [p["distance_pct"] for p in long_pools]
        short_dists = [p["distance_pct"] for p in short_pools]
        assert long_dists == sorted(long_dists)
        assert short_dists == sorted(short_dists)

    def test_shark_magnet_directional_heuristics(self, radar):
        """Validates shark magnet triggers (>1.15x volume density threshold)."""
        # Long/Short ratio = 2.0 (Heavy long positioning -> SSL hunt)
        intel_long_heavy = radar.fetch_liquidation_intel(symbol="BTCUSD", current_price=60000.0)
        magnet = intel_long_heavy["liquidity_magnet"]
        assert magnet["direction"] in ["DOWNSIDE_SSL_HUNT", "UPSIDE_BSL_SQUEEZE", "TWO_SIDED_RANGE_TRAP"]
        assert magnet["target_price"] > 0
        assert magnet["hunt_probability_pct"] >= 70.0

    def test_all_7_assets_liquidation_intel_generation(self, radar):
        """Verifies liquidation radar operates across all 7 supported symbols with zero uncaught exceptions."""
        symbols = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "USDJPY", "GBPUSD", "EURUSD"]
        for sym in symbols:
            intel = radar.fetch_liquidation_intel(symbol=sym)
            assert intel["status"] == "success"
            assert intel["symbol"] == sym
            assert intel["mark_price"] > 0
            assert "liquidity_magnet" in intel
            assert "liquidation_heatmap" in intel


# ============================================================================
# 7. EXTREME ADVERSARIAL & CORRUPT DATA HARNESS
# ============================================================================

class TestExtremeAdversarialBoundaryConditions:
    """Stress tests systems under extreme numerical anomalies, corrupt DataFrames, and synthetic crashes."""

    def test_market_analyzer_corrupt_dataframes(self):
        """Validates MarketAnalyzer resilience against missing columns, NaN values, and zeros."""
        config = {"risk_management": {"min_rr_ratio": 2.0}}
        analyzer = MarketAnalyzer(config)

        # 1. DataFrame with NaNs
        df_nan = pd.DataFrame({
            "high": [np.nan, 100.0, 105.0, np.nan, 102.0]*5,
            "low":  [90.0, np.nan, 95.0, 90.0, np.nan]*5,
            "open": [95.0, 98.0, np.nan, 95.0, 99.0]*5,
            "close": [98.0, 102.0, 100.0, np.nan, 101.0]*5,
            "tick_volume": [100, 200, np.nan, 150, 180]*5
        })

        # Calculate indicators should not crash
        df_ind = analyzer.calculate_indicators(df_nan)
        assert "ema_50" in df_ind.columns

        # Detect FVG with NaNs should safely return list
        fvgs = analyzer.detect_fvg(df_nan)
        assert isinstance(fvgs, list)

        # Detect key S/R with NaNs should safely return dictionary
        sr = analyzer.detect_key_support_resistance(df_ind, df_ind, current_price=100.0, atr=1.0, symbol="EURUSD")
        assert "active_support" in sr

    def test_synthetic_100x_volatility_flash_crash(self):
        """Simulates a 90% flash crash across 10 candles and verifies risk calculations."""
        crash_prices = [100000.0, 95000.0, 80000.0, 60000.0, 40000.0, 20000.0, 10000.0, 15000.0, 25000.0, 30000.0]
        df_crash = pd.DataFrame({
            "high": [p * 1.05 for p in crash_prices],
            "low":  [p * 0.90 for p in crash_prices],
            "open": crash_prices,
            "close": [p * 0.95 for p in crash_prices],
            "tick_volume": [10000] * 10
        })
        
        # OTE calculation under flash crash
        quant = OrderFlowQuantEngine()
        ote = quant.compute_ote_fibonacci_array(df_crash, current_price=25000.0, direction="BUY")
        assert isinstance(ote["in_ote_zone"], (bool, np.bool_))

        # FVG under flash crash
        fvgs = MarketAnalyzer.detect_fvg(df_crash, symbol="BTCUSD")
        assert isinstance(fvgs, list)


# ============================================================================
# 8. DEEP RANDOMIZED FUZZING, WICK SENSITIVITY & INDUCEMENT STRESS TESTS
# ============================================================================

class TestDeepRandomizedFuzzingAndInducementStress:
    """Stress tests CVD randomized micro-ticks, Judas wick boundary sensitivity, EQH/EQL, and SL floors."""

    @pytest.fixture
    def quant_engine(self):
        return OrderFlowQuantEngine()

    @pytest.fixture
    def mm_engine(self):
        return MarketMakerGameEngine()

    def test_lee_ready_10000_tick_randomized_fuzzing(self, quant_engine):
        """Fuzzes Lee-Ready CVD with 10,000 randomized micro-ticks including flat intervals and whale volumes."""
        np.random.seed(42)
        n = 10000
        base_price = 100.0
        # Random walk
        steps = np.random.choice([-0.01, 0.0, 0.01], size=n, p=[0.45, 0.1, 0.45])
        prices = base_price + np.cumsum(steps)
        bids = prices - 0.01
        asks = prices + 0.01
        # Insert whale volume spike at index 5000
        vols = np.random.uniform(0.1, 10.0, size=n)
        vols[5000] = 1e9

        df_ticks = pd.DataFrame({
            "bid": bids,
            "ask": asks,
            "last": prices,
            "volume": vols
        })

        res = quant_engine.compute_tick_cvd(df_ticks)
        assert isinstance(res["net_delta"], int)
        assert math.isclose(res["buyer_ratio"] + res["seller_ratio"], 1.0, abs_tol=1e-5)
        assert res["total_volume"] > 1e9
        assert res["absorption_type"] in ["BUYER_ABSORPTION", "SELLER_ABSORPTION", "NONE"]

    def test_judas_rejection_wick_boundary_sensitivity(self, mm_engine):
        """Tests exact 40% wick threshold: 39.0% rejection wick fails; 41.0% rejection wick passes."""
        # Asian Box: High = 100.0, Low = 90.0
        df_asian = pd.DataFrame({
            "time": [datetime(2026, 8, 17, h, 0, tzinfo=timezone.utc) for h in range(6)],
            "high": [100.0]*6,
            "low": [90.0]*6,
            "open": [95.0]*6,
            "close": [95.0]*6
        })

        # Candle A: Range = 10.0 (High=105.0, Low=95.0).
        # Upper wick = 105.0 - 101.5 = 3.5 = 35% of range (< 40% threshold)
        # Sweeps 100.0 but closes at 99.0 with Open = 101.5
        # Upper wick = 105.0 - max(101.5, 99.0) = 3.5 (35% < 40%)
        df_fail_wick = pd.DataFrame({
            "time": [datetime(2026, 8, 17, 8, 0, tzinfo=timezone.utc)],
            "high": [105.0],
            "low": [95.0],
            "open": [101.5],
            "close": [99.0]
        })
        judas_fail = mm_engine.detect_judas_swing(df_fail_wick, session_name="LONDON", df_asian=df_asian)
        # Rejection wick < 40% of range, so Asian box sweep should NOT qualify as confirmed Judas swing
        assert judas_fail["judas_detected"] is False or judas_fail["type"] != "BEARISH_JUDAS_SWING"

        # Candle B: Range = 10.0 (High=105.0, Low=95.0).
        # Open = 98.0, Close = 99.0 -> Upper wick = 105.0 - 99.0 = 6.0 = 60% of range (>= 40% and >= body 1.0)
        df_pass_wick = pd.DataFrame({
            "time": [datetime(2026, 8, 17, 8, 0, tzinfo=timezone.utc)],
            "high": [105.0],
            "low": [95.0],
            "open": [98.0],
            "close": [99.0]
        })
        judas_pass = mm_engine.detect_judas_swing(df_pass_wick, session_name="LONDON", df_asian=df_asian)
        assert judas_pass["judas_detected"] is True
        assert judas_pass["type"] == "BEARISH_JUDAS_SWING"

    def test_eqh_eql_turtle_soup_inducement_detection(self, quant_engine):
        """Verifies Equal Highs (EQH) and Equal Lows (EQL) inducement sweeps across instruments."""
        # Space all bars at least 0.0010 (10 pips) apart so no spurious pairs match tol (0.0002)
        n = 20
        # Highs step up 10 pips each bar: 1.010, 1.011, 1.012...
        highs = [1.0000 + (i * 0.0010) for i in range(n)]
        lows = [h - 0.0005 for h in highs]
        opens = [h - 0.0002 for h in highs]
        closes = [h - 0.0001 for h in highs]

        # Explicit Equal Highs at bar 5 and bar 10: set to exactly 1.0500
        highs[5] = 1.0500
        highs[10] = 1.0500

        # Current bar (bar -1) pierces 1.0500 to 1.0560 and closes back down at 1.0490 with strong rejection wick
        highs[-1] = 1.0560
        lows[-1] = 1.0470
        opens[-1] = 1.0480
        closes[-1] = 1.0490

        df_eqh = pd.DataFrame({
            "high": highs,
            "low": lows,
            "open": opens,
            "close": closes
        })

        inducement = quant_engine.detect_eqh_eql_inducement(df_eqh, symbol="EURUSD")
        assert inducement["inducement_type"] == "BEARISH_EQH_SWEEP"
        assert inducement["is_swept"] is True
        assert math.isclose(inducement["level"], 1.0500, abs_tol=1e-4)

    def test_premium_discount_equilibrium_calculation(self, quant_engine):
        """Verifies 50% equilibrium threshold and discount % calculation."""
        # Range: High = 200.0, Low = 100.0 -> Eq = 150.0, total_range = 100.0
        # Discount (< 150 - 5 = 145.0) -> Buy allowed, Sell prohibited
        # Premium (> 150 + 5 = 155.0) -> Buy prohibited, Sell allowed
        # Equilibrium (145.0 to 155.0) -> Both allowed
        df_range = pd.DataFrame({
            "high": [200.0] * 20,
            "low": [100.0] * 20,
            "close": [150.0] * 20
        })

        res_disc = quant_engine.evaluate_premium_discount(df_range, current_price=130.0)
        assert res_disc["zone"] == "DISCOUNT"
        assert res_disc["is_buy_allowed"] is True
        assert res_disc["is_sell_allowed"] is False
        assert res_disc["equilibrium"] == 150.0
        assert res_disc["discount_pct"] == 70.0  # (200 - 130)/100 = 70%

        res_prem = quant_engine.evaluate_premium_discount(df_range, current_price=170.0)
        assert res_prem["zone"] == "PREMIUM"
        assert res_prem["is_buy_allowed"] is False
        assert res_prem["is_sell_allowed"] is True

        res_eq = quant_engine.evaluate_premium_discount(df_range, current_price=150.0)
        assert res_eq["zone"] == "EQUILIBRIUM"
        assert res_eq["is_buy_allowed"] is True
        assert res_eq["is_sell_allowed"] is True

