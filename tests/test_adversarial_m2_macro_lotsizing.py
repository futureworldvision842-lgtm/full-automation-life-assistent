"""
tests/test_adversarial_m2_macro_lotsizing.py — Adversarial Empirical Stress Test Suite for Milestone M2.
========================================================================================================
Adversarially stress-tests Macro Multipliers & Lot Sizing Integration:
1. scale_position_size() in core/geopolitical_trading_fusion.py across:
   - Gold (XAUUSD): base lots from 0.01 to 5.0, equity $1,000 to $1,000,000.
     Assert returned lot size NEVER exceeds 0.10L and dollar risk NEVER exceeds $100.00
     under any condition (including 1.45x DEFCON 2 boost).
   - Forex (EURUSD, GBPUSD): base lots up to 1.0.
     Assert returned lot size NEVER exceeds 0.20L and dollar risk NEVER exceeds $100.00.
   - Crypto (BTCUSD, ETHUSD, SOLUSD): base lots up to 1.0.
     Assert returned lot size NEVER exceeds 0.01L and dollar risk NEVER exceeds $100.00.
2. Crude Oil (WTI) macro multiplier:
   - Verify 1.50x multiplier at DEFCON 2, 1.35x at DEFCON 3.
   - Verify embedded $8.50/bbl structural risk premium.
3. actions/mq3_trading.py execution wiring:
   - Direct trade execution actually submits orders with scaled lot size.
   - Counter-macro vetoes are strictly enforced (zero orders placed).
4. Windows cp1252 console encoding resilience across all assets.
5. Empirical Vulnerability Reproduction:
   - Lowercase symbol 'c' replacement defect in core/geopolitical_trading_fusion.py.
"""

import math
import random
import sys
import unittest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = ROOT / "MQ3 TRADING BOT"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

from core.geopolitical_trading_fusion import geopolitical_fusion, GeopoliticalTradingFusion
from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine
from actions.mq3_trading import _execute_direct_trade, mq3_trading


class TestAdversarialMacroLotSizing(unittest.TestCase):
    """Rigorous empirical stress test suite for M2 Macro Multipliers and Lot Sizing."""

    def setUp(self):
        self.fusion = geopolitical_fusion
        self.fusion._cache = None
        self.fusion._cache_time = 0.0
        self.engine = WorldMonitorIntelligenceEngine()

    def tearDown(self):
        self.fusion._cache = None
        self.fusion._cache_time = 0.0

    # =========================================================================
    # 1. GOLD (XAUUSD) LOT SIZING & DOLLAR RISK STRESS TEST
    # =========================================================================

    def test_01_gold_xauusd_lot_ceiling_and_dollar_risk_caps(self):
        """
        Gold (XAUUSD):
        - Base lots from 0.01 to 5.0 (discrete and Monte Carlo).
        - Equity from $1,000 to $1,000,000.
        - Dollar risk strictly capped at $100.00 max under all conditions (including 1.45x boost).
        - Returned lot size strictly <= 0.10L.
        """
        discrete_lots = [0.01, 0.02, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.12, 0.15, 0.20, 0.50, 1.0, 2.0, 5.0]
        equities = [1000.0, 2500.0, 5000.0, 10000.0, 25000.0, 50000.0, 100000.0, 250000.0, 500000.0, 1000000.0]
        risk_pcts = [0.0025, 0.005, 0.0075, 0.01, 0.02]

        # 1. Systematic Matrix Testing
        for eq in equities:
            for r_pct in risk_pcts:
                calc_risk_usd = eq * r_pct
                for base_lot in discrete_lots:
                    res = self.fusion.scale_position_size(
                        symbol="XAUUSD",
                        base_lot=base_lot,
                        base_risk_usd=calc_risk_usd,
                        action="BUY"
                    )
                    self.assertTrue(res["approved"], f"BUY Gold should be approved at DEFCON 2 for lot {base_lot}")
                    self.assertFalse(res["vetoed"])
                    self.assertEqual(res["asset_class"], "GOLD")
                    self.assertEqual(res["hard_lot_ceiling"], 0.10)
                    self.assertEqual(res["max_risk_usd_cap"], 100.0)

                    # Hard assertions
                    self.assertLessEqual(
                        res["lot_size"], 0.10,
                        f"Gold lot size {res['lot_size']} exceeded hard ceiling 0.10 for base_lot {base_lot}"
                    )
                    self.assertGreaterEqual(
                        res["lot_size"], 0.01,
                        f"Gold lot size {res['lot_size']} below min lot 0.01 for base_lot {base_lot}"
                    )
                    self.assertLessEqual(
                        res["risk_usd"], 100.00,
                        f"Gold dollar risk ${res['risk_usd']} exceeded cap $100.00 for eq ${eq}, risk ${calc_risk_usd}"
                    )

        # 2. Monte Carlo Randomized Invariance (5,000 random trials)
        random.seed(1337)
        for _ in range(5000):
            rnd_lot = random.uniform(0.01, 5.0)
            rnd_equity = random.uniform(1000.0, 1000000.0)
            rnd_risk_pct = random.uniform(0.001, 0.05)
            base_risk = rnd_equity * rnd_risk_pct

            res = self.fusion.scale_position_size(
                symbol="XAUUSD",
                base_lot=rnd_lot,
                base_risk_usd=base_risk,
                action="BUY"
            )
            self.assertLessEqual(res["lot_size"], 0.10)
            self.assertGreaterEqual(res["lot_size"], 0.01)
            self.assertLessEqual(res["risk_usd"], 100.00)

    # =========================================================================
    # 2. FOREX (EURUSD, GBPUSD) LOT SIZING & DOLLAR RISK STRESS TEST
    # =========================================================================

    def test_02_forex_lot_ceiling_and_dollar_risk_caps(self):
        """
        Forex (EURUSD, GBPUSD):
        - Base lots up to 1.0.
        - Assert returned lot size NEVER exceeds 0.20L.
        - Assert dollar risk NEVER exceeds $100.00.
        """
        forex_symbols = ["EURUSD", "GBPUSD"]
        discrete_lots = [0.01, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.50, 0.75, 1.0]

        for sym in forex_symbols:
            # For EURUSD, macro bias is SELL; for GBPUSD, macro is NEUTRAL
            action = "SELL" if sym == "EURUSD" else "BUY"
            for base_lot in discrete_lots:
                for base_risk in [10.0, 25.0, 50.0, 80.0, 100.0, 150.0, 250.0, 500.0]:
                    res = self.fusion.scale_position_size(
                        symbol=sym,
                        base_lot=base_lot,
                        base_risk_usd=base_risk,
                        action=action
                    )
                    self.assertTrue(res["approved"])
                    self.assertEqual(res["asset_class"], "FOREX")
                    self.assertEqual(res["hard_lot_ceiling"], 0.20)
                    self.assertEqual(res["max_risk_usd_cap"], 100.0)

                    self.assertLessEqual(
                        res["lot_size"], 0.20,
                        f"{sym} lot {res['lot_size']} exceeded ceiling 0.20 for base_lot {base_lot}"
                    )
                    self.assertGreaterEqual(
                        res["lot_size"], 0.01,
                        f"{sym} lot {res['lot_size']} below min lot 0.01 for base_lot {base_lot}"
                    )
                    self.assertLessEqual(
                        res["risk_usd"], 100.00,
                        f"{sym} dollar risk ${res['risk_usd']} exceeded cap $100.00"
                    )

        # Monte Carlo (3,000 trials)
        random.seed(4242)
        for _ in range(3000):
            sym = random.choice(forex_symbols)
            action = "SELL" if sym == "EURUSD" else random.choice(["BUY", "SELL"])
            rnd_lot = random.uniform(0.01, 1.0)
            rnd_risk = random.uniform(1.0, 1000.0)
            res = self.fusion.scale_position_size(sym, rnd_lot, rnd_risk, action=action)
            if res["approved"]:
                self.assertLessEqual(res["lot_size"], 0.20)
                self.assertGreaterEqual(res["lot_size"], 0.01)
                self.assertLessEqual(res["risk_usd"], 100.00)

    # =========================================================================
    # 3. CRYPTO (BTCUSD, ETHUSD, SOLUSD) LOT SIZING & DOLLAR RISK STRESS TEST
    # =========================================================================

    def test_03_crypto_lot_ceiling_and_dollar_risk_caps(self):
        """
        Crypto (BTCUSD, ETHUSD, SOLUSD):
        - Base lots up to 1.0.
        - Assert returned lot size NEVER exceeds 0.01L.
        - Assert dollar risk NEVER exceeds $100.00.
        """
        crypto_symbols = ["BTCUSD", "ETHUSD", "SOLUSD"]
        discrete_lots = [0.001, 0.002, 0.005, 0.008, 0.01, 0.02, 0.05, 0.10, 0.50, 1.0]

        for sym in crypto_symbols:
            for base_lot in discrete_lots:
                for base_risk in [10.0, 50.0, 100.0, 200.0, 500.0]:
                    res = self.fusion.scale_position_size(
                        symbol=sym,
                        base_lot=base_lot,
                        base_risk_usd=base_risk,
                        action="BUY"
                    )
                    self.assertTrue(res["approved"])
                    self.assertEqual(res["asset_class"], "CRYPTO")
                    self.assertEqual(res["hard_lot_ceiling"], 0.01)
                    self.assertEqual(res["max_risk_usd_cap"], 100.0)

                    self.assertLessEqual(
                        res["lot_size"], 0.01,
                        f"{sym} lot {res['lot_size']} exceeded ceiling 0.01 for base_lot {base_lot}"
                    )
                    self.assertGreaterEqual(
                        res["lot_size"], 0.001,
                        f"{sym} lot {res['lot_size']} below min lot 0.001 for base_lot {base_lot}"
                    )
                    self.assertLessEqual(
                        res["risk_usd"], 100.00,
                        f"{sym} dollar risk ${res['risk_usd']} exceeded cap $100.00"
                    )

        # Monte Carlo (3,000 trials)
        random.seed(8888)
        for _ in range(3000):
            sym = random.choice(crypto_symbols)
            rnd_lot = random.uniform(0.001, 1.0)
            rnd_risk = random.uniform(1.0, 1000.0)
            res = self.fusion.scale_position_size(sym, rnd_lot, rnd_risk, action="BUY")
            if res["approved"]:
                self.assertLessEqual(res["lot_size"], 0.01)
                self.assertGreaterEqual(res["lot_size"], 0.001)
                self.assertLessEqual(res["risk_usd"], 100.00)

    # =========================================================================
    # 4. CRUDE OIL (WTI) MACRO MULTIPLIERS & STRUCTURAL RISK PREMIUM
    # =========================================================================

    def test_04_wti_crude_oil_multipliers_and_structural_risk_premium(self):
        """
        Crude Oil (WTI):
        - Verify 1.50x multiplier at DEFCON 2.
        - Verify 1.35x multiplier at DEFCON 3.
        - Verify embedded $8.50/bbl structural risk premium.
        """
        # Test 1: Intelligence Engine at DEFCON 2
        orig_defcon = self.engine.defcon_level
        try:
            self.engine.defcon_level = 2
            bias_defcon2 = self.engine.evaluate_geopolitical_market_bias("WTI")
            self.assertEqual(bias_defcon2["macro_multiplier"], 1.50)
            self.assertEqual(bias_defcon2["confluence_boost"], 0.45)
            self.assertEqual(bias_defcon2["bias"], "STRONG_BUY")
            self.assertEqual(bias_defcon2.get("oil_geopolitical_risk_premium_usd"), 8.50)
            self.assertEqual(bias_defcon2.get("structural_risk_premium"), 8.50)
            self.assertIn("$8.50/bbl", bias_defcon2["reasoning"])

            # Test 2: Intelligence Engine at DEFCON 3
            self.engine.defcon_level = 3
            bias_defcon3 = self.engine.evaluate_geopolitical_market_bias("WTI")
            self.assertEqual(bias_defcon3["macro_multiplier"], 1.35)
            self.assertEqual(bias_defcon3["confluence_boost"], 0.45)
            self.assertEqual(bias_defcon3["bias"], "STRONG_BUY")
            self.assertEqual(bias_defcon3.get("oil_geopolitical_risk_premium_usd"), 8.50)
            self.assertEqual(bias_defcon3.get("structural_risk_premium"), 8.50)
            self.assertIn("$8.50/bbl", bias_defcon3["reasoning"])
        finally:
            self.engine.defcon_level = orig_defcon

        # Test 3: Macro Snapshot from GeopoliticalTradingFusion
        self.fusion._cache = None
        snap = self.fusion.get_geopolitical_macro_snapshot()
        self.assertEqual(snap["wti_macro_multiplier"], 1.50)
        self.assertEqual(snap["oil_macro_multiplier"], 1.50)
        self.assertEqual(snap["oil_risk_premium_usd"], 8.50)
        self.assertIn("WTI", snap["macro_bias"])
        wti_info = snap["macro_bias"]["WTI"]
        self.assertEqual(wti_info["macro_multiplier"], 1.50)
        self.assertEqual(wti_info.get("oil_geopolitical_risk_premium_usd", 8.50), 8.50)

    # =========================================================================
    # 5. EXECUTION WIRING IN actions/mq3_trading.py: SCALED LOT SUBMISSION
    # =========================================================================

    def test_05_mq3_trading_submits_scaled_lot_size(self):
        """
        Verify that in actions/mq3_trading.py, direct trade execution actually
        submits orders with the scaled lot size to conn.place_order().
        """
        from actions import mq3_trading

        # Case 1: Gold BUY with base lot 0.05
        # 0.05 * 1.45 = 0.0725 -> scaled to 0.07L
        mock_conn = MagicMock()
        mock_conn.get_symbol_tick.return_value = {"ask": 4298.50, "bid": 4298.00}
        mock_conn.get_historical_candles.return_value = None
        mock_conn.place_order.return_value = {"success": True, "ticket": 777001, "mode": "PAPER"}

        with patch.object(mq3_trading, "_get_mt5_connector", return_value=mock_conn):
            result = mq3_trading.mq3_trading({"action": "buy", "symbol": "XAUUSD", "lots": 0.05})
            self.assertIn("[TRADE EXECUTED]", result)
            self.assertIn("0.07L", result)
            self.assertIn("Ticket: #777001", result)

            # Verify arguments passed to conn.place_order
            mock_conn.place_order.assert_called_once()
            args, kwargs = mock_conn.place_order.call_args
            placed_sym = args[0]
            placed_type = args[1]
            placed_vol = args[2]

            self.assertEqual(placed_sym, "XAUUSD")
            self.assertEqual(placed_type, "BUY")
            self.assertEqual(placed_vol, 0.07, f"Expected 0.07 scaled lots, got {placed_vol}")

        # Case 2: Gold BUY with base lot 0.50 (well above 0.10 ceiling)
        # Scaled lot must be strictly clamped to 0.10L
        mock_conn.reset_mock()
        with patch.object(mq3_trading, "_get_mt5_connector", return_value=mock_conn):
            result = mq3_trading.mq3_trading({"action": "buy", "symbol": "XAUUSD", "lots": 0.50})
            self.assertIn("[TRADE EXECUTED]", result)
            self.assertIn("0.10L", result)

            mock_conn.place_order.assert_called_once()
            args, _ = mock_conn.place_order.call_args
            placed_vol = args[2]
            self.assertEqual(placed_vol, 0.10, f"Expected 0.10 clamped lots, got {placed_vol}")

        # Case 3: Forex BUY with base lot 0.50
        # Clamped to 0.20L
        mock_conn.reset_mock()
        mock_conn.get_symbol_tick.return_value = {"ask": 1.2500, "bid": 1.2498}
        with patch.object(mq3_trading, "_get_mt5_connector", return_value=mock_conn):
            result = mq3_trading.mq3_trading({"action": "buy", "symbol": "GBPUSD", "lots": 0.50})
            self.assertIn("[TRADE EXECUTED]", result)
            self.assertIn("0.20L", result)

            mock_conn.place_order.assert_called_once()
            args, _ = mock_conn.place_order.call_args
            self.assertEqual(args[2], 0.20)

        # Case 4: Crypto BUY with base lot 0.05
        # Clamped to 0.01L
        mock_conn.reset_mock()
        mock_conn.get_symbol_tick.return_value = {"ask": 65000.0, "bid": 64995.0}
        with patch.object(mq3_trading, "_get_mt5_connector", return_value=mock_conn):
            result = mq3_trading.mq3_trading({"action": "buy", "symbol": "BTCUSD", "lots": 0.05})
            self.assertIn("[TRADE EXECUTED]", result)
            self.assertIn("0.01L", result)

            mock_conn.place_order.assert_called_once()
            args, _ = mock_conn.place_order.call_args
            self.assertEqual(args[2], 0.01)

    # =========================================================================
    # 6. EXECUTION WIRING IN actions/mq3_trading.py: MACRO VETO ENFORCEMENT
    # =========================================================================

    def test_06_mq3_trading_enforces_counter_macro_vetoes(self):
        """
        Verify that counter-macro trade setups (e.g. SELL Gold or SELL Oil during DEFCON 2)
        are blocked immediately and NEVER submit orders to conn.place_order().
        """
        from actions import mq3_trading

        mock_conn = MagicMock()

        # Case 1: Selling Gold during DEFCON 2
        with patch.object(mq3_trading, "_get_mt5_connector", return_value=mock_conn):
            result = mq3_trading.mq3_trading({"action": "sell", "symbol": "XAUUSD", "lots": 0.05})
            self.assertIn("[TRADE BLOCKED]", result)
            self.assertIn("COUNTER-MACRO VETO", result)
            mock_conn.place_order.assert_not_called()

        # Case 2: Direct call to _execute_direct_trade for Gold SELL
        mock_conn.reset_mock()
        with patch.object(mq3_trading, "_get_mt5_connector", return_value=mock_conn):
            result = _execute_direct_trade("XAUUSD", "SELL", lots=0.08)
            self.assertIn("[TRADE BLOCKED]", result)
            self.assertIn("COUNTER-MACRO VETO", result)
            mock_conn.place_order.assert_not_called()

        # Case 3: Selling WTI Crude Oil during DEFCON 2
        mock_conn.reset_mock()
        with patch.object(mq3_trading, "_get_mt5_connector", return_value=mock_conn):
            result = mq3_trading.mq3_trading({"action": "sell", "symbol": "WTI", "lots": 0.05})
            self.assertIn("[TRADE BLOCKED]", result)
            self.assertIn("COUNTER-MACRO VETO", result)
            mock_conn.place_order.assert_not_called()

        # Case 4: Buying EURUSD during DEFCON 2 (where macro bias is SELL)
        mock_conn.reset_mock()
        with patch.object(mq3_trading, "_get_mt5_connector", return_value=mock_conn):
            result = mq3_trading.mq3_trading({"action": "buy", "symbol": "EURUSD", "lots": 0.05})
            self.assertIn("[TRADE BLOCKED]", result)
            self.assertIn("COUNTER-MACRO VETO", result)
            mock_conn.place_order.assert_not_called()

    # =========================================================================
    # 7. WINDOWS CP1252 CONSOLE COMPLIANCE STRESS TEST
    # =========================================================================

    def test_07_windows_cp1252_encoding_resilience(self):
        """
        Verifies that every string returned across all assets and actions can be
        encoded into Windows cp1252 without UnicodeEncodeError.
        """
        symbols = ["XAUUSD", "WTI", "EURUSD", "BTCUSD", "GBPUSD", "USDJPY", "ETHUSD", "SOLUSD"]
        actions = ["BUY", "SELL"]

        for sym in symbols:
            for act in actions:
                appr, mult, reason = self.fusion.evaluate_trade_confluence(sym, act)
                try:
                    reason.encode("cp1252")
                except UnicodeEncodeError as uee:
                    self.fail(f"UnicodeEncodeError in reason for {sym} {act}: {uee}")

                res_scaled = self.fusion.scale_position_size(sym, base_lot=0.05, action=act)
                try:
                    res_scaled["reason"].encode("cp1252")
                except UnicodeEncodeError as uee:
                    self.fail(f"UnicodeEncodeError in scale_position_size reason for {sym} {act}: {uee}")

    # =========================================================================
    # 8. ADVERSARIAL VERIFICATION: LOWERCASE & SUFFIX STRIPPING COMPLIANCE
    # =========================================================================

    def test_08_adversarial_reproduction_symbol_c_stripping_vulnerability(self):
        """
        Adversarially probes symbol cleaning in core/geopolitical_trading_fusion.py:
        Verifies resolution of lowercase 'c' stripping bug via .upper().removesuffix('M').removesuffix('C'):
        1. 'btcusd' preserves 'BTC', classified as 'CRYPTO', hard ceiling 0.01L strictly enforced.
        2. 'crude' SELL correctly identifies commodity bias and enforces DEFCON 2 [COUNTER-MACRO VETO].
        3. All lowercase and broker suffix variants adhere strictly to capital preservation rules.
        """
        # Case A: Crypto lot sizing compliance on lowercase 'btcusd'
        res_btc_lower = self.fusion.scale_position_size("btcusd", base_lot=0.50, action="BUY")
        self.assertEqual(res_btc_lower["asset_class"], "CRYPTO")
        self.assertEqual(res_btc_lower["hard_lot_ceiling"], 0.01)
        self.assertEqual(res_btc_lower["lot_size"], 0.01)
        self.assertLessEqual(res_btc_lower["lot_size"], 0.01)
        self.assertLessEqual(res_btc_lower["risk_usd"], 100.0)

        # Case B: Counter-macro veto compliance on lowercase 'crude'
        res_crude_sell = self.fusion.evaluate_trade_confluence("crude", "SELL")
        self.assertFalse(res_crude_sell[0])
        self.assertEqual(res_crude_sell[1], 0.0)
        self.assertIn("COUNTER-MACRO VETO", res_crude_sell[2])

        # Case C: Comprehensive variations of lowercase and broker suffixes
        crypto_cases = ["btcusd", "btcusdm", "btcusdc", "BTCUSDm", "BTCUSDc", "ethusd", "solusd"]
        for sym in crypto_cases:
            res = self.fusion.scale_position_size(sym, base_lot=0.50, action="BUY")
            self.assertTrue(res["approved"], f"{sym} should be approved for BUY")
            self.assertEqual(res["asset_class"], "CRYPTO", f"{sym} must be classified as CRYPTO")
            self.assertEqual(res["hard_lot_ceiling"], 0.01, f"{sym} ceiling must be 0.01L")
            self.assertEqual(res["lot_size"], 0.01, f"{sym} lot size must be strictly clamped to 0.01L")

        commodity_cases = ["crude", "crudem", "CRUDE", "wti", "wtic", "usoil", "brent"]
        for sym in commodity_cases:
            appr, mult, reason = self.fusion.evaluate_trade_confluence(sym, "SELL")
            self.assertFalse(appr, f"{sym} SELL must be vetoed under DEFCON 2")
            self.assertEqual(mult, 0.0)
            self.assertIn("COUNTER-MACRO VETO", reason)


if __name__ == "__main__":
    unittest.main()
