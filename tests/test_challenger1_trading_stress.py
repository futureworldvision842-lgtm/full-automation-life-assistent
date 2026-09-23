"""
test_challenger1_trading_stress.py — Empirical Stress Tests & Mathematical Verification
Executed by Challenger 1 (Trading & Risk Stress Verifier).

Covers all 5 Authoritative Pillars:
1. Pipdance $1,000 Challenge Risk Calculation:
   - Exact 0.75% risk ($7.50 max cap) across balance variations ($1,000, $1,050, $950, $800, $100).
   - 1.5x ATR dynamic SL calculation across asset classes (Forex, JPY, Metals, Crypto).
   - Clamped 1:2.5 to 1:3.0 Risk-to-Reward ratio.
   - Contract multiplier lot sizing and volume step discretization.
2. Dynamic Breakeven Trigger (+1.0R Gain / $7.50 Profit Shift):
   - +1.0R dollar profit ($7.50) trigger and price distance trigger for BUY and SELL positions.
   - Sub-threshold holding behavior ($7.49 / 0.99R).
   - Idempotency / already-protected state detection.
   - Edge case handling (zero entry, zero SL, malformed positions).
3. Multi-Account Auto-Switching:
   - Seamless routing and context switching between FTMO-Demo (#1514382598) and Vebson-Server (#5054542).
   - Login ID, server name, and preferred keyword auto-detection.
   - Independent risk ceilings and hard floor boundaries per account.
4. BlackRock Aladdin 1-Day 99% VaR and CVaR Formula Verification:
   - Analytical normal distribution quantile and PDF mathematical precision against Python statistics.NormalDist.
   - VaR 99%, VaR 95%, CVaR 99%, CVaR 95% dollar and percentage calculations.
   - Coherence and monotonicity invariants: CVaR_99 > VaR_99 > VaR_95.
   - Positive homogeneity and risk scaling.
5. 15-Minute News Blackout Boundary Conditions:
   - Microsecond/second boundary precision: T-16m, T-15m01s, T-15m00s, T-0s, T+15m00s, T+15m01s, T+20m.
   - Multi-currency routing matrix (USD, EUR, GBP, JPY, CAD, Gold, Crypto).
   - Fail-closed security posture when calendar unverified.
"""

from __future__ import annotations

import datetime
import math
import statistics
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Resolve project paths
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = WORKSPACE_ROOT / "MQ3 TRADING BOT"

if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

from src.pipdance_fast_track_engine import PipdanceFastTrackEngine, FastTrackStatus, FastTrackPhase, AccountProfile
from src.portfolio_risk_service import PortfolioRiskService, AccountRiskState
from src.aladdin_risk_engine import AladdinRiskEngine
from src.economic_calendar_radar import EconomicCalendarRadar
from src.economic_calendar_service import EconomicCalendarService, EconomicEvent, EventImpact
from src.mt5_connector import MT5Connector


class TestPipdanceRiskCalculationStress(unittest.TestCase):
    """Domain 1: Pipdance $1,000 Challenge Risk Calculation & Sizing Stress Tests."""

    def setUp(self):
        self.engine = PipdanceFastTrackEngine(
            default_account_size=1000.0,
            risk_pct_per_trade=0.75,
            max_risk_cap_usd=7.50,
            atr_sl_multiplier=1.5,
            min_rr_ratio=2.5,
            max_rr_ratio=3.0,
        )

    def test_exact_risk_calculation_across_balances(self):
        """Verify exact 0.75% risk and $7.50 cap across multiple balance scenarios."""
        test_cases = [
            # (balance, expected_risk_usd, expected_cap)
            (1000.0, 7.50, 7.50),     # Exact starting balance: 1000 * 0.0075 = 7.50
            (1050.0, 7.88, 7.50),     # Scaled balance (+5% profit): 1050 * 0.0075 = 7.875 -> 7.88 (IEEE round)
            (950.0, 7.12, 7.50),      # Scaled balance (-5% drawdown): 950 * 0.0075 = 7.125 -> 7.12 (banker's round)
            (800.0, 6.00, 7.50),      # Deep drawdown balance: 800 * 0.0075 = 6.00
            (100.0, 0.75, 7.50),      # Low balance edge case
            (1200.0, 9.00, 7.50),     # Large funded gain balance
        ]

        for bal, expected_risk, expected_cap in test_cases:
            with self.subTest(balance=bal):
                res = self.engine.calculate_risk(balance=bal, atr=0.0012, symbol="EURUSD", entry_price=1.0850)
                self.assertEqual(res["balance"], bal)
                self.assertEqual(res["risk_pct"], 0.75)
                self.assertEqual(res["risk_usd"], expected_risk)
                self.assertEqual(res["max_risk_cap"], expected_cap)
                if bal <= 1000.0:
                    self.assertLessEqual(res["risk_usd"], 7.50, f"Balance ${bal} risk exceeded $7.50 cap")

    def test_dynamic_1_5x_atr_sl_across_asset_classes(self):
        """Verify 1.5x ATR dynamic Stop Loss across Forex, JPY, Metals, and Crypto."""
        assets = [
            # (symbol, atr, entry_price, expected_decimals)
            ("EURUSD", 0.0014, 1.08500, 5),
            ("GBPUSD", 0.0022, 1.29500, 5),
            ("USDJPY", 0.180, 155.250, 3),
            ("XAUUSD", 3.80, 2650.00, 3),
            ("BTCUSD", 480.0, 65000.0, 3),
            ("ETHUSD", 32.0, 3400.0, 3),
            ("SOLUSD", 2.50, 180.0, 3),
        ]

        for sym, atr_val, entry, dec in assets:
            with self.subTest(symbol=sym, atr=atr_val):
                expected_sl_dist = round(1.5 * atr_val, 6)

                # Test BUY
                res_buy = self.engine.calculate_risk(balance=1000.0, atr=atr_val, symbol=sym, entry_price=entry, direction="BUY")
                self.assertAlmostEqual(res_buy["sl_dist"], expected_sl_dist, places=5)
                self.assertAlmostEqual(res_buy["sl"], round(entry - expected_sl_dist, dec), places=dec)
                self.assertLess(res_buy["sl"], entry)

                # Test SELL
                res_sell = self.engine.calculate_risk(balance=1000.0, atr=atr_val, symbol=sym, entry_price=entry, direction="SELL")
                self.assertAlmostEqual(res_sell["sl_dist"], expected_sl_dist, places=5)
                self.assertAlmostEqual(res_sell["sl"], round(entry + expected_sl_dist, dec), places=dec)
                self.assertGreater(res_sell["sl"], entry)

    def test_atr_fallback_on_zero_or_negative_inputs(self):
        """Verify that zero, negative, or invalid ATR gracefully triggers safe fallback without crashing."""
        for bad_atr in [0.0, -0.0010, -50.0]:
            with self.subTest(bad_atr=bad_atr):
                res_eur = self.engine.calculate_risk(balance=1000.0, atr=bad_atr, symbol="EURUSD")
                self.assertGreater(res_eur["atr"], 0.0)
                self.assertGreater(res_eur["sl_dist"], 0.0)
                self.assertFalse(math.isnan(res_eur["sl"]))

                res_gold = self.engine.calculate_risk(balance=1000.0, atr=bad_atr, symbol="XAUUSD")
                self.assertEqual(res_gold["atr"], 3.50)
                self.assertGreater(res_gold["sl_dist"], 0.0)

    def test_rr_ratio_clamping_bounds(self):
        """Verify strict clamping of RR ratio between 1:2.5 and 1:3.0."""
        rr_tests = [
            (-1.0, 2.5),
            (0.0, 2.5),
            (1.0, 2.5),
            (2.0, 2.5),
            (2.5, 2.5),
            (2.75, 2.75),
            (3.0, 3.0),
            (3.5, 3.0),
            (5.0, 3.0),
            (100.0, 3.0),
        ]
        for requested_rr, expected_clamped_rr in rr_tests:
            with self.subTest(requested=requested_rr, expected=expected_clamped_rr):
                res = self.engine.calculate_risk(balance=1000.0, atr=0.0010, symbol="EURUSD", rr_ratio=requested_rr)
                self.assertEqual(res["rr_ratio"], expected_clamped_rr)
                expected_tp_dist = round(expected_clamped_rr * res["sl_dist"], 6)
                self.assertAlmostEqual(res["tp_dist"], expected_tp_dist, places=5)

    def test_lot_size_discretization_and_risk_integrity(self):
        """Verify that lot sizing strictly rounds down to volume_step so max dollar risk is never breached."""
        # For EURUSD with entry=1.0850, risk_usd=$7.50, sl_dist=0.0015 (15 pips)
        # Loss per lot = 0.0015 * 100,000 = $150.00
        # Raw lots = 7.50 / 150.00 = 0.05 lots
        # Dollar risk with 0.05 lots = 0.05 * 150 = $7.50 <= $7.50
        lots = self.engine.calculate_lot_size(symbol="EURUSD", risk_usd=7.50, sl_dist=0.0015)
        self.assertEqual(lots, 0.05)
        dollar_loss = lots * 0.0015 * 100000.0
        self.assertLessEqual(dollar_loss, 7.500001)

        # For XAUUSD with entry=2650.0, risk_usd=$7.50, sl_dist=5.25 ($5.25 SL)
        # Loss per lot = 5.25 * 100 = $525.00
        # Raw lots = 7.50 / 525 = 0.01428 lots -> Floored to 0.01 lots
        # Dollar loss with 0.01 lots = 0.01 * 525 = $5.25 <= $7.50
        gold_lots = self.engine.calculate_lot_size(symbol="XAUUSD", risk_usd=7.50, sl_dist=5.25)
        self.assertEqual(gold_lots, 0.01)
        gold_dollar_loss = gold_lots * 5.25 * 100.0
        self.assertLessEqual(gold_dollar_loss, 7.50)


class TestDynamicBreakevenTriggerStress(unittest.TestCase):
    """Domain 2: Dynamic Breakeven Trigger (+1.0R Gain / $7.50 Profit Shift) Stress Tests."""

    def setUp(self):
        self.engine = PipdanceFastTrackEngine()

    def test_dollar_profit_breakeven_trigger(self):
        """Verify dynamic breakeven shift when floating profit reaches exactly $7.50 or above."""
        # Exact $7.50 profit threshold
        pos_exact = {
            "ticket": 201,
            "symbol": "EURUSD",
            "type": "BUY",
            "price_open": 1.08500,
            "price_current": 1.08750,
            "sl": 1.08300,
            "tp": 1.09100,
            "profit": 7.50,
            "volume": 0.03,
        }
        res_exact = self.engine.check_breakeven_trigger(position=pos_exact)
        self.assertTrue(res_exact["trigger"])
        self.assertEqual(res_exact["action"], "shift_sl_to_entry")
        self.assertEqual(res_exact["new_sl"], 1.08500)

        # Sub-threshold $7.49 profit (should hold)
        pos_sub = dict(pos_exact, profit=7.49, price_current=1.08600)  # price moved 0.0010 < stop_dist 0.0020
        res_sub = self.engine.check_breakeven_trigger(position=pos_sub)
        self.assertFalse(res_sub["trigger"])
        self.assertEqual(res_sub["action"], "hold")

        # Super-threshold $15.00 (+2.0R profit)
        pos_super = dict(pos_exact, profit=15.00)
        res_super = self.engine.check_breakeven_trigger(position=pos_super)
        self.assertTrue(res_super["trigger"])
        self.assertEqual(res_super["action"], "shift_sl_to_entry")

    def test_price_distance_1r_trigger_buy_and_sell(self):
        """Verify +1.0R price distance trigger on BUY and SELL positions."""
        # BUY: open=1.1000, sl=1.0970 (stop_dist=0.0030)
        # Price reaches 1.103001 (+0.003001 > +1.0R stop dist)
        pos_buy_1r = {
            "ticket": 202,
            "symbol": "EURUSD",
            "type": "BUY",
            "price_open": 1.10000,
            "price_current": 1.10305,
            "sl": 1.09700,
            "tp": 1.10900,
            "profit": 0.0,  # Zero profit reported by broker
            "volume": 0.01,
        }
        res_buy_1r = self.engine.check_breakeven_trigger(position=pos_buy_1r)
        self.assertTrue(res_buy_1r["trigger"])
        self.assertEqual(res_buy_1r["new_sl"], 1.10000)

        # SELL: open=1.1000, sl=1.1030 (stop_dist=0.0030)
        # Price drops to 1.09695 (-0.00305 > +1.0R stop dist)
        pos_sell_1r = {
            "ticket": 203,
            "symbol": "EURUSD",
            "type": "SELL",
            "price_open": 1.10000,
            "price_current": 1.09695,
            "sl": 1.10300,
            "tp": 1.09100,
            "profit": 0.0,
            "volume": 0.01,
        }
        res_sell_1r = self.engine.check_breakeven_trigger(position=pos_sell_1r)
        self.assertTrue(res_sell_1r["trigger"])
        self.assertEqual(res_sell_1r["new_sl"], 1.10000)

    def test_idempotency_and_already_protected_state(self):
        """Verify that positions already at breakeven or trailing in profit do not trigger redundant mutations."""
        # BUY: SL already moved to entry 1.1000
        pos_buy_protected = {
            "ticket": 204,
            "symbol": "EURUSD",
            "type": "BUY",
            "price_open": 1.10000,
            "price_current": 1.10500,
            "sl": 1.10000,
            "tp": 1.10900,
            "profit": 15.00,
        }
        res_buy = self.engine.check_breakeven_trigger(position=pos_buy_protected)
        self.assertFalse(res_buy["trigger"])
        self.assertEqual(res_buy["action"], "already_protected")

        # BUY: SL already trailing higher than entry (1.1020 > 1.1000)
        pos_buy_trailing = dict(pos_buy_protected, sl=1.10200)
        res_trailing = self.engine.check_breakeven_trigger(position=pos_buy_trailing)
        self.assertFalse(res_trailing["trigger"])
        self.assertEqual(res_trailing["action"], "already_protected")

        # SELL: SL already moved to entry 1.1000
        pos_sell_protected = {
            "ticket": 205,
            "symbol": "EURUSD",
            "type": "SELL",
            "price_open": 1.10000,
            "price_current": 1.09500,
            "sl": 1.10000,
            "tp": 1.09100,
            "profit": 15.00,
        }
        res_sell = self.engine.check_breakeven_trigger(position=pos_sell_protected)
        self.assertFalse(res_sell["trigger"])
        self.assertEqual(res_sell["action"], "already_protected")

    def test_malformed_and_boundary_position_inputs(self):
        """Verify robust handling of invalid tickets, missing fields, or negative prices."""
        # Zero entry price
        pos_zero_open = {"ticket": 999, "symbol": "EURUSD", "price_open": 0.0, "sl": 1.0800}
        res_zero = self.engine.check_breakeven_trigger(position=pos_zero_open)
        self.assertFalse(res_zero["trigger"])
        self.assertEqual(res_zero["action"], "hold")

        # Empty dictionary
        res_empty = self.engine.check_breakeven_trigger(position={})
        self.assertFalse(res_empty["trigger"])


class TestMultiAccountAutoSwitchingStress(unittest.TestCase):
    """Domain 3: Multi-Account Auto-Switching between FTMO-Demo (#1514382598) and Vebson-Server (#5054542)."""

    def setUp(self):
        self.engine = PipdanceFastTrackEngine()
        self.connector = MT5Connector(simulation_mode=True)
        self.risk_service = PortfolioRiskService()

    def test_routing_resolution_by_login_id(self):
        """Verify profile routing by exact integer or string login IDs."""
        # FTMO Demo
        prof_ftmo = self.engine.route_account(login_id=1514382598)
        self.assertEqual(prof_ftmo["login"], 1514382598)
        self.assertEqual(prof_ftmo["server"], "FTMO-Demo")
        self.assertEqual(prof_ftmo["starting_balance"], 100000.0)
        self.assertEqual(prof_ftmo["max_risk_usd_cap"], 750.0)
        self.assertEqual(prof_ftmo["hard_floor_equity"], 90000.0)
        self.assertEqual(prof_ftmo["phase_1_profit_target_pct"], 10.0)
        self.assertEqual(prof_ftmo["min_trading_days"], 4)

        # Pipdance / Vebson
        prof_vebson = self.engine.route_account(login_id=5054542)
        self.assertEqual(prof_vebson["login"], 5054542)
        self.assertEqual(prof_vebson["server"], "Vebson-Server")
        self.assertEqual(prof_vebson["starting_balance"], 1000.0)
        self.assertEqual(prof_vebson["max_risk_usd_cap"], 7.50)
        self.assertEqual(prof_vebson["hard_floor_equity"], 900.0)
        self.assertEqual(prof_vebson["phase_1_profit_target_pct"], 8.0)
        self.assertEqual(prof_vebson["min_trading_days"], 2)

    def test_routing_resolution_by_server_name(self):
        """Verify profile routing by server name substrings."""
        for srv in ["FTMO-Demo", "ftmo-demo", "FTMO_SERVER", "ftmo"]:
            with self.subTest(server=srv):
                prof = self.engine.route_account(server_name=srv)
                self.assertEqual(prof["login"], 1514382598)
                self.assertEqual(prof["account_type"], "FTMO_100K_DEMO")

        for srv in ["Vebson-Server", "vebson-server", "VEBSON", "PIPDANCE_FAST"]:
            with self.subTest(server=srv):
                prof = self.engine.route_account(server_name=srv)
                self.assertEqual(prof["login"], 5054542)
                self.assertEqual(prof["account_type"], "PIPDANCE_1K_FAST_TRACK")

    def test_mt5_connector_bidirectional_switching(self):
        """Verify MT5Connector switches execution state and updates balance without crosstalk."""
        # 1. Switch to FTMO $100k
        ok1 = self.connector.switch_account(login=1514382598, server="FTMO-Demo")
        self.assertTrue(ok1)
        self.assertEqual(self.connector.active_login, 1514382598)
        self.assertEqual(self.connector.active_server, "FTMO-Demo")
        info1 = self.connector.get_account_info()
        self.assertEqual(info1["balance"], 100000.0)
        self.assertEqual(info1["equity"], 100000.0)

        # 2. Switch to Vebson $1k
        ok2 = self.connector.switch_account(login=5054542, server="Vebson-Server")
        self.assertTrue(ok2)
        self.assertEqual(self.connector.active_login, 5054542)
        self.assertEqual(self.connector.active_server, "Vebson-Server")
        info2 = self.connector.get_account_info()
        self.assertEqual(info2["balance"], 1000.0)
        self.assertEqual(info2["equity"], 1000.0)

        # 3. Switch back to FTMO $100k
        ok3 = self.connector.switch_account(login=1514382598, server="FTMO-Demo")
        self.assertTrue(ok3)
        self.assertEqual(self.connector.active_login, 1514382598)
        info3 = self.connector.get_account_info()
        self.assertEqual(info3["balance"], 100000.0)

    def test_portfolio_risk_multi_account_isolation(self):
        """Verify PortfolioRiskService maintains independent risk caps and floor limits for both accounts."""
        acc_ftmo = self.risk_service.get_account("1514382598")
        acc_pipdance = self.risk_service.get_account("5054542")

        self.assertIsNotNone(acc_ftmo)
        self.assertIsNotNone(acc_pipdance)

        self.assertEqual(acc_ftmo.starting_balance, 100000.0)
        self.assertEqual(acc_ftmo.max_risk_usd_cap, 750.0)
        self.assertEqual(acc_ftmo.trailing_hwm_floor, 90000.0)

        self.assertEqual(acc_pipdance.starting_balance, 1000.0)
        self.assertEqual(acc_pipdance.max_risk_usd_cap, 7.50)
        self.assertEqual(acc_pipdance.trailing_hwm_floor, 900.0)


class TestBlackRockAladdinVaRCVaRMathematicalVerification(unittest.TestCase):
    """Domain 4: BlackRock Aladdin 1-Day 99% VaR and CVaR Formula Mathematical Verification."""

    def setUp(self):
        self.aladdin = AladdinRiskEngine(max_portfolio_var_pct=0.015, cvar_confidence=0.99)
        self.risk_service = PortfolioRiskService(max_portfolio_var_pct=1.5)
        self.norm_dist = statistics.NormalDist(mu=0, sigma=1)

    def test_statistical_distribution_constants(self):
        """Verify analytical Z-score and Standard Normal PDF values against statistics.NormalDist."""
        # 99% confidence: Z_99 = 2.326348
        # Standard normal PDF phi(z) = 1/sqrt(2*pi) * exp(-0.5 * z^2)
        z_99_exact = self.norm_dist.inv_cdf(0.99)
        z_99_engine = 2.326348
        self.assertAlmostEqual(z_99_engine, z_99_exact, places=5)

        pdf_99_exact = self.norm_dist.pdf(z_99_exact)
        pdf_99_engine = self.aladdin._std_norm_pdf(z_99_engine)
        self.assertAlmostEqual(pdf_99_engine, pdf_99_exact, places=6)

        # Expected Shortfall multiplier: phi(z_99) / (1 - 0.99) = 0.02665214 / 0.01 = 2.665214
        cvar_multiplier_exact = pdf_99_exact / 0.01
        cvar_multiplier_engine = pdf_99_engine / 0.01
        self.assertAlmostEqual(cvar_multiplier_engine, cvar_multiplier_exact, places=5)
        self.assertGreater(cvar_multiplier_engine, z_99_engine, "CVaR multiplier must be strictly greater than VaR quantile")

    def test_parametric_var_and_cvar_formula_ftmo_100k(self):
        """Verify exact mathematical dollar and percentage outputs for FTMO $100k account."""
        equity = 100000.0
        daily_vol = 0.006  # 0.6% daily vol

        res = self.aladdin.compute_parametric_var_cvar(equity=equity, daily_volatility=daily_vol)

        # Expected calculations:
        # VaR_99 = 100,000 * 2.326348 * 0.006 = $1,395.81 (1.40%)
        # CVaR_99 = 100,000 * 0.006 * 2.665214 = $1,599.13 (1.60%)
        # VaR_95 = 100,000 * 1.644853 * 0.006 = $986.91 (0.99%)
        expected_var_99 = round(equity * 2.326348 * daily_vol, 2)
        expected_cvar_99 = round(equity * daily_vol * (self.aladdin._std_norm_pdf(2.326348) / 0.01), 2)
        expected_var_95 = round(equity * 1.644853 * daily_vol, 2)

        self.assertAlmostEqual(res["var_99_dollar"], expected_var_99, places=2)
        self.assertAlmostEqual(res["cvar_99_dollar"], expected_cvar_99, places=2)
        self.assertAlmostEqual(res["var_95_dollar"], expected_var_95, places=2)

        # Coherence order check: CVaR_99 > VaR_99 > VaR_95
        self.assertGreater(res["cvar_99_dollar"], res["var_99_dollar"])
        self.assertGreater(res["var_99_dollar"], res["var_95_dollar"])

    def test_parametric_var_and_cvar_formula_pipdance_1k(self):
        """Verify exact mathematical dollar and percentage outputs for Pipdance $1,000 account."""
        equity = 1000.0
        daily_vol = 0.008  # 0.8% daily vol

        res = self.aladdin.compute_parametric_var_cvar(equity=equity, daily_volatility=daily_vol)

        # VaR_99 = 1,000 * 2.326348 * 0.008 = $18.61 (1.86%)
        # CVaR_99 = 1,000 * 0.008 * 2.665214 = $21.32 (2.13%)
        expected_var_99 = round(equity * 2.326348 * daily_vol, 2)
        expected_cvar_99 = round(equity * daily_vol * (self.aladdin._std_norm_pdf(2.326348) / 0.01), 2)

        self.assertAlmostEqual(res["var_99_dollar"], expected_var_99, places=2)
        self.assertAlmostEqual(res["cvar_99_dollar"], expected_cvar_99, places=2)
        self.assertGreater(res["cvar_99_dollar"], res["var_99_dollar"])

    def test_positive_homogeneity_scaling(self):
        """Verify positive homogeneity: VaR(k * Equity) == k * VaR(Equity)."""
        vol = 0.010
        base_res = self.aladdin.compute_parametric_var_cvar(equity=1000.0, daily_volatility=vol)
        scaled_res = self.aladdin.compute_parametric_var_cvar(equity=100000.0, daily_volatility=vol)

        # Scaled by 100x
        self.assertAlmostEqual(scaled_res["var_99_dollar"], 100.0 * base_res["var_99_dollar"], delta=1.0)
        self.assertAlmostEqual(scaled_res["cvar_99_dollar"], 100.0 * base_res["cvar_99_dollar"], delta=1.0)
        # Percentage VaR must be identical
        self.assertEqual(base_res["var_99_pct"], scaled_res["var_99_pct"])


class TestNewsBlackoutBoundaryConditionsStress(unittest.TestCase):
    """Domain 5: 15-Minute News Blackout Boundary Conditions Stress Tests."""

    def setUp(self):
        self.radar = EconomicCalendarRadar(blackout_minutes_before=15, blackout_minutes_after=15)
        self.radar.clear_events()
        # Mock fetch_live_calendar to return only manual_events for isolated mathematical testing
        self.radar.fetch_live_calendar = lambda: self.radar.manual_events

    def test_exact_time_boundary_intervals(self):
        """
        Stress test exact time boundaries around a scheduled high-impact event at T_0 (2026-08-28 12:30:00 UTC).
        - Window is [T_0 - 15m, T_0 + 15m] = [12:15:00, 12:45:00].
        """
        event_time = datetime.datetime(2026, 8, 28, 12, 30, 0, tzinfo=datetime.timezone.utc)
        self.radar.inject_event(
            title="US Non-Farm Payrolls & Unemployment Rate",
            currency="USD",
            event_time_utc=event_time,
            impact="HIGH",
        )

        test_points = [
            # (eval_time, expected_blackout, expected_cleared, description)
            (event_time - datetime.timedelta(minutes=16), False, True, "16 mins before: Outside window"),
            (event_time - datetime.timedelta(minutes=15, seconds=1), False, True, "15m 1s before: Outside window"),
            (event_time - datetime.timedelta(minutes=15, seconds=0), True, False, "Exact 15m before: Pre-lockout boundary hit"),
            (event_time - datetime.timedelta(minutes=10), True, False, "10m before: Deep pre-lockout"),
            (event_time - datetime.timedelta(minutes=1), True, False, "1m before: Immediate pre-lockout"),
            (event_time, True, False, "Exact T_0 release time: Active event"),
            (event_time + datetime.timedelta(minutes=1), True, False, "1m after: Post-release cooldown"),
            (event_time + datetime.timedelta(minutes=10), True, False, "10m after: Deep post-release cooldown"),
            (event_time + datetime.timedelta(minutes=15, seconds=0), True, False, "Exact 15m after: Post-lockout boundary hit"),
            (event_time + datetime.timedelta(minutes=15, seconds=1), False, True, "15m 1s after: Outside window"),
            (event_time + datetime.timedelta(minutes=20), False, True, "20m after: Cleared"),
        ]

        for eval_dt, exp_blackout, exp_cleared, desc in test_points:
            with self.subTest(case=desc, eval_dt=eval_dt.isoformat()):
                res = self.radar.evaluate_news_clearance(symbol="EURUSD", current_time=eval_dt, check_weekend=False)
                self.assertEqual(res["is_blackout"], exp_blackout, f"{desc}: expected blackout={exp_blackout}, got {res['is_blackout']}")
                self.assertEqual(res["is_cleared"], exp_cleared, f"{desc}: expected cleared={exp_cleared}, got {res['is_cleared']}")

    def test_multi_currency_lockout_matrix(self):
        """Verify cross-currency isolation and correlated symbol lockouts during USD, EUR, GBP, and CAD events."""
        event_time = datetime.datetime(2026, 8, 28, 14, 0, 0, tzinfo=datetime.timezone.utc)
        now_dt = event_time - datetime.timedelta(minutes=5)  # Inside 15m window

        # 1. USD High-Impact Event
        self.radar.clear_events()
        self.radar.inject_event(title="US CPI YoY", currency="USD", event_time_utc=event_time, impact="HIGH")

        # USD pairs and USD commodities/crypto must be locked
        for sym in ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "USDCHF", "XAUUSD", "BTCUSD", "ETHUSD", "SOLUSD"]:
            with self.subTest(event="USD", symbol=sym):
                res = self.radar.evaluate_news_clearance(symbol=sym, current_time=now_dt, check_weekend=False)
                self.assertTrue(res["is_blackout"], f"{sym} should be locked by USD event")

        # Non-USD cross pairs should be cleared
        for sym in ["EURGBP", "EURJPY", "GBPJPY", "AUDNZD", "EURCHF"]:
            with self.subTest(event="USD", symbol=sym):
                res = self.radar.evaluate_news_clearance(symbol=sym, current_time=now_dt, check_weekend=False)
                self.assertTrue(res["is_cleared"], f"{sym} should remain cleared during USD event")

        # 2. EUR High-Impact Event
        self.radar.clear_events()
        self.radar.inject_event(title="ECB Rate Decision", currency="EUR", event_time_utc=event_time, impact="HIGH")

        # EUR pairs must be locked
        for sym in ["EURUSD", "EURGBP", "EURJPY", "EURCHF"]:
            with self.subTest(event="EUR", symbol=sym):
                res = self.radar.evaluate_news_clearance(symbol=sym, current_time=now_dt, check_weekend=False)
                self.assertTrue(res["is_blackout"], f"{sym} should be locked by EUR event")

        # Non-EUR pairs should be cleared
        for sym in ["GBPUSD", "USDJPY", "USDCAD", "GBPJPY"]:
            with self.subTest(event="EUR", symbol=sym):
                res = self.radar.evaluate_news_clearance(symbol=sym, current_time=now_dt, check_weekend=False)
                self.assertTrue(res["is_cleared"], f"{sym} should remain cleared during EUR event")

    def test_fail_closed_clearance_policy(self):
        """Verify that when calendar service is unverified or empty, lockout fails closed."""
        calendar_svc = EconomicCalendarService()
        calendar_svc._events = []
        calendar_svc._calendar_verified = False
        calendar_svc._last_error = "Remote calendar connection timeout."

        locked, reason, event = calendar_svc.evaluate_symbol_lockout("EURUSD")
        self.assertTrue(locked, "Must fail closed when calendar is unverified")
        self.assertIn("fail-closed", reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
