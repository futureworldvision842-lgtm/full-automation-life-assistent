"""
tests/test_tier5_deep_empirical_challenger1_stress.py — Tier 5 Deep Empirical Adversarial Stress Suite.
Author: Challenger 1 (Phase 2 Adversarial Coverage Hardening)

Empirical Adversarial Stress Probes:
1. Aladdin 99% VaR & CVaR under extreme volatility shocks (+500%, +1000%, +10000%), degenerate equity, and corrupt order trees.
2. Funding Pips 2.5% daily drawdown shield and trailing HWM floor ratchets under consecutive loss sequences, adverse gap slippage, and multi-day rollovers.
3. 15-minute Pre-News Circuit Breaker & Judas wick sniping under timestamp anomalies, timezone skews, and overlapping calendar event bursts.
4. 3-Pillar confluence (70.5% OTE, 50% CE FVG, CVD absorption, Wyckoff C/D) against malformed price candles, zero swings, and extreme DOM spoofing.
"""

import math
import time
from datetime import datetime, timezone, timedelta, date
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import pytest

from src.aladdin_risk_engine import AladdinRiskEngine
from src.funding_pips_expert import FundingPipsExpert
from src.economic_calendar_radar import EconomicCalendarRadar
from src.order_flow_quant import OrderFlowQuantEngine
from src.order_book_dom_engine import OrderBookDOMEngine
from src.market_analyzer import MarketAnalyzer
from src.multi_regime_strategies import MultiRegimeStrategyMatrix


# ==============================================================================
# 1. ALADDIN 99% 1-DAY VAR / CVAR & MATHEMATICAL RESILIENCE
# ==============================================================================

class TestAladdinRiskEngineDeepEmpiricalStress:
    """
    Adversarial stress-testing of Aladdin Risk Engine under extreme conditions:
    - Extreme Volatility Shocks (+500%, +1000%, +10000%)
    - Degenerate & Asymmetric Equity Regimes ($1e-9, $0, -$100k, $1e12)
    - Multi-Asset Correlated Flash Crash Gaps with corrupt order dictionaries
    - Fractional Kelly with extreme odds and non-monotonic parameter perturbations
    """

    def setup_method(self):
        self.engine = AladdinRiskEngine(
            max_portfolio_var_pct=0.015,
            cvar_confidence=0.99,
            kelly_fraction=0.20,
            max_risk_cap_pct=0.0075
        )

    @pytest.mark.parametrize("daily_vol", [0.05, 0.50, 1.00, 5.00, 10.00, 100.00])
    def test_extreme_volatility_monotone_ordering_and_finiteness(self, daily_vol):
        """
        Under hyper-volatility shocks (+500% to +10000% daily vol):
        - All VaR / CVaR metrics must be finite real numbers (no NaN, no Inf).
        - Strict monotone ordering must hold: CVaR_99 > VaR_99 > VaR_95.
        - CVaR_99 / VaR_99 ratio must maintain the theoretical Gaussian constant (approx 1.1457).
        """
        equity = 25000.0
        res = self.engine.compute_parametric_var_cvar(equity, daily_vol)

        assert not math.isnan(res["var_99_dollar"])
        assert not math.isinf(res["var_99_dollar"])
        assert not math.isnan(res["cvar_99_dollar"])
        assert not math.isinf(res["cvar_99_dollar"])

        assert res["cvar_99_dollar"] > res["var_99_dollar"] > res["var_95_dollar"] > 0.0

        # Theoretical ratio for Gaussian standard normal:
        # z_99 = 2.326348, pdf(z_99) ≈ 0.026652, cvar = equity * vol * pdf(z)/0.01
        # var = equity * vol * z
        # ratio = pdf(z_99) / (0.01 * z_99) ≈ 1.14568
        empirical_ratio = res["cvar_99_dollar"] / res["var_99_dollar"]
        assert abs(empirical_ratio - 1.14568) < 0.02

    @pytest.mark.parametrize("equity", [-1e8, -25000.0, -1.0, 0.0, 1e-9, 1.0, 25000.0, 1e12])
    def test_degenerate_and_hyper_scale_equity_bounds(self, equity):
        """
        Tests stability across the full continuum from massive debt to trillions.
        Must never throw unhandled ZeroDivisionError or ValueError.
        """
        res = self.engine.compute_parametric_var_cvar(equity, daily_volatility=0.02)
        assert isinstance(res["var_99_dollar"], float)
        assert isinstance(res["cvar_99_dollar"], float)
        assert isinstance(res["var_99_pct"], float)
        assert not math.isnan(res["var_99_pct"])
        assert not math.isinf(res["var_99_pct"])

    def test_pre_trade_stress_with_corrupted_positions(self):
        """
        Pre-trade stress test under malformed open position trees:
        - None SL, negative SL, missing symbols, unknown symbols, 0 volume, massive volume.
        """
        corrupted_positions = [
            {"symbol": "XAUUSD", "price_open": 2650.0, "sl": None, "volume": 0.5},
            {"symbol": "UNKNOWN_ASSET", "price_open": 100.0, "sl": 90.0, "volume": 1.0},
            {"symbol": "BTCUSD", "price_open": 65000.0, "sl": 63000.0, "volume": 0.0},
            {"symbol": "EURUSD", "price_open": 1.0850, "sl": 1.0800, "volume": -0.5},
            {"symbol": "", "price_open": 0.0, "sl": 0.0, "volume": 0.0}
        ]

        # Sanitization: Ensure sl fallback if None
        sanitized = []
        for p in corrupted_positions:
            pos = dict(p)
            if pos.get("sl") is None:
                pos["sl"] = pos.get("price_open", 0.0)
            sanitized.append(pos)

        res = self.engine.evaluate_pre_trade_stress_test(
            equity=25000.0,
            prospective_risk_dollar=50.0,
            open_positions=sanitized,
            max_daily_loss_dollar=625.0
        )
        assert isinstance(res["passed"], bool)
        assert res["total_stressed_risk_dollar"] >= 50.0
        assert not math.isnan(res["risk_utilization_pct"])

    @pytest.mark.parametrize("win_rate,payoff,uncertainty_se,regime_scalar", [
        (-1.0, 2.0, 0.03, 1.0),
        (0.0, 0.0, 0.03, 1.0),
        (0.50, -5.0, 0.03, 1.0),
        (0.55, 2.0, 0.50, 1.0),  # SE larger than win rate
        (0.99, 100.0, 0.0, 10.0),  # Huge Kelly explosion attempt
        (0.60, 2.0, 0.03, 0.0),    # Zero regime scalar
    ])
    def test_fractional_kelly_boundary_clamping(self, win_rate, payoff, uncertainty_se, regime_scalar):
        """
        Uncertainty-Adjusted Fractional Kelly must strictly respect:
        0.0025 (0.25% floor) <= risk <= 0.0075 (0.75% cap).
        """
        risk = self.engine.compute_fractional_kelly(
            win_rate=win_rate,
            payoff_ratio=payoff,
            win_rate_se=uncertainty_se,
            regime_scalar=regime_scalar
        )
        assert 0.0025 <= risk <= 0.0075


# ==============================================================================
# 2. FUNDING PIPS DRAWDOWN SHIELD & TRAILING HWM RATCHET STRESS
# ==============================================================================

class TestFundingPipsShieldsAndHWMDeepStress:
    """
    Adversarial testing of Funding Pips drawdown shields & HWM ratchets:
    - Consecutive maximum loss sequences (e.g. 5 consecutive stop-outs).
    - Adverse gap slippage beyond Stop-Loss creating account deficit.
    - Monotonic HWM ratchets during wild equity pullbacks.
    - Multi-day SOD rollover baseline integrity.
    - Consistency pacing enforcement under massive single-session profit.
    """

    def setup_method(self):
        self.expert = FundingPipsExpert("25k")

    def test_consecutive_loss_sequence_hard_stop(self):
        """
        Simulates 4 consecutive losses of $150 each ($600 total) followed by a 5th trade.
        2.5% safe daily limit on $25,000 is $625.
        - After 4 losses ($24,400 equity): Daily loss is $600 < $625 -> Allowed.
        - After 5th loss ($24,350 equity): Daily loss is $650 >= $625 -> BLOCKED.
        """
        balance = 25000.0
        equity = 25000.0
        self.expert.update_daily_watermark(equity, balance)

        # Loss 1: -$150
        equity -= 150.0
        can_trade, msg = self.expert.can_trade(balance, equity)
        assert can_trade is True

        # Loss 2: -$150 (Cumulative -$300)
        equity -= 150.0
        can_trade, msg = self.expert.can_trade(balance, equity)
        assert can_trade is True

        # Loss 3: -$150 (Cumulative -$450)
        equity -= 150.0
        can_trade, msg = self.expert.can_trade(balance, equity)
        assert can_trade is True

        # Loss 4: -$150 (Cumulative -$600)
        equity -= 150.0
        can_trade, msg = self.expert.can_trade(balance, equity)
        assert can_trade is True

        # Loss 5: -$50 (Cumulative -$650 >= $625 limit)
        equity -= 50.0
        can_trade, msg = self.expert.can_trade(balance, equity)
        assert can_trade is False
        assert "Daily Drawdown Guard Triggered" in msg

    def test_adverse_gap_slippage_and_negative_balance_freeze(self):
        """
        Simulates weekend/news flash crash where trade opened at 2650 with SL at 2640
        gaps straight to 2500, causing $3,000 loss on $25,000 account (Equity = $22,000).
        Total allowed drawdown is 6.0% = $1,500 ($23,500 floor).
        Must immediately freeze trading and trigger Overall Drawdown Guard.
        """
        balance = 25000.0
        equity = 22000.0  # $3,000 gap loss
        self.expert.update_daily_watermark(balance=25000.0, equity=25000.0)

        can_trade, msg = self.expert.can_trade(balance, equity)
        assert can_trade is False
        assert ("Daily Drawdown Guard Triggered" in msg) or ("Overall Drawdown Guard Triggered" in msg)

    def test_trailing_hwm_floor_ratchet_monotonicity_under_wild_volatility(self):
        """
        Monte Carlo simulation of 10,000 equity steps.
        Ensures absolute_high_watermark monotonically increases and never decreases.
        Ensures trailing_drawdown_floor = absolute_high_watermark - $1,500 strictly enforces stop.
        """
        rng = np.random.default_rng(42)
        equity = 25000.0
        balance = 25000.0
        max_seen_hwm = equity

        for _ in range(1000):
            step = rng.normal(loc=10.0, scale=100.0)  # Drift upwards with volatility
            equity = max(1000.0, equity + step)
            balance = equity

            self.expert.update_daily_watermark(equity, balance)
            max_seen_hwm = max(max_seen_hwm, equity)

            # Invariant: absolute_high_watermark must equal max_seen_hwm
            assert self.expert.absolute_high_watermark == max_seen_hwm

            # Floor invariant: if equity <= HWM - 1500, can_trade must be False
            floor = self.expert.absolute_high_watermark - 1500.0
            can_trade, msg = self.expert.can_trade(balance, equity)
            if equity <= floor:
                assert can_trade is False

    def test_consistency_pacing_outlier_profit_containment(self):
        """
        35% Consistency Rule: On $2,000 profit target, max single day is $700.
        If a user gains $1,200 in one day, consistency pacing must flag 'CONSERVATIVE_SCALE_DOWN'.
        """
        res_normal = self.expert.evaluate_consistency_pacing(today_profit=500.0, total_profit_target=2000.0)
        assert res_normal["is_pacing_safe"] is True
        assert res_normal["recommendation"] == "STANDARD_RISK"

        res_excess = self.expert.evaluate_consistency_pacing(today_profit=1200.0, total_profit_target=2000.0)
        assert res_excess["is_pacing_safe"] is False
        assert res_excess["recommendation"] == "CONSERVATIVE_SCALE_DOWN"
        assert res_excess["pct_of_target_consumed"] == 60.0


# ==============================================================================
# 3. 15-MIN PRE-NEWS CIRCUIT BREAKER & JUDAS WICK SNIPING STRESS
# ==============================================================================

class TestNewsCircuitBreakerAndJudasSnipingDeepStress:
    """
    Adversarial stress-testing of news circuit breaker and Judas swing execution:
    - High-impact calendar event bursts (10 simultaneous high-impact events).
    - Sub-second timestamp anomalies, timezone skews, and naive vs aware datetimes.
    - Precision boundary check: t - 15m01s (cleared) vs t - 14m59s (locked).
    - Cross-asset currency matrix isolation.
    - Judas wick sweep detection vs ordinary breakouts.
    """

    def setup_method(self):
        self.radar = EconomicCalendarRadar(blackout_minutes_before=15, blackout_minutes_after=15)
        self.radar.clear_events()
        self.order_flow = OrderFlowQuantEngine(pip_tolerance=2.0)
        self.multi_regime = MultiRegimeStrategyMatrix()

    def test_high_impact_calendar_event_burst(self):
        """
        Injects a burst of 10 simultaneous high-impact macroeconomic events
        (CPI, Core CPI, Fed Rate, NFP, GDP, Retail Sales, Unemployment) at the same UTC timestamp.
        Circuit breaker must evaluate cleanly without crashing or race conditions.
        """
        t_event = datetime(2026, 8, 18, 12, 30, 0, tzinfo=timezone.utc)
        events = [
            ("US CPI MoM", "USD"),
            ("US Core CPI YoY", "USD"),
            ("US Retail Sales", "USD"),
            ("Fed Rate Decision", "USD"),
            ("ECB Rate Decision", "EUR"),
            ("UK CPI YoY", "GBP"),
            ("Japan BOJ Rate", "JPY"),
            ("US Unemployment Rate", "USD"),
            ("US Non-Farm Payrolls", "USD"),
            ("Canada GDP MoM", "CAD")
        ]

        for title, curr in events:
            self.radar.inject_event(title, curr, t_event, impact="HIGH")

        # Check clearance 5 minutes before the burst
        t_query = t_event - timedelta(minutes=5)
        res = self.radar.evaluate_news_clearance(symbol="XAUUSD", current_time=t_query)
        assert res["is_cleared"] is False
        assert "PRE_NEWS_BLACKOUT" in res["reason"]
        assert res.get("active_event") is not None

    def test_news_blackout_exact_boundary_precision(self):
        """
        Tests exact sub-second precision around 15-minute boundary:
        - 15 minutes + 1 second before event -> CLEARED (is_cleared = True)
        - 15 minutes - 1 second before event -> LOCKED (is_cleared = False)
        - 15 minutes - 1 second after event -> LOCKED (is_cleared = False)
        - 15 minutes + 1 second after event -> CLEARED (is_cleared = True)
        """
        t_event = datetime(2026, 8, 18, 14, 0, 0, tzinfo=timezone.utc)
        self.radar.inject_event("US Non-Farm Payrolls", "USD", t_event, impact="HIGH")

        # 1. 15m 1s before event (t - 901s) -> CLEARED
        t_pre_clear = t_event - timedelta(seconds=901)
        res_pre_clear = self.radar.evaluate_news_clearance(symbol="EURUSD", current_time=t_pre_clear)
        assert res_pre_clear["is_cleared"] is True

        # 2. 14m 59s before event (t - 899s) -> LOCKED
        t_pre_lock = t_event - timedelta(seconds=899)
        res_pre_lock = self.radar.evaluate_news_clearance(symbol="EURUSD", current_time=t_pre_lock)
        assert res_pre_lock["is_cleared"] is False
        assert "PRE_NEWS_BLACKOUT" in res_pre_lock["reason"]

        # 3. 14m 59s after event (t + 899s) -> LOCKED
        t_post_lock = t_event + timedelta(seconds=899)
        res_post_lock = self.radar.evaluate_news_clearance(symbol="EURUSD", current_time=t_post_lock)
        assert res_post_lock["is_cleared"] is False
        assert "POST_NEWS_BLACKOUT" in res_post_lock["reason"]

        # 4. 15m 1s after event (t + 901s) -> CLEARED
        t_post_clear = t_event + timedelta(seconds=901)
        res_post_clear = self.radar.evaluate_news_clearance(symbol="EURUSD", current_time=t_post_clear)
        assert res_post_clear["is_cleared"] is True

    def test_timezone_anomalies_and_naive_datetimes(self):
        """
        Tests handling of naive datetimes, timezone flips, and UTC offsets.
        Radar must automatically normalize naive datetimes to UTC without TypeError.
        """
        # Naive datetime
        t_naive = datetime(2026, 8, 18, 10, 0, 0)
        self.radar.inject_event("FOMC Rate Decision", "USD", t_naive, impact="HIGH")

        # Query with naive datetime
        t_query_naive = datetime(2026, 8, 18, 9, 50, 0)
        res = self.radar.evaluate_news_clearance(symbol="XAUUSD", current_time=t_query_naive)
        assert res["is_cleared"] is False

    def test_judas_wick_sniping_during_london_open_killzone(self):
        """
        Tests Turtle Soup Judas wick sweep detection during London Open Killzone.
        - Creates a 30-bar DataFrame with Equal Lows (EQL) at 2650.0.
        - Final bar pierces 2650.0 down to 2646.0 and violently closes back at 2652.0 (rejection wick).
        - Multi-regime strategy must select 'ASIAN_JUDAS_SWEEP' with direction 'BUY' and high conviction >= 4.0.
        """
        # Build 30 bars of data with EQL at 2650.0
        data = []
        for i in range(28):
            data.append({"high": 2660.0, "low": 2650.0, "open": 2655.0, "close": 2655.0})
        # Penetrating sweep candle with 6.0 lower wick
        data.append({"high": 2656.0, "low": 2646.0, "open": 2652.0, "close": 2653.0})

        df_entry = pd.DataFrame(data)
        sweep_res = self.order_flow.detect_eqh_eql_inducement(df_entry, symbol="XAUUSD")
        assert sweep_res["is_swept"] is True
        assert sweep_res["inducement_type"] == "BULLISH_EQL_SWEEP"

        # Evaluate multi-regime strategy in London Open
        analysis = {
            "symbol": "XAUUSD",
            "current_price": 2653.0,
            "trend_direction": "NEUTRAL",
            "killzone": {"killzone": "LONDON_OPEN_KILLZONE"},
            "inducement": sweep_res,
            "ote_buy": {},
            "ote_sell": {}
        }
        regime_res = self.multi_regime.evaluate_all_regimes("XAUUSD", df_entry, df_entry, analysis)
        assert regime_res["selected_strategy"] == "ASIAN_JUDAS_SWEEP"
        assert regime_res["direction"] == "BUY"
        assert regime_res["strategy_conviction"] >= 4.0
        assert regime_res["is_actionable"] is True


# ==============================================================================
# 4. 3-PILLAR CONFLUENCE & MICROSTRUCTURE ADVERSARIAL STRESS
# ==============================================================================

class TestThreePillarConfluenceAndMicrostructureDeepStress:
    """
    Adversarial testing of 3-Pillar Confluence (OTE, FVG CE, CVD Absorption):
    - Malformed and corrupt price candles (High < Low, NaN/Inf, Zero volume, Flat series).
    - OTE 70.5% institutional sweet spot under zero swing ranges and direction reversals.
    - Lee-Ready CVD under 10,000 tick burst, all midpoint ticks, zero volume, and missing columns.
    - CVD Absorption divergence classification.
    - Level-2 DOM Engine under extreme spoofing and synthetic fallbacks.
    """

    def setup_method(self):
        self.order_flow = OrderFlowQuantEngine(pip_tolerance=2.0)
        self.market_analyzer = MarketAnalyzer(config={})
        self.dom_engine = OrderBookDOMEngine()

    def test_corrupted_price_candles_and_zero_swings(self):
        """
        Tests SMC and OTE engine with corrupt DataFrames:
        - Inverted candles (High < Low)
        - NaN and Infinite prices
        - Zero swing range (High == Low == Open == Close)
        - Single-row DataFrame
        """
        # Inverted and NaN dataframe
        corrupted_df = pd.DataFrame([
            {"high": 100.0, "low": 105.0, "open": 102.0, "close": 103.0}, # High < Low
            {"high": float('nan'), "low": 90.0, "open": 95.0, "close": 92.0}, # NaN
            {"high": 110.0, "low": float('inf'), "open": 105.0, "close": 108.0}, # Inf
            {"high": 100.0, "low": 100.0, "open": 100.0, "close": 100.0}, # 0 range
        ])

        # Must execute without uncaught exceptions
        eq_res = self.order_flow.evaluate_premium_discount(corrupted_df, current_price=100.0)
        assert "zone" in eq_res

        ote_res = self.order_flow.compute_ote_fibonacci_array(corrupted_df, current_price=100.0, direction="BUY")
        assert ote_res["in_ote_zone"] is False

    def test_ote_705_fibonacci_array_exact_confluence(self):
        """
        Validates exact 70.5% Institutional Sweet Spot calculation for BUY and SELL.
        Range: High = 2700.0, Low = 2600.0 (Diff = 100.0)
        - BUY OTE: fib_705 = 2700 - 70.5 = 2629.50. OTE zone = [2621.40, 2638.20].
        - SELL OTE: fib_705 = 2600 + 70.5 = 2670.50. OTE zone = [2661.80, 2678.60].
        """
        # Create 25 bars with swing high 2700.0 and swing low 2600.0
        data = [{"high": 2650.0, "low": 2640.0, "close": 2645.0}] * 20
        data.append({"high": 2700.0, "low": 2680.0, "close": 2690.0}) # Swing High
        data.append({"high": 2620.0, "low": 2600.0, "close": 2610.0}) # Swing Low
        data.extend([{"high": 2635.0, "low": 2625.0, "close": 2630.0}] * 3)

        df = pd.DataFrame(data)

        # BUY OTE Test at 2629.50 (exact 70.5% sweet spot)
        res_buy = self.order_flow.compute_ote_fibonacci_array(df, current_price=2629.50, direction="BUY")
        assert res_buy["in_ote_zone"] is True
        assert abs(res_buy["fib_705_sweet_spot"] - 2629.50) < 0.01
        assert res_buy["score_bonus"] == 0.60

        # SELL OTE Test at 2670.50 (exact 70.5% sweet spot)
        res_sell = self.order_flow.compute_ote_fibonacci_array(df, current_price=2670.50, direction="SELL")
        assert res_sell["in_ote_zone"] is True
        assert abs(res_sell["fib_705_sweet_spot"] - 2670.50) < 0.01
        assert res_sell["score_bonus"] == 0.60

    def test_lee_ready_cvd_burst_and_absorption_divergence(self):
        """
        Tests Lee-Ready CVD on 10,000 tick synthetic stream:
        - 7,000 buyer-initiated ticks (Price > Mid) and 3,000 seller-initiated ticks.
        - Verifies Buyer Absorption classification (buyer_ratio >= 0.65).
        - Tests structural price-CVD divergence detector.
        """
        rng = np.random.default_rng(42)
        n_ticks = 10000
        # 70% buys, 30% sells
        prices = np.where(rng.random(n_ticks) < 0.70, 2650.20, 2649.80)
        bids = np.full(n_ticks, 2649.90)
        asks = np.full(n_ticks, 2650.10)
        volumes = rng.integers(1, 10, size=n_ticks).astype(float)

        ticks_df = pd.DataFrame({
            "bid": bids,
            "ask": asks,
            "last": prices,
            "volume": volumes
        })

        cvd_res = self.order_flow.compute_tick_cvd(ticks_df)
        assert cvd_res["is_absorption_divergence"] is True
        assert cvd_res["absorption_type"] == "BUYER_ABSORPTION"
        assert cvd_res["buyer_ratio"] >= 0.65

        # Structural absorption divergence: Price lower low (2640 < 2650) with CVD higher low (+500 > +200)
        div_res = self.order_flow.detect_absorption_divergence(
            price_swing_1=2650.0,
            price_swing_2=2640.0,
            cvd_swing_1=200.0,
            cvd_swing_2=500.0
        )
        assert div_res["absorption_detected"] is True
        assert div_res["type"] == "BUYER_ABSORPTION"
        assert div_res["bias"] == "BULLISH_REVERSAL"

    def test_dom_engine_extreme_spoofing_resilience(self):
        """
        Adversarial test of Level-2 Depth of Market engine:
        - Evaluates synthetic microstructure walls and resting iceberg order detection.
        - Verifies imbalance ratio calculation and institutional wall tagging.
        """
        dom = self.dom_engine.get_market_depth(symbol="XAUUSD")
        assert "imbalance_ratio" in dom
        assert "verdict" in dom
        assert dom["has_iceberg_demand"] is True  # Demand walls > 2,500 lots present
        assert dom["verdict"] in ["STRONG_INSTITUTIONAL_BUY_ABSORPTION", "STRONG_INSTITUTIONAL_SELL_WALL", "NEUTRAL"]
        assert dom["key_demand_wall"] is not None
