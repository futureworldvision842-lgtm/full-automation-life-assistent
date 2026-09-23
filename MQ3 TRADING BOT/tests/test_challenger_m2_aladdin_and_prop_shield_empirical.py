"""
test_challenger_m2_aladdin_and_prop_shield_empirical.py
Empirical Challenger 1 Test Suite for Milestone 2:
- BlackRock Aladdin 1-Day 99% VaR, Analytical CVaR, Fractional Kelly under extreme edge cases.
- Start-of-Day (00:00 UTC) 2.5% daily drawdown hard shield under flash crashes and micro-cent boundaries.
- Funding Pips 2-Phase Adaptive Progression (Phase 1 -> Phase 2 -> Master Funded).
- Economic Calendar 15-minute News Circuit Breaker.
- Mandatory Stop-Loss & Take-Profit with min 1:2.0 R:R validation.
"""

import unittest
import math
import datetime
from datetime import timezone, timedelta
import numpy as np

from src.aladdin_risk_engine import AladdinRiskEngine
from src.fleet_risk_manager import FleetRiskManager
from src.funding_pips_expert import FundingPipsExpert
from src.economic_calendar_radar import EconomicCalendarRadar
from src.multi_account_auto_onboarder import MultiAccountAutoOnboarder


class TestAladdinExtremeAdversarialMath(unittest.TestCase):
    """
    Adversarial mathematical stress tests for BlackRock Aladdin Risk Engine.
    """

    def setUp(self):
        self.aladdin = AladdinRiskEngine()

    def test_var_cvar_zero_variance(self):
        """Zero volatility must yield 0 VaR and 0 CVaR without NaN or division errors."""
        res = self.aladdin.compute_parametric_var_cvar(equity=50000.0, daily_volatility=0.0)
        self.assertEqual(res["var_99_dollar"], 0.0)
        self.assertEqual(res["cvar_99_dollar"], 0.0)
        self.assertEqual(res["var_95_dollar"], 0.0)
        self.assertEqual(res["cvar_95_dollar"], 0.0)
        self.assertEqual(res["var_99_pct"], 0.0)
        self.assertEqual(res["cvar_99_pct"], 0.0)

    def test_var_cvar_sub_zero_equity_negative_returns(self):
        """Negative equity (e.g. gap loss / debt) must not produce unhandled math exceptions."""
        res = self.aladdin.compute_parametric_var_cvar(equity=-1000.0, daily_volatility=0.02)
        self.assertIsInstance(res["var_99_dollar"], float)
        self.assertIsInstance(res["cvar_99_dollar"], float)
        # Check percentage calculation has max(equity, 1.0) guard to prevent negative percentage inversion
        self.assertFalse(math.isnan(res["var_99_pct"]))
        self.assertFalse(math.isinf(res["var_99_pct"]))

    def test_var_cvar_black_swan_gap_shock_volatility(self):
        """Extreme black-swan market volatility shock (e.g. 500% annualized / 5.0 daily)."""
        equity = 100000.0
        daily_vol = 5.0  # 500% daily standard deviation shock
        res = self.aladdin.compute_parametric_var_cvar(equity=equity, daily_volatility=daily_vol)
        
        # Expected VaR = 100,000 * 2.326348 * 5.0 = 1,163,174.00
        self.assertEqual(res["var_99_dollar"], 1163174.0)
        # CVaR multiplier = phi(2.326348) / 0.01 = 0.02665214 / 0.01 = 2.665214
        # Expected CVaR = 100,000 * 5.0 * 2.665214 = 1,332,607.12
        self.assertGreater(res["cvar_99_dollar"], res["var_99_dollar"])
        self.assertAlmostEqual(res["cvar_99_dollar"] / res["var_99_dollar"], 1.14567, places=2)

    def test_cvar_strictly_dominates_var_at_all_confidence_levels(self):
        """Mathematical Invariant: CVaR_alpha > VaR_alpha for all alpha in (0, 1) when vol > 0."""
        equity = 25000.0
        for vol in [0.001, 0.01, 0.05, 0.20, 1.0]:
            res = self.aladdin.compute_parametric_var_cvar(equity, vol)
            self.assertGreater(res["cvar_99_dollar"], res["var_99_dollar"], f"Failed at vol {vol}")
            self.assertGreater(res["cvar_95_dollar"], res["var_95_dollar"], f"Failed at vol {vol}")

    def test_fractional_kelly_extreme_win_rate_and_haircut(self):
        """Fractional Kelly with uncertainty haircut (win_rate_se > win_rate)."""
        # win_rate = 0.02, win_rate_se = 0.05 -> adj_win_rate clamped to 0.05
        # Full Kelly is heavily negative -> Must return 0.0025 floor
        risk = self.aladdin.compute_fractional_kelly(win_rate=0.02, payoff_ratio=2.0, win_rate_se=0.05)
        self.assertEqual(risk, 0.0025)

    def test_fractional_kelly_zero_and_negative_payoff_ratio(self):
        """Fractional Kelly when payoff_ratio is 0 or negative."""
        risk_zero = self.aladdin.compute_fractional_kelly(win_rate=0.60, payoff_ratio=0.0)
        self.assertEqual(risk_zero, 0.0025)

        risk_neg = self.aladdin.compute_fractional_kelly(win_rate=0.60, payoff_ratio=-1.5)
        self.assertEqual(risk_neg, 0.0025)

    def test_fractional_kelly_perfect_win_rate_clamped_to_max_risk_cap(self):
        """Even with 100% win rate and 10.0 payoff, risk is strictly clamped to max_risk_cap_pct (0.75%)."""
        risk_max = self.aladdin.compute_fractional_kelly(win_rate=1.0, payoff_ratio=10.0, win_rate_se=0.0)
        self.assertEqual(risk_max, 0.0075)


class TestSODDailyDrawdownAndMicroCentShield(unittest.TestCase):
    """
    Stress-testing Start-of-Day (00:00 UTC) 2.5% daily drawdown hard shield under sudden flash crashes and micro-cent boundaries.
    """

    def setUp(self):
        self.test_config = "data/test_challenger_m2_sod_config.json"
        self.onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)
        self.onboarder.onboard_new_account(
            account_id="FP_25K_SHIELD",
            server="MetaQuotes-Demo",
            balance=25000.00,
            account_type="FUNDING_PIPS"
        )
        self.onboarder.onboard_new_account(
            account_id="FP_100K_SHIELD",
            server="MetaQuotes-Demo",
            balance=100000.00,
            account_type="FUNDING_PIPS"
        )
        self.risk_mgr = FleetRiskManager(config_path=self.test_config, auto_onboarder=self.onboarder)

    def test_micro_cent_drawdown_boundary_precision(self):
        """
        Micro-Cent Boundary Stress:
        For $25,000.00 baseline, 2.5% = $625.00000000.
        Case A: Loss = $624.9999 (Equity = $24,375.0001) -> SAFE
        Case B: Loss = $625.0000 (Equity = $24,375.0000) -> BREACH / LOCKOUT
        Case C: Loss = $625.0001 (Equity = $24,374.9999) -> BREACH / LOCKOUT
        """
        acc_id = "FP_25K_SHIELD"
        
        # Case A: $624.9999 loss
        res_a = self.risk_mgr.update_account_telemetry(acc_id, balance=24375.0001, equity=24375.0001)
        self.assertTrue(res_a["daily_loss_shield_ok"])
        self.assertFalse(res_a["is_locked_out"])

        # Case B: $625.0000 loss
        res_b = self.risk_mgr.update_account_telemetry(acc_id, balance=24375.0000, equity=24375.0000)
        self.assertFalse(res_b["daily_loss_shield_ok"])
        self.assertTrue(res_b["is_locked_out"])

        # Reset SOD
        self.risk_mgr.update_account_telemetry(acc_id, balance=25000.00, equity=25000.00, sod_reset=True)

        # Case C: $625.0001 loss
        res_c = self.risk_mgr.update_account_telemetry(acc_id, balance=24374.9999, equity=24374.9999)
        self.assertFalse(res_c["daily_loss_shield_ok"])
        self.assertTrue(res_c["is_locked_out"])

    def test_flash_crash_instantaneous_deactivation(self):
        """Sudden flash crash (e.g. 50% loss in 1 tick) immediately halts account and blocks all subsequent orders."""
        acc_id = "FP_100K_SHIELD"
        # 100k account drops to 50k in a flash crash
        res = self.risk_mgr.update_account_telemetry(acc_id, balance=50000.0, equity=50000.0)
        self.assertFalse(res["daily_loss_shield_ok"])
        self.assertFalse(res["trailing_floor_ok"])
        self.assertTrue(res["is_locked_out"])

        # Attempt to submit an order through pre-trade risk interceptor
        approved, reason = self.risk_mgr.validate_pre_trade_risk(
            account_id=acc_id, symbol="EURUSD", lot_size=0.10, side="BUY", entry_price=1.0850, sl_price=1.0800
        )
        self.assertFalse(approved)
        self.assertIn("Account locked out", reason)

    def test_trailing_hwm_profit_lock_invariant(self):
        """
        Funding Pips Profit Lock Invariant:
        When account scales from $25,000 to $27,000 (+8% evaluation target passed),
        Trailing floor ($27,000 - $1,500 = $25,500) is strictly > $25,000 starting balance.
        Initial capital is permanently locked from risk.
        """
        acc_id = "FP_25K_SHIELD"
        res = self.risk_mgr.update_account_telemetry(acc_id, balance=27000.0, equity=27000.0)
        self.assertEqual(res["absolute_hwm"], 27000.0)
        self.assertEqual(res["trailing_hwm_floor"], 25500.0)
        self.assertGreater(res["trailing_hwm_floor"], 25000.0)

        st = self.risk_mgr.get_account_state(acc_id)
        self.assertTrue(st.get("hwm_locked_at_starting_balance", False))


class TestFundingPips2PhaseAdaptiveAndRules(unittest.TestCase):
    """
    Verification of 2-Phase Adaptive Prop Firm Challenge Engine & Compliance Rules.
    """

    def test_2_phase_adaptive_progression(self):
        """
        Phase 1: 8% target ($2,000 on 25k) -> 0.75% risk
        Phase 2: 5% target ($1,250 on 25k) -> 0.50% risk
        Master Funded: Capital Preservation -> 0.35% risk
        """
        expert = FundingPipsExpert("25k")
        
        # 1. Starting phase (0% profit)
        p1 = expert.evaluate_phase_progression(current_equity=25000.0)
        self.assertEqual(p1["current_phase"], "PHASE_1_STUDENT")
        self.assertEqual(p1["suggested_risk_per_trade_pct"], 0.75)
        self.assertEqual(p1["active_target_pct"], 8.0)

        # 2. Phase 1 completed (+8.5% profit = $27,125)
        p2 = expert.evaluate_phase_progression(current_equity=27125.0)
        self.assertEqual(p2["current_phase"], "PHASE_2_PRACTITIONER")
        self.assertEqual(p2["suggested_risk_per_trade_pct"], 0.50)
        self.assertEqual(p2["active_target_pct"], 5.0)

        # 3. Phase 2 completed (+14.0% profit = $28,500)
        p3 = expert.evaluate_phase_progression(current_equity=28500.0)
        self.assertEqual(p3["current_phase"], "MASTER_FUNDED_ACCOUNT")
        self.assertEqual(p3["suggested_risk_per_trade_pct"], 0.35)
        self.assertEqual(p3["active_target_pct"], 0.0)

    def test_mandatory_sl_tp_and_minimum_rr_enforcement(self):
        """Mandatory SL/TP and minimum Risk-to-Reward ratio."""
        expert = FundingPipsExpert("25k")

        # Missing SL
        audit_no_sl = expert.audit_trade("EURUSD", "BUY", price=1.0850, sl=0.0, tp=1.0950, current_open_count=0)
        self.assertFalse(audit_no_sl["passed"])

        # Missing TP
        audit_no_tp = expert.audit_trade("EURUSD", "BUY", price=1.0850, sl=1.0800, tp=0.0, current_open_count=0)
        self.assertFalse(audit_no_tp["passed"])

        # Sub-minimum R:R (< 1:1 floor on base audit)
        audit_bad_rr = expert.audit_trade("EURUSD", "BUY", price=1.0850, sl=1.0800, tp=1.0820, current_open_count=0)
        self.assertFalse(audit_bad_rr["passed"])

        # Valid 1:2.0 R:R
        audit_valid = expert.audit_trade("EURUSD", "BUY", price=1.0850, sl=1.0800, tp=1.0950, current_open_count=0)
        self.assertTrue(audit_valid["passed"])


class TestNewsCircuitBreakerEmpirical(unittest.TestCase):
    """
    Verification of 15-minute Pre-News Circuit Breakers and Judas Wick Filter.
    """

    def setUp(self):
        self.radar = EconomicCalendarRadar(blackout_minutes_before=15, blackout_minutes_after=15)
        self.radar.clear_events()

    def test_15_minute_pre_news_blackout_trigger(self):
        """Event in exactly 10 minutes must trigger PRE_NEWS_BLACKOUT for affected currency cross."""
        now_utc = datetime.datetime.now(timezone.utc)
        event_time = now_utc + timedelta(minutes=10)
        
        self.radar.inject_event(
            title="US Non-Farm Payrolls (NFP)",
            currency="USD",
            event_time_utc=event_time,
            impact="HIGH"
        )

        clearance_xau = self.radar.evaluate_news_clearance(symbol="XAUUSD", current_time=now_utc, check_weekend=False)
        self.assertFalse(clearance_xau["is_cleared"])
        self.assertTrue(clearance_xau["is_blackout"])
        self.assertIn("PRE_NEWS_BLACKOUT", clearance_xau["lockout_reason"])

    def test_15_minute_post_news_blackout_trigger(self):
        """Event that occurred 8 minutes ago must remain in POST_NEWS_BLACKOUT cooloff."""
        now_utc = datetime.datetime.now(timezone.utc)
        event_time = now_utc - timedelta(minutes=8)
        
        self.radar.inject_event(
            title="US CPI YoY",
            currency="USD",
            event_time_utc=event_time,
            impact="HIGH"
        )

        clearance_eur = self.radar.evaluate_news_clearance(symbol="EURUSD", current_time=now_utc, check_weekend=False)
        self.assertFalse(clearance_eur["is_cleared"])
        self.assertTrue(clearance_eur["is_blackout"])
        self.assertIn("POST_NEWS_BLACKOUT", clearance_eur["lockout_reason"])

    def test_outside_blackout_window_cleared(self):
        """Event in 30 minutes (> 15 min buffer) is CLEARED to trade."""
        now_utc = datetime.datetime.now(timezone.utc)
        event_time = now_utc + timedelta(minutes=30)
        
        self.radar.inject_event(
            title="FOMC Statement",
            currency="USD",
            event_time_utc=event_time,
            impact="HIGH"
        )

        clearance = self.radar.evaluate_news_clearance(symbol="XAUUSD", current_time=now_utc, check_weekend=False)
        self.assertTrue(clearance["is_cleared"])
        self.assertFalse(clearance["is_blackout"])
        self.assertEqual(clearance["upcoming_events_count"], 1)


if __name__ == "__main__":
    unittest.main()
