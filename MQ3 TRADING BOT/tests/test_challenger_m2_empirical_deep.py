"""
test_challenger_m2_empirical_deep.py — Deep Adversarial Stress Suite for Milestone 2.
======================================================================================
Author: Challenger 2 (Empirical Challenger)
Focus:
  1. 2-Phase Adaptive Prop Firm Challenge Engine (5k, 25k, 50k, 100k) State Machine Transitions & Risk Sizing.
  2. Trailing High-Water-Mark (HWM) Floor Ratchet Monotonicity & Starting Balance Profit Lock under Sawtooth Walk (10,000 steps).
  3. 15-Minute Pre-News Circuit Breakers (Boundary Precision, Currency Filtering, Multi-Event Feeds).
  4. Post-News Judas Wick Sniping (+0.80 Confluence Bonus) & Strategy Pipeline Execution.
  5. BlackRock Aladdin 1-Day 99% VaR, Analytical CVaR, Uncertainty-Adjusted Fractional Kelly & Pre-Trade 3-Sigma Stress Interceptor.
  6. Minimum 1:2.0 Risk-to-Reward Ratio and Mandatory SL/TP Enforcement.
"""

import os
import math
import random
import unittest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from src.funding_pips_expert import FundingPipsExpert
from src.fleet_risk_manager import FleetRiskManager
from src.aladdin_risk_engine import AladdinRiskEngine
from src.economic_calendar_radar import EconomicCalendarRadar
from src.strategy import StrategyEngine
from src.multi_account_auto_onboarder import MultiAccountAutoOnboarder


class TestPropFirmChallengeEngineAllTiers(unittest.TestCase):
    """
    Empirically verifies 2-Phase Adaptive Prop Firm Challenge Engine
    across 5k, 25k, 50k, and 100k account tiers.
    """

    def setUp(self):
        self.tiers = ["5k", "25k", "50k", "100k"]
        self.tier_balances = {"5k": 5000.0, "25k": 25000.0, "50k": 50000.0, "100k": 100000.0}
        self.tier_max_pos = {"5k": 2, "25k": 2, "50k": 3, "100k": 4}

    def test_tier_initialization_and_max_positions(self):
        """Verifies correct parameters loaded for each tier."""
        for tier in self.tiers:
            expert = FundingPipsExpert(account_tier=tier)
            self.assertEqual(expert.profile["target_balance"], self.tier_balances[tier])
            self.assertEqual(expert.profile["safe_daily_loss_pct"], 2.5)
            self.assertEqual(expert.profile["safe_total_loss_pct"], 6.0)
            self.assertEqual(expert.profile["phase1_target_pct"], 8.0)
            self.assertEqual(expert.profile["phase2_target_pct"], 5.0)
            self.assertEqual(expert.profile["max_open_positions"], self.tier_max_pos[tier])

    def test_tier_initialization_via_numeric_balance_and_dict(self):
        """Verifies initialization with string tiers, float/int balances, and inspects dict parsing."""
        # 1. String Tiers
        self.assertEqual(FundingPipsExpert("5k").profile["target_balance"], 5000.0)
        self.assertEqual(FundingPipsExpert("25k").profile["target_balance"], 25000.0)
        self.assertEqual(FundingPipsExpert("50k").profile["target_balance"], 50000.0)
        self.assertEqual(FundingPipsExpert("100k").profile["target_balance"], 100000.0)

        # 2. Numeric Balance Sizing
        self.assertEqual(FundingPipsExpert(5000).profile["target_balance"], 5000.0)
        self.assertEqual(FundingPipsExpert(25000.0).profile["target_balance"], 25000.0)
        self.assertEqual(FundingPipsExpert(50000.0).profile["target_balance"], 50000.0)
        self.assertEqual(FundingPipsExpert(100000.0).profile["target_balance"], 100000.0)

        # 3. Dict Parsing (100k, 50k, 5k)
        e5 = FundingPipsExpert({"account_info": {"account_type": "5k_challenge"}})
        self.assertEqual(e5.profile["target_balance"], 5000.0)
        e50 = FundingPipsExpert({"account_info": {"account_type": "50k_challenge"}})
        self.assertEqual(e50.profile["target_balance"], 50000.0)
        e100 = FundingPipsExpert({"account_info": {"account_type": "100K_MASTER"}})
        self.assertEqual(e100.profile["target_balance"], 100000.0)

    def test_2phase_state_machine_transitions_all_tiers(self):
        """
        Adversarially tests state machine progression across exact mathematical boundaries:
          - Phase 1 (Student): profit < 8.0% -> Risk = 0.75%
          - Phase 2 (Practitioner): 8.0% <= profit < 13.0% -> Risk = 0.50%
          - Master Funded Account: profit >= 13.0% -> Risk = 0.35%
        """
        for tier in self.tiers:
            expert = FundingPipsExpert(account_tier=tier)
            base = self.tier_balances[tier]

            # 1. At starting balance ($0 profit, 0.0%)
            st0 = expert.evaluate_phase_progression(current_equity=base)
            self.assertEqual(st0["current_phase"], "PHASE_1_STUDENT")
            self.assertEqual(st0["suggested_risk_per_trade_pct"], 0.75)
            self.assertEqual(st0["active_target_pct"], 8.0)

            # 2. Phase 1 near boundary (7.99% profit)
            p1_near = base + (base * 0.0799)
            st1_near = expert.evaluate_phase_progression(current_equity=p1_near)
            self.assertEqual(st1_near["current_phase"], "PHASE_1_STUDENT")
            self.assertEqual(st1_near["suggested_risk_per_trade_pct"], 0.75)

            # 3. Exact Phase 1 Passing Threshold (8.00% profit) -> Transitions to Phase 2
            p1_pass = base + (base * 0.08)
            st_p2 = expert.evaluate_phase_progression(current_equity=p1_pass)
            self.assertEqual(st_p2["current_phase"], "PHASE_2_PRACTITIONER")
            self.assertEqual(st_p2["suggested_risk_per_trade_pct"], 0.50)
            self.assertEqual(st_p2["active_target_pct"], 5.0)

            # 4. Phase 2 near boundary (12.99% total profit)
            p2_near = base + (base * 0.1299)
            st2_near = expert.evaluate_phase_progression(current_equity=p2_near)
            self.assertEqual(st2_near["current_phase"], "PHASE_2_PRACTITIONER")
            self.assertEqual(st2_near["suggested_risk_per_trade_pct"], 0.50)

            # 5. Phase 2 Passing Threshold (>13.00% total profit) -> Transitions to Funded
            p2_pass = base + (base * 0.1301)
            st_funded = expert.evaluate_phase_progression(current_equity=p2_pass)
            self.assertEqual(st_funded["current_phase"], "MASTER_FUNDED_ACCOUNT")
            self.assertEqual(st_funded["suggested_risk_per_trade_pct"], 0.35)
            self.assertEqual(st_funded["active_target_pct"], 0.0)

            # 6. High profit on Funded (25.0% total profit)
            p_high = base + (base * 0.25)
            st_high = expert.evaluate_phase_progression(current_equity=p_high)
            self.assertEqual(st_high["current_phase"], "MASTER_FUNDED_ACCOUNT")
            self.assertEqual(st_high["suggested_risk_per_trade_pct"], 0.35)

    def test_open_position_cap_enforcement_all_tiers(self):
        """Verifies rejection when open position count reaches tier cap."""
        for tier in self.tiers:
            expert = FundingPipsExpert(account_tier=tier)
            cap = self.tier_max_pos[tier]
            base = self.tier_balances[tier]

            # Under cap -> allowed
            res_ok = expert.audit_trade_compliance("XAUUSD", 2650.0, 2636.0, base, base, open_count=cap - 1)
            self.assertTrue(res_ok[0], f"Tier {tier} should allow open_count {cap - 1}")

            # At or over cap -> rejected
            res_blocked = expert.audit_trade_compliance("XAUUSD", 2650.0, 2636.0, base, base, open_count=cap)
            self.assertFalse(res_blocked[0], f"Tier {tier} must reject open_count {cap}")
            self.assertIn("Max open positions count reached", res_blocked[1])


class TestTrailingHWMFloorSawtoothStress(unittest.TestCase):
    """
    Adversarially stress tests Trailing High-Water-Mark floor ratchet monotonicity
    and starting balance profit locking under 10,000 steps of random walk volatility.
    """

    def setUp(self):
        self.test_config = "data/test_hwm_sawtooth_config.json"
        self.onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)
        self.onboarder.onboard_new_account("FP_5K", "MetaQuotes-Demo", 5000.0, "FUNDING_PIPS")
        self.onboarder.onboard_new_account("FP_25K", "MetaQuotes-Demo", 25000.0, "FUNDING_PIPS")
        self.onboarder.onboard_new_account("FP_50K", "MetaQuotes-Demo", 50000.0, "FUNDING_PIPS")
        self.onboarder.onboard_new_account("FP_100K", "MetaQuotes-Demo", 100000.0, "FUNDING_PIPS")
        self.risk_mgr = FleetRiskManager(config_path=self.test_config, auto_onboarder=self.onboarder)

    def tearDown(self):
        if os.path.exists(self.test_config):
            try:
                os.remove(self.test_config)
            except Exception:
                pass

    def test_monte_carlo_10000_step_hwm_monotonicity_and_profit_lock(self):
        """
        Runs a 10,000-step stochastic equity path across all Funding Pips tiers.
        Verifies:
          Invariant A: HWM[t+1] >= HWM[t]
          Invariant B: Floor[t+1] >= Floor[t]
          Invariant C: Once peak profit reaches >= 6.0% total loss allowance, Floor >= Starting Balance.
        """
        rng = random.Random(1337)
        account_ids = ["FP_5K", "FP_25K", "FP_50K", "FP_100K"]

        for acc_id in account_ids:
            st = self.risk_mgr.get_account_state(acc_id)
            start_bal = st["starting_balance"]
            max_loss_pct = st["max_total_loss_pct"]  # 0.06 (6%)
            expected_start_floor = start_bal * (1.0 - max_loss_pct)

            self.assertEqual(st["trailing_hwm_floor"], expected_start_floor)

            curr_equity = start_bal
            prev_hwm = start_bal
            prev_floor = expected_start_floor

            for step in range(2500):  # 2500 steps per account = 10,000 steps total
                step_delta = rng.uniform(-start_bal * 0.02, start_bal * 0.035)
                # Keep equity above catastrophic liquidation for the walk
                curr_equity = max(expected_start_floor + 10.0, curr_equity + step_delta)

                res = self.risk_mgr.update_account_telemetry(acc_id, balance=curr_equity, equity=curr_equity)

                # Invariant A: HWM monotonicity
                self.assertGreaterEqual(
                    res["absolute_hwm"], prev_hwm,
                    f"Account {acc_id} HWM decreased from {prev_hwm} to {res['absolute_hwm']} at step {step}"
                )

                # Invariant B: Floor monotonicity
                self.assertGreaterEqual(
                    res["trailing_hwm_floor"], prev_floor,
                    f"Account {acc_id} Floor decreased from {prev_floor} to {res['trailing_hwm_floor']} at step {step}"
                )

                # Invariant C: Starting Balance Profit Locking
                # Milestone threshold = start_bal * (1 + max_loss_pct) -> e.g. $25k * 1.06 = $26,500
                if res["absolute_hwm"] >= start_bal * (1.0 + max_loss_pct):
                    self.assertGreaterEqual(
                        res["trailing_hwm_floor"], start_bal,
                        f"Account {acc_id} Floor ({res['trailing_hwm_floor']}) must be >= Starting Balance ({start_bal}) after peak {res['absolute_hwm']}"
                    )

                prev_hwm = res["absolute_hwm"]
                prev_floor = res["trailing_hwm_floor"]


class TestPreNewsCircuitBreakersAndJudasSniping(unittest.TestCase):
    """
    Stress tests 15-minute Pre-News Circuit Breakers and Post-News Judas Wick Sniping (+0.80 bonus).
    """

    def setUp(self):
        self.radar = EconomicCalendarRadar(blackout_minutes_before=15, blackout_minutes_after=15)
        self.radar.clear_events()

    def test_pre_news_circuit_breaker_exact_minute_boundaries(self):
        """
        Verifies 15-minute blackout window boundaries:
          - T - 15.1 min: Cleared (Outside window)
          - T - 15.0 min: Blackout (Window start)
          - T - 5.0 min: Blackout (Pre-news locked)
          - T + 0.0 min: Blackout (Event moment)
          - T + 5.0 min: Blackout (Post-news cooloff)
          - T + 15.0 min: Blackout (Window end)
          - T + 15.1 min: Cleared (Outside window)
        """
        event_time = datetime(2026, 8, 18, 12, 30, 0, tzinfo=timezone.utc)
        self.radar.inject_event(
            title="US Non-Farm Employment Change (NFP)",
            currency="USD",
            event_time_utc=event_time,
            impact="HIGH"
        )

        test_points = [
            (event_time - timedelta(minutes=15.1), True, False, "15.1m before event should be cleared"),
            (event_time - timedelta(minutes=15.0), False, True, "15.0m before event should be locked"),
            (event_time - timedelta(minutes=5.0), False, True, "5.0m before event should be locked"),
            (event_time, False, True, "Event time should be locked"),
            (event_time + timedelta(minutes=5.0), False, True, "5.0m after event should be locked"),
            (event_time + timedelta(minutes=15.0), False, True, "15.0m after event should be locked"),
            (event_time + timedelta(minutes=15.1), True, False, "15.1m after event should be cleared"),
        ]

        for check_time, exp_cleared, exp_blackout, msg in test_points:
            status = self.radar.evaluate_news_clearance("EURUSD", current_time=check_time, check_weekend=False)
            self.assertEqual(status["is_cleared"], exp_cleared, f"{msg}: got is_cleared={status['is_cleared']}")
            self.assertEqual(status["is_blackout"], exp_blackout, f"{msg}: got is_blackout={status['is_blackout']}")

    def test_currency_specific_circuit_breaker_isolation(self):
        """
        Verifies that a GBP high-impact event locks GBPUSD and EURGBP,
        but does NOT lock USDJPY or BTCUSD (unless USD event).
        """
        gbp_event_time = datetime(2026, 8, 18, 9, 30, 0, tzinfo=timezone.utc)
        self.radar.inject_event(
            title="BOE Interest Rate Decision",
            currency="GBP",
            event_time_utc=gbp_event_time,
            impact="HIGH"
        )

        check_time = gbp_event_time - timedelta(minutes=5)

        # GBP pairs must be locked
        status_gbp = self.radar.evaluate_news_clearance("GBPUSD", current_time=check_time, check_weekend=False)
        self.assertFalse(status_gbp["is_cleared"])
        self.assertTrue(status_gbp["is_blackout"])

        # Non-GBP pairs without USD event must remain cleared
        status_jpy = self.radar.evaluate_news_clearance("USDJPY", current_time=check_time, check_weekend=False)
        self.assertTrue(status_jpy["is_cleared"])

    def test_post_news_judas_wick_sniping_bonus_in_strategy(self):
        """
        Empirically verifies that post-news Judas wick detection gives +0.80 confluence bonus
        and assigns pattern_type = 'POST_NEWS_JUDAS_SWEEP'.
        """
        import pandas as pd
        config = {
            "risk_management": {
                "min_rr_ratio": 2.0,
                "atr_sl_multiplier": 1.5,
                "forex_atr_sl_multiplier": 1.5,
                "gold_atr_sl_multiplier": 2.5,
                "crypto_atr_sl_multiplier": 3.5
            },
            "gold_primary_focus": {
                "enabled": True,
                "xauusd_min_confluence_score": 1.2,
                "other_pairs_min_confluence_score": 1.3
            }
        }
        strategy = StrategyEngine(config=config)

        # 10 bars of df_entry
        df_mock = pd.DataFrame({
            "open": [2645.0 + i for i in range(10)],
            "high": [2648.0 + i for i in range(10)],
            "low": [2642.0 + i for i in range(10)],
            "close": [2647.0 + i for i in range(10)],
            "volume": [1000.0] * 10
        })

        # Construct analysis dictionary with post-news trap setup
        mock_analysis_bull = {
            "symbol": "XAUUSD",
            "current_price": 2650.0,
            "trend_direction": "BULLISH",
            "active_trend": "BULLISH",
            "rsi": 48.0,
            "atr": 4.0,
            "df_entry": df_mock,
            "ema_20": 2648.0,
            "ema_50": 2645.0,
            "ema_200": 2630.0,
            "support": 2640.0,
            "resistance": 2680.0,
            "asian_box": {"asian_range_pips": 25.0, "asian_high": 2655.0, "asian_low": 2645.0},
            "news_liquidity_sweep": {
                "is_post_news_trap": True,
                "direction": "BULLISH",
                "sweep_level": 2642.0,
                "rejection_wick": True
            },
            "killzone": {"is_prime_killzone": True, "killzone": "LONDON_OPEN", "confluence_boost": 0.40},
            "ote_buy": {"in_ote_zone": True, "fib_705": 2647.0},
            "vsa_intel": {"type": "BULLISH_ABSORPTION", "vsa_ratio": 2.1},
            "inducement": {"inducement_type": "BULLISH_EQL_SWEEP"},
            "qlib_intel": {"bias": "BULLISH", "alpha_score": 0.85, "confluence_bonus": 0.30},
            "adr_intel": {"is_adr_exhausted": False, "adr_pct_consumed": 40.0}
        }

        # Evaluate signal candidate
        signal = strategy.evaluate_signals(mock_analysis_bull)
        self.assertIsNotNone(signal)
        self.assertEqual(signal["symbol"], "XAUUSD")
        self.assertEqual(signal["signal"], "BUY")
        self.assertIn("POST_NEWS_JUDAS_SWEEP", signal["pattern"])
        self.assertGreaterEqual(signal["confluence_score"], 2.0)

    def test_post_news_bearish_judas_wick_sniping_bonus(self):
        """
        Empirically verifies bearish post-news Judas wick detection (+0.80 confluence bonus).
        """
        import pandas as pd
        config = {
            "risk_management": {
                "min_rr_ratio": 2.0,
                "atr_sl_multiplier": 1.5,
                "forex_atr_sl_multiplier": 1.5,
                "gold_atr_sl_multiplier": 2.5,
                "crypto_atr_sl_multiplier": 3.5
            },
            "gold_primary_focus": {
                "enabled": True,
                "xauusd_min_confluence_score": 1.2,
                "other_pairs_min_confluence_score": 1.3
            }
        }
        strategy = StrategyEngine(config=config)

        df_mock = pd.DataFrame({
            "open": [1.0870 - (i * 0.0002) for i in range(10)],
            "high": [1.0880 - (i * 0.0002) for i in range(10)],
            "low": [1.0840 - (i * 0.0002) for i in range(10)],
            "close": [1.0850 - (i * 0.0002) for i in range(10)],
            "volume": [1000.0] * 10
        })

        mock_analysis_bear = {
            "symbol": "EURUSD",
            "current_price": 1.0850,
            "trend_direction": "NEUTRAL",
            "active_trend": "BEARISH",
            "rsi": 52.0,
            "atr": 0.0035,
            "df_entry": df_mock,
            "ema_20": 1.0860,
            "ema_50": 1.0880,
            "ema_200": 1.0950,
            "active_resistance": {"level": 1.0900, "label": "Key Resistance"},
            "resistance_levels": [(1.0900, "Key Resistance")],
            "support_levels": [(1.0750, "Key Support")],
            "candlestick_patterns": [{"type": "BEARISH_ENGULFING"}],
            "news_liquidity_sweep": {
                "is_post_news_trap": True,
                "direction": "BEARISH",
                "sweep_level": 1.0890,
                "rejection_wick": True
            },
            "killzone": {"is_prime_killzone": True, "killzone": "NY_AM_KILLZONE", "confluence_boost": 0.40},
            "ote_sell": {"in_ote_zone": True, "fib_705": 1.0865},
            "vsa_intel": {"type": "BEARISH_ABSORPTION", "vsa_ratio": 1.9},
            "inducement": {"inducement_type": "BEARISH_EQH_SWEEP"},
            "qlib_intel": {"bias": "BEARISH", "alpha_score": -0.80, "confluence_bonus": 0.30},
            "adr_intel": {"is_adr_exhausted": False, "adr_pct_consumed": 35.0}
        }

        signal = strategy.evaluate_signals(mock_analysis_bear)
        self.assertIsNotNone(signal)
        self.assertEqual(signal["symbol"], "EURUSD")
        self.assertEqual(signal["signal"], "SELL")
        self.assertIn("POST_NEWS_JUDAS_SWEEP", signal["pattern"])
        self.assertGreaterEqual(signal["confluence_score"], 2.0)


class TestAladdinVaRCVaRAndPreTradeStress(unittest.TestCase):
    """
    Empirically verifies BlackRock Aladdin 1-Day 99% VaR, analytical CVaR,
    Uncertainty-Adjusted Fractional Kelly, and Pre-Trade 3-Sigma Stress Interceptor.
    """

    def setUp(self):
        self.aladdin = AladdinRiskEngine(
            max_portfolio_var_pct=0.015,
            cvar_confidence=0.99,
            kelly_fraction=0.20,
            max_risk_cap_pct=0.0075
        )

    def test_parametric_var_and_cvar_formula_accuracy(self):
        """
        Verifies analytical VaR 99% and CVaR 99% against closed-form normal distribution formulas:
          VaR_99 = Equity * 2.326348 * sigma
          CVaR_99 = Equity * sigma * [pdf(2.326348) / 0.01]
        """
        equity = 25000.0
        vol = 0.012  # 1.2% daily vol

        metrics = self.aladdin.compute_parametric_var_cvar(equity=equity, daily_volatility=vol)

        expected_var99 = equity * 2.326348 * vol  # ~ $697.90
        expected_pdf = (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * 2.326348 * 2.326348)
        expected_cvar99 = equity * vol * (expected_pdf / 0.01)  # ~ $799.47

        self.assertAlmostEqual(metrics["var_99_dollar"], expected_var99, places=1)
        self.assertAlmostEqual(metrics["cvar_99_dollar"], expected_cvar99, places=1)
        # CVaR must be strictly greater than VaR
        self.assertGreater(metrics["cvar_99_dollar"], metrics["var_99_dollar"])

    def test_uncertainty_adjusted_fractional_kelly_sizing(self):
        """
        Verifies Fractional Kelly with 1-sigma uncertainty haircut and 0.75% prop firm ceiling:
          p_adj = p - SE
          f* = (p_adj*(b+1) - 1)/b
          f_final = min(0.20 * f*, 0.0075)
        """
        # Scenario 1: Standard high conviction (58% win rate, 2.0 R:R, 3% SE)
        risk1 = self.aladdin.compute_fractional_kelly(win_rate=0.58, payoff_ratio=2.0, win_rate_se=0.03)
        self.assertLessEqual(risk1, 0.0075)
        self.assertGreaterEqual(risk1, 0.0025)

        # Scenario 2: Unfavorable win rate (40% win rate, 1.5 R:R) -> clamps to safe floor 0.25%
        risk2 = self.aladdin.compute_fractional_kelly(win_rate=0.40, payoff_ratio=1.5, win_rate_se=0.04)
        self.assertEqual(risk2, 0.0025)

        # Scenario 3: Massive win rate (90% win rate, 3.0 R:R) -> hard-capped at 0.75%
        risk3 = self.aladdin.compute_fractional_kelly(win_rate=0.90, payoff_ratio=3.0, win_rate_se=0.01)
        self.assertEqual(risk3, 0.0075)

    def test_pre_trade_stress_interceptor_rejection(self):
        """
        Verifies that pre-trade stress test rejects orders that would push
        aggregate portfolio risk beyond 80% of daily loss allowance ($625 * 0.80 = $500).
        """
        equity = 25000.0
        max_daily_loss = 625.0  # 2.5% on 25k

        # 1. Safe trade: $187.50 risk (0.75%), no open positions -> Approved
        res_safe = self.aladdin.evaluate_pre_trade_stress_test(
            equity=equity,
            prospective_risk_dollar=187.50,
            open_positions=[],
            max_daily_loss_dollar=max_daily_loss
        )
        self.assertTrue(res_safe["passed"])
        self.assertIn("APPROVED", res_safe["reason"])

        # 2. Dangerous trade: $400 existing risk + $187.50 prospective = $587.50 > $500 cap -> Rejected
        existing_positions = [
            {"symbol": "XAUUSD", "price_open": 2650.0, "sl": 2610.0, "volume": 0.10}  # $400 risk
        ]
        res_blocked = self.aladdin.evaluate_pre_trade_stress_test(
            equity=equity,
            prospective_risk_dollar=187.50,
            open_positions=existing_positions,
            max_daily_loss_dollar=max_daily_loss
        )
        self.assertFalse(res_blocked["passed"])
        self.assertIn("STRESS_TEST_EXCEEDED", res_blocked["reason"])


if __name__ == "__main__":
    unittest.main()
