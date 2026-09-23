"""
tests/test_challenger_m2_adversarial.py
===============================================================================
Adversarial Empirical Stress Test Suite for Milestone M2:
World Monitor & Geopolitical DEFCON Engine.

Authored by Challenger 2 (teamwork_preview_challenger_m2_2).

Exhaustively verifies:
1. Maritime Chokepoints & CII:
   - Disruption percentage with extreme values (baseline 0, negative flows, flow > baseline,
     baseline < 0, Monte Carlo randomized inputs).
   - 4-pillar Country Instability Index (CII) edge cases (all 0, all 100, out-of-range,
     negative, >100, empty dict, string conversions, weight invariance).
2. DEFCON Scale Transitions:
   - Exact boundary thresholds: 85.0 (DEFCON 1), 70.0 (DEFCON 2), 50.0 (DEFCON 3), 25.0 (DEFCON 4).
   - Epsilon boundaries (84.999, 69.999, 49.999, 24.999, 0.0, -10.0, 150.0).
   - Asset macro multiplier transitions across all 5 DEFCON regimes.
3. Counter-Macro Conflict Gating:
   - Full directional permutation matrix:
     - BUY Gold @ DEFCON 2 -> APPROVE with 1.45x multiplier, lot clamped to 0.10 ceiling.
     - SELL Gold @ DEFCON 2 -> VETO (approved=False, lot=0.0, risk=0.0).
     - BUY WTI @ DEFCON 2 -> APPROVE with 1.50x multiplier, lot clamped to 0.20 ceiling.
     - SELL WTI @ DEFCON 2 -> VETO (approved=False, lot=0.0, risk=0.0).
     - EURUSD SELL -> APPROVE (0.80x), EURUSD BUY -> VETO.
     - BTCUSD BUY -> APPROVE (1.20x, ceiling 0.01), BTCUSD SELL -> VETO.
     - Neutral assets (AUDCAD) -> APPROVE with 1.0x.
   - Verification of _execute_direct_trade blocking counter-macro trades.
4. Windows cp1252 Console Encoding Safety:
   - Assertion of zero UnicodeEncodeError across all fusion outputs, reasoning strings,
     JSON serialization, and trade blocking receipts.
===============================================================================
"""

import json
import random
import sys
import unittest
from pathlib import Path
from typing import Any, Dict

# Setup search paths
ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = ROOT / "MQ3 TRADING BOT"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

from actions.geospatial_intelligence import CHOKEPOINTS_DATA, get_chokepoints_telemetry
from core.geopolitical_trading_fusion import geopolitical_fusion, GeopoliticalTradingFusion
from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine
from actions.mq3_trading import _execute_direct_trade


class TestChallenger2MilestoneM2Adversarial(unittest.TestCase):
    """Rigorous empirical challenger test suite for Milestone M2."""

    def setUp(self):
        self.engine = WorldMonitorIntelligenceEngine()
        self.fusion = geopolitical_fusion

    # =========================================================================
    # 1. MARITIME CHOKEPOINTS & CII STRESS TESTING
    # =========================================================================

    def test_01_disruption_calculation_extreme_values(self):
        """Adversarially test disruption formula with baseline 0, negative flow, flow > baseline."""
        calc = WorldMonitorIntelligenceEngine.calculate_disruption_percentage

        # Case 1A: Zero baseline with varied incident counts
        self.assertEqual(calc(0.0, 0.0, incident_count=0), 0.0)
        self.assertEqual(calc(0.0, 0.0, incident_count=25), 20.0)  # 25 * 0.8 = 20.0
        self.assertEqual(calc(0.0, 0.0, incident_count=125), 100.0)  # 125 * 0.8 = 100.0 (clamped)
        self.assertEqual(calc(0.0, 0.0, incident_count=500), 100.0)  # extreme incident count clamped to 100.0
        self.assertEqual(calc(0.0, 0.0, incident_count=-10), 0.0)  # negative incident clamped to 0.0
        self.assertEqual(calc(0.0, 15.0, incident_count=30), 24.0)  # baseline 0 ignores current_mbd

        # Case 1B: Negative flows (must clamp to 100% disruption, never > 100%)
        self.assertEqual(calc(21.0, -1.0), 100.0)
        self.assertEqual(calc(21.0, -999.0), 100.0)
        self.assertEqual(calc(8.8, -0.0001), 100.0)
        self.assertEqual(calc(5.0, -50.0), 100.0)

        # Case 1C: Flow > baseline (surge flows; disruption must clamp to 0.0%, never negative)
        self.assertEqual(calc(21.0, 21.0), 0.0)
        self.assertEqual(calc(21.0, 25.0), 0.0)
        self.assertEqual(calc(21.0, 100.0), 0.0)
        self.assertEqual(calc(8.8, 15.0), 0.0)
        self.assertEqual(calc(5.0, 50.0), 0.0)
        self.assertEqual(calc(3.0, 3.0001), 0.0)

        # Case 1D: Baseline < 0 (malformed baseline; gracefully handles via fallback branch)
        res_neg_baseline = calc(-10.0, 5.0, incident_count=20)
        self.assertTrue(0.0 <= res_neg_baseline <= 100.0)
        self.assertEqual(res_neg_baseline, 16.0)  # 20 * 0.8 = 16.0

        # Case 1E: Monte Carlo randomized stress test (5,000 trials)
        random.seed(1337)
        for _ in range(5000):
            baseline = random.uniform(0.01, 100.0)
            current = random.uniform(-100.0, 200.0)
            disruption = calc(baseline, current)
            self.assertTrue(
                0.0 <= disruption <= 100.0,
                f"Disruption {disruption} out of [0.0, 100.0] for baseline={baseline}, current={current}"
            )
            # Monotonicity check: decreasing flow must never decrease disruption
            current_lower = current - random.uniform(0.1, 20.0)
            disruption_higher = calc(baseline, current_lower)
            self.assertGreaterEqual(
                disruption_higher,
                disruption,
                f"Monotonicity violation: lower flow {current_lower} gave lower disruption {disruption_higher} vs {disruption}"
            )

    def test_02_chokepoint_state_update_mutation(self):
        """Verify update_chokepoint_flow with extreme values recalculates metrics and risk levels."""
        engine = WorldMonitorIntelligenceEngine()

        # Update Hormuz to negative flow -> clamped disruption 100.0%, CRITICAL_WARZONE, anomaly True
        cp = engine.update_chokepoint_flow("hormuz_strait", current_mbd=-5.0, incident_count=50)
        self.assertEqual(cp["disruption_pct"], 100.0)
        self.assertEqual(cp["risk_level"], "CRITICAL_WARZONE")
        self.assertTrue(cp["anomaly_signal"])

        # Update Malacca to surge flow (35.0 mbd > baseline 17.2) -> disruption 0.0%
        cp_malacca = engine.update_chokepoint_flow("malacca_strait", current_mbd=35.0, incident_count=0)
        self.assertEqual(cp_malacca["disruption_pct"], 0.0)
        self.assertGreater(cp_malacca["flow_pct_of_baseline"], 100.0)

        # Update Taiwan Strait (baseline 0) with incident count 50 -> disruption 40.0%, incident >= 40 -> CRITICAL_WARZONE
        cp_taiwan_50 = engine.update_chokepoint_flow("taiwan_strait", current_mbd=0.0, incident_count=50)
        self.assertEqual(cp_taiwan_50["disruption_pct"], 40.0)
        self.assertEqual(cp_taiwan_50["risk_level"], "CRITICAL_WARZONE")

        # Test HIGH_TENSION tier: incident count 25 (20 <= count < 40, disruption = 20.0%)
        cp_taiwan_25 = engine.update_chokepoint_flow("taiwan_strait", current_mbd=0.0, incident_count=25)
        self.assertEqual(cp_taiwan_25["disruption_pct"], 20.0)
        self.assertEqual(cp_taiwan_25["risk_level"], "HIGH_TENSION")

        # Test MODERATE_DISRUPTION tier: incident count 12 (10 <= count < 20, disruption = 9.6%)
        cp_taiwan_12 = engine.update_chokepoint_flow("taiwan_strait", current_mbd=0.0, incident_count=12)
        self.assertEqual(cp_taiwan_12["disruption_pct"], 9.6)
        self.assertEqual(cp_taiwan_12["risk_level"], "MODERATE_DISRUPTION")

        # Test STABLE_SURVEILLANCE tier: incident count 5 (< 10, disruption = 4.0%)
        cp_taiwan_5 = engine.update_chokepoint_flow("taiwan_strait", current_mbd=0.0, incident_count=5)
        self.assertEqual(cp_taiwan_5["disruption_pct"], 4.0)
        self.assertEqual(cp_taiwan_5["risk_level"], "STABLE_SURVEILLANCE")

    def test_03_four_pillar_cii_edge_cases_and_weight_invariance(self):
        """Adversarially test CII formula with all 0, all 100, out-of-range, and empty inputs."""
        calc = WorldMonitorIntelligenceEngine.calculate_country_instability_score

        # Case 3A: Weight sum invariance
        weights = WorldMonitorIntelligenceEngine.CII_WEIGHTS
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)
        self.assertEqual(weights["unrest"], 0.20)
        self.assertEqual(weights["conflict"], 0.40)
        self.assertEqual(weights["security"], 0.25)
        self.assertEqual(weights["information"], 0.15)

        # Case 3B: All zeroes -> 0.0
        self.assertEqual(calc({"unrest": 0, "conflict": 0, "security": 0, "information": 0}), 0.0)
        self.assertEqual(calc({"unrest": 0.0, "conflict": 0.0, "security": 0.0, "information": 0.0}), 0.0)

        # Case 3C: All 100s -> 100.0
        self.assertEqual(calc({"unrest": 100, "conflict": 100, "security": 100, "information": 100}), 100.0)

        # Case 3D: Out-of-range negative values (must clamp to 0.0, never negative)
        self.assertEqual(calc({"unrest": -50.0, "conflict": -100.0, "security": -20.0, "information": -10.0}), 0.0)
        self.assertEqual(calc({"unrest": -500.0, "conflict": 0.0, "security": 0.0, "information": 0.0}), 0.0)

        # Case 3E: Out-of-range high values (must clamp to 100.0, never exceed 100.0)
        self.assertEqual(calc({"unrest": 200.0, "conflict": 150.0, "security": 180.0, "information": 300.0}), 100.0)
        self.assertEqual(calc({"unrest": 100.0, "conflict": 250.0, "security": 50.0, "information": 50.0}), 100.0)

        # Case 3F: Missing keys & empty dict (graceful default to 0.0)
        self.assertEqual(calc({}), 0.0)
        self.assertEqual(calc({"conflict": 100.0}), 40.0)  # 0.40 * 100 = 40.0
        self.assertEqual(calc({"unrest": 50.0}), 10.0)     # 0.20 * 50 = 10.0
        self.assertEqual(calc({"security": 80.0}), 20.0)   # 0.25 * 80 = 20.0
        self.assertEqual(calc({"information": 60.0}), 9.0) # 0.15 * 60 = 9.0

        # Case 3G: String input resilience
        score_str = calc({"unrest": "80", "conflict": "90", "security": "70", "information": "60"})
        self.assertEqual(score_str, 78.5)

    # =========================================================================
    # 2. DEFCON SCALE EXACT BOUNDARY TRANSITIONS
    # =========================================================================

    def test_04_defcon_exact_boundary_thresholds(self):
        """Test exact boundary transitions for DEFCON: 85.0, 70.0, 50.0, 25.0 and epsilon steps."""
        get_defcon = WorldMonitorIntelligenceEngine.get_defcon_level

        # Boundary 1: DEFCON 1 vs 2 (Threshold 85.0)
        self.assertEqual(get_defcon(100.0), 1, "100.0 must be DEFCON 1")
        self.assertEqual(get_defcon(90.0), 1, "90.0 must be DEFCON 1")
        self.assertEqual(get_defcon(85.0), 1, "Exact 85.0 must be DEFCON 1")
        self.assertEqual(get_defcon(84.999), 2, "84.999 must fall to DEFCON 2")
        self.assertEqual(get_defcon(84.9), 2, "84.9 must be DEFCON 2")

        # Boundary 2: DEFCON 2 vs 3 (Threshold 70.0)
        self.assertEqual(get_defcon(75.0), 2, "75.0 must be DEFCON 2")
        self.assertEqual(get_defcon(70.0), 2, "Exact 70.0 must be DEFCON 2")
        self.assertEqual(get_defcon(69.999), 3, "69.999 must fall to DEFCON 3")
        self.assertEqual(get_defcon(69.9), 3, "69.9 must be DEFCON 3")

        # Boundary 3: DEFCON 3 vs 4 (Threshold 50.0)
        self.assertEqual(get_defcon(55.0), 3, "55.0 must be DEFCON 3")
        self.assertEqual(get_defcon(50.0), 3, "Exact 50.0 must be DEFCON 3")
        self.assertEqual(get_defcon(49.999), 4, "49.999 must fall to DEFCON 4")
        self.assertEqual(get_defcon(49.9), 4, "49.9 must be DEFCON 4")

        # Boundary 4: DEFCON 4 vs 5 (Threshold 25.0)
        self.assertEqual(get_defcon(30.0), 4, "30.0 must be DEFCON 4")
        self.assertEqual(get_defcon(25.0), 4, "Exact 25.0 must be DEFCON 4")
        self.assertEqual(get_defcon(24.999), 5, "24.999 must fall to DEFCON 5")
        self.assertEqual(get_defcon(24.9), 5, "24.9 must be DEFCON 5")
        self.assertEqual(get_defcon(0.0), 5, "0.0 must be DEFCON 5")

        # Extreme values
        self.assertEqual(get_defcon(-50.0), 5, "Negative score must be DEFCON 5")
        self.assertEqual(get_defcon(250.0), 1, "Extremely high score must be DEFCON 1")

    def test_05_asset_macro_multipliers_across_all_defcon_levels(self):
        """Verify Gold and WTI multipliers across all 5 DEFCON regimes."""
        engine = WorldMonitorIntelligenceEngine()

        # Regime Matrix: (defcon_level, expected_gold_mult, expected_oil_mult)
        regimes = [
            (1, 1.45, 1.50),
            (2, 1.45, 1.50),
            (3, 1.35, 1.35),
            (4, 1.05, 1.10),
            (5, 1.00, 1.00),
        ]

        for lvl, exp_gold, exp_oil in regimes:
            engine.defcon_level = lvl
            gold = engine.evaluate_geopolitical_market_bias("XAUUSD")
            oil = engine.evaluate_geopolitical_market_bias("WTI")

            self.assertEqual(
                gold["macro_multiplier"],
                exp_gold,
                f"Gold multiplier mismatch at DEFCON {lvl}: got {gold['macro_multiplier']}, expected {exp_gold}"
            )
            self.assertEqual(
                oil["macro_multiplier"],
                exp_oil,
                f"Oil multiplier mismatch at DEFCON {lvl}: got {oil['macro_multiplier']}, expected {exp_oil}"
            )

    # =========================================================================
    # 3. COUNTER-MACRO CONFLICT GATING & POSITION SIZING
    # =========================================================================

    def test_06_gold_counter_macro_permutations_defcon2(self):
        """Adversarially verify BUY Gold -> APPROVE (1.45x) and SELL Gold -> VETO (0.0x, lot=0.0)."""
        # 1. BUY Gold (confluence aligns)
        appr, mult, reason = self.fusion.evaluate_trade_confluence("XAUUSD", "BUY")
        self.assertTrue(appr, "BUY Gold must be approved under DEFCON 2 Bullish Macro")
        self.assertEqual(mult, 1.45)
        self.assertIn("[CONFLUENCE]", reason)

        # Sizing: base_lot 0.04 -> 0.04 * 1.45 = 0.058 -> 0.06L (below 0.10 ceiling)
        sized_buy = self.fusion.scale_position_size("XAUUSD", base_lot=0.04, base_risk_usd=50.0, action="BUY")
        self.assertTrue(sized_buy["approved"])
        self.assertFalse(sized_buy["vetoed"])
        self.assertEqual(sized_buy["lot_size"], 0.06)
        self.assertEqual(sized_buy["risk_usd"], 72.50)
        self.assertLessEqual(sized_buy["lot_size"], 0.10)
        self.assertLessEqual(sized_buy["risk_usd"], 100.0)

        # Sizing with high base lot: base_lot 0.08 -> 0.08 * 1.45 = 0.116 -> strictly clamped to 0.10 ceiling
        sized_buy_high = self.fusion.scale_position_size("XAUUSD", base_lot=0.08, base_risk_usd=90.0, action="BUY")
        self.assertEqual(sized_buy_high["lot_size"], 0.10)
        self.assertEqual(sized_buy_high["risk_usd"], 100.0)  # 90 * 1.45 = 130.5 -> strictly capped to 100.0

        # 2. SELL Gold (conflict: counter-macro)
        appr_sell, mult_sell, reason_sell = self.fusion.evaluate_trade_confluence("XAUUSD", "SELL")
        self.assertFalse(appr_sell, "SELL Gold MUST be VETOED under DEFCON 2 Bullish Macro")
        self.assertEqual(mult_sell, 0.0)
        self.assertIn("[COUNTER-MACRO VETO]", reason_sell)

        sized_sell = self.fusion.scale_position_size("XAUUSD", base_lot=0.08, base_risk_usd=80.0, action="SELL")
        self.assertFalse(sized_sell["approved"])
        self.assertTrue(sized_sell["vetoed"])
        self.assertEqual(sized_sell["lot_size"], 0.0)
        self.assertEqual(sized_sell["risk_usd"], 0.0)
        self.assertEqual(sized_sell["macro_multiplier"], 0.0)

        # Direct execution in mq3_trading blocks trade
        msg = _execute_direct_trade("XAUUSD", "SELL", lots=0.05)
        self.assertIn("[TRADE BLOCKED]", msg)
        self.assertIn("COUNTER-MACRO VETO", msg)

    def test_07_wti_counter_macro_permutations_defcon2(self):
        """Adversarially verify BUY WTI -> APPROVE (1.50x) and SELL WTI -> VETO (0.0x, lot=0.0)."""
        # 1. BUY WTI (confluence aligns)
        appr, mult, reason = self.fusion.evaluate_trade_confluence("WTI", "BUY")
        self.assertTrue(appr, "BUY WTI must be approved under DEFCON 2 Bullish Macro")
        self.assertEqual(mult, 1.50)
        self.assertIn("[CONFLUENCE]", reason)

        # Sizing: base_lot 0.10 -> 0.10 * 1.50 = 0.15L (below 0.20 ceiling)
        sized_buy = self.fusion.scale_position_size("WTI", base_lot=0.10, base_risk_usd=60.0, action="BUY")
        self.assertTrue(sized_buy["approved"])
        self.assertFalse(sized_buy["vetoed"])
        self.assertEqual(sized_buy["lot_size"], 0.15)
        self.assertEqual(sized_buy["risk_usd"], 90.0)
        self.assertLessEqual(sized_buy["lot_size"], 0.20)

        # Sizing with high base lot: base_lot 0.16 -> 0.16 * 1.50 = 0.24 -> strictly clamped to 0.20 ceiling
        sized_buy_high = self.fusion.scale_position_size("WTI", base_lot=0.16, base_risk_usd=80.0, action="BUY")
        self.assertEqual(sized_buy_high["lot_size"], 0.20)
        self.assertEqual(sized_buy_high["risk_usd"], 100.0)

        # 2. SELL WTI (conflict: counter-macro)
        appr_sell, mult_sell, reason_sell = self.fusion.evaluate_trade_confluence("WTI", "SELL")
        self.assertFalse(appr_sell, "SELL WTI MUST be VETOED under DEFCON 2 Bullish Macro")
        self.assertEqual(mult_sell, 0.0)
        self.assertIn("[COUNTER-MACRO VETO]", reason_sell)

        sized_sell = self.fusion.scale_position_size("WTI", base_lot=0.10, base_risk_usd=60.0, action="SELL")
        self.assertFalse(sized_sell["approved"])
        self.assertTrue(sized_sell["vetoed"])
        self.assertEqual(sized_sell["lot_size"], 0.0)
        self.assertEqual(sized_sell["risk_usd"], 0.0)
        self.assertEqual(sized_sell["macro_multiplier"], 0.0)

        # Direct execution in mq3_trading blocks trade
        msg = _execute_direct_trade("WTI", "SELL", lots=0.10)
        self.assertIn("[TRADE BLOCKED]", msg)
        self.assertIn("COUNTER-MACRO VETO", msg)

    def test_08_multiverse_macro_bias_conflict_matrix(self):
        """Test trade conflict gating across EURUSD, BTCUSD, and neutral symbols."""
        # EURUSD: Macro bias is SELL (0.80x)
        appr_eur_sell, mult_eur_sell, _ = self.fusion.evaluate_trade_confluence("EURUSD", "SELL")
        self.assertTrue(appr_eur_sell)
        self.assertEqual(mult_eur_sell, 0.80)

        appr_eur_buy, mult_eur_buy, reason_eur_buy = self.fusion.evaluate_trade_confluence("EURUSD", "BUY")
        self.assertFalse(appr_eur_buy, "Buying EUR against strong bearish macro during DEFCON 2 must be vetoed")
        self.assertEqual(mult_eur_buy, 0.0)
        self.assertIn("[COUNTER-MACRO VETO]", reason_eur_buy)

        # BTCUSD: Macro bias is BUY (1.20x)
        appr_btc_buy, mult_btc_buy, _ = self.fusion.evaluate_trade_confluence("BTCUSD", "BUY")
        self.assertTrue(appr_btc_buy)
        self.assertEqual(mult_btc_buy, 1.20)
        sized_btc = self.fusion.scale_position_size("BTCUSD", base_lot=0.005, action="BUY")
        self.assertEqual(sized_btc["lot_size"], 0.006)
        self.assertEqual(sized_btc["hard_lot_ceiling"], 0.01)

        appr_btc_sell, mult_btc_sell, reason_btc_sell = self.fusion.evaluate_trade_confluence("BTCUSD", "SELL")
        self.assertFalse(appr_btc_sell, "Selling BTC against strong bullish macro during DEFCON 2 must be vetoed")
        self.assertEqual(mult_btc_sell, 0.0)
        self.assertIn("[COUNTER-MACRO VETO]", reason_btc_sell)

        # Neutral symbol (e.g. AUDCAD)
        appr_aud_buy, mult_aud_buy, reason_aud_buy = self.fusion.evaluate_trade_confluence("AUDCAD", "BUY")
        self.assertTrue(appr_aud_buy)
        self.assertEqual(mult_aud_buy, 1.0)
        self.assertIn("[MACRO NEUTRAL]", reason_aud_buy)

        appr_aud_sell, mult_aud_sell, reason_aud_sell = self.fusion.evaluate_trade_confluence("AUDCAD", "SELL")
        self.assertTrue(appr_aud_sell)
        self.assertEqual(mult_aud_sell, 1.0)
        self.assertIn("[MACRO NEUTRAL]", reason_aud_sell)

    # =========================================================================
    # 4. WINDOWS CP1252 CONSOLE ENCODING SAFETY
    # =========================================================================

    def test_09_windows_cp1252_encoding_safety_all_fusion_outputs(self):
        """Adversarially assert zero UnicodeEncodeError when encoding all fusion outputs into cp1252."""
        symbols = [
            "XAUUSD", "GOLD", "WTI", "USOIL", "BRENT", "CRUDE",
            "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD", "AUDCAD", "NZDCHF"
        ]
        actions = ["BUY", "SELL"]

        for sym in symbols:
            for act in actions:
                # 1. evaluate_trade_confluence
                appr, mult, reason = self.fusion.evaluate_trade_confluence(sym, act)
                try:
                    raw_bytes = reason.encode("cp1252")
                    self.assertIsInstance(raw_bytes, bytes)
                    # Verify no un-substituted unicode escape sequences remain
                    self.assertNotIn(b"\\u2705", raw_bytes)
                    self.assertNotIn(b"\\u26a0", raw_bytes)
                except UnicodeEncodeError as uee:
                    self.fail(f"cp1252 UnicodeEncodeError for confluence({sym}, {act}): {uee}")

                # 2. scale_position_size
                scaled = self.fusion.scale_position_size(sym, base_lot=0.05, base_risk_usd=50.0, action=act)
                try:
                    scaled_json = json.dumps(scaled)
                    raw_json_bytes = scaled_json.encode("cp1252")
                    self.assertIsInstance(raw_json_bytes, bytes)
                except UnicodeEncodeError as uee:
                    self.fail(f"cp1252 UnicodeEncodeError for scale_position_size({sym}, {act}): {uee}")

        # 3. get_geopolitical_macro_snapshot
        snapshot = self.fusion.get_geopolitical_macro_snapshot()
        try:
            snap_json = json.dumps(snapshot)
            raw_snap_bytes = snap_json.encode("cp1252")
            self.assertIsInstance(raw_snap_bytes, bytes)
        except UnicodeEncodeError as uee:
            self.fail(f"cp1252 UnicodeEncodeError for get_geopolitical_macro_snapshot: {uee}")

        # 4. get_chokepoints_telemetry
        telemetry = get_chokepoints_telemetry()
        try:
            tel_json = json.dumps(telemetry)
            raw_tel_bytes = tel_json.encode("cp1252")
            self.assertIsInstance(raw_tel_bytes, bytes)
        except UnicodeEncodeError as uee:
            self.fail(f"cp1252 UnicodeEncodeError for get_chokepoints_telemetry: {uee}")

        # 5. Direct trade blocking messages
        for sym in ["XAUUSD", "WTI", "EURUSD"]:
            blocked_msg = _execute_direct_trade(sym, "SELL" if sym in ["XAUUSD", "WTI"] else "BUY", lots=0.05)
            try:
                blocked_bytes = blocked_msg.encode("cp1252")
                self.assertIsInstance(blocked_bytes, bytes)
            except UnicodeEncodeError as uee:
                self.fail(f"cp1252 UnicodeEncodeError for _execute_direct_trade blocked message ({sym}): {uee}")


if __name__ == "__main__":
    unittest.main()
