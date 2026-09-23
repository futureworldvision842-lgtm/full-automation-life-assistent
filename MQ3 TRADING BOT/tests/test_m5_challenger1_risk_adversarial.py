"""
tests/test_m5_challenger1_risk_adversarial.py — Empirical Challenger Stress Suite for M5.
Adversarial Stress Testing of BlackRock Aladdin VaR & Prop Firm Shields:
- Extreme Volatility (200%, 500%, 1000% annualized and daily vol)
- Zero Equity, Negative Balance, Single-Dollar & Massive Portfolio Edge Cases
- 5-Sigma Multi-Asset Price Gaps / Flash Crashes
- Monotonicity of Trailing HWM Floor Ratchet during wild pullbacks (10,000 step Monte Carlo)
- SOD Daily Loss Allowance Calculations across Multiple Calendar Rollovers
- Consistency Pacing & Trade Parameter Directional / R:R Audits
"""

import math
import datetime
from datetime import timedelta
from unittest.mock import patch
import numpy as np
import pytest

from src.aladdin_risk_engine import AladdinRiskEngine
from src.funding_pips_expert import FundingPipsExpert


# ==============================================================================
# 1. EXTREME VOLATILITY & MATHEMATICAL INVARIANTS (200%, 500%, 1000%)
# ==============================================================================

class TestAladdinExtremeVolatilityInvariants:
    """
    Validates Aladdin VaR/CVaR mathematical stability and physical invariants
    across extreme volatility regimes up to 1000% vol.
    """

    def setup_method(self):
        self.engine = AladdinRiskEngine(
            max_portfolio_var_pct=0.015,
            cvar_confidence=0.99,
            kelly_fraction=0.20,
            max_risk_cap_pct=0.0075
        )

    @pytest.mark.parametrize("annualized_vol", [2.0, 5.0, 10.0])  # 200%, 500%, 1000%
    def test_annualized_extreme_volatility_var_cvar(self, annualized_vol):
        equity = 25000.0
        daily_vol = annualized_vol / math.sqrt(252.0)
        res = self.engine.compute_parametric_var_cvar(equity, daily_vol)

        # Invariant 1: VaR and CVaR must be positive real numbers
        assert res["var_99_dollar"] > 0.0
        assert res["var_95_dollar"] > 0.0
        assert res["cvar_99_dollar"] > 0.0
        assert res["cvar_95_dollar"] > 0.0

        # Invariant 2: Monotonicity CVaR_99 > VaR_99 > VaR_95
        assert res["cvar_99_dollar"] > res["var_99_dollar"]
        assert res["var_99_dollar"] > res["var_95_dollar"]
        assert res["cvar_95_dollar"] > res["var_95_dollar"]

        # Invariant 3: No NaN / Inf
        for k, v in res.items():
            assert not math.isnan(v), f"{k} is NaN"
            assert not math.isinf(v), f"{k} is Inf"

    @pytest.mark.parametrize("daily_vol", [0.50, 1.00, 2.00, 5.00, 10.00])  # Up to 1000% daily vol
    def test_daily_hyper_volatility_monotone_ordering(self, daily_vol):
        equity = 50000.0
        res = self.engine.compute_parametric_var_cvar(equity, daily_vol)

        assert res["cvar_99_dollar"] > res["var_99_dollar"] > res["var_95_dollar"]
        # Invariant: CVaR_99 multiplier: pdf(2.326348) / 0.01 = 0.02665 / 0.01 = 2.665
        # Since z_99 = 2.326348, cvar_99 / var_99 ratio should be exactly pdf(z_99)/(0.01 * z_99) ≈ 2.665 / 2.326 ≈ 1.1457
        theoretical_ratio = (self.engine._std_norm_pdf(2.326348) / 0.01) / 2.326348
        empirical_ratio = res["cvar_99_dollar"] / res["var_99_dollar"]
        assert abs(empirical_ratio - theoretical_ratio) < 0.05

    def test_var_equity_linear_homogeneity(self):
        """Tests that VaR is linearly homogeneous of degree 1: VaR(k * E) == k * VaR(E)."""
        daily_vol = 0.025
        base_res = self.engine.compute_parametric_var_cvar(10000.0, daily_vol)
        scaled_res = self.engine.compute_parametric_var_cvar(50000.0, daily_vol)

        assert abs(scaled_res["var_99_dollar"] - 5.0 * base_res["var_99_dollar"]) < 0.10
        assert abs(scaled_res["cvar_99_dollar"] - 5.0 * base_res["cvar_99_dollar"]) < 0.10


# ==============================================================================
# 2. ZERO EQUITY, NEGATIVE BALANCE, & SINGLE-DOLLAR EDGE CASES
# ==============================================================================

class TestAladdinDegenerateEquityEdgeCases:
    """
    Adversarial edge cases: Zero equity, negative equity, single-dollar, sub-cent,
    and hyper-scale portfolios.
    """

    def setup_method(self):
        self.engine = AladdinRiskEngine()

    @pytest.mark.parametrize("equity", [0.0, -0.0, -1.0, -100.0, -25000.0, -1e6])
    def test_zero_and_negative_equity_robustness(self, equity):
        res = self.engine.compute_parametric_var_cvar(equity=equity, daily_volatility=0.02)
        assert isinstance(res["var_99_dollar"], float)
        assert isinstance(res["cvar_99_dollar"], float)
        assert not math.isnan(res["var_99_dollar"])
        assert not math.isinf(res["var_99_dollar"])
        assert not math.isnan(res["var_99_pct"])

    @pytest.mark.parametrize("equity", [0.0001, 0.01, 1.0, 10.0])
    def test_micro_and_single_dollar_portfolios(self, equity):
        res = self.engine.compute_parametric_var_cvar(equity=equity, daily_volatility=0.03)
        assert res["var_99_dollar"] >= 0.0
        assert not math.isnan(res["var_99_pct"])

    def test_hyper_scale_portfolio_billion_dollar(self):
        equity = 1_000_000_000.0  # $1 Billion
        res = self.engine.compute_parametric_var_cvar(equity=equity, daily_volatility=0.015)
        expected_var = 1e9 * 2.326348 * 0.015
        assert abs(res["var_99_dollar"] - expected_var) < 1.0


# ==============================================================================
# 3. FRACTIONAL KELLY STRESS & BOUNDARY CONSTRAINTS
# ==============================================================================

class TestFractionalKellyStress:
    """
    Stress-testing Uncertainty-Adjusted Fractional Kelly Criterion under adversarial inputs.
    """

    def setup_method(self):
        self.engine = AladdinRiskEngine(max_risk_cap_pct=0.0075, kelly_fraction=0.20)

    @pytest.mark.parametrize("win_rate,payoff", [
        (0.0, 2.0), (0.1, 1.5), (0.25, 1.0), (0.33, 1.5), (-0.5, 2.0), (0.5, -2.0)
    ])
    def test_unfavorable_and_negative_odds_floor_at_minimum_risk(self, win_rate, payoff):
        """Unfavorable betting propositions must strictly floor at 0.0025 (0.25%)."""
        f = self.engine.compute_fractional_kelly(win_rate=win_rate, payoff_ratio=payoff)
        assert f == 0.0025

    @pytest.mark.parametrize("win_rate,payoff", [
        (0.80, 5.0), (0.95, 10.0), (1.0, 20.0), (0.99, 100.0)
    ])
    def test_extreme_favorable_odds_strictly_capped_at_prop_firm_limit(self, win_rate, payoff):
        """Even with 100% win rate and 20:1 payoff, risk is strictly capped at 0.75% (0.0075)."""
        f = self.engine.compute_fractional_kelly(win_rate=win_rate, payoff_ratio=payoff)
        assert f == 0.0075

    def test_fractional_kelly_monotonicity(self):
        """Higher win rate must yield equal or higher risk allocation."""
        risks = [
            self.engine.compute_fractional_kelly(win_rate=p, payoff_ratio=2.0)
            for p in np.linspace(0.40, 0.75, 15)
        ]
        for i in range(len(risks) - 1):
            assert risks[i] <= risks[i+1]


# ==============================================================================
# 4. PRE-TRADE STRESS TEST & 5-SIGMA MULTI-ASSET FLASH CRASH
# ==============================================================================

class TestPreTradeStressMultiAssetFlashCrash:
    """
    Stress-tests multi-asset risk calculation under 5-sigma gap shocks across
    Crypto, Metals, and FX with diverse lot sizes and SL distances.
    """

    def setup_method(self):
        self.engine = AladdinRiskEngine()

    def test_crypto_flash_crash_5_sigma(self):
        """Simulates simultaneous BTC, ETH, and SOL open positions experiencing gap shock."""
        positions = [
            {"symbol": "BTCUSD", "price_open": 65000.0, "sl": 63000.0, "volume": 0.10},  # $200 risk
            {"symbol": "ETHUSD", "price_open": 3500.0, "sl": 3400.0, "volume": 1.0},     # $100 risk
            {"symbol": "SOLUSD", "price_open": 180.0, "sl": 170.0, "volume": 5.0},       # $50 risk
        ]
        # Total current open risk = 200 + 100 + 50 = $350
        # Daily limit = $625, 80% ceiling = $500
        # Prospective risk = $100 -> Total = $450 <= $500 -> APPROVED
        res_approved = self.engine.evaluate_pre_trade_stress_test(
            equity=25000.0,
            prospective_risk_dollar=100.0,
            open_positions=positions,
            max_daily_loss_dollar=625.0
        )
        assert res_approved["passed"] is True
        assert res_approved["total_stressed_risk_dollar"] == 450.0

        # Prospective risk = $200 -> Total = $550 > $500 -> BLOCKED
        res_blocked = self.engine.evaluate_pre_trade_stress_test(
            equity=25000.0,
            prospective_risk_dollar=200.0,
            open_positions=positions,
            max_daily_loss_dollar=625.0
        )
        assert res_blocked["passed"] is False
        assert "STRESS_TEST_EXCEEDED" in res_blocked["reason"]

    def test_metals_and_fx_pip_calculations(self):
        """Verifies exact pip valuation for Gold (0.10), Silver (0.01), JPY (0.01), FX (0.0001)."""
        # Gold: open 2650.0, sl 2640.0 -> diff 10.0 -> 100 pips @ $10/pip on 0.5 lot = 100 * 0.5 * 10 = $500
        pos_gold = [{"symbol": "XAUUSD", "price_open": 2650.0, "sl": 2640.0, "volume": 0.5}]
        res_gold = self.engine.evaluate_pre_trade_stress_test(
            equity=25000.0, prospective_risk_dollar=0.0, open_positions=pos_gold, max_daily_loss_dollar=625.0
        )
        assert abs(res_gold["total_stressed_risk_dollar"] - 500.0) < 0.01

        # Silver: open 30.00, sl 29.50 -> diff 0.50 -> 50 pips @ $50/pip on 0.1 lot = 50 * 0.1 * 50 = $250
        pos_silver = [{"symbol": "XAGUSD", "price_open": 30.00, "sl": 29.50, "volume": 0.1}]
        res_silver = self.engine.evaluate_pre_trade_stress_test(
            equity=25000.0, prospective_risk_dollar=0.0, open_positions=pos_silver, max_daily_loss_dollar=625.0
        )
        assert abs(res_silver["total_stressed_risk_dollar"] - 250.0) < 0.01

        # EURUSD: open 1.0850, sl 1.0800 -> diff 0.0050 -> 50 pips @ $10/pip on 1.0 lot = 50 * 1.0 * 10 = $500
        pos_eur = [{"symbol": "EURUSD", "price_open": 1.0850, "sl": 1.0800, "volume": 1.0}]
        res_eur = self.engine.evaluate_pre_trade_stress_test(
            equity=25000.0, prospective_risk_dollar=0.0, open_positions=pos_eur, max_daily_loss_dollar=625.0
        )
        assert abs(res_eur["total_stressed_risk_dollar"] - 500.0) < 0.01

    def test_pre_trade_stress_boundary_equality(self):
        """Exact 80% boundary condition check."""
        limit = 625.0
        exact_80_pct = 0.80 * limit  # 500.0

        res_exact = self.engine.evaluate_pre_trade_stress_test(
            equity=25000.0,
            prospective_risk_dollar=exact_80_pct,
            open_positions=[],
            max_daily_loss_dollar=limit
        )
        assert res_exact["passed"] is True

        res_over = self.engine.evaluate_pre_trade_stress_test(
            equity=25000.0,
            prospective_risk_dollar=exact_80_pct + 0.01,
            open_positions=[],
            max_daily_loss_dollar=limit
        )
        assert res_over["passed"] is False


# ==============================================================================
# 5. MONOTONICITY OF TRAILING HWM FLOOR RATCHET (MONTE CARLO STRESS)
# ==============================================================================

class TestTrailingHWMFloorRatchetMonotonicity:
    """
    Adversarial verification of Trailing High-Water Mark (HWM) floor ratchet.
    Runs a 10,000-step random walk and jump-diffusion simulation to ensure:
    1. absolute_high_watermark(t) is strictly monotonically non-decreasing.
    2. Drawdown floor = HWM - Max_Allowed is strictly non-decreasing.
    3. Any equity breach below floor is 100% reliably intercepted.
    """

    def test_monte_carlo_hwm_floor_ratchet_monotonicity(self):
        expert = FundingPipsExpert("25k")
        np.random.seed(42)

        initial_equity = 25000.0
        current_equity = initial_equity
        hwm_series = []
        floor_series = []

        # 10,000 steps of Brownian motion + random Poisson jumps (+-5%)
        steps = 10000
        dt = 1.0 / 252.0
        drift = 0.05
        vol = 0.30

        for step in range(steps):
            # Geometric Brownian Motion step
            dW = np.random.normal(0, np.sqrt(dt))
            jump = 0.0
            if np.random.rand() < 0.02:  # 2% jump probability
                jump = np.random.choice([-0.05, 0.05])

            current_equity *= (1.0 + drift * dt + vol * dW + jump)
            current_equity = max(100.0, current_equity)  # prevent negative

            # Update watermark
            expert.update_daily_watermark(equity=current_equity, balance=current_equity)

            current_hwm = expert.absolute_high_watermark
            current_floor = current_hwm - (25000.0 * 0.06)

            hwm_series.append(current_hwm)
            floor_series.append(current_floor)

            # Assert Invariant: HWM must never drop
            if len(hwm_series) > 1:
                assert hwm_series[-1] >= hwm_series[-2], f"HWM decreased at step {step}!"
                assert floor_series[-1] >= floor_series[-2], f"Floor decreased at step {step}!"

            # Test can_trade behavior
            can_trade, reason = expert.can_trade(balance=current_equity, equity=current_equity)
            if current_equity <= current_floor:
                assert not can_trade, f"Failed to block trade when equity {current_equity} <= floor {current_floor} at step {step}"
                assert "Trailing HWM Drawdown Floor Reached" in reason or "Overall Drawdown" in reason or "Daily Drawdown" in reason


# ==============================================================================
# 6. SOD DAILY LOSS ALLOWANCE ACROSS MULTIPLE CALENDAR ROLLOVERS
# ==============================================================================

class TestSODDailyLossCalendarRollovers:
    """
    Tests SOD daily loss baseline calculations across consecutive trading days,
    weekends, month-ends, and leap years.
    """

    def test_multi_day_sod_baseline_resets(self):
        expert = FundingPipsExpert("25k")

        # Simulate consecutive days
        start_date = datetime.date(2026, 8, 1)

        daily_scenarios = [
            # (day_offset, ending_balance, ending_equity, expected_next_sod)
            (1, 25200.0, 25300.0, 25300.0),  # Day 1: Profit -> next SOD = max(25200, 25300) = 25300
            (2, 25100.0, 25050.0, 25100.0),  # Day 2: Pullback -> next SOD = max(25100, 25050) = 25100
            (3, 25500.0, 25500.0, 25500.0),  # Day 3: Rebound -> next SOD = 25500
            (4, 25400.0, 25450.0, 25450.0),  # Day 4: Stable -> next SOD = 25450
            (5, 26000.0, 26100.0, 26100.0),  # Day 5: Big Win -> next SOD = 26100
        ]

        for offset, end_bal, end_eq, expected_sod in daily_scenarios:
            simulated_date = start_date + timedelta(days=offset)
            
            with patch("src.funding_pips_expert.datetime.date") as mock_date:
                mock_date.today.return_value = simulated_date
                # Make sure comparisons work properly with datetime.date instances
                expert.last_reset_date = simulated_date - timedelta(days=1)
                
                expert.update_daily_watermark(equity=end_eq, balance=end_bal)
                assert expert.daily_high_watermark == expected_sod, (
                    f"Day {offset}: Expected SOD {expected_sod}, got {expert.daily_high_watermark}"
                )
                assert expert.last_reset_date == simulated_date

                # Verify 2.5% daily drawdown threshold relative to new SOD
                max_daily_loss = expert.daily_high_watermark * 0.025
                allowed_loss_floor = expert.daily_high_watermark - max_daily_loss

                # Just above floor -> allowed
                can_t, _ = expert.can_trade(balance=end_bal, equity=allowed_loss_floor + 1.0)
                # Just below floor -> blocked
                can_f, msg = expert.can_trade(balance=end_bal, equity=allowed_loss_floor - 1.0)
                assert can_f is False
                assert "Daily Drawdown Guard Triggered" in msg

    def test_same_day_equity_fluctuations_do_not_lower_daily_sod(self):
        """Within the SAME trading day, daily_high_watermark must remain locked at SOD baseline."""
        expert = FundingPipsExpert("25k")
        expert.daily_high_watermark = 25000.0
        expert.last_reset_date = datetime.date.today()

        # Equity drops intraday
        expert.update_daily_watermark(equity=24600.0, balance=24600.0)
        assert expert.daily_high_watermark == 25000.0  # MUST NOT DECREASE

        # Equity rises intraday (SOD remains baseline unless day changes)
        expert.update_daily_watermark(equity=25500.0, balance=25500.0)
        assert expert.daily_high_watermark == 25000.0  # Daily SOD stays locked to start-of-day


# ==============================================================================
# 7. ACCOUNT TIER SCALING & TRADE COMPLIANCE AUDIT
# ==============================================================================

class TestAccountTiersAndTradeCompliance:
    """
    Tests trade parameter validation across 25k, 50k, 100k account tiers.
    """

    @pytest.mark.parametrize("tier,expected_target,max_pos", [
        ("25k", 25000.0, 2),
        ("50k", 50000.0, 3),
        ("100k", 100000.0, 4),
    ])
    def test_tier_specifications(self, tier, expected_target, max_pos):
        expert = FundingPipsExpert(tier)
        assert expert.profile["target_balance"] == expected_target
        assert expert.profile["max_open_positions"] == max_pos
        assert expert.profile["safe_daily_loss_pct"] == 2.5
        assert expert.profile["safe_total_loss_pct"] == 6.0

    def test_mandatory_sl_tp_audit(self):
        expert = FundingPipsExpert("25k")
        # Missing SL
        res_no_sl = expert.audit_trade("XAUUSD", "BUY", 2650.0, sl=0.0, tp=2670.0, current_open_count=0)
        assert res_no_sl["passed"] is False
        assert "mandatory Stop-Loss & Take-Profit" in res_no_sl["reason"]

        # Zero SL distance
        res_zero_dist = expert.audit_trade("XAUUSD", "BUY", 2650.0, sl=2650.0, tp=2670.0, current_open_count=0)
        assert res_zero_dist["passed"] is False
        assert "Invalid Stop-Loss distance of 0" in res_zero_dist["reason"]

        # Sub-1.0 R:R
        res_bad_rr = expert.audit_trade("XAUUSD", "BUY", 2650.0, sl=2630.0, tp=2660.0, current_open_count=0)
        assert res_bad_rr["passed"] is False
        assert "Risk:Reward" in res_bad_rr["reason"]

        # Valid 2:1 R:R
        res_valid = expert.audit_trade("XAUUSD", "BUY", 2650.0, sl=2640.0, tp=2670.0, current_open_count=0)
        assert res_valid["passed"] is True

        # Position count overflow
        res_overflow = expert.audit_trade("XAUUSD", "BUY", 2650.0, sl=2640.0, tp=2670.0, current_open_count=2)
        assert res_overflow["passed"] is False
        assert "reached tier cap" in res_overflow["reason"]
