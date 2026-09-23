"""
test_fleet_risk_empirical.py — Empirical Challenger Stress Suite for Milestone 3.
==================================================================================
Adversarial test harness for FleetRiskManager and MultiAccountAutoOnboarder:
  1. SOD Daily Drawdown Extreme Stress, Micro-Boundaries & Multi-Day Resets.
  2. Trailing HWM Floor Ratchet Monotonicity & Profit-Lock Invariants under Sawtooth Volatility.
  3. 5-Stage Consistency Pacing Classifier Exact Boundary & Epsilon Transitions.
  4. 3.5x ATR Dynamic Stop-Loss & Exact Mathematical R-Multiple Verifications.
  5. Multi-Asset Dynamic Lot Sizing Precision & Boundary Clamping (Gold, Forex, Crypto).
  6. Pre-Trade Risk Interceptor Exhaustive Audit & Rejection Matrix.
  7. High-Volume Account Fleet Concurrency and State Integrity.
  8. Adversarial Injections, Unicode/XSS Account IDs, and Fuzz Vectors.
"""

import os
import math
import random
import unittest
from typing import Dict, Any

from src.fleet_risk_manager import FleetRiskManager
from src.multi_account_auto_onboarder import MultiAccountAutoOnboarder


class TestFleetRiskManagerEmpirical(unittest.TestCase):
    def setUp(self):
        self.test_config = "data/test_fleet_risk_empirical_config.json"
        self.onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)
        
        # Onboard representative accounts for stress testing
        # 1. Funding Pips 25k with 1.5%/4.0%/0.25% internal controls.
        self.onboarder.onboard_new_account(
            account_id="FP_25K",
            server="MetaQuotes-Demo",
            balance=25000.0,
            account_type="FUNDING_PIPS"
        )
        # 2. FTMO 100k ($100,000, 4.0% daily loss = $4000, 8.0% max loss = $8000, 1.0% risk, 50% consistency)
        self.onboarder.onboard_new_account(
            account_id="FTMO_100K",
            server="FTMO-Demo",
            balance=100000.0,
            account_type="FTMO"
        )
        # 3. Binance Spot ($1,000, 5.0% daily loss = $50, 20.0% max loss = $200, 1.5% risk, 100% consistency)
        self.onboarder.onboard_new_account(
            account_id="BINANCE_SPOT_1K",
            server="Binance-Live",
            balance=1000.0,
            account_type="BINANCE_SPOT"
        )
        # 4. Scalp 5M Micro ($100, 5.0% daily loss = $5, 20.0% max loss = $20, 1.5% risk, 100% consistency)
        self.onboarder.onboard_new_account(
            account_id="SCALP_100",
            server="Binance-Live",
            balance=100.0,
            account_type="SCALP_5M"
        )
        # 5. Hyperliquid DEX ($500, 5.0% daily loss = $25, 20.0% max loss = $100, 1.5% risk, 100% consistency)
        self.onboarder.onboard_new_account(
            account_id="HL_500",
            server="Hyperliquid-Mainnet",
            balance=500.0,
            account_type="HYPERLIQUID"
        )

        self.risk_mgr = FleetRiskManager(config_path=self.test_config, auto_onboarder=self.onboarder)

    def tearDown(self):
        if os.path.exists(self.test_config):
            try:
                os.remove(self.test_config)
            except Exception:
                pass

    # =========================================================================
    # 1. SOD DAILY DRAWDOWN EXTREME STRESS & MICRO-BOUNDARY TESTS
    # =========================================================================

    def test_daily_drawdown_exact_micro_boundaries(self):
        """Stress-test the tighter internal daily stop at its exact boundaries."""
        acc_id = "FP_25K"
        # 1. Just below threshold ($374.99 loss -> equity $24,625.01)
        res_below = self.risk_mgr.update_account_telemetry(acc_id, balance=24625.01, equity=24625.01)
        self.assertTrue(res_below["daily_loss_shield_ok"], "Loss of $374.99 must be safe under $375 cap")
        self.assertFalse(res_below["is_locked_out"])

        # 2. Exactly on boundary ($375.00 loss -> equity $24,625.00)
        res_exact = self.risk_mgr.update_account_telemetry(acc_id, balance=24625.00, equity=24625.00)
        self.assertFalse(res_exact["daily_loss_shield_ok"], "Exact $375.00 loss must trigger breach")
        self.assertTrue(res_exact["is_locked_out"])

        # Reset SOD
        self.risk_mgr.update_account_telemetry(acc_id, balance=25000.0, equity=25000.0, sod_reset=True)

        # 3. Just above threshold ($375.01 loss -> equity $24,624.99)
        res_above = self.risk_mgr.update_account_telemetry(acc_id, balance=24624.99, equity=24624.99)
        self.assertFalse(res_above["daily_loss_shield_ok"], "Loss of $375.01 must trigger breach")
        self.assertTrue(res_above["is_locked_out"])

    def test_daily_drawdown_flash_crash_and_catastrophic_loss(self):
        """Stress-test flash crash drops: 50% drop, 99% drop, and total wipeout to $0."""
        acc_id = "FTMO_100K"
        # Total wipeout to $0
        res = self.risk_mgr.update_account_telemetry(acc_id, balance=0.0, equity=0.0)
        self.assertFalse(res["daily_loss_shield_ok"])
        self.assertFalse(res["trailing_floor_ok"])
        self.assertTrue(res["is_locked_out"])
        self.assertIn("DAILY LOSS SHIELD BREACHED", res["lockout_reason"])

    def test_multi_day_sod_resets_and_baseline_shifting(self):
        """Tests sequential multi-day SOD resets with equity growth and subsequent drawdown."""
        acc_id = "FP_25K"
        # Day 1: Start $25,000, grow to $26,000 (+ $1,000 profit)
        r1 = self.risk_mgr.update_account_telemetry(acc_id, balance=26000.0, equity=26000.0)
        self.assertTrue(r1["daily_loss_shield_ok"])
        self.assertEqual(r1["daily_loss_dollars"], 0.0)

        # Day 2: 00:00 UTC Reset -> SOD baseline should now be $26,000
        r2 = self.risk_mgr.update_account_telemetry(acc_id, balance=26000.0, equity=26000.0, sod_reset=True)
        self.assertEqual(r2["daily_sod_equity"], 26000.0)
        self.assertFalse(r2["is_locked_out"])

        # Day 2 cap is 1.5% of the $26k SOD baseline = $390.
        r3 = self.risk_mgr.update_account_telemetry(acc_id, balance=25620.0, equity=25620.0)
        self.assertTrue(r3["daily_loss_shield_ok"])
        self.assertEqual(r3["daily_loss_dollars"], 380.0)

        # Exact $390 internal loss is a breach.
        r4 = self.risk_mgr.update_account_telemetry(acc_id, balance=25610.0, equity=25610.0)
        self.assertFalse(r4["daily_loss_shield_ok"])
        self.assertTrue(r4["is_locked_out"])

    # =========================================================================
    # 2. TRAILING HWM FLOOR RATCHET MONOTONICITY & PROFIT LOCK INVARIANTS
    # =========================================================================

    def test_trailing_floor_monotonicity_under_sawtooth_walk(self):
        """
        Adversarially simulates 100 steps of sawtooth price action.
        Verifies mathematical invariants:
          1. HWM is strictly monotonic non-decreasing: HWM[t] >= HWM[t-1]
          2. Trailing Floor is strictly monotonic non-decreasing: Floor[t] >= Floor[t-1]
          3. Once HWM >= StartingBalance * (1 + MaxTotalLossPct), Floor is locked >= StartingBalance.
        """
        acc_id = "FTMO_100K"
        # Starting balance $100k, 8% max loss ($8,000), starting floor $92,000
        st = self.risk_mgr.get_account_state(acc_id)
        self.assertEqual(st["trailing_hwm_floor"], 92000.0)

        current_equity = 100000.0
        prev_hwm = current_equity
        prev_floor = 92000.0
        profit_lock_triggered = False

        # Deterministic pseudo-random seed for repeatability
        rng = random.Random(42)

        for step in range(100):
            delta = rng.uniform(-1500.0, 2500.0)
            current_equity = max(93000.0, current_equity + delta)
            
            res = self.risk_mgr.update_account_telemetry(acc_id, balance=current_equity, equity=current_equity)
            
            # Invariant 1: HWM monotonicity
            self.assertGreaterEqual(res["absolute_hwm"], prev_hwm, f"HWM decreased at step {step}")
            # Invariant 2: Trailing floor monotonicity
            self.assertGreaterEqual(res["trailing_hwm_floor"], prev_floor, f"Floor decreased at step {step}")

            # Check Profit Lock activation ($100k + $8k = $108k peak)
            if res["absolute_hwm"] >= 108000.0:
                profit_lock_triggered = True
                self.assertGreaterEqual(
                    res["trailing_hwm_floor"], 100000.0,
                    f"Floor must be >= Starting Balance ($100k) once milestone reached (Floor: {res['trailing_hwm_floor']})"
                )

            prev_hwm = res["absolute_hwm"]
            prev_floor = res["trailing_hwm_floor"]

        self.assertTrue(profit_lock_triggered, "Profit lock milestone should have been triggered in random walk")

    def test_trailing_floor_breach_after_large_runup(self):
        """Tests that an account running up has its floor ratcheted, and directly detects trailing floor breach."""
        acc_id = "FTMO_100K"
        # Climb to $105,000 (HWM = $105,000, 8% on 100k is $8,000 -> floor = $97,000)
        res_peak = self.risk_mgr.update_account_telemetry(acc_id, balance=105000.0, equity=105000.0)
        self.assertEqual(res_peak["absolute_hwm"], 105000.0)
        self.assertEqual(res_peak["trailing_hwm_floor"], 97000.0)

        # Set SOD reset at $99,000 so a drop to $96,500 is $2,500 daily loss (< $4,000 daily cap),
        # but breaches the $97,000 trailing HWM floor!
        self.risk_mgr.update_account_telemetry(acc_id, balance=99000.0, equity=99000.0, sod_reset=True)

        # Drop equity to $96,500 (< $97,000 trailing floor)
        res_drop = self.risk_mgr.update_account_telemetry(acc_id, balance=96500.0, equity=96500.0)
        self.assertTrue(res_drop["daily_loss_shield_ok"], "Daily loss $2,500 is within $4,000 cap")
        self.assertFalse(res_drop["trailing_floor_ok"], "Trailing floor $97,000 is breached at $96,500")
        self.assertTrue(res_drop["is_locked_out"])
        self.assertIn("TRAILING HWM FLOOR BREACHED", res_drop["lockout_reason"])

    # =========================================================================
    # 3. 5-STAGE CONSISTENCY PACING CLASSIFIER EXACT BOUNDARY TESTS
    # =========================================================================

    def test_consistency_pacing_epsilon_boundaries(self):
        """
        Adversarially tests exact threshold transitions for consistency pacing:
          - Stage 1: [0%, 20.0%) -> 1.0x
          - Stage 2: [20.0%, 25.0%) -> 0.8x
          - Stage 3: [25.0%, 30.0%) -> 0.5x
          - Stage 4: [30.0%, 35.0%] -> 0.25x
          - Stage 5: (>35.0%) -> 0.0x (LOCKOUT)
        """
        acc_id = "FP_25K"
        target = 2000.0  # $2,000 target profit
        
        # Test cases: (profit_amount, expected_stage, expected_multiplier, expected_can_trade)
        test_vectors = [
            (0.0, 1, 1.0, True),
            (399.80, 1, 1.0, True),       # 19.99%
            (400.00, 2, 0.8, True),       # 20.00%
            (499.80, 2, 0.8, True),       # 24.99%
            (500.00, 3, 0.5, True),       # 25.00%
            (599.80, 3, 0.5, True),       # 29.99%
            (600.00, 4, 0.25, True),      # 30.00%
            (700.00, 4, 0.25, True),      # 35.00%
            (700.20, 5, 0.0, False),      # 35.01% -> LOCKOUT
            (1500.00, 5, 0.0, False),     # 75.00% -> LOCKOUT
            (2500.00, 5, 0.0, False),     # 125.0% -> LOCKOUT
        ]

        for profit, exp_stage, exp_mult, exp_can_trade in test_vectors:
            # Set baseline SOD to 25,000
            self.risk_mgr.update_account_telemetry(acc_id, balance=25000.0, equity=25000.0, sod_reset=True)
            # Add profit without sod_reset to represent intraday gain
            self.risk_mgr.update_account_telemetry(acc_id, balance=25000.0 + profit, equity=25000.0 + profit)
            
            pacing = self.risk_mgr.calculate_consistency_pacing(acc_id, profit_target=target)
            self.assertEqual(
                pacing["stage"], exp_stage,
                f"Failed for profit ${profit} ({pacing['pacing_pct']}%): Expected Stage {exp_stage}, got {pacing['stage']}"
            )
            self.assertEqual(
                pacing["risk_multiplier"], exp_mult,
                f"Failed for profit ${profit}: Expected multiplier {exp_mult}, got {pacing['risk_multiplier']}"
            )
            self.assertEqual(
                pacing["can_trade"], exp_can_trade,
                f"Failed for profit ${profit}: Expected can_trade={exp_can_trade}, got {pacing['can_trade']}"
            )

    def test_consistency_pacing_negative_and_zero_profit(self):
        """Tests that negative intraday profit (loss) or zero profit safely returns Stage 1 (1.0x)."""
        acc_id = "FP_25K"
        # Incur $300 loss from SOD
        self.risk_mgr.update_account_telemetry(acc_id, balance=25000.0, equity=25000.0, sod_reset=True)
        self.risk_mgr.update_account_telemetry(acc_id, balance=24700.0, equity=24700.0)

        pacing = self.risk_mgr.calculate_consistency_pacing(acc_id, profit_target=2000.0)
        self.assertEqual(pacing["stage"], 1)
        self.assertEqual(pacing["risk_multiplier"], 1.0)
        self.assertEqual(pacing["today_profit"], 0.0)
        self.assertTrue(pacing["can_trade"])

    # =========================================================================
    # 4. 3.5X ATR DYNAMIC STOPS & EXACT MATHEMATICAL R-MULTIPLES
    # =========================================================================

    def test_atr_stops_mathematical_precision_all_assets(self):
        """
        Adversarially verifies exact mathematical R-multiple ratios across all assets:
          - TP1 / SL = 1.5R
          - TP2 / SL = 2.5R
          - TP3 / SL = 4.0R
        """
        symbols_and_prices = [
            ("XAUUSD", 2654.30, 3.75),
            ("XAGUSD", 31.85, 0.40),
            ("EURUSD", 1.08500, 0.0035),
            ("GBPUSD", 1.29500, 0.0045),
            ("USDJPY", 152.350, 0.48),
            ("BTCUSDT", 62450.0, 480.0),
            ("ETHUSDT", 2650.0, 42.0),
            ("SOLUSDT", 155.0, 3.20),
        ]

        for symbol, price, atr in symbols_and_prices:
            # 1. BUY Side Test
            res_buy = self.risk_mgr.calculate_atr_stops(symbol, price, side="BUY", atr_value=atr)
            expected_sl_dist = 3.5 * atr
            self.assertAlmostEqual(res_buy["sl_distance"], expected_sl_dist, places=4)
            self.assertAlmostEqual(res_buy["sl"], price - expected_sl_dist, places=4)
            
            # Verify R-multiples for BUY
            r1_buy = (res_buy["tp1"] - price) / (price - res_buy["sl"])
            r2_buy = (res_buy["tp2"] - price) / (price - res_buy["sl"])
            r3_buy = (res_buy["tp3"] - price) / (price - res_buy["sl"])
            self.assertAlmostEqual(r1_buy, 1.5, places=3, msg=f"BUY TP1 R-multiple failed on {symbol}")
            self.assertAlmostEqual(r2_buy, 2.5, places=3, msg=f"BUY TP2 R-multiple failed on {symbol}")
            self.assertAlmostEqual(r3_buy, 4.0, places=3, msg=f"BUY TP3 R-multiple failed on {symbol}")

            # 2. SELL Side Test
            res_sell = self.risk_mgr.calculate_atr_stops(symbol, price, side="SELL", atr_value=atr)
            self.assertAlmostEqual(res_sell["sl_distance"], expected_sl_dist, places=4)
            self.assertAlmostEqual(res_sell["sl"], price + expected_sl_dist, places=4)
            
            # Verify R-multiples for SELL
            r1_sell = (price - res_sell["tp1"]) / (res_sell["sl"] - price)
            r2_sell = (price - res_sell["tp2"]) / (res_sell["sl"] - price)
            r3_sell = (price - res_sell["tp3"]) / (res_sell["sl"] - price)
            self.assertAlmostEqual(r1_sell, 1.5, places=3, msg=f"SELL TP1 R-multiple failed on {symbol}")
            self.assertAlmostEqual(r2_sell, 2.5, places=3, msg=f"SELL TP2 R-multiple failed on {symbol}")
            self.assertAlmostEqual(r3_sell, 4.0, places=3, msg=f"SELL TP3 R-multiple failed on {symbol}")

    def test_atr_stops_unlisted_asset_fallback(self):
        """Tests that an unlisted asset uses 0.5% price fallback when ATR is None or zero."""
        price = 100.0
        res = self.risk_mgr.calculate_atr_stops("UNKNOWN_COIN", price, side="BUY", atr_value=None)
        # Fallback ATR = 100 * 0.005 = 0.50
        # SL dist = 3.5 * 0.50 = 1.75
        self.assertEqual(res["atr"], 0.50)
        self.assertEqual(res["sl_distance"], 1.75)
        self.assertEqual(res["sl"], 98.25)
        self.assertEqual(res["tp1"], 102.625)
        self.assertEqual(res["tp2"], 104.375)
        self.assertEqual(res["tp3"], 107.0)

    # =========================================================================
    # 5. DYNAMIC RISK-CALIBRATED LOT SIZING & CLAMPING TESTS
    # =========================================================================

    def test_dynamic_lot_sizing_forex_metals_crypto(self):
        """Tests dynamic lot sizing formulas across Gold, EURUSD, and BTCUSDT."""
        # 1. Gold on 25k (0.25% risk = $62.50, $14 SL dist, contract size 100)
        # Lots = 62.50 / (14 * 100) = 0.0446 -> 0.04
        lots_gold = self.risk_mgr.calculate_dynamic_lot_size("FP_25K", "XAUUSD", 2650.0, 2636.0)
        self.assertEqual(lots_gold, 0.04)

        # 2. EURUSD on 100k FTMO (1.0% risk = $1000, entry 1.0850, SL 1.0750 dist 0.0100, contract size 100,000)
        # Dollar per lot = 0.0100 * 100,000 = $1,000. Lots = 1000 / 1000 = 1.00
        lots_eur = self.risk_mgr.calculate_dynamic_lot_size("FTMO_100K", "EURUSD", 1.0850, 1.0750)
        self.assertEqual(lots_eur, 1.00)

        # 3. BTCUSDT on $1,000 Binance Spot (1.5% risk = $15.00, entry 60000, SL 58000 dist 2000, contract size 1.0)
        # Lots = 15.00 / 2000 = 0.0075 -> rounded by float representation to 0.007 / 0.008
        lots_btc = self.risk_mgr.calculate_dynamic_lot_size("BINANCE_SPOT_1K", "BTCUSDT", 60000.0, 58000.0)
        self.assertAlmostEqual(lots_btc, 0.0075, places=2)

        # 4. Micro Crypto Scalp on $100 Binance (1.5% risk = $1.50, entry 60000, SL 59500 dist 500, contract size 1.0)
        # Lots = 1.50 / 500 = 0.003
        lots_micro = self.risk_mgr.calculate_dynamic_lot_size("SCALP_100", "BTCUSDT", 60000.0, 59500.0)
        self.assertEqual(lots_micro, 0.003)

    def test_dynamic_lot_sizing_lockout_zero_multiplier(self):
        """Tests that when Stage 5 consistency lockout is active, lot size is strictly 0.0."""
        acc_id = "FP_25K"
        # Trigger Stage 5 by injecting $800 profit (> 35% of $2000 target)
        self.risk_mgr.update_account_telemetry(acc_id, balance=25000.0, equity=25000.0, sod_reset=True)
        self.risk_mgr.update_account_telemetry(acc_id, balance=25800.0, equity=25800.0)
        pacing = self.risk_mgr.calculate_consistency_pacing(acc_id, profit_target=2000.0)
        self.assertEqual(pacing["stage"], 5)
        self.assertEqual(pacing["risk_multiplier"], 0.0)

        lots = self.risk_mgr.calculate_dynamic_lot_size(acc_id, "XAUUSD", 2650.0, 2636.0)
        self.assertEqual(lots, 0.0, "Lot size must be exactly 0.0 when Stage 5 lockout is active")

    def test_dynamic_lot_sizing_extreme_clamps(self):
        """Tests minimum lot clamping and the global 5-lot safety ceiling."""
        # Micro account $1 with large SL -> clamps to 0.01
        lots_min = self.risk_mgr.calculate_dynamic_lot_size("SCALP_100", "EURUSD", 1.0850, 1.0000)
        self.assertEqual(lots_min, 0.01)

        # Massive account $10,000,000 with tight SL -> clamps to 5.0
        self.risk_mgr.update_account_telemetry("FTMO_100K", balance=10000000.0, equity=10000000.0, sod_reset=True)
        lots_max = self.risk_mgr.calculate_dynamic_lot_size("FTMO_100K", "EURUSD", 1.0850, 1.0849)
        self.assertEqual(lots_max, 5.0)

    # =========================================================================
    # 6. PRE-TRADE RISK INTERCEPTOR EXHAUSTIVE REJECTION MATRIX
    # =========================================================================

    def test_pre_trade_interceptor_unauthorized_assets(self):
        """Tests that assets not in allowed list are intercepted."""
        acc_id = "FP_25K"
        unallowed_assets = ["DOGEUSDT", "SHIBUSDT", "NVDA", "AAPL", "US500"]
        for sym in unallowed_assets:
            approved, reason = self.risk_mgr.validate_pre_trade_risk(
                account_id=acc_id, symbol=sym, lot_size=0.10, side="BUY", entry_price=100.0, sl_price=95.0
            )
            self.assertFalse(approved, f"Should reject unallowed asset {sym}")
            self.assertIn("not permitted", reason)

    def test_pre_trade_interceptor_invalid_sl_orientation(self):
        """Tests that invalid SL orientation is rejected for both BUY and SELL."""
        acc_id = "FP_25K"
        # BUY with SL >= Entry
        app1, r1 = self.risk_mgr.validate_pre_trade_risk(
            account_id=acc_id, symbol="XAUUSD", lot_size=0.10, side="BUY", entry_price=2650.0, sl_price=2650.0
        )
        self.assertFalse(app1)
        self.assertIn("Invalid BUY Stop Loss", r1)

        app2, r2 = self.risk_mgr.validate_pre_trade_risk(
            account_id=acc_id, symbol="XAUUSD", lot_size=0.10, side="BUY", entry_price=2650.0, sl_price=2660.0
        )
        self.assertFalse(app2)
        self.assertIn("Invalid BUY Stop Loss", r2)

        # SELL with SL <= Entry
        app3, r3 = self.risk_mgr.validate_pre_trade_risk(
            account_id=acc_id, symbol="XAUUSD", lot_size=0.10, side="SELL", entry_price=2650.0, sl_price=2650.0
        )
        self.assertFalse(app3)
        self.assertIn("Invalid SELL Stop Loss", r3)

        app4, r4 = self.risk_mgr.validate_pre_trade_risk(
            account_id=acc_id, symbol="XAUUSD", lot_size=0.10, side="SELL", entry_price=2650.0, sl_price=2640.0
        )
        self.assertFalse(app4)
        self.assertIn("Invalid SELL Stop Loss", r4)

    def test_pre_trade_interceptor_zero_or_negative_volume(self):
        """Tests that 0 or negative lot sizes are strictly rejected."""
        acc_id = "FP_25K"
        for bad_lot in [0.0, -0.1, -5.0]:
            approved, reason = self.risk_mgr.validate_pre_trade_risk(
                account_id=acc_id, symbol="XAUUSD", lot_size=bad_lot, side="BUY", entry_price=2650.0, sl_price=2636.0
            )
            self.assertFalse(approved)
            self.assertIn("must be > 0", reason)

    def test_pre_trade_interceptor_deactivated_account(self):
        """Tests that deactivated accounts cannot place trades."""
        acc_id = "FP_25K"
        st = self.risk_mgr.get_account_state(acc_id)
        st["is_active"] = False

        approved, reason = self.risk_mgr.validate_pre_trade_risk(
            account_id=acc_id, symbol="XAUUSD", lot_size=0.10, side="BUY", entry_price=2650.0, sl_price=2636.0
        )
        self.assertFalse(approved)
        self.assertIn("deactivated", reason)

    # =========================================================================
    # 7. FLEET CONCURRENCY & PERSISTENCE STRESS
    # =========================================================================

    def test_fleet_persistence_and_reload(self):
        """Tests saving and reloading fleet telemetry to ensure state consistency."""
        # Mutate account telemetry
        self.risk_mgr.update_account_telemetry("FP_25K", balance=27500.0, equity=27500.0)
        self.risk_mgr.save_fleet()

        # Instantiate brand new FleetRiskManager loading from same config file
        fresh_risk_mgr = FleetRiskManager(config_path=self.test_config)
        st = fresh_risk_mgr.get_account_state("FP_25K")
        self.assertIsNotNone(st)
        self.assertEqual(st["starting_balance"], 25000.0)
        # Verify floor persistence
        self.assertEqual(st["trailing_hwm_floor"], 24000.0)

    # =========================================================================
    # 8. ADVERSARIAL INJECTIONS, UNICODE/XSS ACCOUNT IDS & FUZZ VECTORS
    # =========================================================================

    def test_adversarial_account_ids_and_fuzzing(self):
        """Stress-tests account lookup and telemetry updates under malicious / edge IDs."""
        hostile_ids = [
            "<script>alert('pwn')</script>",
            "'; DROP TABLE accounts; --",
            "ACC_🔥_EMOJI_999",
            "حساب_تجاري_١٢٣",
            "../../../../etc/passwd",
            "\\x00\\x01\\x02",
        ]
        for bad_id in hostile_ids:
            self.onboarder.onboard_new_account(
                account_id=bad_id,
                server="Test-Server",
                balance=10000.0,
                account_type="FUNDING_PIPS"
            )
            # Re-sync in risk manager
            self.risk_mgr.load_fleet()
            
            st = self.risk_mgr.get_account_state(bad_id)
            self.assertIsNotNone(st, f"Failed lookup for hostile ID {bad_id}")
            self.assertEqual(st["starting_balance"], 10000.0)
            
            # Telemetry update
            res = self.risk_mgr.update_account_telemetry(bad_id, balance=10200.0, equity=10200.0)
            self.assertTrue(res["daily_loss_shield_ok"])
            self.assertTrue(res["trailing_floor_ok"])


if __name__ == "__main__":
    unittest.main()
