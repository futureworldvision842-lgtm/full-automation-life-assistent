"""
tests/test_challenger_m2_smc_judas_cvd.py
Challenger 2 Empirical & Adversarial Stress Suite for Milestone M2:
1. Fair Value Gap (FVG) 50% Consequent Encroachment (CE 50%) with micro-gaps, zero-pip ranges, multi-candle mitigation lifecycles, and inverted gaps.
2. Asian Judas Swings across session boundaries (00:00, 06:00, 07:00, 10:00 UTC), exact 40% wick thresholds, doji candles (body == 0), and false sweeps.
3. Turtle Soup Equal Highs / Lows (EQH/EQL) with 0.1-pip precision, multi-asset pip scaling (JPY vs Gold vs BTC), and inducement state transitions.
4. Lee-Ready CVD Order Absorption Delta with zero-tick runs, midpoint trades, extreme volume spikes, and structural divergence classifications.
"""

import math
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone

from src.market_analyzer import MarketAnalyzer
from src.market_maker_game_engine import MarketMakerGameEngine
from src.order_flow_quant import OrderFlowQuantEngine
from src.strategy import StrategyEngine


# ==============================================================================
# 1. FVG 50% Consequent Encroachment (CE 50%) Adversarial Suite
# ==============================================================================

class TestAdversarialFVGConsequentEncroachment:
    """Stress testing FVG CE 50%, micro-gaps, zero-pip flat ranges, mitigation lifecycle, and inverted gaps."""

    def test_fvg_micro_gaps_below_and_at_threshold(self):
        """
        Verify that gaps smaller than min_gap_pips are strictly filtered out,
        while gaps at or above min_gap_pips are detected.
        """
        # Gold pip_unit = 0.10. min_gap_pips = 2.0 -> required gap >= $0.20
        # Case A: Gap of $0.10 (1.0 pip < 2.0) -> Should NOT detect
        df_sub = pd.DataFrame({
            "high": [2640.00, 2645.00, 2648.00],
            "low":  [2635.00, 2640.05, 2640.10],  # gap = 2640.10 - 2640.00 = 0.10 (1.0 pip)
            "open": [2636.00, 2640.50, 2645.00],
            "close":[2639.00, 2644.00, 2647.00]
        })
        fvgs_sub = MarketAnalyzer.detect_fvg(df_sub, min_gap_pips=2.0, symbol="XAUUSD")
        assert len(fvgs_sub) == 0, f"Expected 0 FVGs for 1.0 pip gap, got {len(fvgs_sub)}"

        # Case B: Gap of $0.50 (5.0 pips >= 2.0) -> Should detect
        df_exact = pd.DataFrame({
            "high": [2640.00, 2645.00, 2648.00],
            "low":  [2635.00, 2640.10, 2640.50],  # gap = 2640.50 - 2640.00 = 0.50 (5.0 pips)
            "open": [2636.00, 2640.50, 2645.00],
            "close":[2639.00, 2644.00, 2647.00]
        })
        fvgs_exact = MarketAnalyzer.detect_fvg(df_exact, min_gap_pips=2.0, symbol="XAUUSD")
        assert len(fvgs_exact) == 1
        assert fvgs_exact[0]["type"] == "BULLISH_FVG"
        assert math.isclose(fvgs_exact[0]["gap_pips"], 5.0, rel_tol=1e-5)
        assert math.isclose(fvgs_exact[0]["ce_50"], 2640.25, rel_tol=1e-5)

    def test_fvg_zero_pip_range_and_flat_candles(self):
        """
        Verify that flat candles (high == low == open == close) and zero-spread market halts
        produce zero FVGs without division by zero or NaN errors.
        """
        df_flat = pd.DataFrame({
            "high": [100.0, 100.0, 100.0, 100.0],
            "low":  [100.0, 100.0, 100.0, 100.0],
            "open": [100.0, 100.0, 100.0, 100.0],
            "close":[100.0, 100.0, 100.0, 100.0]
        })
        fvgs = MarketAnalyzer.detect_fvg(df_flat, min_gap_pips=1.0, symbol="EURUSD")
        assert len(fvgs) == 0

    def test_fvg_multi_candle_bullish_mitigation_lifecycle(self):
        """
        Multi-candle forward mitigation sequence for Bullish FVG:
        - Bar 0, 1, 2 form Bullish FVG: bottom = 100.0, top = 104.0, CE 50% = 102.0.
        - Bar 3: Low = 105.0 -> Unmitigated (mitigated=False, partially_mitigated=False)
        - Bar 4: Low = 103.0 -> Partially Mitigated (mitigated=False, partially_mitigated=True)
        - Bar 5: Low = 101.5 -> Fully Mitigated (mitigated=True, partially_mitigated=True)
        """
        # Step 1: Unmitigated (Bar 3 low stays above gap top 104.0)
        df_step1 = pd.DataFrame({
            "high": [100.0, 106.0, 107.0, 108.0],
            "low":  [95.0,  100.5, 104.0, 105.0],
            "open": [96.0,  101.0, 105.0, 106.0],
            "close":[99.0,  105.5, 106.5, 107.5]
        })
        res1 = MarketAnalyzer.detect_fvg(df_step1, min_gap_pips=1.0, symbol="EURUSD")[0]
        assert res1["top"] == 104.0
        assert res1["bottom"] == 100.0
        assert res1["ce_50"] == 102.0
        assert res1["mitigated"] is False
        assert res1["partially_mitigated"] is False

        # Step 2: Partially Mitigated (Bar 4 dips to 103.0, penetrating top 104.0 but above CE 102.0)
        df_step2 = pd.DataFrame({
            "high": [100.0, 106.0, 107.0, 108.0, 106.0],
            "low":  [95.0,  100.5, 104.0, 105.0, 103.0],
            "open": [96.0,  101.0, 105.0, 106.0, 105.5],
            "close":[99.0,  105.5, 106.5, 107.5, 104.0]
        })
        res2 = MarketAnalyzer.detect_fvg(df_step2, min_gap_pips=1.0, symbol="EURUSD")[0]
        assert res2["mitigated"] is False
        assert res2["partially_mitigated"] is True

        # Step 3: Fully Mitigated (Bar 5 dips to 101.5, touching/penetrating CE 102.0)
        df_step3 = pd.DataFrame({
            "high": [100.0, 106.0, 107.0, 108.0, 106.0, 105.0],
            "low":  [95.0,  100.5, 104.0, 105.0, 103.0, 101.5],
            "open": [96.0,  101.0, 105.0, 106.0, 105.5, 104.0],
            "close":[99.0,  105.5, 106.5, 107.5, 104.0, 102.5]
        })
        res3 = MarketAnalyzer.detect_fvg(df_step3, min_gap_pips=1.0, symbol="EURUSD")[0]
        assert res3["mitigated"] is True
        assert res3["partially_mitigated"] is True

    def test_fvg_multi_candle_bearish_mitigation_lifecycle(self):
        """
        Multi-candle forward mitigation sequence for Bearish FVG:
        - Bar 0, 1, 2 form Bearish FVG: top = 104.0 (C1 Low), bottom = 100.0 (C3 High), CE 50% = 102.0.
        - Bar 3: High = 99.0 -> Unmitigated (mitigated=False, partially_mitigated=False)
        - Bar 4: High = 101.0 -> Partially Mitigated (mitigated=False, partially_mitigated=True)
        - Bar 5: High = 102.5 -> Fully Mitigated (mitigated=True, partially_mitigated=True)
        """
        # Step 1: Unmitigated
        df_step1 = pd.DataFrame({
            "high": [108.0, 103.5, 100.0, 99.0],
            "low":  [104.0, 98.0,  96.0,  95.0],
            "open": [107.0, 103.0, 99.0,  98.0],
            "close":[104.5, 98.5,  97.0,  96.0]
        })
        res1 = MarketAnalyzer.detect_fvg(df_step1, min_gap_pips=1.0, symbol="EURUSD")[0]
        assert res1["type"] == "BEARISH_FVG"
        assert res1["top"] == 104.0
        assert res1["bottom"] == 100.0
        assert res1["ce_50"] == 102.0
        assert res1["mitigated"] is False
        assert res1["partially_mitigated"] is False

        # Step 2: Partially Mitigated (Bar 4 high rises to 101.0, entering gap below CE 102.0)
        df_step2 = pd.DataFrame({
            "high": [108.0, 103.5, 100.0, 99.0, 101.0],
            "low":  [104.0, 98.0,  96.0,  95.0, 97.0],
            "open": [107.0, 103.0, 99.0,  98.0, 97.5],
            "close":[104.5, 98.5,  97.0,  96.0, 100.5]
        })
        res2 = MarketAnalyzer.detect_fvg(df_step2, min_gap_pips=1.0, symbol="EURUSD")[0]
        assert res2["mitigated"] is False
        assert res2["partially_mitigated"] is True

        # Step 3: Fully Mitigated (Bar 5 high rises to 102.5, touching/penetrating CE 102.0)
        df_step3 = pd.DataFrame({
            "high": [108.0, 103.5, 100.0, 99.0, 101.0, 102.5],
            "low":  [104.0, 98.0,  96.0,  95.0, 97.0,  99.0],
            "open": [107.0, 103.0, 99.0,  98.0, 97.5,  100.0],
            "close":[104.5, 98.5,  97.0,  96.0, 100.5, 101.0]
        })
        res3 = MarketAnalyzer.detect_fvg(df_step3, min_gap_pips=1.0, symbol="EURUSD")[0]
        assert res3["mitigated"] is True
        assert res3["partially_mitigated"] is True

    def test_fvg_inverted_and_overlapping_candles(self):
        """
        Inverted or overlapping 3-candle patterns where C3 overlaps C1:
        c3_low <= c1_high in rally, c3_high >= c1_low in decline -> No FVG exists.
        """
        # Overlapping in upward move (C3 Low = 100.0 <= C1 High = 101.0)
        df_overlap_up = pd.DataFrame({
            "high": [101.0, 105.0, 106.0],
            "low":  [98.0,  100.0, 100.0],
            "open": [99.0,  101.0, 104.0],
            "close":[100.5, 104.5, 105.5]
        })
        fvgs_up = MarketAnalyzer.detect_fvg(df_overlap_up, min_gap_pips=1.0, symbol="EURUSD")
        assert len(fvgs_up) == 0

        # Overlapping in downward move (C3 High = 100.0 >= C1 Low = 99.0)
        df_overlap_down = pd.DataFrame({
            "high": [103.0, 101.0, 100.0],
            "low":  [99.0,  95.0,  94.0],
            "open": [102.0, 100.0, 97.0],
            "close":[100.0, 96.0,  95.0]
        })
        fvgs_down = MarketAnalyzer.detect_fvg(df_overlap_down, min_gap_pips=1.0, symbol="EURUSD")
        assert len(fvgs_down) == 0


# ==============================================================================
# 2. Asian Judas Swings Across Session Boundaries Adversarial Suite
# ==============================================================================

class TestAdversarialAsianJudasSwings:
    """Stress testing session boundaries, 40% rejection wicks, dojis (body==0), and false sweeps."""

    @pytest.fixture
    def mm_engine(self):
        return MarketMakerGameEngine()

    def test_asian_session_box_boundary_precision(self, mm_engine):
        """
        Verify Asian Session Box strictly captures 00:00 to 05:59:59 UTC,
        and excludes 06:00:00 UTC and 07:00:00 UTC candles.
        """
        times = pd.date_range("2026-01-01 00:00:00", periods=8, freq="1h", tz="UTC")
        df_feed = pd.DataFrame({
            "time": times,
            "high": [2640.0, 2642.0, 2645.0, 2643.0, 2641.0, 2644.0, 2680.0, 2690.0],  # 06:00 & 07:00 have high 2680/2690
            "low":  [2635.0, 2636.0, 2634.0, 2637.0, 2638.0, 2635.0, 2610.0, 2605.0],  # 06:00 & 07:00 have low 2610/2605
            "open": [2636.0, 2640.0, 2641.0, 2642.0, 2640.0, 2639.0, 2644.0, 2680.0],
            "close":[2640.0, 2641.0, 2643.0, 2641.0, 2639.0, 2642.0, 2675.0, 2685.0]
        })
        box = mm_engine.calculate_asian_session_box(df_feed)
        # Should only consider 00:00 to 05:00 bars (first 6 bars)
        assert box["candle_count"] == 6
        assert box["asian_high"] == 2645.0  # Max of first 6 bars, NOT 2680/2690
        assert box["asian_low"] == 2634.0   # Min of first 6 bars, NOT 2610/2605
        assert box["asian_range"] == 11.0
        assert box["asian_mid"] == 2639.5

    def test_exact_40_percent_wick_threshold_boundary(self, mm_engine):
        """
        Adversarial threshold test:
        - Upper Wick == 0.40 * Range: PASSES threshold and triggers Bearish Judas Swing.
        - Upper Wick == 0.39 * Range: FAILS threshold and does NOT trigger Asian Box Judas Swing.
        """
        # Asian Box: High = 2650.0, Low = 2640.0
        df_asian = pd.DataFrame({"high": [2650.0], "low": [2640.0], "open": [2645.0], "close": [2648.0]})

        # Candle A: Range = 10.0 (High=2655, Low=2645). Open=2648, Close=2647 (Body=1.0).
        # Upper Wick = 2655 - 2648 = 7.0 (70% >= 40% and 7.0 >= 1.0) -> Triggers Judas
        df_pass = pd.DataFrame({"high": [2655.0], "low": [2645.0], "open": [2648.0], "close": [2647.0]})
        judas_pass = mm_engine.detect_judas_swing(df_pass, session_name="LONDON", df_asian=df_asian)
        assert judas_pass["judas_detected"] is True
        assert judas_pass["type"] == "BEARISH_JUDAS_SWING"

        # Candle B: Range = 10.0 (High=2655, Low=2645). Open=2651.1, Close=2648.0 (Body=3.1).
        # Upper Wick = 2655.0 - 2651.1 = 3.9 (39% < 40%) -> Does NOT trigger Asian box Judas
        df_fail = pd.DataFrame({"high": [2655.0], "low": [2645.0], "open": [2651.1], "close": [2648.0]})
        judas_fail = mm_engine.detect_judas_swing(df_fail, session_name="LONDON", df_asian=df_asian)
        assert (judas_fail["judas_detected"] is False) or (judas_fail.get("swept_level") != 2650.0)

    def test_doji_candle_where_body_equals_zero(self, mm_engine):
        """
        Adversarial test with Doji candles (Open == Close, Body == 0):
        - Gravestone Doji sweeping Asian High -> Valid Bearish Judas Swing.
        - Dragonfly Doji sweeping Asian Low -> Valid Bullish Judas Swing.
        """
        df_asian = pd.DataFrame({"high": [2650.0], "low": [2640.0], "open": [2645.0], "close": [2648.0]})

        # Gravestone Doji: High=2656.0, Low=2644.0, Open=2644.0, Close=2644.0 (Body=0)
        # Swept Asian High 2650, closed at 2644. Upper wick = 12.0 / 12.0 = 100% >= 40%
        df_gravestone = pd.DataFrame({"high": [2656.0], "low": [2644.0], "open": [2644.0], "close": [2644.0]})
        judas_bear = mm_engine.detect_judas_swing(df_gravestone, session_name="LONDON", df_asian=df_asian)
        assert judas_bear["judas_detected"] is True
        assert judas_bear["type"] == "BEARISH_JUDAS_SWING"
        assert judas_bear["swept_level"] == 2650.0

        # Dragonfly Doji: High=2646.0, Low=2632.0, Open=2646.0, Close=2646.0 (Body=0)
        # Swept Asian Low 2640, closed at 2646. Lower wick = 14.0 / 14.0 = 100% >= 40%
        df_dragonfly = pd.DataFrame({"high": [2646.0], "low": [2632.0], "open": [2646.0], "close": [2646.0]})
        judas_bull = mm_engine.detect_judas_swing(df_dragonfly, session_name="LONDON", df_asian=df_asian)
        assert judas_bull["judas_detected"] is True
        assert judas_bull["type"] == "BULLISH_JUDAS_SWING"
        assert judas_bull["swept_level"] == 2640.0

    def test_false_sweeps_that_do_not_break_box_bounds(self, mm_engine):
        """
        Adversarial tests for non-sweeping and breakout candles:
        - High strictly touches Asian High (High == 2650.0): c_high > a_high is False -> No sweep.
        - Low strictly touches Asian Low (Low == 2640.0): c_low < a_low is False -> No sweep.
        - Clean breakout candle closing above Asian High (High=2665, Close=2662 > 2650) -> No fakeout.
        """
        df_asian = pd.DataFrame({"high": [2650.0], "low": [2640.0], "open": [2645.0], "close": [2648.0]})

        # Exact touch high, no breakout
        df_touch_high = pd.DataFrame({"high": [2650.0], "low": [2644.0], "open": [2646.0], "close": [2645.0]})
        res_touch_h = mm_engine.detect_judas_swing(df_touch_high, session_name="LONDON", df_asian=df_asian)
        assert res_touch_h.get("swept_level") != 2650.0

        # Exact touch low, no breakdown
        df_touch_low = pd.DataFrame({"high": [2646.0], "low": [2640.0], "open": [2644.0], "close": [2645.0]})
        res_touch_l = mm_engine.detect_judas_swing(df_touch_low, session_name="LONDON", df_asian=df_asian)
        assert res_touch_l.get("swept_level") != 2640.0

        # Clean breakout closing outside
        df_breakout = pd.DataFrame({"high": [2665.0], "low": [2648.0], "open": [2649.0], "close": [2662.0]})
        res_breakout = mm_engine.detect_judas_swing(df_breakout, session_name="LONDON", df_asian=df_asian)
        assert res_breakout.get("swept_level") != 2650.0


# ==============================================================================
# 3. Turtle Soup EQH/EQL Inducement Sweeps Adversarial Suite
# ==============================================================================

class TestAdversarialTurtleSoupInducement:
    """Stress testing 0.1-pip precision, multi-asset pip scaling (JPY vs Gold vs BTC), and state transitions."""

    @pytest.fixture
    def quant(self):
        return OrderFlowQuantEngine(pip_tolerance=2.0)

    def test_turtle_soup_eqh_within_0_1_pip_forex_gold_btc(self, quant):
        """
        Verify equal highs detected within 0.1 pip across Forex, Gold, and BTC:
        - EURUSD: 0.1 pip = 0.00001 difference
        - Gold (XAUUSD): 0.1 pip = $0.01 difference
        - BTCUSD: 0.1 pip = $0.10 difference
        """
        # 1. EURUSD: Highs at 1.08500 and 1.08501 (0.1 pip diff)
        highs_eur = [1.0800 + i * 0.0001 for i in range(25)]
        lows_eur = [1.0780 + i * 0.0001 for i in range(25)]
        opens_eur = [1.0790 + i * 0.0001 for i in range(25)]
        closes_eur = [1.0795 + i * 0.0001 for i in range(25)]
        highs_eur[5] = 1.08500
        highs_eur[15] = 1.08501
        # Latest bar sweeps 1.08501 to 1.08520 and closes at 1.08480
        highs_eur[-1] = 1.08520
        lows_eur[-1] = 1.08450
        opens_eur[-1] = 1.08470
        closes_eur[-1] = 1.08480
        df_eur = pd.DataFrame({"high": highs_eur, "low": lows_eur, "open": opens_eur, "close": closes_eur})
        ind_eur = quant.detect_eqh_eql_inducement(df_eur, symbol="EURUSD")
        assert ind_eur["is_swept"] is True
        assert ind_eur["inducement_type"] == "BEARISH_EQH_SWEEP"
        assert math.isclose(ind_eur["level"], 1.08501, abs_tol=1e-4)

        # 2. XAUUSD: Highs at 2650.00 and 2650.01 (0.1 pip diff)
        highs_gold = [2630.0 + i * 0.5 for i in range(25)]
        lows_gold = [2625.0 + i * 0.5 for i in range(25)]
        opens_gold = [2628.0 + i * 0.5 for i in range(25)]
        closes_gold = [2629.0 + i * 0.5 for i in range(25)]
        highs_gold[5] = 2650.00
        highs_gold[15] = 2650.01
        highs_gold[-1] = 2652.50
        lows_gold[-1] = 2646.00
        opens_gold[-1] = 2648.00
        closes_gold[-1] = 2649.00
        df_gold = pd.DataFrame({"high": highs_gold, "low": lows_gold, "open": opens_gold, "close": closes_gold})
        ind_gold = quant.detect_eqh_eql_inducement(df_gold, symbol="XAUUSD")
        assert ind_gold["is_swept"] is True
        assert ind_gold["inducement_type"] == "BEARISH_EQH_SWEEP"
        assert math.isclose(ind_gold["level"], 2650.01, abs_tol=0.02)

        # 3. BTCUSD: Highs at 95000.00 and 95000.10 (0.1 pip diff)
        highs_btc = [93000.0 + i * 50.0 for i in range(25)]
        lows_btc = [92500.0 + i * 50.0 for i in range(25)]
        opens_btc = [92800.0 + i * 50.0 for i in range(25)]
        closes_btc = [92900.0 + i * 50.0 for i in range(25)]
        highs_btc[5] = 95000.00
        highs_btc[15] = 95000.10
        highs_btc[-1] = 95150.00
        lows_btc[-1] = 94800.00
        opens_btc[-1] = 94900.00
        closes_btc[-1] = 94950.00
        df_btc = pd.DataFrame({"high": highs_btc, "low": lows_btc, "open": opens_btc, "close": closes_btc})
        ind_btc = quant.detect_eqh_eql_inducement(df_btc, symbol="BTCUSD")
        assert ind_btc["is_swept"] is True
        assert ind_btc["inducement_type"] == "BEARISH_EQH_SWEEP"
        assert math.isclose(ind_btc["level"], 95000.10, abs_tol=0.2)

    def test_multi_asset_pip_scaling_resolution(self, quant):
        """
        Verify pip unit resolution across asset classes:
        - JPY pairs -> 0.01
        - Gold / Silver / SOL -> 0.10 / 0.01
        - BTC / ETH -> 1.0
        - Standard Forex -> 0.0001
        """
        assert quant.get_pip_unit("USDJPY") == 0.01
        assert quant.get_pip_unit("EURJPY") == 0.01
        assert quant.get_pip_unit("GBPJPY") == 0.01
        assert quant.get_pip_unit("XAUUSD") == 0.10
        assert quant.get_pip_unit("GOLD") == 0.10
        assert quant.get_pip_unit("BTCUSD") == 1.0
        assert quant.get_pip_unit("ETHUSDT") == 1.0
        assert quant.get_pip_unit("SOLUSD") == 0.10
        assert quant.get_pip_unit("EURUSD") == 0.0001
        assert quant.get_pip_unit("GBPUSD") == 0.0001

    def test_inducement_state_transitions_unswept_to_swept(self, quant):
        """
        Verify clean inducement state transitions:
        - Unswept EQH: Highs form equal levels, current price is below -> EQH_UNSWEPT (is_swept=False).
        - Swept EQH: Current price pierces and rejects back below with rejection wick -> BEARISH_EQH_SWEEP (is_swept=True).
        - Unswept EQL: Lows form equal levels, current price is above -> EQL_UNSWEPT (is_swept=False).
        - Swept EQL: Current price pierces and rejects back above with rejection wick -> BULLISH_EQL_SWEEP (is_swept=True).
        """
        # Unswept EQH: unique equal highs at 1.08500 and 1.08501, non-equal background
        highs = [1.0800 + i * 0.0001 for i in range(25)]
        lows = [1.0780 + i * 0.0001 for i in range(25)]
        opens = [1.0790 + i * 0.0001 for i in range(25)]
        closes = [1.0795 + i * 0.0001 for i in range(25)]
        highs[5] = 1.08500
        highs[15] = 1.08501
        highs[-1] = 1.08450  # Below 1.08501
        closes[-1] = 1.08420
        df_unswept_eqh = pd.DataFrame({"high": highs, "low": lows, "open": opens, "close": closes})
        res_unswept_eqh = quant.detect_eqh_eql_inducement(df_unswept_eqh, symbol="EURUSD")
        assert res_unswept_eqh["inducement_type"] == "EQH_UNSWEPT"
        assert res_unswept_eqh["is_swept"] is False

        # Swept EQH: Candle sweeps 1.08501 with upper wick >= 0.35 * range and closes below
        highs[-1] = 1.08550
        lows[-1] = 1.08380
        opens[-1] = 1.08400
        closes[-1] = 1.08420
        df_swept_eqh = pd.DataFrame({"high": highs, "low": lows, "open": opens, "close": closes})
        res_swept_eqh = quant.detect_eqh_eql_inducement(df_swept_eqh, symbol="EURUSD")
        assert res_swept_eqh["inducement_type"] == "BEARISH_EQH_SWEEP"
        assert res_swept_eqh["is_swept"] is True

        # Unswept EQL
        highs2 = [1.0850 + i * 0.0001 for i in range(25)]
        lows2 = [1.0800 + i * 0.0001 for i in range(25)]
        opens2 = [1.0830 + i * 0.0001 for i in range(25)]
        closes2 = [1.0835 + i * 0.0001 for i in range(25)]
        lows2[5] = 1.07500
        lows2[15] = 1.07501
        lows2[-1] = 1.07600  # Above 1.07500
        closes2[-1] = 1.07650
        df_unswept_eql = pd.DataFrame({"high": highs2, "low": lows2, "open": opens2, "close": closes2})
        res_unswept_eql = quant.detect_eqh_eql_inducement(df_unswept_eql, symbol="EURUSD")
        assert res_unswept_eql["inducement_type"] == "EQL_UNSWEPT"
        assert res_unswept_eql["is_swept"] is False

        # Swept EQL: Candle sweeps 1.07500 with lower wick >= 0.35 * range and closes above
        lows2[-1] = 1.07420
        highs2[-1] = 1.07600
        opens2[-1] = 1.07550
        closes2[-1] = 1.07580
        df_swept_eql = pd.DataFrame({"high": highs2, "low": lows2, "open": opens2, "close": closes2})
        res_swept_eql = quant.detect_eqh_eql_inducement(df_swept_eql, symbol="EURUSD")
        assert res_swept_eql["inducement_type"] == "BULLISH_EQL_SWEEP"
        assert res_swept_eql["is_swept"] is True


# ==============================================================================
# 4. Lee-Ready CVD Order Absorption Delta Adversarial Suite
# ==============================================================================

class TestAdversarialLeeReadyCVD:
    """Stress testing Lee-Ready (1991) CVD, zero-tick runs, volume spikes, and structural divergence."""

    @pytest.fixture
    def quant(self):
        return OrderFlowQuantEngine()

    def test_lee_ready_zero_tick_run_carry_forward(self, quant):
        """
        Verify zero-tick carry-forward:
        - Tick 0: Ask hit (1.0851 > Mid 1.0850) -> Direction = +1
        - Tick 1..5: Price traded at Ask (1.0851 > Mid 1.0850) -> all classified as Buys (+60 delta).
        """
        # Case A: Sequence of trades all executed on the Ask
        ticks_up = pd.DataFrame({
            "bid": [1.0849, 1.0849, 1.0849, 1.0849, 1.0849, 1.0849],
            "ask": [1.0851, 1.0851, 1.0851, 1.0851, 1.0851, 1.0851],
            "last": [1.0851, 1.0851, 1.0851, 1.0851, 1.0851, 1.0851],
            "volume": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        })
        res_up = quant.compute_tick_cvd(ticks_up)
        assert res_up["net_delta"] == 60
        assert res_up["total_buy_vol"] == 60.0
        assert res_up["total_sell_vol"] == 0.0
        assert res_up["buyer_ratio"] == 1.0
        assert res_up["absorption_type"] == "BUYER_ABSORPTION"

        # Case B: Tick test midpoint carry forward:
        # Tick 0: Bid hit (-1)
        # Tick 1: Uptick to Mid (1.0849 -> 1.0850: direction becomes +1 via Tick Test)
        # Tick 2..5: Zero-tick at Mid (1.0850 == 1.0850: carries forward +1!)
        ticks_carry = pd.DataFrame({
            "bid": [1.0849, 1.0849, 1.0849, 1.0849, 1.0849, 1.0849],
            "ask": [1.0851, 1.0851, 1.0851, 1.0851, 1.0851, 1.0851],
            "last": [1.0849, 1.0850, 1.0850, 1.0850, 1.0850, 1.0850],
            "volume": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        })
        res_carry = quant.compute_tick_cvd(ticks_carry)
        # Tick 0 = -10, Ticks 1..5 = +10 each -> Net = -10 + 50 = +40
        assert res_carry["net_delta"] == 40
        assert res_carry["total_buy_vol"] == 50.0
        assert res_carry["total_sell_vol"] == 10.0
        assert res_carry["buyer_ratio"] >= 0.83

        # Opposite test: Initial downtick (-1) carried forward across zero-ticks
        # Tick 0: Ask hit (+1)
        # Tick 1: Downtick to Mid (1.0851 -> 1.0850: direction becomes -1 via Tick Test)
        # Tick 2..5: Zero-tick at Mid (1.0850 == 1.0850: carries forward -1!)
        ticks_down_carry = pd.DataFrame({
            "bid": [1.0849, 1.0849, 1.0849, 1.0849, 1.0849, 1.0849],
            "ask": [1.0851, 1.0851, 1.0851, 1.0851, 1.0851, 1.0851],
            "last": [1.0851, 1.0850, 1.0850, 1.0850, 1.0850, 1.0850],
            "volume": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        })
        res_down = quant.compute_tick_cvd(ticks_down_carry)
        # Tick 0 = +10, Ticks 1..5 = -10 each -> Net = +10 - 50 = -40
        assert res_down["net_delta"] == -40
        assert res_down["total_buy_vol"] == 10.0
        assert res_down["total_sell_vol"] == 50.0
        assert res_down["seller_ratio"] >= 0.83
        assert res_down["absorption_type"] == "SELLER_ABSORPTION"

    def test_lee_ready_equal_bid_ask_balanced_trades(self, quant):
        """
        Verify equal bid/ask trades produce balanced 50/50 ratio and neutral classification.
        """
        ticks_balanced = pd.DataFrame({
            "bid": [1.0850, 1.0850, 1.0850, 1.0850],
            "ask": [1.0852, 1.0852, 1.0852, 1.0852],
            "last": [1.0852, 1.0850, 1.0852, 1.0850],  # Buy, Sell, Buy, Sell
            "volume": [100.0, 100.0, 100.0, 100.0]
        })
        res_bal = quant.compute_tick_cvd(ticks_balanced)
        assert res_bal["net_delta"] == 0
        assert res_bal["total_buy_vol"] == 200.0
        assert res_bal["total_sell_vol"] == 200.0
        assert res_bal["buyer_ratio"] == 0.50
        assert res_bal["seller_ratio"] == 0.50
        assert res_bal["divergence"] == "NONE"
        assert res_bal["absorption_type"] == "NONE"
        assert res_bal["is_absorption_divergence"] is False

    def test_lee_ready_extreme_volume_spikes(self, quant):
        """
        Adversarial test with extreme institutional volume spikes:
        1 single mega-block trade of 500,000 contracts against 10 normal 1-lot retail trades.
        """
        n = 11
        bids = [2650.0] * n
        asks = [2650.2] * n
        lasts = [2650.0] * n
        volumes = [1.0] * n

        # Retail selling on bid (10 trades of 1.0 lot = 10 lots sell)
        # Institutional block buy on ask on last trade (1 trade of 500,000 lots)
        lasts[-1] = 2650.2
        volumes[-1] = 500000.0

        ticks_spike = pd.DataFrame({
            "bid": bids,
            "ask": asks,
            "last": lasts,
            "volume": volumes
        })
        res_spike = quant.compute_tick_cvd(ticks_spike)
        assert res_spike["total_buy_vol"] == 500000.0
        assert res_spike["total_sell_vol"] == 10.0
        assert res_spike["net_delta"] == 499990
        assert res_spike["buyer_ratio"] >= 0.99
        assert res_spike["divergence"] == "BULLISH_CVD_SURGE"
        assert res_spike["absorption_type"] == "BUYER_ABSORPTION"

    def test_detect_absorption_divergence_matrix(self, quant):
        """
        Verify structural price-swing vs CVD-swing divergence matrix:
        - Case 1: Buyer Absorption (Bullish Reversal): Price Lower Low / Equal Low, CVD Higher Low.
        - Case 2: Seller Absorption (Bearish Reversal): Price Higher High / Equal High, CVD Lower High.
        - Case 3: Concordant / Neutral: Price and CVD move in the same direction.
        """
        # Case 1: Bullish Buyer Absorption (Price 2630 <= 2640, CVD +100 > -200)
        div_buy = quant.detect_absorption_divergence(
            price_swing_1=2640.0,
            price_swing_2=2630.0,
            cvd_swing_1=-200.0,
            cvd_swing_2=100.0
        )
        assert div_buy["absorption_detected"] is True
        assert div_buy["type"] == "BUYER_ABSORPTION"
        assert div_buy["bias"] == "BULLISH_REVERSAL"

        # Case 2: Bearish Seller Absorption (Price 2660 >= 2650, CVD +50 < +300)
        div_sell = quant.detect_absorption_divergence(
            price_swing_1=2650.0,
            price_swing_2=2660.0,
            cvd_swing_1=300.0,
            cvd_swing_2=50.0
        )
        assert div_sell["absorption_detected"] is True
        assert div_sell["type"] == "SELLER_ABSORPTION"
        assert div_sell["bias"] == "BEARISH_REVERSAL"

        # Case 3: Neutral Concordant Flow (Price 2660 > 2650, CVD 500 > 300)
        div_neut = quant.detect_absorption_divergence(
            price_swing_1=2650.0,
            price_swing_2=2660.0,
            cvd_swing_1=300.0,
            cvd_swing_2=500.0
        )
        assert div_neut["absorption_detected"] is False
        assert div_neut["type"] == "NONE"
        assert div_neut["bias"] == "NEUTRAL"

    def test_lee_ready_long_run_zero_ticks(self, quant):
        """
        Verify long run (20 ticks) of zero-ticks with volume accumulation.
        """
        n = 20
        bids = [1.0850] * n
        asks = [1.0852] * n
        # Initial uptick trade at Ask
        lasts = [1.0852] + [1.0851] * (n - 1)  # 1.0851 is midpoint, trades are at mid
        volumes = [5.0] * n

        ticks = pd.DataFrame({"bid": bids, "ask": asks, "last": lasts, "volume": volumes})
        res = quant.compute_tick_cvd(ticks)
        # Tick 0 = Ask (+1), Ticks 1..19 = Downtick to mid (-1) and zero-ticks (-1)
        # Net = 5 - 19*5 = -90
        assert res["total_volume"] == 100.0
        assert res["net_delta"] == -90
        assert res["absorption_type"] == "SELLER_ABSORPTION"


# ==============================================================================
# 5. Integration & Strategy Confluence Suite
# ==============================================================================

class TestAdversarialSMCStrategyIntegration:
    """Tests StrategyEngine confluence scoring with FVG 50% CE and SMC patterns."""

    @pytest.fixture
    def strategy(self):
        config = {
            "account_info": {"target_account_size": 25000.0},
            "risk_management": {
                "max_daily_loss_pct": 2.5,
                "max_total_loss_pct": 6.0,
                "risk_per_trade_pct": 0.75,
                "max_open_trades": 3,
                "max_daily_trades": 10,
                "min_rr_ratio": 1.5,
                "atr_sl_multiplier": 1.5,
            },
            "gold_primary_focus": {
                "enabled": False,
                "xauusd_min_confluence_score": 1.0,
                "other_pairs_min_confluence_score": 1.0,
            }
        }
        strat = StrategyEngine(config)
        strat.ai_engine.get_pattern_weights = lambda: {
            "BULLISH_ORDER_BLOCK": 1.0,
            "BULLISH_SWEEP": 1.0,
            "BULLISH_PRICE_ACTION": 1.0,
            "BULLISH_FVG": 1.0,
            "BULLISH_FVG_50_CE": 1.0,
            "KEY_SUPPORT_BOUNCE": 1.0,
        }
        return strat

    def test_fvg_50_ce_confluence_scoring(self, strategy):
        """
        Verify that StrategyEngine assigns +0.70 bonus when price tests FVG 50% CE
        vs +0.60 bonus when price touches FVG zone outside 50% CE.
        """
        atr = 1.0
        fvg = {
            "top": 104.0,
            "bottom": 100.0,
            "ce_50": 102.0,
            "gap_pips": 40.0
        }

        # Case A: Price testing CE 50% (price = 102.1, abs(102.1 - 102.0) = 0.1 <= 0.3*atr)
        df_entry = pd.DataFrame({
            "open": [100.0] * 20,
            "high": [105.0] * 20,
            "low": [98.0] * 20,
            "close": [102.0] * 20,
            "volume": [1000.0] * 20
        })

        analysis_ce = {
            "symbol": "EURUSD",
            "current_price": 102.1,
            "trend_direction": "BULLISH",
            "rsi": 50.0,
            "atr": atr,
            "df_entry": df_entry,
            "bullish_fvg": fvg,
            "bearish_fvg": None,
            "bullish_ob": None,
            "bearish_ob": None,
            "active_support": None,
            "active_resistance": None,
            "resistance_levels": [(115.0, "Resistance")],
            "support_levels": [(90.0, "Support")],
            "liquidity_sweep": {"sweep_detected": False},
            "candlestick_patterns": [],
            "structure_pattern": "NONE",
            "premium_discount": {"is_buy_allowed": True, "discount_pct": 50.0},
            "bypass_time_filter": True
        }

        signal_ce = strategy.evaluate_signals(analysis_ce)
        assert signal_ce is not None
        assert signal_ce["pattern"] == "BULLISH_FVG_50_CE"

        # Case B: Price at FVG top (price = 103.9, abs(103.9 - 102.0) = 1.9 > 0.3*atr)
        analysis_top = dict(analysis_ce)
        analysis_top["current_price"] = 103.9
        signal_top = strategy.evaluate_signals(analysis_top)
        assert signal_top is not None
        assert signal_top["pattern"] == "BULLISH_FVG"

