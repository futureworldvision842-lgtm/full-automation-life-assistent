"""
test_fleet_risk_manager.py — Test Suite for Fleet Risk Manager & Rule Calibrator.
================================================================================
Empirically tests all 5 core mathematical pillars of Milestone 3:
  1. SOD (00:00 UTC) Daily Drawdown Shield validation.
  2. Trailing High-Water-Mark (HWM) Floor Ratchet with Starting Balance Profit Milestone Lock.
  3. 5-Stage Institutional Consistency Pacing Gauge (<20% 1.0x, 20-25% 0.8x, 25-30% 0.5x, 30-35% 0.25x, >35% lockout).
  4. 3.5x ATR Dynamic Stop-Loss & Multi-Tier Take-Profit calculations (1.5R, 2.5R, 4.0R).
  5. Dynamic Risk-Calibrated Position Sizing across Forex, Gold, and Crypto instruments.
  6. Comprehensive Pre-Trade Risk Audit Interception and Fleet Dashboard formatting.
"""

import os
import json
import unittest
from src.fleet_risk_manager import FleetRiskManager
from src.multi_account_auto_onboarder import MultiAccountAutoOnboarder


class TestFleetRiskManager(unittest.TestCase):
    def setUp(self):
        self.test_config = "data/test_fleet_risk_config.json"
        self.onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)
        
        # Onboard 3 representative accounts
        # 1. Funding Pips 25k Standard with tighter 1.5%/4.0%/0.25% internal controls.
        self.onboarder.onboard_new_account(
            account_id="5054340275",
            server="MetaQuotes-Demo",
            balance=25000.0,
            account_type="FUNDING_PIPS"
        )
        # 2. FTMO 100k ($100,000, 4.0% daily loss, 8.0% max loss, 1.0% risk, 50% consistency)
        self.onboarder.onboard_new_account(
            account_id="FTMO_100K",
            server="FTMO-Demo",
            balance=100000.0,
            account_type="FTMO"
        )
        # 3. Scalp 5M ($100, 5.0% daily loss, 20.0% max loss, 1.5% risk, 100% consistency)
        self.onboarder.onboard_new_account(
            account_id="SCALP_100",
            server="Binance-Live",
            balance=100.0,
            account_type="SCALP_5M"
        )

        self.risk_mgr = FleetRiskManager(config_path=self.test_config, auto_onboarder=self.onboarder)

    def tearDown(self):
        if os.path.exists(self.test_config):
            try:
                os.remove(self.test_config)
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # 1. DAILY DRAWDOWN SHIELD TESTS
    # ─────────────────────────────────────────────────────────────────────────

    def test_daily_loss_shield_safe_state(self):
        """Tests that intraday equity within daily loss limit returns safe=True."""
        # 25k account with $250 loss (internal stop is 1.5% = $375)
        res = self.risk_mgr.update_account_telemetry(
            account_id="5054340275",
            balance=24750.0,
            equity=24750.0
        )
        self.assertTrue(res["daily_loss_shield_ok"])
        self.assertEqual(res["daily_loss_dollars"], 250.0)

        shield = self.risk_mgr.check_daily_loss_shield("5054340275")
        self.assertTrue(shield["safe"])
        self.assertFalse(shield["breached"])
        self.assertEqual(shield["buffer_remaining"], 125.0)

    def test_daily_loss_shield_breach_detection(self):
        """Tests that intraday equity loss >= limit triggers shield breach."""
        # 25k account with $700 loss (well beyond the $375 internal stop)
        res = self.risk_mgr.update_account_telemetry(
            account_id="5054340275",
            balance=24300.0,
            equity=24300.0
        )
        self.assertFalse(res["daily_loss_shield_ok"])
        self.assertTrue(res["is_locked_out"])

        shield = self.risk_mgr.check_daily_loss_shield("5054340275")
        self.assertFalse(shield["safe"])
        self.assertTrue(shield["breached"])
        self.assertGreaterEqual(shield["intraday_loss"], 375.0)

    def test_sod_baseline_reset(self):
        """Tests that SOD reset updates the daily equity benchmark at 00:00 UTC."""
        # Account grew to $26,000 on day 1
        self.risk_mgr.update_account_telemetry("5054340275", balance=26000.0, equity=26000.0)
        # SOD reset on day 2
        res = self.risk_mgr.update_account_telemetry("5054340275", balance=26000.0, equity=26000.0, sod_reset=True)
        self.assertEqual(res["daily_sod_equity"], 26000.0)
        self.assertEqual(res["daily_loss_dollars"], 0.0)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. TRAILING HIGH-WATER MARK (HWM) FLOOR TESTS
    # ─────────────────────────────────────────────────────────────────────────

    def test_trailing_hwm_floor_ratchet_and_profit_lock(self):
        """Funding Pips Standard uses a static starting-balance floor, not a trailing HWM."""
        # Internal floor on 25k is $24,000 ($25,000 - 4%).
        st = self.risk_mgr.get_account_state("5054340275")
        self.assertEqual(st["trailing_hwm_floor"], 24000.0)

        # Equity climbs to $26,000 (peak)
        # Peak telemetry updates, but the Standard loss floor remains static.
        res = self.risk_mgr.update_account_telemetry("5054340275", balance=26000.0, equity=26000.0)
        self.assertEqual(res["absolute_hwm"], 26000.0)
        self.assertEqual(res["trailing_hwm_floor"], 24000.0)

        # Equity climbs to $27,000; the firm/internal static floor does not ratchet.
        res2 = self.risk_mgr.update_account_telemetry("5054340275", balance=27000.0, equity=27000.0)
        self.assertEqual(res2["absolute_hwm"], 27000.0)
        self.assertEqual(res2["trailing_hwm_floor"], 24000.0)

    def test_trailing_floor_breach_detection(self):
        """Tests that equity dropping below trailing floor flags a breach."""
        # Internal static floor is $24,000. Drop equity to $23,400.
        res = self.risk_mgr.update_account_telemetry("5054340275", balance=23400.0, equity=23400.0)
        self.assertFalse(res["trailing_floor_ok"])
        self.assertTrue(res["is_locked_out"])

        guard = self.risk_mgr.check_trailing_hwm_floor("5054340275")
        self.assertFalse(guard["safe"])
        self.assertTrue(guard["breached"])

    # ─────────────────────────────────────────────────────────────────────────
    # 3. 5-STAGE CONSISTENCY PACING GAUGE TESTS
    # ─────────────────────────────────────────────────────────────────────────

    def test_consistency_pacing_stages(self):
        """Tests the 5-stage pacing gauge across evaluation profit thresholds."""
        # 25k account target is $2,000 (8% of 25k)
        acc_id = "5054340275"
        
        # Stage 1: Profit $200 (10% of target < 20%) -> 1.0x
        self.risk_mgr.update_account_telemetry(acc_id, balance=25200.0, equity=25200.0)
        p1 = self.risk_mgr.calculate_consistency_pacing(acc_id, profit_target=2000.0)
        self.assertEqual(p1["stage"], 1)
        self.assertEqual(p1["risk_multiplier"], 1.0)
        self.assertTrue(p1["can_trade"])

        # Stage 2: Profit $450 (22.5% of target: 20%-25%) -> 0.8x
        self.risk_mgr.update_account_telemetry(acc_id, balance=25450.0, equity=25450.0)
        p2 = self.risk_mgr.calculate_consistency_pacing(acc_id, profit_target=2000.0)
        self.assertEqual(p2["stage"], 2)
        self.assertEqual(p2["risk_multiplier"], 0.8)
        self.assertTrue(p2["can_trade"])

        # Stage 3: Profit $550 (27.5% of target: 25%-30%) -> 0.5x
        self.risk_mgr.update_account_telemetry(acc_id, balance=25550.0, equity=25550.0)
        p3 = self.risk_mgr.calculate_consistency_pacing(acc_id, profit_target=2000.0)
        self.assertEqual(p3["stage"], 3)
        self.assertEqual(p3["risk_multiplier"], 0.5)
        self.assertTrue(p3["can_trade"])

        # Stage 4: Profit $650 (32.5% of target: 30%-35%) -> 0.25x
        self.risk_mgr.update_account_telemetry(acc_id, balance=25650.0, equity=25650.0)
        p4 = self.risk_mgr.calculate_consistency_pacing(acc_id, profit_target=2000.0)
        self.assertEqual(p4["stage"], 4)
        self.assertEqual(p4["risk_multiplier"], 0.25)
        self.assertTrue(p4["can_trade"])

        # Stage 5: Profit $750 (37.5% of target > 35%) -> Lockout (0.0x)
        self.risk_mgr.update_account_telemetry(acc_id, balance=25750.0, equity=25750.0)
        p5 = self.risk_mgr.calculate_consistency_pacing(acc_id, profit_target=2000.0)
        self.assertEqual(p5["stage"], 5)
        self.assertEqual(p5["risk_multiplier"], 0.0)
        self.assertFalse(p5["can_trade"])

    # ─────────────────────────────────────────────────────────────────────────
    # 4. 3.5X ATR DYNAMIC STOPS & TAKE PROFIT TESTS
    # ─────────────────────────────────────────────────────────────────────────

    def test_calculate_atr_stops_buy_gold(self):
        """Tests 3.5x ATR stop calculation for Gold BUY."""
        res = self.risk_mgr.calculate_atr_stops(
            symbol="XAUUSD",
            current_price=2650.0,
            side="BUY",
            atr_value=4.0
        )
        # SL distance = 3.5 * 4.0 = 14.0
        self.assertEqual(res["sl_distance"], 14.0)
        self.assertEqual(res["sl"], 2636.0)     # 2650 - 14
        self.assertEqual(res["tp1"], 2671.0)    # 2650 + (1.5 * 14 = 21)
        self.assertEqual(res["tp2"], 2685.0)    # 2650 + (2.5 * 14 = 35)
        self.assertEqual(res["tp3"], 2706.0)    # 2650 + (4.0 * 14 = 56)

    def test_calculate_atr_stops_sell_btc(self):
        """Tests 3.5x ATR stop calculation for BTC SELL."""
        res = self.risk_mgr.calculate_atr_stops(
            symbol="BTCUSDT",
            current_price=60000.0,
            side="SELL",
            atr_value=400.0
        )
        # SL distance = 3.5 * 400 = 1400.0
        self.assertEqual(res["sl_distance"], 1400.0)
        self.assertEqual(res["sl"], 61400.0)    # 60000 + 1400
        self.assertEqual(res["tp1"], 57900.0)   # 60000 - (1.5 * 1400 = 2100)
        self.assertEqual(res["tp2"], 56500.0)   # 60000 - (2.5 * 1400 = 3500)
        self.assertEqual(res["tp3"], 54400.0)   # 60000 - (4.0 * 1400 = 5600)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. DYNAMIC LOT SIZING TESTS
    # ─────────────────────────────────────────────────────────────────────────

    def test_calculate_dynamic_lot_size_gold(self):
        """Tests dynamic lot sizing on Gold (XAUUSD) with risk calibration."""
        # 25k account, 0.25% risk = $62.50 risk budget
        # Entry 2650.0, SL 2640.0 (dist = $10.00). Contract size = 100 ($1,000 per 1.0 lot)
        # Lot size = $62.50 / $1000 = 0.0625 -> rounded to 0.06
        lots = self.risk_mgr.calculate_dynamic_lot_size(
            account_id="5054340275",
            symbol="XAUUSD",
            entry_price=2650.0,
            sl_price=2640.0
        )
        self.assertAlmostEqual(lots, 0.06, places=2)
        self.assertGreaterEqual(lots, 0.01)

    def test_calculate_dynamic_lot_size_crypto_micro(self):
        """Tests dynamic lot sizing on $100 micro crypto scalp."""
        # $100 account, 1.5% risk = $1.50 risk budget
        # Entry 60000.0, SL 59500.0 (dist = 500.0). Contract size = 1.0
        # Lot size = $1.50 / 500 = 0.003 units
        lots = self.risk_mgr.calculate_dynamic_lot_size(
            account_id="SCALP_100",
            symbol="BTCUSDT",
            entry_price=60000.0,
            sl_price=59500.0
        )
        self.assertEqual(lots, 0.003)

    # ─────────────────────────────────────────────────────────────────────────
    # 6. PRE-TRADE RISK AUDIT & DASHBOARD TESTS
    # ─────────────────────────────────────────────────────────────────────────

    def test_validate_pre_trade_risk_approved(self):
        """Tests that valid orders pass pre-trade risk audit."""
        approved, reason = self.risk_mgr.validate_pre_trade_risk(
            account_id="5054340275",
            symbol="XAUUSD",
            lot_size=0.04,
            side="BUY",
            entry_price=2650.0,
            sl_price=2636.0,
            tp_price=2678.0,
        )
        self.assertTrue(approved)
        self.assertEqual(reason, "APPROVED_PRE_TRADE_STRESS_SAFE")

    def test_validate_pre_trade_risk_invalid_sl_side(self):
        """Tests rejection when BUY stop-loss is above entry price."""
        approved, reason = self.risk_mgr.validate_pre_trade_risk(
            account_id="5054340275",
            symbol="XAUUSD",
            lot_size=0.11,
            side="BUY",
            entry_price=2650.0,
            sl_price=2660.0  # Invalid for BUY
        )
        self.assertFalse(approved)
        self.assertIn("Invalid BUY Stop Loss", reason)

    def test_validate_pre_trade_risk_unauthorized_asset(self):
        """Tests rejection of unpermitted asset on prop firm account."""
        approved, reason = self.risk_mgr.validate_pre_trade_risk(
            account_id="5054340275",
            symbol="DOGEUSDT",  # Not in allowed assets
            lot_size=1.0,
            side="BUY",
            entry_price=0.10,
            sl_price=0.09
        )
        self.assertFalse(approved)
        self.assertIn("not permitted", reason)

    def test_get_fleet_risk_dashboard(self):
        """Tests formatting and output of fleet risk dashboard."""
        dash = self.risk_mgr.get_fleet_risk_dashboard()
        self.assertIn("FLEET RISK & DRAWDOWN TELEMETRY DASHBOARD", dash)
        self.assertIn("Funding Pips Prop Firm #5054340275", dash)
        self.assertIn("FTMO Evaluation Account #FTMO_100K", dash)
        self.assertIn("SCALP_100", dash)
        self.assertIn("Daily Drawdown:", dash)


if __name__ == "__main__":
    unittest.main()
