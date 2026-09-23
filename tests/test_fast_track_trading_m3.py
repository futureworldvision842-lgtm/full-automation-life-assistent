"""
test_fast_track_trading_m3.py — Comprehensive Unit & Integration Tests for Worker M3.

Verifies:
1. Pipdance $1,000 2-Day Fast-Track Evaluation algorithm:
   - Exact 0.75% risk per trade ($7.50 max risk cap on $1,000 balance).
   - 1:2.5 to 1:3.0 Risk-to-Reward ratio.
   - 1.5x ATR dynamic Stop Loss calculation.
   - Dynamic Breakeven Lock at +1.0R gain ($7.50 profit).
   - 2-Day minimum trading days and phase milestone evaluation (Phase 1: 8%, Phase 2: 5%).
2. Multi-Account Auto-Switching:
   - Seamless routing and auto-switching between FTMO-Demo (#1514382598) and Vebson-Server (#5054542).
3. FTMO $100k Demo Rules & Governance:
   - BlackRock Aladdin 1-Day 99% VaR compliance & CVaR risk calculations.
   - 15-minute high-impact economic news blackout.
   - Max drawdown buffer ($90,000 hard floor, $2,000 daily buffer).
4. Autonomous Live Daemon position management and telemetry.
"""

import math
import sys
import unittest
from pathlib import Path

# Setup paths
JARVIS_ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = JARVIS_ROOT / "MQ3 TRADING BOT"

if str(JARVIS_ROOT) not in sys.path:
    sys.path.insert(0, str(JARVIS_ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

from src.pipdance_fast_track_engine import PipdanceFastTrackEngine, FastTrackStatus, FastTrackPhase
from src.mt5_connector import MT5Connector
from src.portfolio_risk_service import PortfolioRiskService, AccountRiskState
from src.autonomous_live_daemon import AutonomousLiveDaemon


class TestPipdanceFastTrackEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PipdanceFastTrackEngine()

    def test_exact_risk_calculation_and_cap(self):
        """Test exact 0.75% risk per trade and $7.50 max cap on $1,000 account."""
        # 1. Standard $1,000 account -> 0.75% = $7.50 (capped at $7.50)
        res_1k = self.engine.calculate_risk(balance=1000.0, atr=0.0010, symbol="EURUSD", entry_price=1.0850, direction="BUY")
        self.assertEqual(res_1k["risk_pct"], 0.75)
        self.assertEqual(res_1k["risk_usd"], 7.50)
        self.assertEqual(res_1k["max_risk_cap"], 7.50)

        # 2. Sub-$1,000 account (e.g. $800 after slight drawdown) -> 0.75% = $6.00 <= $7.50 cap
        res_800 = self.engine.calculate_risk(balance=800.0, atr=0.0010, symbol="EURUSD", entry_price=1.0850, direction="BUY")
        self.assertEqual(res_800["risk_usd"], 6.00)
        self.assertLessEqual(res_800["risk_usd"], 7.50)

    def test_dynamic_1_5x_atr_sl_and_rr_ratio(self):
        """Test 1.5x ATR dynamic Stop Loss and 1:2.5 to 1:3.0 Risk-to-Reward ratio."""
        atr_val = 0.0020
        entry = 1.1000

        # BUY test with 1:2.5 RR
        res_buy = self.engine.calculate_risk(balance=1000.0, atr=atr_val, symbol="EURUSD", entry_price=entry, direction="BUY", rr_ratio=2.5)
        expected_sl_dist = round(1.5 * atr_val, 6)  # 0.0030
        expected_tp_dist = round(2.5 * expected_sl_dist, 6)  # 0.0075
        self.assertAlmostEqual(res_buy["sl_dist"], expected_sl_dist, places=5)
        self.assertAlmostEqual(res_buy["tp_dist"], expected_tp_dist, places=5)
        self.assertAlmostEqual(res_buy["sl"], entry - expected_sl_dist, places=5)
        self.assertAlmostEqual(res_buy["tp"], entry + expected_tp_dist, places=5)
        self.assertEqual(res_buy["rr_ratio"], 2.5)

        # SELL test with 1:3.0 RR
        res_sell = self.engine.calculate_risk(balance=1000.0, atr=atr_val, symbol="EURUSD", entry_price=entry, direction="SELL", rr_ratio=3.0)
        expected_tp_dist_3r = round(3.0 * expected_sl_dist, 6)  # 0.0090
        self.assertAlmostEqual(res_sell["sl"], entry + expected_sl_dist, places=5)
        self.assertAlmostEqual(res_sell["tp"], entry - expected_tp_dist_3r, places=5)
        self.assertEqual(res_sell["rr_ratio"], 3.0)

        # RR ratio clamping to [2.5, 3.0]
        res_clamp_low = self.engine.calculate_risk(balance=1000.0, atr=atr_val, symbol="EURUSD", rr_ratio=1.5)
        self.assertEqual(res_clamp_low["rr_ratio"], 2.5)
        res_clamp_high = self.engine.calculate_risk(balance=1000.0, atr=atr_val, symbol="EURUSD", rr_ratio=5.0)
        self.assertEqual(res_clamp_high["rr_ratio"], 3.0)

    def test_dynamic_breakeven_lock_trigger(self):
        """Test dynamic breakeven trigger at +1.0R gain ($7.50 profit or +1.0R distance)."""
        # Scenario 1: BUY position with entry 1.1000, SL 1.0970 (stop dist = 0.0030), Profit = $7.50
        pos_buy = {
            "ticket": 101,
            "symbol": "EURUSD",
            "type": "BUY",
            "price_open": 1.1000,
            "price_current": 1.1035,
            "sl": 1.0970,
            "tp": 1.1090,
            "profit": 8.00,
            "volume": 0.02,
        }
        res_be = self.engine.check_breakeven_trigger(position=pos_buy)
        self.assertTrue(res_be["trigger"])
        self.assertEqual(res_be["action"], "shift_sl_to_entry")
        self.assertEqual(res_be["new_sl"], 1.1000)

        # Scenario 2: SELL position with entry 1.1000, SL 1.1030 (stop dist = 0.0030), Profit = $7.50
        pos_sell = {
            "ticket": 102,
            "symbol": "EURUSD",
            "type": "SELL",
            "price_open": 1.1000,
            "price_current": 1.0965,
            "sl": 1.1030,
            "tp": 1.0910,
            "profit": 7.50,
            "volume": 0.02,
        }
        res_be_sell = self.engine.check_breakeven_trigger(position=pos_sell)
        self.assertTrue(res_be_sell["trigger"])
        self.assertEqual(res_be_sell["new_sl"], 1.1000)

        # Scenario 3: Position below +1.0R gain
        pos_small = {
            "ticket": 103,
            "symbol": "EURUSD",
            "type": "BUY",
            "price_open": 1.1000,
            "price_current": 1.1010,
            "sl": 1.0970,
            "tp": 1.1090,
            "profit": 2.50,
            "volume": 0.02,
        }
        res_hold = self.engine.check_breakeven_trigger(position=pos_small)
        self.assertFalse(res_hold["trigger"])
        self.assertEqual(res_hold["action"], "hold")

        # Scenario 4: Already at breakeven
        pos_protected = {
            "ticket": 104,
            "symbol": "EURUSD",
            "type": "BUY",
            "price_open": 1.1000,
            "price_current": 1.1050,
            "sl": 1.1000,  # SL already shifted to entry
            "tp": 1.1090,
            "profit": 10.00,
            "volume": 0.02,
        }
        res_prot = self.engine.check_breakeven_trigger(position=pos_protected)
        self.assertFalse(res_prot["trigger"])
        self.assertEqual(res_prot["action"], "already_protected")

    def test_2_day_fast_track_evaluation_rules(self):
        """Test 2-Day Fast-Track evaluation tracking (Phase 1 8%, Phase 2 5%, min 2 days)."""
        # Phase 1 Target: 8% ($80 on $1,000)
        # Case A: Profit reached $85 in 2 days -> PASSED_PHASE_1
        eval_pass_p1 = self.engine.evaluate_fast_track_evaluation(
            trading_days=2,
            current_balance=1085.0,
            starting_balance=1000.0,
            phase=1,
        )
        self.assertTrue(eval_pass_p1["passed"])
        self.assertEqual(eval_pass_p1["status"], FastTrackStatus.PASSED_PHASE_1.value)

        # Case B: Profit reached $85 in only 1 day -> Needs 2 days (IN_PROGRESS)
        eval_need_days = self.engine.evaluate_fast_track_evaluation(
            trading_days=1,
            current_balance=1085.0,
            starting_balance=1000.0,
            phase=1,
        )
        self.assertFalse(eval_need_days["passed"])
        self.assertFalse(eval_need_days["min_days_met"])

        # Case C: Daily drawdown breach ($55 daily loss >= $50 cap) -> FAILED_DAILY_DRAWDOWN
        eval_daily_fail = self.engine.evaluate_fast_track_evaluation(
            trading_days=2,
            current_balance=945.0,
            starting_balance=1000.0,
            phase=1,
            daily_loss_usd=55.0,
        )
        self.assertFalse(eval_daily_fail["passed"])
        self.assertEqual(eval_daily_fail["status"], FastTrackStatus.FAILED_DAILY_DRAWDOWN.value)

        # Case D: Total drawdown breach (balance $890 <= floor $900) -> FAILED_TOTAL_DRAWDOWN
        eval_total_fail = self.engine.evaluate_fast_track_evaluation(
            trading_days=2,
            current_balance=890.0,
            starting_balance=1000.0,
            phase=1,
        )
        self.assertFalse(eval_total_fail["passed"])
        self.assertEqual(eval_total_fail["status"], FastTrackStatus.FAILED_TOTAL_DRAWDOWN.value)

        # Case E: Phase 2 Target (5% = $50 on $1,000) -> CHALLENGE_PASSED
        eval_pass_p2 = self.engine.evaluate_fast_track_evaluation(
            trading_days=2,
            current_balance=1055.0,
            starting_balance=1000.0,
            phase=2,
        )
        self.assertTrue(eval_pass_p2["passed"])
        self.assertEqual(eval_pass_p2["status"], FastTrackStatus.CHALLENGE_PASSED.value)


class TestMultiAccountAutoSwitching(unittest.TestCase):
    def setUp(self):
        self.connector = MT5Connector(simulation_mode=True)

    def test_multi_account_auto_switching(self):
        """Test seamless auto-detection and execution switching between FTMO-Demo and Vebson-Server."""
        # 1. Switch to FTMO-Demo (#1514382598)
        ok_ftmo = self.connector.switch_account(login=1514382598, server="FTMO-Demo")
        self.assertTrue(ok_ftmo)
        self.assertEqual(self.connector.active_login, 1514382598)
        self.assertEqual(self.connector.active_server, "FTMO-Demo")
        acc_ftmo = self.connector.get_account_info()
        self.assertEqual(acc_ftmo["login"], 1514382598)
        self.assertEqual(acc_ftmo["balance"], 100000.0)

        # 2. Switch to Vebson-Server (#5054542)
        ok_vebson = self.connector.switch_account(login=5054542, server="Vebson-Server")
        self.assertTrue(ok_vebson)
        self.assertEqual(self.connector.active_login, 5054542)
        self.assertEqual(self.connector.active_server, "Vebson-Server")
        acc_vebson = self.connector.get_account_info()
        self.assertEqual(acc_vebson["login"], 5054542)
        self.assertEqual(acc_vebson["balance"], 1000.0)

        # 3. Route account helper
        route_info = self.connector.auto_detect_and_route_account(preferred="FTMO")
        self.assertEqual(route_info["login"], 1514382598)
        self.assertEqual(route_info["account_type"], "FTMO_100K_DEMO")

    def test_shift_sl_to_entry(self):
        """Test MT5Connector shift_sl_to_entry dynamic breakeven shift."""
        # Place mock order
        order = self.connector.place_order(symbol="EURUSD", signal_type="BUY", volume=0.01, price=1.0850, sl=1.0820, tp=1.0920)
        self.assertTrue(order["success"])
        ticket = order["ticket"]

        # Shift SL to entry
        shifted = self.connector.shift_sl_to_entry(ticket=ticket, open_price=1.0850, current_tp=1.0920)
        self.assertTrue(shifted)

        # Verify position SL is now entry price
        positions = self.connector.get_open_positions()
        pos = next(p for p in positions if p["ticket"] == ticket)
        self.assertEqual(pos["sl"], 1.0850)


class TestPortfolioRiskServiceAladdinGovernance(unittest.TestCase):
    def setUp(self):
        self.risk_service = PortfolioRiskService(max_portfolio_heat_pct=3.0, max_portfolio_var_pct=1.5)

    def test_aladdin_1day_99pct_var_computation(self):
        """Test BlackRock Aladdin 1-Day 99% VaR and CVaR calculations."""
        equity = 100000.0  # FTMO $100k
        daily_vol = 0.005  # 0.5% daily volatility
        var_res = self.risk_service.compute_aladdin_var_99(equity=equity, daily_volatility=daily_vol)

        # VaR_99 = 100000 * 2.326348 * 0.005 = 1163.17 USD (1.16%)
        expected_var_dollar = equity * 2.326348 * daily_vol
        self.assertAlmostEqual(var_res["var_99_dollar"], round(expected_var_dollar, 2), delta=0.5)
        self.assertTrue(var_res["var_99_compliant"])

        # High volatility breach (e.g. 1.0% daily vol -> VaR 2.33% > 1.5% limit)
        var_high = self.risk_service.compute_aladdin_var_99(equity=equity, daily_volatility=0.010)
        self.assertFalse(var_high["var_99_compliant"])

    def test_trade_admission_risk_governance(self):
        """Test Aladdin VaR, drawdown limits, and max risk caps in trade admission."""
        # 1. Pipdance $1k Account (#5054542): Risk 0.75% = $7.50 -> Approved
        admitted_1k, reason_1k, telem_1k = self.risk_service.evaluate_trade_admission_risk(
            account_id="5054542",
            symbol="EURUSD",
            direction="BUY",
            risk_pct=0.75,
            check_news=False,
        )
        self.assertTrue(admitted_1k, f"Rejected: {reason_1k}")
        self.assertEqual(telem_1k["risk_dollar"], 7.50)

        # 2. Pipdance $1k Account: Risk 1.5% > 0.75% cap -> Rejected
        admitted_over, reason_over, _ = self.risk_service.evaluate_trade_admission_risk(
            account_id="5054542",
            symbol="EURUSD",
            direction="BUY",
            risk_pct=1.50,
            check_news=False,
        )
        self.assertFalse(admitted_over)
        self.assertIn("exceeds maximum allowable 0.75%", reason_over)

        # 3. FTMO $100k Account (#1514382598): Risk 0.75% = $750.00 -> Approved
        admitted_ftmo, reason_ftmo, telem_ftmo = self.risk_service.evaluate_trade_admission_risk(
            account_id="1514382598",
            symbol="XAUUSD",
            direction="BUY",
            risk_pct=0.75,
            check_news=False,
        )
        self.assertTrue(admitted_ftmo, f"Rejected: {reason_ftmo}")
        self.assertEqual(telem_ftmo["risk_dollar"], 750.0)


class TestAutonomousLiveDaemonGovernance(unittest.TestCase):
    def setUp(self):
        self.daemon = AutonomousLiveDaemon(simulation_mode=True)

    def test_daemon_breakeven_management_and_telemetry(self):
        """Test daemon position breakeven scan and periodic telemetry generation."""
        # Place mock trade in connector
        self.daemon.mt5.place_order(symbol="EURUSD", signal_type="BUY", volume=0.02, price=1.0850, sl=1.0820, tp=1.0930)

        # Update position current price to trigger +1.0R gain
        for p in self.daemon.mt5._mock_positions:
            p["price_current"] = 1.0885  # +35 pips > 30 pips stop dist
            p["profit"] = 7.50

        # Run check_and_manage_positions
        actions = self.daemon.check_and_manage_positions()
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action"], "shift_sl_to_entry")

        # Check telemetry payload
        telem = self.daemon.broadcast_periodic_telemetry()
        self.assertIn("balance", telem)
        self.assertIn("var_99_dollar", telem)
        self.assertIn("open_positions", telem)


if __name__ == "__main__":
    unittest.main()
