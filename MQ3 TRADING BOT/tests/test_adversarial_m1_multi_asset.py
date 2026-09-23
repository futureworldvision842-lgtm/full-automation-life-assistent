"""
tests/test_adversarial_m1_multi_asset.py — Adversarial Stress Test Harness for Milestone 1 (M1).
Focus: Multi-Asset Support (XAUUSD, XAGUSD, EURUSD, GBPUSD, USDJPY), D1 Floor Pivots across price scales,
Pip Scaling & 4-Account Sizing, Asian Box & 70.5% OTE Extraction, and Scenario A/B Invalidation Boundaries.

Executed by Challenger 2 (.agents/challenger_m1_2).
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

# Ensure repo root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.daily_institutional_routine_engine import DailyInstitutionalRoutineEngine
from src.order_flow_quant import OrderFlowQuantEngine
from src.market_analyzer import MarketAnalyzer


class TestAdversarialM1MultiAsset(unittest.TestCase):
    """
    Adversarial Challenge Suite for M1 Multi-Asset Macro Briefing and Playbook Engine.
    """

    def setUp(self):
        self.engine = DailyInstitutionalRoutineEngine()
        self.of_quant = OrderFlowQuantEngine()
        self.analyzer = MarketAnalyzer(self.engine.config)

    # ══════════════════════════════════════════════════════════════════════════
    # 1. D1 PIVOT CALCULATIONS ACROSS PRICE SCALES
    # ══════════════════════════════════════════════════════════════════════════

    def test_d1_pivots_price_scales_invariants(self):
        """
        Verify D1 Floor Pivot formulas and mathematical ordering across distinct asset price scales:
        - Gold ($4000 - $4400)
        - Silver ($30 - $40)
        - EURUSD (1.05 - 1.10)
        - GBPUSD (1.25 - 1.35)
        - USDJPY (150 - 165)
        - Extreme Scales: Ultra-high ($100,000 BTC) and Micro ($0.05 Penny)
        """
        test_cases = [
            ("XAUUSD", 4420.00, 4340.00, 4390.00, 4380.00),
            ("XAGUSD", 39.50, 37.80, 38.60, 38.40),
            ("EURUSD", 1.0920, 1.0810, 1.0865, 1.0850),
            ("GBPUSD", 1.3050, 1.2910, 1.2980, 1.2950),
            ("USDJPY", 159.50, 157.80, 158.60, 158.40),
            ("BTCUSD", 98500.0, 93200.0, 96000.0, 95500.0),
            ("MICRO_ASSET", 0.0550, 0.0450, 0.0520, 0.0500),
        ]

        for sym, h, l, c, cur in test_cases:
            df_d1 = pd.DataFrame({
                "open": [cur * 0.995, cur],
                "high": [h, h * 1.01],
                "low": [l, l * 0.99],
                "close": [c, cur],
                "time": [datetime.now(timezone.utc) - timedelta(days=2), datetime.now(timezone.utc) - timedelta(days=1)]
            })
            df_w1 = pd.DataFrame({"open": [cur * 0.98], "close": [cur]})
            df_mn1 = pd.DataFrame({"open": [cur * 0.95], "close": [cur]})

            pivots = self.engine._calculate_d1_benchmarks_and_pivots(df_d1, df_w1, df_mn1, cur, sym)

            expected_p = (h + l + c) / 3.0
            expected_r1 = 2.0 * expected_p - l
            expected_s1 = 2.0 * expected_p - h
            expected_r2 = expected_p + (h - l)
            expected_s2 = expected_p - (h - l)
            expected_r3 = h + 2.0 * (expected_p - l)
            expected_s3 = l - 2.0 * (h - expected_p)

            self.assertAlmostEqual(pivots["pivot"], expected_p, places=5, msg=f"Pivot mismatch on {sym}")
            self.assertAlmostEqual(pivots["r1"], expected_r1, places=5, msg=f"R1 mismatch on {sym}")
            self.assertAlmostEqual(pivots["s1"], expected_s1, places=5, msg=f"S1 mismatch on {sym}")
            self.assertAlmostEqual(pivots["r2"], expected_r2, places=5, msg=f"R2 mismatch on {sym}")
            self.assertAlmostEqual(pivots["s2"], expected_s2, places=5, msg=f"S2 mismatch on {sym}")
            self.assertAlmostEqual(pivots["r3"], expected_r3, places=5, msg=f"R3 mismatch on {sym}")
            self.assertAlmostEqual(pivots["s3"], expected_s3, places=5, msg=f"S3 mismatch on {sym}")

            # Ordering Invariant: S3 < S2 < S1 < P < R1 < R2 < R3
            self.assertLessEqual(pivots["s3"], pivots["s2"], f"Ordering violation on {sym}: S3 > S2")
            self.assertLessEqual(pivots["s2"], pivots["s1"], f"Ordering violation on {sym}: S2 > S1")
            self.assertLessEqual(pivots["s1"], pivots["pivot"], f"Ordering violation on {sym}: S1 > Pivot")
            self.assertLessEqual(pivots["pivot"], pivots["r1"], f"Ordering violation on {sym}: Pivot > R1")
            self.assertLessEqual(pivots["r1"], pivots["r2"], f"Ordering violation on {sym}: R1 > R2")
            self.assertLessEqual(pivots["r2"], pivots["r3"], f"Ordering violation on {sym}: R2 > R3")

            # Symmetry Invariant: R2 - P == P - S2 == H - L
            self.assertAlmostEqual(pivots["r2"] - pivots["pivot"], h - l, places=5)
            self.assertAlmostEqual(pivots["pivot"] - pivots["s2"], h - l, places=5)

    def test_d1_pivots_flat_session_and_empty_candles(self):
        """
        Stress test D1 pivots when session has zero range (High == Low == Close) or empty dataframe.
        """
        # 1. Zero Range (Flat Day)
        df_flat = pd.DataFrame({
            "open": [100.0, 100.0],
            "high": [100.0, 100.0],
            "low": [100.0, 100.0],
            "close": [100.0, 100.0]
        })
        pivots = self.engine._calculate_d1_benchmarks_and_pivots(df_flat, pd.DataFrame(), pd.DataFrame(), 100.0, "XAUUSD")
        self.assertEqual(pivots["pivot"], 100.0)
        self.assertEqual(pivots["r1"], 100.0)
        self.assertEqual(pivots["s1"], 100.0)
        self.assertEqual(pivots["r2"], 100.0)
        self.assertEqual(pivots["s2"], 100.0)
        self.assertEqual(pivots["r3"], 100.0)
        self.assertEqual(pivots["s3"], 100.0)

        # 2. Empty Dataframe fallback
        df_empty = pd.DataFrame()
        pivots_fallback = self.engine._calculate_d1_benchmarks_and_pivots(df_empty, df_empty, df_empty, 4350.0, "XAUUSD")
        self.assertIn("pivot", pivots_fallback)
        self.assertGreater(pivots_fallback["r1"], pivots_fallback["pivot"])
        self.assertLess(pivots_fallback["s1"], pivots_fallback["pivot"])

    # ══════════════════════════════════════════════════════════════════════════
    # 2. PIP SCALING DIFFERENCES & LOT SIZING
    # ══════════════════════════════════════════════════════════════════════════

    def test_pip_scaling_and_sizing_across_assets(self):
        """
        Adversarially verify pip value and lot sizing mechanics across assets:
        - XAUUSD ($10.0/pip): $500 risk / (50 pips * 10) = 1.00 lot
        - EURUSD ($10.0/pip): $500 risk / (50 pips * 10) = 1.00 lot
        - GBPUSD ($10.0/pip): $500 risk / (50 pips * 10) = 1.00 lot
        - USDJPY ($6.50/pip): $500 risk / (50 pips * 6.50) = 1.54 lots
        """
        # Test 50 pips SL
        sizing_gold = self.engine._calculate_calibrated_lot_sizing(50.0, "XAUUSD")
        sizing_eur = self.engine._calculate_calibrated_lot_sizing(50.0, "EURUSD")
        sizing_gbp = self.engine._calculate_calibrated_lot_sizing(50.0, "GBPUSD")
        sizing_jpy = self.engine._calculate_calibrated_lot_sizing(50.0, "USDJPY")

        # 100k Account ($500 risk)
        self.assertEqual(sizing_gold["account_100k"]["lots"], 1.00)
        self.assertEqual(sizing_eur["account_100k"]["lots"], 1.00)
        self.assertEqual(sizing_gbp["account_100k"]["lots"], 1.00)
        self.assertEqual(sizing_jpy["account_100k"]["lots"], 1.54)  # 500 / (50 * 6.50) = 1.538 -> 1.54

        # USDJPY lot size should be strictly greater than Gold/EUR lot size for the same SL distance
        self.assertGreater(sizing_jpy["account_100k"]["lots"], sizing_gold["account_100k"]["lots"])
        self.assertGreater(sizing_jpy["account_50k"]["lots"], sizing_gold["account_50k"]["lots"])
        self.assertGreater(sizing_jpy["account_25k"]["lots"], sizing_gold["account_25k"]["lots"])
        self.assertGreater(sizing_jpy["account_5k"]["lots"], sizing_gold["account_5k"]["lots"])

    def test_lot_sizing_boundary_and_stress_cases(self):
        """
        Stress test sizing with adversarial SL inputs (0, negative, micro, massive).
        """
        adversarial_sls = [0.0, -10.0, -500.0, 0.0001, 1.0, 5.0, 10.0, 1000.0, 50000.0]

        for sl in adversarial_sls:
            for sym in ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]:
                sizing = self.engine._calculate_calibrated_lot_sizing(sl, sym)

                # Check all 4 accounts
                for acc, max_cap in [("account_100k", 5.00), ("account_50k", 3.00), ("account_25k", 2.00), ("account_5k", 1.00)]:
                    lot = sizing[acc]["lots"]
                    risk = sizing[acc]["risk_usd"]
                    # Invariants:
                    self.assertGreaterEqual(lot, 0.01, f"Lot fell below 0.01 floor on {acc} with sl={sl}, sym={sym}")
                    self.assertLessEqual(lot, max_cap, f"Lot exceeded max cap {max_cap} on {acc} with sl={sl}, sym={sym}")
                    self.assertGreater(risk, 0.0, f"Risk USD must be positive")

    # ══════════════════════════════════════════════════════════════════════════
    # 3. ASIAN BOX RANGE & 70.5% OTE DISCOUNT EXTRACTION
    # ══════════════════════════════════════════════════════════════════════════

    def test_asian_box_volatile_vs_flat_sessions(self):
        """
        Test Asian session box extraction under volatile (wide range) vs flat (narrow range) conditions.
        """
        base_time = datetime(2026, 8, 15, 0, 0, tzinfo=timezone.utc)
        times = [base_time + timedelta(minutes=15 * i) for i in range(40)]

        # 1. Volatile Asian Session (Wide Range: $4350 to $4420)
        highs_vol = [4350.0 + (i * 2.0) if i < 24 else 4390.0 for i in range(40)]
        lows_vol = [4340.0 - (i * 0.5) if i < 24 else 4380.0 for i in range(40)]
        df_m15_vol = pd.DataFrame({
            "time": times,
            "open": [(h + l) / 2.0 for h, l in zip(highs_vol, lows_vol)],
            "high": highs_vol,
            "low": lows_vol,
            "close": highs_vol,
            "tick_volume": [500] * 40
        })

        smc_vol = self.engine._extract_order_blocks_and_asian_box(
            df_h4=df_m15_vol, df_h1=df_m15_vol, df_m15=df_m15_vol, current_price=4385.0, symbol="XAUUSD"
        )
        self.assertGreater(smc_vol["asian_range_pips"], 500.0)
        self.assertGreater(smc_vol["asian_high"], smc_vol["asian_low"])

        # 2. Flat Asian Session (Narrow Range: $4350.0 to $4350.5)
        highs_flat = [4350.5 for _ in range(40)]
        lows_flat = [4350.0 for _ in range(40)]
        df_m15_flat = pd.DataFrame({
            "time": times,
            "open": [4350.2] * 40,
            "high": highs_flat,
            "low": lows_flat,
            "close": [4350.3] * 40,
            "tick_volume": [100] * 40
        })

        smc_flat = self.engine._extract_order_blocks_and_asian_box(
            df_h4=df_m15_flat, df_h1=df_m15_flat, df_m15=df_m15_flat, current_price=4350.3, symbol="XAUUSD"
        )
        self.assertAlmostEqual(smc_flat["asian_range_pips"], 5.0, places=1)

    def test_ote_fibonacci_mathematical_precision(self):
        """
        Verify exact 70.5% Fibonacci OTE Sweet Spot calculation for BUY and SELL directions.
        BUY OTE: High - 0.705 * (High - Low)
        SELL OTE: Low + 0.705 * (High - Low)
        """
        df = pd.DataFrame({
            "high": [100.0] * 30,
            "low": [0.0] * 30,
            "close": [50.0] * 30,
            "open": [50.0] * 30
        })

        # Buy Direction
        res_buy = self.of_quant.compute_ote_fibonacci_array(df, current_price=29.5, direction="BUY")
        self.assertAlmostEqual(res_buy["fib_618"], 38.2, places=2)  # 100 - 61.8 = 38.2
        self.assertAlmostEqual(res_buy["fib_705_sweet_spot"], 29.5, places=2)  # 100 - 70.5 = 29.5
        self.assertAlmostEqual(res_buy["fib_786"], 21.4, places=2)  # 100 - 78.6 = 21.4
        self.assertTrue(res_buy["in_ote_zone"])
        self.assertEqual(res_buy["score_bonus"], 0.60)

        # Sell Direction
        res_sell = self.of_quant.compute_ote_fibonacci_array(df, current_price=70.5, direction="SELL")
        self.assertAlmostEqual(res_sell["fib_618"], 61.8, places=2)  # 0 + 61.8 = 61.8
        self.assertAlmostEqual(res_sell["fib_705_sweet_spot"], 70.5, places=2)  # 0 + 70.5 = 70.5
        self.assertAlmostEqual(res_sell["fib_786"], 78.6, places=2)  # 0 + 78.6 = 78.6
        self.assertTrue(res_sell["in_ote_zone"])
        self.assertEqual(res_sell["score_bonus"], 0.60)

    # ══════════════════════════════════════════════════════════════════════════
    # 4. SCENARIO A/B IF-THEN MATRIX & INVALIDATION BOUNDARIES
    # ══════════════════════════════════════════════════════════════════════════

    def test_scenario_ab_invalidation_boundaries(self):
        """
        Verify that Scenario A and B invalidation boundaries are mathematically consistent and protect against adverse drift.
        """
        pivots = {
            "pivot": 4380.0,
            "r1": 4410.0,
            "r2": 4440.0,
            "s1": 4350.0,
            "s2": 4320.0,
            "r3": 4470.0,
            "s3": 4290.0,
            "prev_close": 4375.0,
            "prev_high": 4400.0,
            "prev_low": 4340.0,
            "prev_open": 4360.0
        }
        smc = {
            "asian_high": 4400.0,
            "asian_low": 4355.0,
            "asian_range_pips": 450.0,
            "active_bull_ob": {"high": 4360.0, "low": 4350.0, "entry_price": 4355.0, "sl_price": 4345.0},
            "active_bear_ob": {"high": 4410.0, "low": 4400.0, "entry_price": 4405.0, "sl_price": 4415.0},
            "ote_705_sweet_spot": 4362.0,
            "in_ote_zone": True,
            "discount_zone": "DISCOUNT",
            "equilibrium": 4377.5
        }
        atr = 15.0

        matrix = self.engine._synthesize_if_then_matrix("XAUUSD", 4375.0, pivots, smc, atr)
        sc_a = matrix["scenario_a"]
        sc_b = matrix["scenario_b"]

        # Invariants for Scenario A:
        # 1. Invalidation A = min(bull_ob['low'], asian_low) - 0.5 * atr = min(4350, 4355) - 7.5 = 4342.5
        self.assertEqual(sc_a["invalidation_level"], 4342.5)
        # 2. Invalidation A strictly below Entry A and Asian Low
        self.assertLess(sc_a["invalidation_level"], sc_a["entry_price"])
        self.assertLess(sc_a["invalidation_level"], smc["asian_low"])
        # 3. Targets TP1 and TP2 strictly above Entry A
        self.assertGreater(sc_a["tp1"], sc_a["entry_price"])
        self.assertGreater(sc_a["tp2"], sc_a["tp1"])

        # Invariants for Scenario B:
        # 1. Trigger B is breach of Scenario A Invalidation
        # 2. Invalidation B = S2 - 1.0 * atr = 4320.0 - 15.0 = 4305.0
        self.assertEqual(sc_b["invalidation_level"], 4305.0)
        # 3. Invalidation B strictly below S2 and Invalidation A
        self.assertLess(sc_b["invalidation_level"], pivots["s2"])
        self.assertLess(sc_b["invalidation_level"], sc_a["invalidation_level"])
        # 4. Scenario B Targets strictly above Invalidation B
        self.assertGreater(sc_b["target_1"], sc_b["invalidation_level"])
        self.assertGreater(sc_b["target_2"], sc_b["target_1"])

    def test_master_morning_briefing_multi_symbol_generation(self):
        """
        Verify end-to-end generate_morning_master_briefing executes cleanly across all 5 symbols.
        """
        symbols = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY"]

        for sym in symbols:
            briefing = self.engine.generate_morning_master_briefing(sym)

            # Assertions on content & sections
            self.assertIsInstance(briefing, str)
            self.assertGreater(len(briefing), 500, f"Briefing too short for {sym}")
            self.assertIn("GOOD MORNING — INSTITUTIONAL DAILY PLAYBOOK", briefing)
            self.assertIn("1. GLOBAL GEOPOLITICAL & MACRO RADAR:", briefing)
            self.assertIn("2. HISTORICAL CONTEXT & CLOSING BENCHMARKS", briefing)
            self.assertIn("3. TODAY'S IF-THEN STRATEGY MATRIX", briefing)
            self.assertIn("4. ACCOUNT-BY-ACCOUNT EXECUTION BLUEPRINT", briefing)
            self.assertIn("SCENARIO A", briefing)
            self.assertIn("SCENARIO B", briefing)
            self.assertIn("$100k Master", briefing)
            self.assertIn("$50k Funded", briefing)
            self.assertIn("$25k Active", briefing)
            self.assertIn("$5k Fast Scalp", briefing)

    # ══════════════════════════════════════════════════════════════════════════
    # 5. MONTE CARLO RANDOMIZED STRESS TEST (1000 TRIALS)
    # ══════════════════════════════════════════════════════════════════════════

    def test_monte_carlo_randomized_invariants_1000_trials(self):
        """
        Adversarial Monte Carlo stress test across 1000 randomized price/volatility vectors:
        - Random High, Low, Close across random magnitudes ($0.01 to $150,000.00).
        - Random SL distances (-500 to +50000 pips).
        - Verify mathematical invariants hold across all 1000 trials without exception.
        """
        np.random.seed(1337)
        symbols = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY"]

        for trial in range(1000):
            sym = symbols[trial % len(symbols)]
            # Generate random base magnitude
            base_mag = 10.0 ** np.random.uniform(-1, 5)  # 0.1 to 100,000
            low = base_mag * np.random.uniform(0.90, 0.99)
            high = low * np.random.uniform(1.01, 1.20)
            close = np.random.uniform(low, high)
            open_p = np.random.uniform(low, high)

            df_d1 = pd.DataFrame({
                "open": [open_p, open_p],
                "high": [high, high],
                "low": [low, low],
                "close": [close, close],
                "time": [datetime.now(timezone.utc) - timedelta(days=2), datetime.now(timezone.utc) - timedelta(days=1)]
            })
            df_w1 = pd.DataFrame({"open": [open_p], "close": [close]})
            df_mn1 = pd.DataFrame({"open": [open_p], "close": [close]})

            # 1. Test Pivots
            pivots = self.engine._calculate_d1_benchmarks_and_pivots(df_d1, df_w1, df_mn1, close, sym)

            # Invariant 1: Pivot strictly between Low and High
            self.assertGreaterEqual(pivots["pivot"], low)
            self.assertLessEqual(pivots["pivot"], high)

            # Invariant 2: Ordering S3 <= S2 <= S1 <= P <= R1 <= R2 <= R3
            self.assertLessEqual(pivots["s3"], pivots["s2"])
            self.assertLessEqual(pivots["s2"], pivots["s1"])
            self.assertLessEqual(pivots["s1"], pivots["pivot"])
            self.assertLessEqual(pivots["pivot"], pivots["r1"])
            self.assertLessEqual(pivots["r1"], pivots["r2"])
            self.assertLessEqual(pivots["r2"], pivots["r3"])

            # Invariant 3: Symmetry R2 - P == P - S2 == H - L
            self.assertAlmostEqual(pivots["r2"] - pivots["pivot"], high - low, places=4)
            self.assertAlmostEqual(pivots["pivot"] - pivots["s2"], high - low, places=4)

            # 2. Test Lot Sizing
            random_sl = float(np.random.uniform(-100.0, 5000.0))
            sizing = self.engine._calculate_calibrated_lot_sizing(random_sl, sym)
            for acc, cap, risk_usd in [
                ("account_100k", 5.00, 500.0),
                ("account_50k", 3.00, 250.0),
                ("account_25k", 2.00, 125.0),
                ("account_5k", 1.00, 25.0),
            ]:
                lot = sizing[acc]["lots"]
                self.assertGreaterEqual(lot, 0.01)
                self.assertLessEqual(lot, cap)
                self.assertEqual(sizing[acc]["risk_usd"], risk_usd)

    def test_invalidation_boundaries_under_extreme_atr(self):
        """
        Stress test Scenario A and B invalidation with extreme ATR (0.0, 0.0001, 1000.0).
        """
        pivots = {
            "pivot": 4350.0, "r1": 4380.0, "r2": 4410.0,
            "s1": 4320.0, "s2": 4290.0, "r3": 4440.0, "s3": 4260.0,
            "prev_close": 4350.0, "prev_high": 4370.0, "prev_low": 4330.0, "prev_open": 4340.0
        }
        smc = {
            "asian_high": 4370.0, "asian_low": 4340.0, "asian_range_pips": 300.0,
            "active_bull_ob": {"high": 4345.0, "low": 4335.0, "entry_price": 4340.0, "sl_price": 4330.0},
            "active_bear_ob": {"high": 4375.0, "low": 4365.0, "entry_price": 4370.0, "sl_price": 4380.0},
            "ote_705_sweet_spot": 4342.0, "in_ote_zone": True, "discount_zone": "DISCOUNT", "equilibrium": 4355.0
        }

        # 1. Zero ATR
        res_zero = self.engine._synthesize_if_then_matrix("XAUUSD", 4350.0, pivots, smc, atr=0.0)
        self.assertEqual(res_zero["scenario_a"]["invalidation_level"], 4335.0)  # min(4335, 4340) - 0 = 4335
        self.assertEqual(res_zero["scenario_b"]["invalidation_level"], 4290.0)  # S2 - 0 = 4290

        # 2. Massive ATR (1000.0)
        res_massive = self.engine._synthesize_if_then_matrix("XAUUSD", 4350.0, pivots, smc, atr=1000.0)
        self.assertEqual(res_massive["scenario_a"]["invalidation_level"], 4335.0 - 500.0)  # 3835.0
        self.assertEqual(res_massive["scenario_b"]["invalidation_level"], 4290.0 - 1000.0)  # 3290.0
        self.assertLess(res_massive["scenario_b"]["invalidation_level"], res_massive["scenario_a"]["invalidation_level"])


if __name__ == "__main__":
    unittest.main()
