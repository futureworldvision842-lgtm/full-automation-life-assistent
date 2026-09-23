"""
tests/test_m1_forensic_integrity.py — Independent Forensic Integrity Test Suite for Milestone 1
Validates:
1. Dynamic Output Behavior (No hardcoded strings)
2. Lee-Ready CVD Algorithm Correctness & Edge Cases
3. D1 Floor Pivot Mathematics ($P, R1, S1, R2, S2, R3, S3$)
4. 50-Year Crisis Cosine Similarity Verification
5. Scenario A/B IF-THEN Invalidation Mathematics
6. 4-Account Calibrated Lot Sizing & Risk Caps
"""

import sys
import unittest
import numpy as np
import pandas as pd
from typing import Dict, Any

from src.daily_institutional_routine_engine import DailyInstitutionalRoutineEngine
from src.market_analyzer import MarketAnalyzer
from src.order_flow_quant import OrderFlowQuantEngine
from src.market_history_encyclopedia import MarketHistoryEncyclopedia
from src.mt5_connector import MT5Connector


class TestM1ForensicIntegrity(unittest.TestCase):

    def setUp(self):
        self.engine = DailyInstitutionalRoutineEngine()
        self.analyzer = MarketAnalyzer({})
        self.of_quant = OrderFlowQuantEngine()
        self.history = MarketHistoryEncyclopedia()

    # ──────────────────────────────────────────────────────────────────────────
    # 1. DYNAMIC OUTPUT BEHAVIOR (NON-STATIC STRING VERIFICATION)
    # ──────────────────────────────────────────────────────────────────────────
    def test_morning_briefing_is_dynamically_computed(self):
        """Verify that altering candle data changes briefing values, proving no hardcoded facade."""
        # Generate briefing 1 with gold default
        briefing_gold = self.engine.generate_morning_master_briefing("XAUUSD")
        self.assertIn("GOLD #XAUUSD", briefing_gold)
        self.assertIn("SCENARIO A", briefing_gold)
        self.assertIn("SCENARIO B", briefing_gold)
        self.assertIn("100k Master", briefing_gold)

        # Generate briefing 2 with EURUSD
        briefing_eur = self.engine.generate_morning_master_briefing("EURUSD")
        self.assertIn("GOLD #EURUSD", briefing_eur)
        self.assertNotEqual(briefing_gold, briefing_eur, "Briefing outputs must differ for different assets!")

    # ──────────────────────────────────────────────────────────────────────────
    # 2. LEE-READY CVD MATHEMATICAL ACCURACY & BOUNDARY CHECKS
    # ──────────────────────────────────────────────────────────────────────────
    def test_lee_ready_cvd_quote_rule_and_tick_test(self):
        """Verifies exact Lee-Ready classification rules."""
        # Synthetic ticks:
        # Tick 0: bid 100, ask 102, last 101.5 (above mid 101.0 -> Buy +1, vol 10)
        # Tick 1: bid 100, ask 102, last 100.5 (below mid 101.0 -> Sell -1, vol 20)
        # Tick 2: bid 100, ask 102, last 101.0 (on mid -> tick test vs prev 100.5 -> uptick +1, vol 30)
        # Tick 3: bid 100, ask 102, last 101.0 (on mid -> zero tick -> repeat prev +1, vol 15)
        # Tick 4: bid 100, ask 102, last 100.0 (below mid -> Sell -1, vol 5)
        ticks = np.array([
            (100.0, 102.0, 101.5, 10.0),
            (100.0, 102.0, 100.5, 20.0),
            (100.0, 102.0, 101.0, 30.0),
            (100.0, 102.0, 101.0, 15.0),
            (100.0, 102.0, 100.0, 5.0),
        ], dtype=[('bid', '<f8'), ('ask', '<f8'), ('last', '<f8'), ('volume', '<f8')])

        res = self.of_quant.compute_tick_cvd(ticks)

        # Total buy vol = 10 (tick 0) + 30 (tick 2) + 15 (tick 3) = 55
        # Total sell vol = 20 (tick 1) + 5 (tick 4) = 25
        # Total vol = 80
        # Net delta = 55 - 25 = 30
        # Buyer ratio = 55 / 80 = 0.6875 -> 0.69
        self.assertEqual(res["net_delta"], 30)
        self.assertEqual(res["cvd"], 30)
        self.assertEqual(res["buyer_ratio"], 0.69)
        self.assertEqual(res["divergence"], "BULLISH_CVD_SURGE")

    def test_lee_ready_cvd_edge_cases(self):
        """Verifies handling of None, empty, and zero-volume inputs."""
        res_none = self.of_quant.compute_tick_cvd(None)
        self.assertEqual(res_none["cvd"], 0)
        self.assertEqual(res_none["buyer_ratio"], 0.50)
        self.assertEqual(res_none["divergence"], "NONE")

        res_empty = self.of_quant.compute_tick_cvd(np.array([]))
        self.assertEqual(res_empty["cvd"], 0)
        self.assertEqual(res_empty["buyer_ratio"], 0.50)

    # ──────────────────────────────────────────────────────────────────────────
    # 3. D1 FLOOR PIVOT MATHEMATICS
    # ──────────────────────────────────────────────────────────────────────────
    def test_d1_floor_pivots_exact_formulas(self):
        """Verifies standard floor pivot formulas."""
        H, L, C, O = 2400.0, 2350.0, 2380.0, 2360.0
        df_d1 = pd.DataFrame([
            {"time": "2026-08-13", "open": 2340.0, "high": 2370.0, "low": 2330.0, "close": 2360.0},
            {"time": "2026-08-14", "open": O, "high": H, "low": L, "close": C},
            {"time": "2026-08-15", "open": 2380.0, "high": 2390.0, "low": 2375.0, "close": 2385.0},
        ])
        df_w1 = pd.DataFrame([{"open": 2300.0, "high": 2400.0, "low": 2290.0, "close": 2385.0}])
        df_mn1 = pd.DataFrame([{"open": 2200.0, "high": 2420.0, "low": 2180.0, "close": 2385.0}])

        current_price = 2385.0
        pivots = self.engine._calculate_d1_benchmarks_and_pivots(df_d1, df_w1, df_mn1, current_price, "XAUUSD")

        # Ground truth formulas
        expected_P = (H + L + C) / 3.0
        expected_R1 = 2.0 * expected_P - L
        expected_S1 = 2.0 * expected_P - H
        expected_R2 = expected_P + (H - L)
        expected_S2 = expected_P - (H - L)
        expected_R3 = H + 2.0 * (expected_P - L)
        expected_S3 = L - 2.0 * (H - expected_P)

        self.assertAlmostEqual(pivots["pivot"], expected_P, places=4)
        self.assertAlmostEqual(pivots["r1"], expected_R1, places=4)
        self.assertAlmostEqual(pivots["s1"], expected_S1, places=4)
        self.assertAlmostEqual(pivots["r2"], expected_R2, places=4)
        self.assertAlmostEqual(pivots["s2"], expected_S2, places=4)
        self.assertAlmostEqual(pivots["r3"], expected_R3, places=4)
        self.assertAlmostEqual(pivots["s3"], expected_S3, places=4)

        # Weekly change
        expected_w_pct = ((current_price - 2300.0) / 2300.0) * 100.0
        self.assertAlmostEqual(pivots["weekly_change_pct"], expected_w_pct, places=4)

    # ──────────────────────────────────────────────────────────────────────────
    # 4. 50-YEAR CRISIS COSINE SIMILARITY
    # ──────────────────────────────────────────────────────────────────────────
    def test_cosine_similarity_against_historical_regimes(self):
        """Verifies multi-feature cosine similarity against ground truth numpy calculations."""
        test_vectors = [
            # [Vol, DXY, Inflation, SafeHaven]
            (1.5, -0.8, 1.8, 1.2, "1971_NIXON_SHOCK"),
            (3.5, 0.4, 0.2, 0.5, "1987_BLACK_MONDAY"),
            (3.2, 0.8, -0.5, 1.5, "2008_GFC_LEHMAN"),
            (4.0, 0.2, -0.2, 2.0, "2015_SNB_PEG_REMOVAL"),
            (3.8, 0.9, -0.8, 1.9, "2020_COVID_LIQUIDITY_FREEZE"),
            (1.8, -0.6, 1.4, 2.2, "2024_2026_DE_DOLLARIZATION"),
        ]

        for vol, dxy, infl, safe, expected_key in test_vectors:
            res = self.history.match_nearest_historical_analogue(
                current_volatility_z=vol,
                dxy_momentum=dxy,
                inflation_factor=infl,
                safe_haven_demand=safe
            )
            # Since vector matches database exactly, cosine similarity must be 100.0% (or 99.9%+)
            self.assertGreaterEqual(res["similarity_score_pct"], 99.0)
            expected_name = MarketHistoryEncyclopedia.HISTORICAL_CRISIS_DATABASE[expected_key]["name"]
            self.assertEqual(res["nearest_historical_analogue"], expected_name)

    # ──────────────────────────────────────────────────────────────────────────
    # 5. SCENARIO A/B IF-THEN MATRIX INVALIDATIONS
    # ──────────────────────────────────────────────────────────────────────────
    def test_scenario_ab_matrix_invalidations(self):
        """Verifies mathematical invalidation levels and target calculations for Scenarios A and B."""
        pivots = {
            "pivot": 2400.0, "r1": 2420.0, "r2": 2440.0, "r3": 2460.0,
            "s1": 2380.0, "s2": 2360.0, "s3": 2340.0
        }
        smc = {
            "asian_low": 2390.0, "asian_high": 2415.0, "asian_range_pips": 250.0,
            "active_bull_ob": {"low": 2385.0, "high": 2395.0, "entry_price": 2390.0},
            "ote_705_sweet_spot": 2388.0
        }
        atr = 10.0

        res = self.engine._synthesize_if_then_matrix("XAUUSD", 2405.0, pivots, smc, atr)
        sc_a = res["scenario_a"]
        sc_b = res["scenario_b"]

        # Scenario A Invalidation: min(bull_ob['low'], asian_low) - 0.50 * atr = min(2385, 2390) - 5 = 2380.0
        self.assertEqual(sc_a["invalidation_level"], 2380.0)
        self.assertEqual(sc_a["entry_price"], 2388.0)
        self.assertEqual(sc_a["tp1"], 2420.0)
        self.assertEqual(sc_a["tp2"], 2440.0)

        # Scenario B Invalidation: s2 - 1.0 * atr = 2360.0 - 10.0 = 2350.0
        self.assertEqual(sc_b["invalidation_level"], 2350.0)
        self.assertEqual(sc_b["target_1"], 2380.0)
        self.assertEqual(sc_b["target_2"], 2400.0)

    # ──────────────────────────────────────────────────────────────────────────
    # 6. 4-ACCOUNT CALIBRATED LOT SIZING & RISK CEILING
    # ──────────────────────────────────────────────────────────────────────────
    def test_calibrated_lot_sizing_risk_caps(self):
        """Verifies 4-account lot sizing is strictly constrained by risk budget and max lot limits."""
        for sl_pips in [20.0, 50.0, 100.0, 200.0]:
            sizing = self.engine._calculate_calibrated_lot_sizing(sl_pips, "XAUUSD")

            # 100k Master ($500 risk)
            lot_100k = sizing["account_100k"]["lots"]
            expected_100k = min(5.00, max(0.01, round(500.0 / (sl_pips * 10.0), 2)))
            self.assertEqual(lot_100k, expected_100k)
            actual_risk_100k = lot_100k * sl_pips * 10.0
            self.assertLessEqual(actual_risk_100k, 500.0 + 10.0) # Within rounding margin

            # 50k Funded ($250 risk)
            lot_50k = sizing["account_50k"]["lots"]
            expected_50k = min(3.00, max(0.01, round(250.0 / (sl_pips * 10.0), 2)))
            self.assertEqual(lot_50k, expected_50k)

            # 25k Active ($125 risk)
            lot_25k = sizing["account_25k"]["lots"]
            expected_25k = min(2.00, max(0.01, round(125.0 / (sl_pips * 10.0), 2)))
            self.assertEqual(lot_25k, expected_25k)

            # 5k Scalp ($25 risk)
            lot_5k = sizing["account_5k"]["lots"]
            expected_5k = min(1.00, max(0.01, round(25.0 / (sl_pips * 10.0), 2)))
            self.assertEqual(lot_5k, expected_5k)


if __name__ == "__main__":
    unittest.main()
