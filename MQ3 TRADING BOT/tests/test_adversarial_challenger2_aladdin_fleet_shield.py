"""
tests/test_adversarial_challenger2_aladdin_fleet_shield.py
========================================================================================
CHALLENGER 2 EMPIRICAL ADVERSARIAL STRESS TEST SUITE
BlackRock Aladdin Risk Governance, 2.5% SOD Drawdown Shield & Fleet Multi-Account Gating
========================================================================================

Focus Areas:
1. Start-of-Day (SOD 00:00 UTC) 2.5% Daily Drawdown Shield:
   - Micro-cent boundary equity testing across 5k, 25k, 50k, 100k accounts.
   - Simulated flash crashes (50% instantaneous drawdown) and pre-trade order deactivation.
   - Multi-tick rapid adverse fill cascades and persistent session lockout.
   - Rolling multi-day SOD resets and baseline equity shifting.
2. Aladdin 1-Day 99% VaR/CVaR, 3-Sigma Pre-Trade Stress, and Trailing HWM Floor Ratchet:
   - Analytical VaR (99%) and CVaR (Expected Shortfall) mathematical invariant audits.
   - Extreme volatility (500% shock), zero-volatility, negative equity mathematical robustness.
   - Uncertainty-adjusted Fractional Kelly position sizing bounds [0.25% floor, 0.75% ceiling].
   - 3-sigma multi-asset pre-trade gap stress testing against 80% daily loss allowance.
3. Trailing HWM Floor Ratchet & Capital Protection:
   - 1,000-step volatile sawtooth random walk floor monotonicity (Floor[t] >= Floor[t-1]).
   - Milestone profit lock-in: Once account passes evaluation target (+8%), starting capital is 100% shielded.
   - Trailing floor breach triggering lockout even when daily loss is within safe limits.
4. Multi-Account Fleet Gating & Cross-Account Isolation:
   - Funding Pips rule matrix enforcement across 5k, 25k, 50k, and 100k accounts.
   - Strict account risk isolation (disaster on 5k/100k does NOT contaminate other accounts).
   - 5-stage consistency pacing classifier boundary tests across all tiers (<20%, 20-25%, 25-30%, 30-35%, >35%).
   - Dynamic lot sizing precision and asset-specific clamping across all account tiers.
"""

import os
import math
import random
import unittest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import numpy as np

from src.aladdin_risk_engine import AladdinRiskEngine
from src.funding_pips_expert import FundingPipsExpert
from src.fleet_risk_manager import FleetRiskManager
from src.multi_account_auto_onboarder import MultiAccountAutoOnboarder
from src.multi_account_manager import MultiAccountManager


class TestSOD25DailyDrawdownShieldAdversarial(unittest.TestCase):
    """
    Adversarial stress testing of the Start-of-Day 2.5% Daily Drawdown Shield.
    """

    def setUp(self):
        self.test_config = "data/test_challenger2_sod_fleet_config.json"
        self.onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)
        
        # Onboard representative accounts
        self.onboarder.onboard_new_account("FP_5K", "FundingPips-Server", 5000.0, "5k")
        self.onboarder.onboard_new_account("FP_25K", "MetaQuotes-Demo", 25000.0, "25k")
        self.onboarder.onboard_new_account("FP_50K", "FundingPips-Server", 50000.0, "50k")
        self.onboarder.onboard_new_account("FP_100K", "FundingPips-Server", 100000.0, "100k")
        
        self.risk_mgr = FleetRiskManager(config_path=self.test_config, auto_onboarder=self.onboarder)

    def tearDown(self):
        if os.path.exists(self.test_config):
            try:
                os.remove(self.test_config)
            except Exception:
                pass

    def test_micro_cent_boundary_equity_all_four_tiers(self):
        """
        Tests exact micro-cent boundary behavior for 2.5% daily drawdown across 5k, 25k, 50k, 100k tiers:
          - 5k ($5,000 baseline): 2.5% = $125.00 limit. (Loss $124.99 -> SAFE, Loss $125.00 -> LOCKOUT, Loss $125.01 -> LOCKOUT)
          - 25k ($25,000 baseline): 2.5% = $625.00 limit. (Loss $624.99 -> SAFE, Loss $625.00 -> LOCKOUT, Loss $625.01 -> LOCKOUT)
          - 50k ($50,000 baseline): 2.5% = $1,250.00 limit. (Loss $1,249.99 -> SAFE, Loss $1,250.00 -> LOCKOUT, Loss $1,250.01 -> LOCKOUT)
          - 100k ($100,000 baseline): 2.5% = $2,500.00 limit. (Loss $2,499.99 -> SAFE, Loss $2,500.00 -> LOCKOUT, Loss $2,500.01 -> LOCKOUT)
        """
        tiers = [
            ("FP_5K", 5000.0, 125.0),
            ("FP_25K", 25000.0, 625.0),
            ("FP_50K", 50000.0, 1250.0),
            ("FP_100K", 100000.0, 2500.0),
        ]

        for acc_id, start_bal, max_loss in tiers:
            # 1. Just below threshold (Loss = max_loss - $0.01) -> SAFE
            safe_equity = start_bal - max_loss + 0.01
            res_safe = self.risk_mgr.update_account_telemetry(acc_id, balance=safe_equity, equity=safe_equity)
            self.assertTrue(res_safe["daily_loss_shield_ok"], f"{acc_id}: Loss ${max_loss - 0.01:.2f} must be SAFE")
            self.assertFalse(res_safe["is_locked_out"], f"{acc_id}: Should not be locked out at safe equity")

            # 2. Exactly on boundary (Loss = max_loss) -> BREACH / LOCKOUT
            boundary_equity = start_bal - max_loss
            res_exact = self.risk_mgr.update_account_telemetry(acc_id, balance=boundary_equity, equity=boundary_equity)
            self.assertFalse(res_exact["daily_loss_shield_ok"], f"{acc_id}: Exact loss ${max_loss:.2f} must trigger breach")
            self.assertTrue(res_exact["is_locked_out"], f"{acc_id}: Must be locked out on exact boundary")

            # Reset SOD for next check
            self.risk_mgr.update_account_telemetry(acc_id, balance=start_bal, equity=start_bal, sod_reset=True)

            # 3. Beyond boundary (Loss = max_loss + $0.01) -> BREACH / LOCKOUT
            breach_equity = start_bal - max_loss - 0.01
            res_breach = self.risk_mgr.update_account_telemetry(acc_id, balance=breach_equity, equity=breach_equity)
            self.assertFalse(res_breach["daily_loss_shield_ok"], f"{acc_id}: Loss ${max_loss + 0.01:.2f} must trigger breach")
            self.assertTrue(res_breach["is_locked_out"], f"{acc_id}: Must be locked out beyond boundary")

    def test_simulated_flash_crash_instantaneous_deactivation(self):
        """
        Simulates a catastrophic 50% flash crash on Gold & Crypto.
        Asserts:
          1. Risk telemetry flags daily drawdown and trailing floor breaches immediately.
          2. Account state is marked `is_locked_out = True`.
          3. Pre-trade risk interceptor blocks 100% of all subsequent orders.
        """
        acc_id = "FP_100K"
        # 50% flash crash from $100k to $50k
        res = self.risk_mgr.update_account_telemetry(acc_id, balance=50000.0, equity=50000.0)
        self.assertFalse(res["daily_loss_shield_ok"])
        self.assertFalse(res["trailing_floor_ok"])
        self.assertTrue(res["is_locked_out"])
        self.assertIn("DAILY LOSS SHIELD BREACHED", res["lockout_reason"])

        # Attempt multiple orders across assets — all must be rejected
        test_orders = [
            ("XAUUSD", 0.50, "BUY", 2650.0, 2636.0),
            ("EURUSD", 1.00, "BUY", 1.0850, 1.0800),
            ("BTCUSD", 0.10, "SELL", 60000.0, 61000.0),
        ]
        for sym, lots, side, ep, sl in test_orders:
            approved, reason = self.risk_mgr.validate_pre_trade_risk(
                account_id=acc_id, symbol=sym, lot_size=lots, side=side, entry_price=ep, sl_price=sl
            )
            self.assertFalse(approved, f"Order {sym} must be blocked on locked account")
            self.assertIn("Account locked out", reason)

    def test_rapid_adverse_fill_cascade_lockout(self):
        """
        Simulates a rapid sequence of 10 micro-loss fills on a 25k account ($625 daily cap).
        Verifies that the exact fill exceeding $625 triggers lockout and arrests further exposure.
        """
        acc_id = "FP_25K"
        current_equity = 25000.0
        step_loss = 70.0  # $70 loss per step

        # Steps 1 to 8: Cumulative loss $70 * 8 = $560 (< $625 cap) -> Safe
        for step in range(1, 9):
            current_equity -= step_loss
            res = self.risk_mgr.update_account_telemetry(acc_id, balance=current_equity, equity=current_equity)
            self.assertTrue(res["daily_loss_shield_ok"], f"Step {step} ($560 loss) should be safe")
            self.assertFalse(res["is_locked_out"])

        # Step 9: Cumulative loss $70 * 9 = $630 (>= $625 cap) -> BREACH & LOCKOUT
        current_equity -= step_loss
        res_trip = self.risk_mgr.update_account_telemetry(acc_id, balance=current_equity, equity=current_equity)
        self.assertFalse(res_trip["daily_loss_shield_ok"], "Step 9 ($630 loss) must trigger daily drawdown shield")
        self.assertTrue(res_trip["is_locked_out"])

        # Subsequent step must remain locked out
        current_equity -= step_loss
        res_after = self.risk_mgr.update_account_telemetry(acc_id, balance=current_equity, equity=current_equity)
        self.assertTrue(res_after["is_locked_out"])

    def test_rolling_multi_day_sod_resets_and_baseline_shifting(self):
        """
        Tests rolling multi-day SOD resets with equity growth and subsequent drawdown.
        Verifies that the daily shield resets strictly relative to the 00:00 UTC watermark.
        """
        acc_id = "FP_50K"
        # Day 1: Starting at $50,000, grow to $52,000 (+ $2,000 profit)
        r1 = self.risk_mgr.update_account_telemetry(acc_id, balance=52000.0, equity=52000.0)
        self.assertTrue(r1["daily_loss_shield_ok"])
        self.assertEqual(r1["daily_loss_dollars"], 0.0)

        # Day 2: 00:00 UTC Reset -> SOD baseline is now $52,000 (Daily loss cap is 2.5% of $50k profile cap: $1,250)
        r2 = self.risk_mgr.update_account_telemetry(acc_id, balance=52000.0, equity=52000.0, sod_reset=True)
        self.assertEqual(r2["daily_sod_equity"], 52000.0)
        self.assertFalse(r2["is_locked_out"])

        # Day 2: Drop to $50,800 ($1,200 intraday loss from Day 2 SOD $52k, under $1,250 cap) -> SAFE
        r3 = self.risk_mgr.update_account_telemetry(acc_id, balance=50800.0, equity=50800.0)
        self.assertTrue(r3["daily_loss_shield_ok"])
        self.assertEqual(r3["daily_loss_dollars"], 1200.0)

        # Day 2: Drop further to $50,700 ($1,300 intraday loss from Day 2 SOD $52k >= $1,250 cap) -> BREACH
        # Even though equity ($50,700) is ABOVE starting balance ($50,000), Day 2 SOD shield triggers!
        r4 = self.risk_mgr.update_account_telemetry(acc_id, balance=50700.0, equity=50700.0)
        self.assertFalse(r4["daily_loss_shield_ok"])
        self.assertTrue(r4["is_locked_out"])


class TestAladdinVaRCVaRAnd3SigmaPreTradeStress(unittest.TestCase):
    """
    Adversarial stress testing of BlackRock Aladdin Risk Engine:
    VaR 99%, CVaR, Fractional Kelly, and 3-Sigma Pre-Trade Stress Tests.
    """

    def setUp(self):
        self.aladdin = AladdinRiskEngine(
            max_portfolio_var_pct=0.015,
            cvar_confidence=0.99,
            kelly_fraction=0.20,
            max_risk_cap_pct=0.0075
        )

    def test_var_cvar_mathematical_invariants_and_ratios(self):
        """
        Adversarially tests analytical properties:
          1. VaR(99%) = Equity * 2.326348 * vol
          2. CVaR(99%) = Equity * vol * (pdf(2.326348) / 0.01)
          3. CVaR(99%) > VaR(99%) strictly holds for all non-zero volatilities.
          4. Theoretical ratio CVaR(99%) / VaR(99%) is approximately 1.14567.
        """
        equity = 25000.0
        test_vols = [0.005, 0.01, 0.02, 0.05, 0.10, 0.50]

        for vol in test_vols:
            res = self.aladdin.compute_parametric_var_cvar(equity, vol)
            
            # Expected calculations
            expected_var_99 = equity * 2.326348 * vol
            pdf_z = (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * 2.326348 * 2.326348)
            expected_cvar_99 = equity * vol * (pdf_z / 0.01)

            self.assertAlmostEqual(res["var_99_dollar"], round(expected_var_99, 2), places=1)
            self.assertAlmostEqual(res["cvar_99_dollar"], round(expected_cvar_99, 2), places=1)
            self.assertGreater(res["cvar_99_dollar"], res["var_99_dollar"], f"CVaR must exceed VaR at vol {vol}")
            
            ratio = res["cvar_99_dollar"] / res["var_99_dollar"]
            self.assertAlmostEqual(ratio, 1.14567, places=2)

    def test_var_cvar_extreme_boundary_shocks(self):
        """
        Tests mathematical boundaries:
          - Zero volatility (vol = 0.0): Returns 0 without division by zero.
          - Hyper-volatility (vol = 5.0 / 500% daily shock).
          - Sub-zero equity (debt / liquidation deficit): Handled gracefully without crash.
        """
        # Zero volatility
        res_zero = self.aladdin.compute_parametric_var_cvar(equity=50000.0, daily_volatility=0.0)
        self.assertEqual(res_zero["var_99_dollar"], 0.0)
        self.assertEqual(res_zero["cvar_99_dollar"], 0.0)

        # 500% volatility shock
        res_hyper = self.aladdin.compute_parametric_var_cvar(equity=100000.0, daily_volatility=5.0)
        self.assertEqual(res_hyper["var_99_dollar"], 1163174.0)
        self.assertGreater(res_hyper["cvar_99_dollar"], res_hyper["var_99_dollar"])

        # Negative equity
        res_neg = self.aladdin.compute_parametric_var_cvar(equity=-5000.0, daily_volatility=0.02)
        self.assertFalse(math.isnan(res_neg["var_99_dollar"]))
        self.assertFalse(math.isinf(res_neg["var_99_dollar"]))

    def test_uncertainty_adjusted_fractional_kelly_bounds(self):
        """
        Adversarially verifies Fractional Kelly position sizing bounds:
          1. 1 standard-error haircut: adj_win_rate = max(0.05, win_rate - win_rate_se)
          2. Floor protection: minimum safe baseline is 0.0025 (0.25%).
          3. Ceiling protection: maximum prop firm risk cap is 0.0075 (0.75%).
        """
        # Case A: Low win-rate with high uncertainty -> Floor 0.25%
        risk_floor = self.aladdin.compute_fractional_kelly(win_rate=0.10, payoff_ratio=1.5, win_rate_se=0.08)
        self.assertEqual(risk_floor, 0.0025)

        # Case B: Zero or negative payoff ratio -> Floor 0.25%
        risk_zero_payoff = self.aladdin.compute_fractional_kelly(win_rate=0.60, payoff_ratio=0.0)
        self.assertEqual(risk_zero_payoff, 0.0025)

        # Case C: Institutional benchmark setup (55% win rate, 2.0 R:R, 0.03 SE, 1.0 scalar)
        # adj_win_rate = 0.52. Full Kelly = (0.52 * 3 - 1) / 2 = 0.28.
        # Quarter-Kelly = 0.20 * 0.28 = 0.056. Capped at 0.0075.
        risk_std = self.aladdin.compute_fractional_kelly(win_rate=0.55, payoff_ratio=2.0, win_rate_se=0.03)
        self.assertEqual(risk_std, 0.0075)

        # Case D: Super-trader setup (90% win rate, 5.0 R:R) -> Strictly capped at 0.0075
        risk_max = self.aladdin.compute_fractional_kelly(win_rate=0.90, payoff_ratio=5.0, win_rate_se=0.0)
        self.assertEqual(risk_max, 0.0075)

    def test_3sigma_pre_trade_gap_stress_test_audit(self):
        """
        Adversarially tests Aladdin 3-Sigma Pre-Trade Stress Test:
        Total Stressed Risk = Open Positions Risk + Prospective Trade Risk
        Gate Rule: Total Stressed Risk <= 0.80 * Max Daily Loss Dollar
        """
        max_daily_loss = 625.0  # $625 cap (25k account)
        safe_allowance = 0.80 * max_daily_loss  # $500.00 threshold

        # Scenario 1: No open positions, prospective risk = $350 -> PASS
        eval_safe = self.aladdin.evaluate_pre_trade_stress_test(
            equity=25000.0,
            prospective_risk_dollar=350.0,
            open_positions=[],
            max_daily_loss_dollar=max_daily_loss
        )
        self.assertTrue(eval_safe["passed"])
        self.assertEqual(eval_safe["total_stressed_risk_dollar"], 350.0)
        self.assertIn("APPROVED_PRE_TRADE_STRESS_SAFE", eval_safe["reason"])

        # Scenario 2: Open Gold position ($180 risk) + prospective risk $350 -> Total $530 > $500 (80% cap) -> REJECT
        open_pos = [{"symbol": "XAUUSD", "price_open": 2650.0, "sl": 2632.0, "volume": 0.10}]  # 18 pips * 0.1 * 100 = $180
        eval_reject = self.aladdin.evaluate_pre_trade_stress_test(
            equity=25000.0,
            prospective_risk_dollar=350.0,
            open_positions=open_pos,
            max_daily_loss_dollar=max_daily_loss
        )
        self.assertFalse(eval_reject["passed"])
        self.assertGreater(eval_reject["total_stressed_risk_dollar"], safe_allowance)
        self.assertIn("STRESS_TEST_EXCEEDED", eval_reject["reason"])


class TestTrailingHWMFloorRatchetAndProfitLockIn(unittest.TestCase):
    """
    Adversarial verification of Trailing HWM Floor Ratchet and Capital Lock-In.
    """

    def setUp(self):
        self.test_config = "data/test_challenger2_hwm_config.json"
        self.onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)
        self.onboarder.onboard_new_account("FP_25K_HWM", "MetaQuotes-Demo", 25000.0, "25k")
        self.risk_mgr = FleetRiskManager(config_path=self.test_config, auto_onboarder=self.onboarder)

    def tearDown(self):
        if os.path.exists(self.test_config):
            try:
                os.remove(self.test_config)
            except Exception:
                pass

    def test_1000_step_sawtooth_walk_floor_monotonicity(self):
        """
        Simulates a 1,000-step volatile sawtooth random walk.
        Verifies mathematical invariants:
          1. HWM is strictly monotonic non-decreasing: HWM[t] >= HWM[t-1]
          2. Trailing Floor is strictly monotonic non-decreasing: Floor[t] >= Floor[t-1]
        """
        acc_id = "FP_25K_HWM"
        current_equity = 25000.0
        prev_hwm = 25000.0
        prev_floor = 23500.0  # 25k - 6% ($1,500) = $23,500 starting floor

        rng = random.Random(1337)  # Deterministic seed

        for step in range(1000):
            # Equity fluctuation: random step between -$300 and +$500
            step_delta = rng.uniform(-300.0, 500.0)
            current_equity = max(23600.0, current_equity + step_delta)

            res = self.risk_mgr.update_account_telemetry(acc_id, balance=current_equity, equity=current_equity)

            # Invariant 1: HWM Monotonicity
            self.assertGreaterEqual(res["absolute_hwm"], prev_hwm, f"Step {step}: HWM decreased!")
            # Invariant 2: Trailing Floor Monotonicity
            self.assertGreaterEqual(res["trailing_hwm_floor"], prev_floor, f"Step {step}: Floor decreased!")

            prev_hwm = res["absolute_hwm"]
            prev_floor = res["trailing_hwm_floor"]

    def test_milestone_profit_lock_in_protection(self):
        """
        Verifies that once an account achieves Phase 1 target (+8% = $27,000 on 25k),
        the Trailing HWM Floor ($27,000 - $1,500 = $25,500) is strictly > Starting Balance ($25,000).
        The original $25,000 principal is permanently locked and cannot be lost.
        """
        acc_id = "FP_25K_HWM"
        res = self.risk_mgr.update_account_telemetry(acc_id, balance=27000.0, equity=27000.0)
        
        self.assertEqual(res["absolute_hwm"], 27000.0)
        self.assertEqual(res["trailing_hwm_floor"], 25500.0)
        self.assertGreater(res["trailing_hwm_floor"], 25000.0)

        st = self.risk_mgr.get_account_state(acc_id)
        self.assertTrue(st.get("hwm_locked_at_starting_balance", False))

    def test_trailing_floor_breach_detection_independent_of_daily_loss(self):
        """
        Tests that an account pulling back below its ratcheted floor triggers a trailing floor breach
        even if the intraday loss is completely within the daily loss cap.
        """
        acc_id = "FP_25K_HWM"
        # 1. Climb to $27,000 -> Floor ratchets to $25,500
        self.risk_mgr.update_account_telemetry(acc_id, balance=27000.0, equity=27000.0)

        # 2. Next morning: 00:00 UTC Reset at $26,000
        self.risk_mgr.update_account_telemetry(acc_id, balance=26000.0, equity=26000.0, sod_reset=True)

        # 3. Pullback to $25,400:
        # Intraday loss from $26,000 is $600 (< $625 daily cap) -> Daily shield is SAFE
        # BUT equity $25,400 <= Floor $25,500 -> Trailing Floor BREACHED & Account LOCKED
        res = self.risk_mgr.update_account_telemetry(acc_id, balance=25400.0, equity=25400.0)
        self.assertTrue(res["daily_loss_shield_ok"], "Daily loss $600 is within $625 cap")
        self.assertFalse(res["trailing_floor_ok"], "Trailing floor $25,500 is breached at $25,400")
        self.assertTrue(res["is_locked_out"])
        self.assertIn("TRAILING HWM FLOOR BREACHED", res["lockout_reason"])


class TestMultiAccountFleetGatingAndIsolation(unittest.TestCase):
    """
    Adversarial stress testing of Multi-Account Fleet Gating across 5k, 25k, 50k, 100k accounts.
    """

    def setUp(self):
        self.test_config = "data/test_challenger2_fleet_gating_config.json"
        self.onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)
        
        self.onboarder.onboard_new_account("ACC_5K", "FundingPips-Server", 5000.0, "5k")
        self.onboarder.onboard_new_account("ACC_25K", "MetaQuotes-Demo", 25000.0, "25k")
        self.onboarder.onboard_new_account("ACC_50K", "FundingPips-Server", 50000.0, "50k")
        self.onboarder.onboard_new_account("ACC_100K", "FundingPips-Server", 100000.0, "100k")
        
        self.risk_mgr = FleetRiskManager(config_path=self.test_config, auto_onboarder=self.onboarder)

    def tearDown(self):
        if os.path.exists(self.test_config):
            try:
                os.remove(self.test_config)
            except Exception:
                pass

    def test_multi_account_strict_isolation_under_single_account_wipeout(self):
        """
        Disaster Isolation Stress:
        Wipe out ACC_5K (drops to $0) and breach ACC_100K.
        Assert that ACC_25K and ACC_50K remain completely active, unlocked, and able to trade.
        """
        # Wipe out ACC_5K
        res_5k = self.risk_mgr.update_account_telemetry("ACC_5K", balance=0.0, equity=0.0)
        self.assertTrue(res_5k["is_locked_out"])

        # Breach ACC_100K
        res_100k = self.risk_mgr.update_account_telemetry("ACC_100K", balance=96000.0, equity=96000.0)
        self.assertTrue(res_100k["is_locked_out"])

        # Verify ACC_25K is healthy and can trade
        st_25k = self.risk_mgr.get_account_state("ACC_25K")
        self.assertFalse(st_25k["is_locked_out"])
        app_25k, _ = self.risk_mgr.validate_pre_trade_risk(
            account_id="ACC_25K", symbol="XAUUSD", lot_size=0.10, side="BUY", entry_price=2650.0, sl_price=2636.0
        )
        self.assertTrue(app_25k, "ACC_25K must remain fully approved to trade")

        # Verify ACC_50K is healthy and can trade
        st_50k = self.risk_mgr.get_account_state("ACC_50K")
        self.assertFalse(st_50k["is_locked_out"])
        app_50k, _ = self.risk_mgr.validate_pre_trade_risk(
            account_id="ACC_50K", symbol="EURUSD", lot_size=0.50, side="BUY", entry_price=1.0850, sl_price=1.0800
        )
        self.assertTrue(app_50k, "ACC_50K must remain fully approved to trade")

    def test_5_stage_consistency_pacing_across_all_tiers(self):
        """
        Verifies 5-stage consistency pacing classifier across all four tiers:
          - Stage 1 (<20% target): 1.0x
          - Stage 2 (20-25% target): 0.8x
          - Stage 3 (25-30% target): 0.5x
          - Stage 4 (30-35% target): 0.25x
          - Stage 5 (>35% target): 0.0x Lockout
        """
        tier_targets = [
            ("ACC_5K", 5000.0, 400.0),    # $400 target (8% on 5k)
            ("ACC_25K", 25000.0, 2000.0), # $2,000 target (8% on 25k)
            ("ACC_50K", 50000.0, 4000.0), # $4,000 target (8% on 50k)
            ("ACC_100K", 100000.0, 8000.0)# $8,000 target (8% on 100k)
        ]

        for acc_id, start_bal, target in tier_targets:
            # Stage 1: 15% of target
            p1_profit = target * 0.15
            self.risk_mgr.update_account_telemetry(acc_id, balance=start_bal, equity=start_bal, sod_reset=True)
            self.risk_mgr.update_account_telemetry(acc_id, balance=start_bal + p1_profit, equity=start_bal + p1_profit)
            pacing1 = self.risk_mgr.calculate_consistency_pacing(acc_id, profit_target=target)
            self.assertEqual(pacing1["stage"], 1)
            self.assertEqual(pacing1["risk_multiplier"], 1.0)
            self.assertTrue(pacing1["can_trade"])

            # Stage 2: 22% of target
            p2_profit = target * 0.22
            self.risk_mgr.update_account_telemetry(acc_id, balance=start_bal, equity=start_bal, sod_reset=True)
            self.risk_mgr.update_account_telemetry(acc_id, balance=start_bal + p2_profit, equity=start_bal + p2_profit)
            pacing2 = self.risk_mgr.calculate_consistency_pacing(acc_id, profit_target=target)
            self.assertEqual(pacing2["stage"], 2)
            self.assertEqual(pacing2["risk_multiplier"], 0.8)
            self.assertTrue(pacing2["can_trade"])

            # Stage 3: 27% of target
            p3_profit = target * 0.27
            self.risk_mgr.update_account_telemetry(acc_id, balance=start_bal, equity=start_bal, sod_reset=True)
            self.risk_mgr.update_account_telemetry(acc_id, balance=start_bal + p3_profit, equity=start_bal + p3_profit)
            pacing3 = self.risk_mgr.calculate_consistency_pacing(acc_id, profit_target=target)
            self.assertEqual(pacing3["stage"], 3)
            self.assertEqual(pacing3["risk_multiplier"], 0.5)
            self.assertTrue(pacing3["can_trade"])

            # Stage 4: 33% of target
            p4_profit = target * 0.33
            self.risk_mgr.update_account_telemetry(acc_id, balance=start_bal, equity=start_bal, sod_reset=True)
            self.risk_mgr.update_account_telemetry(acc_id, balance=start_bal + p4_profit, equity=start_bal + p4_profit)
            pacing4 = self.risk_mgr.calculate_consistency_pacing(acc_id, profit_target=target)
            self.assertEqual(pacing4["stage"], 4)
            self.assertEqual(pacing4["risk_multiplier"], 0.25)
            self.assertTrue(pacing4["can_trade"])

            # Stage 5: 36% of target -> Lockout (0.0x)
            p5_profit = target * 0.36
            self.risk_mgr.update_account_telemetry(acc_id, balance=start_bal, equity=start_bal, sod_reset=True)
            self.risk_mgr.update_account_telemetry(acc_id, balance=start_bal + p5_profit, equity=start_bal + p5_profit)
            pacing5 = self.risk_mgr.calculate_consistency_pacing(acc_id, profit_target=target)
            self.assertEqual(pacing5["stage"], 5)
            self.assertEqual(pacing5["risk_multiplier"], 0.0)
            self.assertFalse(pacing5["can_trade"])

    def test_dynamic_lot_sizing_proportional_scaling_across_tiers(self):
        """
        Verifies that position sizing scales proportionally across account tiers:
        For Gold ($14 SL distance, 100 contract size, 0.75% risk):
          - 5k: Risk $37.50 / $1400 = 0.0267 -> 0.03 lots
          - 25k: Risk $187.50 / $1400 = 0.1339 -> 0.13 lots
          - 50k: Risk $375.00 / $1400 = 0.2678 -> 0.27 lots
          - 100k: Risk $750.00 / $1400 = 0.5357 -> 0.54 lots
        """
        lots_5k = self.risk_mgr.calculate_dynamic_lot_size("ACC_5K", "XAUUSD", 2650.0, 2636.0)
        lots_25k = self.risk_mgr.calculate_dynamic_lot_size("ACC_25K", "XAUUSD", 2650.0, 2636.0)
        lots_50k = self.risk_mgr.calculate_dynamic_lot_size("ACC_50K", "XAUUSD", 2650.0, 2636.0)
        lots_100k = self.risk_mgr.calculate_dynamic_lot_size("ACC_100K", "XAUUSD", 2650.0, 2636.0)

        self.assertEqual(lots_5k, 0.03)
        self.assertEqual(lots_25k, 0.13)
        self.assertEqual(lots_50k, 0.27)
        self.assertEqual(lots_100k, 0.54)


if __name__ == "__main__":
    unittest.main(verbosity=2)
